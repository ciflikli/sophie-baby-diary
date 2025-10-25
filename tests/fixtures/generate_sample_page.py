"""Generate synthetic test PDF with known placeholder positions.

This creates a PDF with rectangular placeholders at precise coordinates
for testing docling detection accuracy.
"""

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def generate_sample_book_page() -> None:
    """Generate sample_book_page.pdf with 2 known placeholders.

    Placeholders:
    - Rectangle 1: (20mm, 40mm) size 80x60mm - light gray fill
    - Rectangle 2: (120mm, 40mm) size 60x80mm - light gray fill

    These coordinates are in top-left mm, but ReportLab uses bottom-left origin.
    """
    output_path = Path(__file__).parent / "sample_book_page.pdf"

    # A4 dimensions
    page_width_mm = 210
    page_height_mm = 297

    c = canvas.Canvas(str(output_path), pagesize=(page_width_mm * mm, page_height_mm * mm))

    # Set stroke and fill colors
    c.setStrokeColorRGB(0, 0, 0)  # Black border
    c.setFillColorRGB(0.9, 0.9, 0.9)  # Light gray fill

    # Placeholder 1: (20mm, 40mm) from top-left, size 80x60mm
    # Convert to bottom-left origin: y_bottom = page_height - y_top - height
    x1_mm = 20
    y1_top_mm = 40
    width1_mm = 80
    height1_mm = 60
    y1_bottom_mm = page_height_mm - y1_top_mm - height1_mm

    c.rect(x1_mm * mm, y1_bottom_mm * mm, width1_mm * mm, height1_mm * mm, stroke=1, fill=1)

    # Placeholder 2: (120mm, 40mm) from top-left, size 60x80mm
    x2_mm = 120
    y2_top_mm = 40
    width2_mm = 60
    height2_mm = 80
    y2_bottom_mm = page_height_mm - y2_top_mm - height2_mm

    c.rect(x2_mm * mm, y2_bottom_mm * mm, width2_mm * mm, height2_mm * mm, stroke=1, fill=1)

    # Add page title for debugging
    c.setFont("Helvetica", 10)
    c.drawString(10 * mm, (page_height_mm - 10) * mm, "Sample Book Page - Test Placeholders")

    c.save()
    print(f"✓ Generated {output_path}")
    print(f"  Placeholder 1: x={x1_mm}mm, y={y1_top_mm}mm, w={width1_mm}mm, h={height1_mm}mm")
    print(f"  Placeholder 2: x={x2_mm}mm, y={y2_top_mm}mm, w={width2_mm}mm, h={height2_mm}mm")


if __name__ == "__main__":
    generate_sample_book_page()
