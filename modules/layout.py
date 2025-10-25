"""Image-to-placeholder mapping and layout generation.

This module handles:
- Mapping user images to detected placeholders
- Calculating scale/crop transforms for each image
- Generating layout JSON for rendering
"""

import json
from pathlib import Path
from typing import TypedDict

from PIL import Image

from modules.coordinates import mm_to_px
from modules.validation import DetectionOutput


class Transform(TypedDict):
    """Image transform specification."""

    scale_factor: float
    crop_rect_px: dict[str, int]  # {x, y, width, height}


class PositionedImage(TypedDict):
    """Image positioned in a placeholder."""

    placeholder_id: str
    source_image: str
    target_bbox_mm: dict[str, float]  # {x, y, width, height}
    scaling_mode: str
    transform: Transform


class LayoutOutput(TypedDict):
    """Complete layout output for a page."""

    schema_version: str
    page: int
    book_id: str
    positioned_images: list[PositionedImage]


def calculate_transform(
    source_width_px: int,
    source_height_px: int,
    target_width_px: float,
    target_height_px: float,
    mode: str = "fill",
) -> Transform:
    """Calculate scale and crop transform to fit source into target.

    Args:
        source_width_px: Source image width in pixels
        source_height_px: Source image height in pixels
        target_width_px: Target placeholder width in pixels
        target_height_px: Target placeholder height in pixels
        mode: Scaling mode: "fill" | "fit" | "center_crop"

    Returns:
        Transform with scale_factor and crop_rect_px

    Note:
        - "fill": Scale to cover target (may crop edges)
        - "fit": Scale to fit within target (may have borders)
        - "center_crop": Not implemented yet (Phase 3)
    """
    if mode == "fill":
        # Scale to cover target completely (crop excess)
        scale_x = target_width_px / source_width_px
        scale_y = target_height_px / source_height_px
        scale_factor = max(scale_x, scale_y)  # Use larger to cover

        # Calculate crop rectangle (centered)
        scaled_width = source_width_px * scale_factor
        scaled_height = source_height_px * scale_factor

        crop_x = int((scaled_width - target_width_px) / 2)
        crop_y = int((scaled_height - target_height_px) / 2)

        # Crop rect is in source image coordinates (before scaling)
        crop_width = int(target_width_px / scale_factor)
        crop_height = int(target_height_px / scale_factor)
        crop_x_source = int((source_width_px - crop_width) / 2)
        crop_y_source = int((source_height_px - crop_height) / 2)

        return Transform(
            scale_factor=scale_factor,
            crop_rect_px={
                "x": crop_x_source,
                "y": crop_y_source,
                "width": crop_width,
                "height": crop_height,
            },
        )
    elif mode == "fit":
        # Scale to fit within target (may have borders)
        scale_x = target_width_px / source_width_px
        scale_y = target_height_px / source_height_px
        scale_factor = min(scale_x, scale_y)  # Use smaller to fit

        # No crop needed for fit mode
        return Transform(
            scale_factor=scale_factor,
            crop_rect_px={"x": 0, "y": 0, "width": source_width_px, "height": source_height_px},
        )
    else:
        raise ValueError(f"Unsupported scaling mode: {mode}")


def create_layout(
    detection_json_path: str,
    image_dir: str,
    scaling_mode: str = "fill",
    print_dpi: int = 300,
) -> LayoutOutput:
    """Generate layout JSON from detection and user images.

    Args:
        detection_json_path: Path to detection JSON file
        image_dir: Directory containing user images
        scaling_mode: How to scale images ("fill" or "fit")
        print_dpi: Target print DPI (default 300)

    Returns:
        LayoutOutput dict with positioned images

    Raises:
        FileNotFoundError: If detection JSON or images not found
        ValueError: If no images found in directory

    Note:
        This is a minimal implementation for Phase 2 vertical slice.
        Auto-mapping logic (sorting by size) deferred to Phase 3.
    """
    # Load detection JSON
    detection_path = Path(detection_json_path)
    if not detection_path.exists():
        raise FileNotFoundError(f"Detection JSON not found: {detection_json_path}")

    detection_data = json.loads(detection_path.read_text())
    detection = DetectionOutput(**detection_data)  # Validate with Pydantic

    # Find images in directory
    image_path_obj = Path(image_dir)
    image_files = sorted(
        list(image_path_obj.glob("*.jpg")) + list(image_path_obj.glob("*.jpeg"))
    )

    if not image_files:
        raise ValueError(f"No images found in {image_dir}")

    # Simple 1:1 mapping for Phase 2 (first image to first placeholder)
    positioned_images: list[PositionedImage] = []

    for i, placeholder in enumerate(detection.placeholders):
        if i >= len(image_files):
            break  # More placeholders than images

        image_file = image_files[i]

        # Load image to get dimensions
        with Image.open(image_file) as img:
            source_width_px, source_height_px = img.size

        # Convert placeholder mm → pixels at print DPI
        bbox_mm = placeholder.bbox_mm
        target_width_px = mm_to_px(bbox_mm.width, print_dpi)
        target_height_px = mm_to_px(bbox_mm.height, print_dpi)

        # Calculate transform
        transform = calculate_transform(
            source_width_px, source_height_px, target_width_px, target_height_px, scaling_mode
        )

        positioned_images.append(
            PositionedImage(
                placeholder_id=placeholder.id,
                source_image=str(image_file),
                target_bbox_mm={
                    "x": bbox_mm.x,
                    "y": bbox_mm.y,
                    "width": bbox_mm.width,
                    "height": bbox_mm.height,
                },
                scaling_mode=scaling_mode,
                transform=transform,
            )
        )

    return LayoutOutput(
        schema_version="1.0.0",
        page=detection.page,
        book_id=detection.book_id,
        positioned_images=positioned_images,
    )
