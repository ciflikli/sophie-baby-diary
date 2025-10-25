"""Coordinate transformation and DPI conversion utilities.

This module handles:
- DPI conversions (pixels ↔ millimeters)
- Coordinate system transforms (top-left mm → ReportLab bottom-left points)
- PDF rasterization using PyMuPDF
"""

from pathlib import Path
from typing import TypedDict

import fitz  # type: ignore[import-untyped]  # PyMuPDF lacks type stubs


class PageMetadata(TypedDict):
    """Metadata for a rasterized PDF page."""

    page_num: int
    image_path: str
    width_px: int
    height_px: int
    dpi: int


def px_to_mm(px: float, dpi: int) -> float:
    """Convert pixels to millimeters.

    Args:
        px: Size in pixels
        dpi: Dots per inch (resolution)

    Returns:
        Size in millimeters

    Note:
        1 inch = 25.4 mm
    """
    return (px / dpi) * 25.4


def mm_to_px(mm: float, dpi: int) -> float:
    """Convert millimeters to pixels.

    Args:
        mm: Size in millimeters
        dpi: Dots per inch (resolution)

    Returns:
        Size in pixels
    """
    return (mm / 25.4) * dpi


def mm_to_pdf_coords(x_mm: float, y_mm: float, page_height_mm: float) -> tuple[float, float]:
    """Convert top-left mm coordinates to ReportLab bottom-left points.

    Args:
        x_mm: X coordinate in millimeters from top-left
        y_mm: Y coordinate in millimeters from top-left
        page_height_mm: Total page height in millimeters

    Returns:
        Tuple of (x_pt, y_pt) in ReportLab points (1pt = 1/72 inch)

    Note:
        ReportLab uses bottom-left origin, so Y axis is flipped.
        Conversion: 1mm = 2.834 points
    """
    x_pt = x_mm * 2.834  # mm to points
    y_pt = (page_height_mm - y_mm) * 2.834  # flip Y axis
    return x_pt, y_pt


def rasterize_pdf(pdf_path: str, output_dir: str, dpi: int, book_id: str) -> list[PageMetadata]:
    """Rasterize PDF pages to PNG images.

    Args:
        pdf_path: Path to input PDF file
        output_dir: Directory to save rasterized images
        dpi: Resolution for rasterization
        book_id: Identifier for this book (used in filenames)

    Returns:
        List of PageMetadata dicts with metadata for each rasterized page

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If PDF cannot be opened or rasterization fails
    """
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Failed to open PDF: {e}") from e

    results: list[PageMetadata] = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Calculate zoom factor to achieve target DPI
        # PyMuPDF default is 72 DPI, so zoom = target_dpi / 72
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        try:
            pix = page.get_pixmap(matrix=mat)
        except Exception as e:
            doc.close()
            raise RuntimeError(f"Failed to rasterize page {page_num + 1}: {e}") from e

        # Save as PNG
        image_filename = f"page_{page_num + 1:04d}.png"
        image_path = output_path / image_filename
        pix.save(str(image_path))

        results.append(
            PageMetadata(
                page_num=page_num + 1,  # 1-indexed for user-facing
                image_path=str(image_path),
                width_px=pix.width,
                height_px=pix.height,
                dpi=dpi,
            )
        )

    doc.close()
    return results
