"""PDF rendering from layout specifications.

This module handles:
- Loading layout JSON and source images
- Applying scale/crop transforms using Pillow
- Generating print-ready PDFs with ReportLab
"""

import json
from pathlib import Path

from PIL import Image
from reportlab.lib.units import mm as reportlab_mm
from reportlab.pdfgen import canvas

from modules.config import PAPER_TYPES
from modules.coordinates import mm_to_pdf_coords
from modules.layout import LayoutOutput


def render_pdf(
    layout_json_path: str,
    paper_type: str,
    output_path: str,
) -> None:
    """Generate print-ready PDF from layout JSON.

    Args:
        layout_json_path: Path to layout JSON file
        paper_type: Paper type from config.PAPER_TYPES (e.g., "A4")
        output_path: Where to save the generated PDF

    Raises:
        FileNotFoundError: If layout JSON or source images not found
        KeyError: If paper_type not in PAPER_TYPES
        ValueError: If layout JSON is invalid

    Note:
        - PDF uses ReportLab's bottom-left origin (converted from top-left mm)
        - Images are cropped and scaled according to transform spec
        - Output is at PRINT_DPI resolution (from config)
    """
    # Load layout JSON
    layout_path = Path(layout_json_path)
    if not layout_path.exists():
        raise FileNotFoundError(f"Layout JSON not found: {layout_json_path}")

    layout_data = json.loads(layout_path.read_text())
    # TypedDict casting (layout_data is dict from JSON)
    layout: LayoutOutput = layout_data

    # Get paper configuration
    if paper_type not in PAPER_TYPES:
        raise KeyError(f"Unknown paper type: {paper_type}")

    paper_config = PAPER_TYPES[paper_type]
    page_width_mm: float = paper_config["width_mm"]  # type: ignore
    page_height_mm: float = paper_config["height_mm"]  # type: ignore

    # Create PDF canvas
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(
        str(output_path),
        pagesize=(page_width_mm * reportlab_mm, page_height_mm * reportlab_mm),
    )

    # Process each positioned image
    for positioned_image in layout["positioned_images"]:
        source_image_path = positioned_image["source_image"]
        if not Path(source_image_path).exists():
            raise FileNotFoundError(f"Source image not found: {source_image_path}")

        # Load source image
        with Image.open(source_image_path) as img:
            # Apply crop from transform
            crop_rect = positioned_image["transform"]["crop_rect_px"]
            cropped = img.crop(
                (
                    crop_rect["x"],
                    crop_rect["y"],
                    crop_rect["x"] + crop_rect["width"],
                    crop_rect["y"] + crop_rect["height"],
                )
            )

            # Scale to target size
            target_bbox = positioned_image["target_bbox_mm"]
            scale_factor = positioned_image["transform"]["scale_factor"]

            # Target size in pixels (scale factor already accounts for DPI)
            target_width_px = int(crop_rect["width"] * scale_factor)
            target_height_px = int(crop_rect["height"] * scale_factor)

            scaled = cropped.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)

            # Save to temporary file for ReportLab
            # (ReportLab can't directly use PIL Image objects efficiently)
            temp_path = output_path_obj.parent / f"temp_{positioned_image['placeholder_id']}.jpg"
            scaled.save(temp_path, "JPEG", quality=95)

        # Convert top-left mm to ReportLab bottom-left points
        x_pt, y_pt = mm_to_pdf_coords(target_bbox["x"], target_bbox["y"], page_height_mm)

        # Draw image on PDF
        # Note: y_pt is bottom-left of image, need to adjust for image height
        image_height_mm = target_bbox["height"]
        y_pt_bottom = y_pt - (image_height_mm * reportlab_mm)

        c.drawImage(
            str(temp_path),
            x_pt,
            y_pt_bottom,
            width=target_bbox["width"] * reportlab_mm,
            height=target_bbox["height"] * reportlab_mm,
            preserveAspectRatio=False,  # We already handled aspect ratio
        )

        # Clean up temp file
        temp_path.unlink()

    # Save PDF
    c.save()
