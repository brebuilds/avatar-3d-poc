"""
Face detection service using MediaPipe.
Validates uploaded images contain a clear, detectable face.
"""
import cv2
import numpy as np
import mediapipe as mp
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image


class FaceDetector:
    """Face detection and validation using MediaPipe Face Mesh."""

    def __init__(self):
        """Initialize MediaPipe Face Mesh."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

    def detect_face(self, image_path: Path) -> Dict[str, Any]:
        """
        Detect face in an image and return landmarks.

        Args:
            image_path: Path to the image file

        Returns:
            Dict containing:
                - success: bool
                - landmarks: list of facial landmarks (if successful)
                - face_found: bool
                - face_count: int
                - message: str
                - bounding_box: dict with {x_min, y_min, x_max, y_max}

        Raises:
            ValueError: If image cannot be read
        """
        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, _ = image_rgb.shape

        # Process image
        results = self.face_mesh.process(image_rgb)

        # Check if face detected
        if not results.multi_face_landmarks:
            return {
                "success": False,
                "face_found": False,
                "face_count": 0,
                "landmarks": None,
                "bounding_box": None,
                "message": "No face detected in image. Please use a clear front-facing portrait."
            }

        # Get first face landmarks
        face_landmarks = results.multi_face_landmarks[0]

        # Convert normalized landmarks to pixel coordinates
        landmarks_px = []
        x_coords = []
        y_coords = []

        for landmark in face_landmarks.landmark:
            x_px = int(landmark.x * width)
            y_px = int(landmark.y * height)
            landmarks_px.append({"x": x_px, "y": y_px, "z": landmark.z})
            x_coords.append(x_px)
            y_coords.append(y_px)

        # Calculate bounding box
        bounding_box = {
            "x_min": min(x_coords),
            "y_min": min(y_coords),
            "x_max": max(x_coords),
            "y_max": max(y_coords),
            "width": max(x_coords) - min(x_coords),
            "height": max(y_coords) - min(y_coords)
        }

        # Check face size (should be reasonable portion of image)
        face_area_ratio = (bounding_box["width"] * bounding_box["height"]) / (width * height)

        if face_area_ratio < 0.05:
            return {
                "success": False,
                "face_found": True,
                "face_count": 1,
                "landmarks": landmarks_px,
                "bounding_box": bounding_box,
                "message": "Face is too small in image. Please use a closer portrait photo."
            }

        if face_area_ratio > 0.9:
            return {
                "success": False,
                "face_found": True,
                "face_count": 1,
                "landmarks": landmarks_px,
                "bounding_box": bounding_box,
                "message": "Face is too close. Please use a photo with some space around the face."
            }

        return {
            "success": True,
            "face_found": True,
            "face_count": 1,
            "landmarks": landmarks_px,
            "bounding_box": bounding_box,
            "face_area_ratio": face_area_ratio,
            "image_dimensions": {"width": width, "height": height},
            "message": "Face detected successfully!"
        }

    def crop_to_face(
        self,
        image_path: Path,
        output_path: Path,
        padding: float = 0.3
    ) -> bool:
        """
        Crop image to focus on detected face with padding.

        Args:
            image_path: Path to input image
            output_path: Path to save cropped image
            padding: Padding around face (0.3 = 30% extra space)

        Returns:
            True if successful, False otherwise
        """
        # Detect face first
        result = self.detect_face(image_path)
        if not result["success"]:
            return False

        # Load image
        image = Image.open(image_path)
        width, height = image.size

        # Get bounding box
        bbox = result["bounding_box"]

        # Calculate crop region with padding
        face_width = bbox["width"]
        face_height = bbox["height"]

        pad_x = int(face_width * padding)
        pad_y = int(face_height * padding)

        crop_left = max(0, bbox["x_min"] - pad_x)
        crop_top = max(0, bbox["y_min"] - pad_y)
        crop_right = min(width, bbox["x_max"] + pad_x)
        crop_bottom = min(height, bbox["y_max"] + pad_y)

        # Crop and save
        cropped = image.crop((crop_left, crop_top, crop_right, crop_bottom))
        cropped.save(output_path)

        return True

    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
