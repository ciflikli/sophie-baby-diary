"""PDF rendering from layout specifications.

This module handles:
- Loading layout JSON and source images
- Applying scale/crop transforms using Pillow
- Generating print-ready PDFs with ReportLab
- Applying printer calibration offsets (optional)
"""

import json
import logging
from pathlib import Path
from typing import TypedDict

from PIL import Image
from reportlab.lib.units import mm as reportlab_mm
from reportlab.pdfgen import canvas

from modules.config import PAPER_TYPES
from modules.coordinates import mm_to_pdf_coords
from modules.layout import LayoutOutput

logger = logging.getLogger(__name__)


class CalibrationData(TypedDict):
    """Printer calibration data schema."""
    
    printer_name: str
    paper_type: str
    scale_factor_x: float
    scale_factor_y: float
    offset_mm: dict[str, float]  # {x, y}
    notes: str


def load_calibration(printer_name: str, paper_type: str) -> CalibrationData | None:
    """Load printer calibration data if available.
    
    Args:
        printer_name: Printer identifier (e.g., "hp_laserjet", "default")
        paper_type: Paper type (e.g., "A4")
    
    Returns:
        CalibrationData if file exists, None otherwise
    
    Note:
        Calibration files should be named:
        printer_calibration_{printer_name}_{paper_type}.json
        
        Example file content:
        {
            "printer_name": "hp_laserjet",
            "paper_type": "A4",
            "scale_factor_x": 1.02,
            "scale_factor_y": 0.98,
            "offset_mm": {"x": 2.0, "y": -1.5},
            "notes": "Measured 2024-10-25 using calibration grid"
        }
    """
    calib_path = Path(f"printer_calibration_{printer_name}_{paper_type}.json")
    
    if not calib_path.exists():
        logger.debug(f"No calibration file found: {calib_path}")
        return None
    
    try:
        data = json.loads(calib_path.read_text())
        logger.info(f"Loaded calibration from: {calib_path}")
        logger.info(f"  Scale factors: X={data['scale_factor_x']}, Y={data['scale_factor_y']}")
        logger.info(f"  Offsets: X={data['offset_mm']['x']}mm, Y={data['offset_mm']['y']}mm")
        return CalibrationData(**data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Invalid calibration file {calib_path}: {e}")
        return None


def apply_calibration(
    bbox_mm: dict[str, float],
    calibration: CalibrationData,
) -> dict[str, float]:
    """Apply calibration to a bounding box.
    
    Args:
        bbox_mm: Bounding box {x, y, width, height} in mm
        calibration: Calibration data to apply
    
    Returns:
        Calibrated bounding box {x, y, width, height} in mm
    """
    return {
        "x": bbox_mm["x"] * calibration["scale_factor_x"] + calibration["offset_mm"]["x"],
        "y": bbox_mm["y"] * calibration["scale_factor_y"] + calibration["offset_mm"]["y"],
        "width": bbox_mm["width"] * calibration["scale_factor_x"],
        "height": bbox_mm["height"] * calibration["scale_factor_y"],
    }


def render_pdf(
    layout_json_path: str,
    paper_type: str,
    output_path: str,
    printer_name: str = "default",
) -> None:
    """Generate print-ready PDF from layout JSON.

    Args:
        layout_json_path: Path to layout JSON file
        paper_type: Paper type from config.PAPER_TYPES (e.g., "A4")
        output_path: Where to save the generated PDF
        printer_name: Printer identifier for calibration lookup (default: "default")

    Raises:
        FileNotFoundError: If layout JSON or source images not found
        KeyError: If paper_type not in PAPER_TYPES
        ValueError: If layout JSON is invalid

    Note:
        - PDF uses ReportLab's bottom-left origin (converted from top-left mm)
        - Images are cropped and scaled according to transform spec
        - Output is at PRINT_DPI resolution (from config)
        - Calibration applied if printer_calibration_{printer}_{paper}.json exists
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
    
    # Load calibration if available
    calibration = load_calibration(printer_name, paper_type)
    if calibration:
        logger.info(f"Using calibration for printer '{printer_name}' on {paper_type}")
    else:
        logger.info(f"No calibration found for printer '{printer_name}' on {paper_type}")

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

        # Apply calibration if available
        if calibration:
            target_bbox = apply_calibration(target_bbox, calibration)
            logger.debug(
                f"Applied calibration to {positioned_image['placeholder_id']}: "
                f"x={target_bbox['x']:.2f}mm, y={target_bbox['y']:.2f}mm"
            )
        
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
