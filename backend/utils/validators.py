"""
Input validation utilities for avatar processing.
"""
from pathlib import Path
from typing import Tuple
from PIL import Image
import os

# Supported file types
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE_MB = 10
MIN_IMAGE_DIMENSION = 512  # pixels
MAX_IMAGE_DIMENSION = 4096  # pixels


def validate_image_file(
    filepath: Path,
    check_size: bool = True,
    check_dimensions: bool = True
) -> Tuple[bool, str]:
    """
    Validate an uploaded image file.

    Args:
        filepath: Path to the image file
        check_size: Whether to check file size limits
        check_dimensions: Whether to check image dimensions

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    # Check file exists
    if not filepath.exists():
        return False, "File does not exist"

    # Check file extension
    if filepath.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        return False, (
            f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Check file size
    if check_size:
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return False, f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)"

    # Check image can be opened and validate dimensions
    try:
        with Image.open(filepath) as img:
            width, height = img.size

            if check_dimensions:
                if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                    return False, (
                        f"Image too small: {width}x{height}px "
                        f"(min {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}px)"
                    )

                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    return False, (
                        f"Image too large: {width}x{height}px "
                        f"(max {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}px)"
                    )

            # Check if RGB or RGBA
            if img.mode not in ['RGB', 'RGBA']:
                return False, f"Unsupported image mode: {img.mode} (need RGB or RGBA)"

    except Exception as e:
        return False, f"Failed to read image: {str(e)}"

    return True, "Image file is valid"


def validate_job_id(job_id: str) -> Tuple[bool, str]:
    """
    Validate a job ID format.

    Args:
        job_id: The job ID to validate

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not job_id:
        return False, "Job ID cannot be empty"

    # Job IDs should be alphanumeric with hyphens
    if not all(c.isalnum() or c in ['-', '_'] for c in job_id):
        return False, "Job ID contains invalid characters"

    if len(job_id) < 8 or len(job_id) > 64:
        return False, "Job ID must be between 8 and 64 characters"

    return True, "Valid job ID"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove potentially dangerous characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove special characters, keep alphanumeric, dots, hyphens, underscores
    sanitized = ''.join(
        c if c.isalnum() or c in ['.', '-', '_'] else '_'
        for c in filename
    )

    # Ensure it has an extension
    if '.' not in sanitized:
        sanitized += '.jpg'

    return sanitized


def ensure_directory(dirpath: Path) -> None:
    """
    Ensure a directory exists, create if it doesn't.

    Args:
        dirpath: Path to the directory
    """
    dirpath.mkdir(parents=True, exist_ok=True)


__all__ = [
    'validate_image_file',
    'validate_job_id',
    'sanitize_filename',
    'ensure_directory',
    'ALLOWED_IMAGE_EXTENSIONS',
    'MAX_FILE_SIZE_MB'
]
