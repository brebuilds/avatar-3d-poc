"""
Avatar generation pipeline orchestrator.
Coordinates all processing steps from photo to 3D printable model.
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from services.face_detector import FaceDetector
from services.cartoonizer import Cartoonizer
from services.three_d_generator import ThreeDGenerator
from services.mesh_optimizer import MeshOptimizer


class AvatarPipeline:
    """
    Orchestrates the complete avatar generation pipeline.

    Pipeline steps:
    1. Face Detection - Validate photo has a clear face
    2. Cartoonization - Transform to Pixar style
    3. 3D Generation - Convert 2D to 3D model
    4. Mesh Optimization - Repair, scale, and prepare for printing
    """

    def __init__(
        self,
        output_dir: Path = Path("output"),
        target_height_mm: float = 80.0,
        printer_profile: str = "ender3v2"
    ):
        """
        Initialize pipeline with services.

        Args:
            output_dir: Base directory for output files
            target_height_mm: Target avatar height in mm
            printer_profile: Printer profile to use
        """
        self.output_dir = Path(output_dir)
        self.target_height_mm = target_height_mm
        self.printer_profile = printer_profile

        # Ensure output directories exist
        for subdir in ["uploads", "cartoonized", "models_3d", "stl_files"]:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Initialize services
        self.face_detector = FaceDetector()
        self.cartoonizer = Cartoonizer()
        self.three_d_generator = ThreeDGenerator()
        self.mesh_optimizer = MeshOptimizer()

    def process_avatar(
        self,
        input_path: Path,
        job_id: str,
        status_callback: Optional[Callable[[str, dict], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a photo through the complete pipeline.

        Args:
            input_path: Path to input photo
            job_id: Unique job identifier
            status_callback: Optional callback for status updates

        Returns:
            Dict with processing results
        """
        start_time = time.time()

        def update_status(step: str, data: dict):
            """Helper to update status."""
            if status_callback:
                status_callback(step, data)
            print(f"[{job_id}] {step}: {data.get('message', '')}")

        try:
            # Define output paths
            cartoon_path = self.output_dir / "cartoonized" / f"{job_id}_cartoon.png"
            model_3d_path = self.output_dir / "models_3d" / f"{job_id}_model.glb"
            stl_path = self.output_dir / "stl_files" / f"{job_id}_avatar.stl"

            results = {
                "job_id": job_id,
                "input_path": str(input_path),
                "start_time": datetime.now().isoformat(),
                "steps": {}
            }

            # Step 1: Face Detection
            update_status("face_detection", {"message": "Detecting face...", "progress": 0})
            face_start = time.time()

            face_result = self.face_detector.detect_face(input_path)
            results["steps"]["face_detection"] = {
                **face_result,
                "duration": time.time() - face_start
            }

            if not face_result["success"]:
                update_status("failed", {"message": face_result["message"]})
                return {**results, "success": False, "error": face_result["message"]}

            update_status("face_detection", {
                "message": "Face detected successfully!",
                "progress": 20,
                **face_result
            })

            # Step 2: Cartoonization
            update_status("cartoonization", {
                "message": "Creating Pixar-style cartoon (30-60s)...",
                "progress": 20
            })
            cartoon_start = time.time()

            cartoon_result = self.cartoonizer.cartoonize(
                input_path,
                cartoon_path,
                style="pixar"
            )
            results["steps"]["cartoonization"] = {
                **cartoon_result,
                "duration": time.time() - cartoon_start
            }

            if not cartoon_result["success"]:
                update_status("failed", {"message": cartoon_result["message"]})
                return {**results, "success": False, "error": cartoon_result["message"]}

            update_status("cartoonization", {
                "message": "Cartoonization complete!",
                "progress": 40,
                "cartoon_path": str(cartoon_path)
            })

            # Step 3: 3D Generation
            update_status("3d_generation", {
                "message": "Generating 3D model (2-3 minutes)...",
                "progress": 40
            })
            model_start = time.time()

            model_result = self.three_d_generator.generate_3d_model(
                cartoon_path,
                model_3d_path,
                timeout=300
            )
            results["steps"]["3d_generation"] = {
                **model_result,
                "duration": time.time() - model_start
            }

            if not model_result["success"]:
                update_status("failed", {"message": model_result["message"]})
                return {**results, "success": False, "error": model_result["message"]}

            update_status("3d_generation", {
                "message": "3D model generated!",
                "progress": 80,
                "model_path": str(model_3d_path)
            })

            # Step 4: Mesh Optimization
            update_status("optimization", {
                "message": "Optimizing mesh for printing...",
                "progress": 80
            })
            optimize_start = time.time()

            optimize_result = self.mesh_optimizer.optimize_for_printing(
                model_3d_path,
                stl_path,
                target_height_mm=self.target_height_mm,
                printer_profile=self.printer_profile
            )
            results["steps"]["optimization"] = {
                **optimize_result,
                "duration": time.time() - optimize_start
            }

            if not optimize_result["success"]:
                update_status("failed", {"message": optimize_result["message"]})
                return {**results, "success": False, "error": optimize_result["message"]}

            update_status("completed", {
                "message": "Avatar ready for printing!",
                "progress": 100,
                "stl_path": str(stl_path)
            })

            # Final results
            total_duration = time.time() - start_time

            return {
                **results,
                "success": True,
                "output_files": {
                    "cartoon": str(cartoon_path),
                    "model_3d": str(model_3d_path),
                    "stl": str(stl_path)
                },
                "total_duration": total_duration,
                "end_time": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            update_status("failed", {"message": error_msg})
            return {
                **results,
                "success": False,
                "error": error_msg,
                "total_duration": time.time() - start_time
            }

    def get_status_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a simplified status summary from pipeline results.

        Args:
            results: Pipeline results dict

        Returns:
            Simplified status dict
        """
        if not results.get("success"):
            return {
                "status": "failed",
                "message": results.get("error", "Processing failed"),
                "progress": 0
            }

        steps = results.get("steps", {})
        completed_steps = sum(1 for s in steps.values() if s.get("success"))
        total_steps = 4

        progress = int((completed_steps / total_steps) * 100)

        current_step = None
        if completed_steps < total_steps:
            step_names = ["face_detection", "cartoonization", "3d_generation", "optimization"]
            current_step = step_names[completed_steps]

        return {
            "status": "completed" if completed_steps == total_steps else "processing",
            "progress": progress,
            "current_step": current_step,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "total_duration": results.get("total_duration"),
            "output_files": results.get("output_files")
        }
