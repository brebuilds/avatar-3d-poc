"""
Printer profile management for 3D avatar optimization.
Defines build volumes and settings for supported FDM printers.
"""
import json
from pathlib import Path
from typing import Dict, Any

# Printer profiles with build volumes and recommended settings
PROFILES = {
    "ender3v2": {
        "name": "Creality Ender 3 V2",
        "bed_size": [220, 220, 250],  # mm [X, Y, Z]
        "nozzle_diameter": 0.4,
        "recommended_layer_height": 0.2,
        "max_model_height": 100,  # mm (conservative for avatars)
        "center_offset": [110, 110, 0],  # mm from origin
        "supports_needed": True,
        "base_thickness": 2.0,  # mm
        "notes": "Standard Ender 3 V2 profile with conservative build volume"
    },
    "biqu_b1": {
        "name": "BIQU B1",
        "bed_size": [235, 235, 270],  # mm [X, Y, Z]
        "nozzle_diameter": 0.4,
        "recommended_layer_height": 0.2,
        "max_model_height": 120,  # mm (conservative for avatars)
        "center_offset": [117.5, 117.5, 0],  # mm from origin
        "supports_needed": True,
        "base_thickness": 2.0,  # mm
        "notes": "BIQU B1 profile with slightly larger build volume than Ender 3"
    }
}


def get_profile(profile_name: str = "ender3v2") -> Dict[str, Any]:
    """
    Get printer profile by name.

    Args:
        profile_name: Name of the printer profile (ender3v2 or biqu_b1)

    Returns:
        Dict containing printer specifications

    Raises:
        ValueError: If profile_name is not found
    """
    if profile_name not in PROFILES:
        raise ValueError(
            f"Unknown printer profile: {profile_name}. "
            f"Available profiles: {list(PROFILES.keys())}"
        )
    return PROFILES[profile_name]


def load_profile_from_file(filepath: Path) -> Dict[str, Any]:
    """
    Load printer profile from JSON file.

    Args:
        filepath: Path to JSON profile file

    Returns:
        Dict containing printer specifications
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def get_max_dimensions(profile_name: str = "ender3v2") -> tuple:
    """
    Get maximum printable dimensions for a profile.

    Args:
        profile_name: Name of the printer profile

    Returns:
        Tuple of (max_x, max_y, max_z) in mm
    """
    profile = get_profile(profile_name)
    bed_size = profile["bed_size"]
    # Use conservative dimensions (90% of bed size)
    return (
        bed_size[0] * 0.9,
        bed_size[1] * 0.9,
        profile["max_model_height"]
    )


def validate_model_size(
    dimensions: tuple,
    profile_name: str = "ender3v2"
) -> tuple[bool, str]:
    """
    Validate if a model fits within printer build volume.

    Args:
        dimensions: Tuple of (x, y, z) dimensions in mm
        profile_name: Name of the printer profile

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    max_dims = get_max_dimensions(profile_name)
    x, y, z = dimensions
    max_x, max_y, max_z = max_dims

    if x > max_x or y > max_y or z > max_z:
        return False, (
            f"Model dimensions ({x:.1f}x{y:.1f}x{z:.1f}mm) exceed "
            f"printer capacity ({max_x:.1f}x{max_y:.1f}x{max_z:.1f}mm)"
        )

    return True, "Model fits within printer build volume"


def get_center_position(profile_name: str = "ender3v2") -> tuple:
    """
    Get the center position of the build plate.

    Args:
        profile_name: Name of the printer profile

    Returns:
        Tuple of (x, y, z) coordinates in mm
    """
    profile = get_profile(profile_name)
    return tuple(profile["center_offset"])


# Export commonly used profiles
__all__ = [
    'PROFILES',
    'get_profile',
    'load_profile_from_file',
    'get_max_dimensions',
    'validate_model_size',
    'get_center_position'
]
