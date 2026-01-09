"""
3D model generation service using Meshy.ai API.
Converts 2D cartoonized images to 3D models.
"""
import os
import requests
import time
import base64
from pathlib import Path
from typing import Optional, Dict, Any


class ThreeDGenerator:
    """Generate 3D models from 2D images using Meshy.ai."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Meshy.ai client.

        Args:
            api_key: Meshy.ai API key (or from MESHY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("MESHY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MESHY_API_KEY not found. "
                "Set environment variable or pass as argument."
            )

        self.base_url = "https://api.meshy.ai/openapi/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_3d_model(
        self,
        image_path: Path,
        output_path: Path,
        timeout: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Generate 3D model from cartoonized image.

        Args:
            image_path: Path to cartoonized image
            output_path: Path to save GLB model
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between status checks

        Returns:
            Dict with:
                - success: bool
                - output_path: str (if successful)
                - task_id: str
                - message: str
                - model_url: str (if successful)
                - thumbnail_url: str (if successful)
        """
        try:
            # Step 1: Create task with base64 encoded image
            print(f"Creating 3D generation task for: {image_path}")

            # Encode image to base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Create 3D generation task directly
            task_response = self._create_task(image_data)
            if not task_response["success"]:
                return task_response

            task_id = task_response["task_id"]
            print(f"3D generation task created: {task_id}")

            # Step 2: Poll for completion
            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    return {
                        "success": False,
                        "task_id": task_id,
                        "message": f"3D generation timed out after {timeout}s",
                        "output_path": None
                    }

                # Check status
                status_result = self._check_status(task_id)

                if status_result["status"] == "SUCCEEDED":
                    # Download the GLB model
                    model_url = status_result["model_url"]
                    print(f"Downloading 3D model from: {model_url}")

                    model_response = requests.get(model_url, timeout=60)
                    model_response.raise_for_status()

                    # Save GLB file
                    with open(output_path, "wb") as f:
                        f.write(model_response.content)

                    print(f"3D model saved: {output_path}")

                    return {
                        "success": True,
                        "output_path": str(output_path),
                        "task_id": task_id,
                        "message": "3D model generated successfully",
                        "model_url": model_url,
                        "thumbnail_url": status_result.get("thumbnail_url")
                    }

                elif status_result["status"] == "FAILED":
                    return {
                        "success": False,
                        "task_id": task_id,
                        "message": f"3D generation failed: {status_result.get('error', 'Unknown error')}",
                        "output_path": None
                    }

                elif status_result["status"] in ["PENDING", "IN_PROGRESS"]:
                    progress = status_result.get("progress", 0)
                    print(f"3D generation in progress: {progress}% (elapsed: {int(elapsed)}s)")
                    time.sleep(poll_interval)

                else:
                    # Unknown status
                    print(f"Unknown status: {status_result['status']}")
                    time.sleep(poll_interval)

        except Exception as e:
            error_msg = f"3D generation error: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "output_path": None,
                "task_id": None
            }

    def _create_task(self, image_base64: str) -> Dict[str, Any]:
        """Create 3D generation task with base64 encoded image."""
        try:
            payload = {
                "mode": "preview",
                "image_base64": f"data:image/png;base64,{image_base64}",
                "enable_pbr": False
            }

            response = requests.post(
                f"{self.base_url}/image-to-3d",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "message": f"Task creation failed: {response.text}"
                }

            data = response.json()
            return {
                "success": True,
                "task_id": data["id"]
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Task creation error: {str(e)}"
            }

    def _check_status(self, task_id: str) -> Dict[str, Any]:
        """Check task status."""
        try:
            response = requests.get(
                f"{self.base_url}/image-to-3d-tasks/{task_id}",
                headers=self.headers,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    "status": "FAILED",
                    "error": response.text
                }

            data = response.json()
            return {
                "status": data["status"],
                "progress": data.get("progress", 0),
                "model_url": data.get("model_urls", {}).get("glb"),
                "thumbnail_url": data.get("thumbnail_url"),
                "error": data.get("error")
            }

        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
