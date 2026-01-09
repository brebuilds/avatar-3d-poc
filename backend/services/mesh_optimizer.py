"""
3D mesh optimization service.
Cleans, repairs, scales, and optimizes meshes for 3D printing.
"""
import trimesh
import pymeshlab
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class MeshOptimizer:
    """Optimize 3D meshes for FDM printing."""

    def __init__(self):
        """Initialize mesh optimizer."""
        pass

    def optimize_for_printing(
        self,
        input_path: Path,
        output_path: Path,
        target_height_mm: float = 80.0,
        printer_profile: str = "ender3v2",
        fix_holes: bool = True,
        simplify: bool = True,
        max_faces: int = 100000
    ) -> Dict[str, Any]:
        """
        Optimize mesh for 3D printing.

        Args:
            input_path: Path to input GLB/OBJ file
            output_path: Path to save optimized STL
            target_height_mm: Target height in millimeters
            printer_profile: Printer profile name
            fix_holes: Whether to attempt hole filling
            simplify: Whether to simplify if too dense
            max_faces: Maximum face count before simplification

        Returns:
            Dict with optimization results
        """
        try:
            print(f"Loading mesh from: {input_path}")

            # Load mesh with trimesh
            mesh = trimesh.load(str(input_path), force='mesh')

            if isinstance(mesh, trimesh.Scene):
                # Extract the first mesh from the scene
                mesh = list(mesh.geometry.values())[0]

            original_stats = self._get_mesh_stats(mesh)
            print(f"Original mesh: {original_stats['vertex_count']} vertices, "
                  f"{original_stats['face_count']} faces")

            # Step 1: Check if watertight (manifold)
            is_watertight = mesh.is_watertight

            if not is_watertight and fix_holes:
                print("Mesh is not watertight. Attempting repair...")
                mesh = self._repair_mesh(input_path)
                if mesh is None:
                    return {
                        "success": False,
                        "message": "Mesh repair failed"
                    }

            # Step 2: Remove duplicate vertices
            mesh.merge_vertices()

            # Step 3: Simplify if too dense
            if simplify and len(mesh.faces) > max_faces:
                print(f"Simplifying mesh from {len(mesh.faces)} to ~{max_faces} faces")
                mesh = mesh.simplify_quadric_decimation(max_faces)

            # Step 4: Scale to target height
            mesh = self._scale_mesh(mesh, target_height_mm)

            # Step 5: Center on build plate (Z=0 at bottom)
            mesh = self._center_mesh(mesh)

            # Step 6: Ensure correct normals
            mesh.fix_normals()

            # Step 7: Export as STL
            mesh.export(str(output_path))
            print(f"Optimized mesh saved: {output_path}")

            # Get final stats
            final_stats = self._get_mesh_stats(mesh)

            return {
                "success": True,
                "output_path": str(output_path),
                "message": "Mesh optimized successfully",
                "original_stats": original_stats,
                "final_stats": final_stats,
                "was_repaired": not is_watertight and fix_holes,
                "was_simplified": len(mesh.faces) < original_stats['face_count']
            }

        except Exception as e:
            error_msg = f"Mesh optimization failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "output_path": None
            }

    def _repair_mesh(self, mesh_path: Path) -> Optional[trimesh.Trimesh]:
        """Repair mesh using PyMeshLab."""
        try:
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(str(mesh_path))

            # Close holes
            ms.meshing_close_holes(maxholesize=30)

            # Remove duplicate vertices
            ms.meshing_remove_duplicate_vertices()

            # Remove non-manifold edges
            ms.meshing_remove_t_vertices(method=0)

            # Rebuild the mesh
            ms.meshing_re_orient_faces_coherently()

            # Export to temporary OBJ
            temp_path = mesh_path.parent / "temp_repaired.obj"
            ms.save_current_mesh(str(temp_path))

            # Load with trimesh
            mesh = trimesh.load(str(temp_path), force='mesh')

            # Clean up temp file
            temp_path.unlink()

            return mesh

        except Exception as e:
            print(f"Mesh repair error: {str(e)}")
            return None

    def _scale_mesh(self, mesh: trimesh.Trimesh, target_height_mm: float) -> trimesh.Trimesh:
        """Scale mesh to target height in millimeters."""
        # Get current dimensions
        bounds = mesh.bounds
        current_height = bounds[1][2] - bounds[0][2]  # Z dimension

        # Calculate scale factor
        scale_factor = target_height_mm / current_height

        # Apply scale
        mesh.apply_scale(scale_factor)

        print(f"Scaled mesh from {current_height:.2f} to {target_height_mm:.2f}mm "
              f"(scale: {scale_factor:.3f}x)")

        return mesh

    def _center_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Center mesh on XY plane with bottom at Z=0."""
        # Get bounds
        bounds = mesh.bounds

        # Calculate translation to center XY and place bottom at Z=0
        center_x = (bounds[0][0] + bounds[1][0]) / 2
        center_y = (bounds[0][1] + bounds[1][1]) / 2
        bottom_z = bounds[0][2]

        translation = np.array([-center_x, -center_y, -bottom_z])

        # Apply translation
        mesh.apply_translation(translation)

        print(f"Centered mesh (translation: {translation})")

        return mesh

    def _get_mesh_stats(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Get mesh statistics."""
        bounds = mesh.bounds
        dimensions = bounds[1] - bounds[0]

        return {
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.faces),
            "is_watertight": mesh.is_watertight,
            "volume": float(mesh.volume) if mesh.is_watertight else None,
            "dimensions": {
                "x": float(dimensions[0]),
                "y": float(dimensions[1]),
                "z": float(dimensions[2])
            },
            "bounds": {
                "min": [float(x) for x in bounds[0]],
                "max": [float(x) for x in bounds[1]]
            }
        }

    def validate_mesh(self, mesh_path: Path) -> Tuple[bool, str]:
        """
        Validate a mesh file for printing.

        Args:
            mesh_path: Path to mesh file

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        try:
            mesh = trimesh.load(str(mesh_path), force='mesh')

            # Check vertex count
            if len(mesh.vertices) < 4:
                return False, "Mesh has too few vertices"

            # Check face count
            if len(mesh.faces) < 4:
                return False, "Mesh has too few faces"

            # Check if watertight
            if not mesh.is_watertight:
                return False, "Mesh is not watertight (has holes)"

            # Check bounds are reasonable
            bounds = mesh.bounds
            dimensions = bounds[1] - bounds[0]

            if any(d <= 0 for d in dimensions):
                return False, "Mesh has invalid dimensions"

            return True, "Mesh is valid for printing"

        except Exception as e:
            return False, f"Mesh validation error: {str(e)}"
