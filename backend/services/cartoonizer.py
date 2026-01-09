"""
Cartoonization service using Replicate API (SDXL).
Transforms photos into Pixar-style 3D character portraits.
"""
import os
import replicate
import requests
from pathlib import Path
from typing import Optional
import time
from PIL import Image


class Cartoonizer:
    """
    Pixar-style cartoonization using Stability AI SDXL via Replicate.
    """

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Replicate client.

        Args:
            api_token: Replicate API token (or from REPLICATE_API_TOKEN env var)
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "REPLICATE_API_TOKEN not found. "
                "Set environment variable or pass as argument."
            )

        # Set API token for replicate client
        os.environ["REPLICATE_API_TOKEN"] = self.api_token

    def cartoonize(
        self,
        image_path: Path,
        output_path: Path,
        style: str = "pixar",
        timeout: int = 120
    ) -> dict:
        """
        Convert photo to Pixar-style cartoon using SDXL.

        Args:
            image_path: Path to input photo
            output_path: Path to save cartoonized image
            style: Cartoon style ("pixar", "disney", "3d_cartoon")
            timeout: Max wait time in seconds

        Returns:
            Dict with:
                - success: bool
                - output_path: Path (if successful)
                - message: str
                - replicate_url: str (prediction URL)
        """
        # Define prompts based on style
        prompts = {
            "pixar": {
                "prompt": (
                    "3D Pixar character portrait, smooth features, big expressive eyes, "
                    "clean render, studio lighting, colorful, CGI animation style, "
                    "cute, friendly expression, high quality 3D render"
                ),
                "negative": (
                    "realistic, photograph, ugly, blurry, lowres, bad anatomy, "
                    "deformed, disfigured, horror, scary, adult themes"
                )
            },
            "disney": {
                "prompt": (
                    "Disney 3D animated character, smooth skin, expressive eyes, "
                    "vibrant colors, professional animation style, clean render"
                ),
                "negative": (
                    "realistic, photograph, ugly, blurry, lowres, bad anatomy"
                )
            },
            "3d_cartoon": {
                "prompt": (
                    "3D cartoon character, stylized features, vibrant colors, "
                    "clean render, animation ready, professional quality"
                ),
                "negative": (
                    "realistic, photograph, ugly, blurry, lowres"
                )
            }
        }

        if style not in prompts:
            style = "pixar"  # Default fallback

        style_config = prompts[style]

        try:
            # Resize image to 1024x1024 max to avoid GPU memory issues
            print(f"Preprocessing image for cartoonization...")
            img = Image.open(image_path)

            # Resize if larger than 1024 on any side
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                # Calculate new size maintaining aspect ratio
                if img.width > img.height:
                    new_width = max_size
                    new_height = int(img.height * (max_size / img.width))
                else:
                    new_height = max_size
                    new_width = int(img.width * (max_size / img.height))

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"Resized image from {image_path} to {new_width}x{new_height}")

            # Convert to RGB if needed
            if img.mode not in ['RGB', 'RGBA']:
                img = img.convert('RGB')

            # Save preprocessed image
            temp_path = image_path.parent / f"temp_{image_path.name}"
            img.save(temp_path, format='PNG', optimize=True)

            # Run SDXL image-to-image
            print(f"Starting cartoonization with style: {style}")

            with open(temp_path, "rb") as img_file:
                output = replicate.run(
                    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                    input={
                        "image": img_file,
                        "prompt": style_config["prompt"],
                        "negative_prompt": style_config["negative"],
                        "num_inference_steps": 30,
                        "guidance_scale": 7.5,
                        "strength": 0.75,  # Balance between original and prompt
                        "scheduler": "K_EULER_ANCESTRAL"
                    }
                )

            # Output is a list of URLs
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            else:
                image_url = output

            # Download the result
            print(f"Downloading cartoonized image from: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # Save to output path
            with open(output_path, "wb") as f:
                f.write(response.content)

            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

            print(f"Cartoonization complete: {output_path}")

            return {
                "success": True,
                "output_path": str(output_path),
                "message": f"Successfully cartoonized image with {style} style",
                "replicate_url": image_url
            }

        except Exception as e:
            error_msg = f"Cartoonization failed: {str(e)}"
            print(f"ERROR: {error_msg}")

            return {
                "success": False,
                "output_path": None,
                "message": error_msg,
                "replicate_url": None
            }

    def batch_cartoonize(
        self,
        image_paths: list[Path],
        output_dir: Path,
        style: str = "pixar"
    ) -> list[dict]:
        """
        Cartoonize multiple images.

        Args:
            image_paths: List of input image paths
            output_dir: Directory to save outputs
            style: Cartoon style

        Returns:
            List of result dicts for each image
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for i, image_path in enumerate(image_paths):
            output_path = output_dir / f"cartoon_{i}_{image_path.name}"
            result = self.cartoonize(image_path, output_path, style)
            results.append(result)

            # Rate limiting: wait between requests
            if i < len(image_paths) - 1:
                time.sleep(2)

        return results
