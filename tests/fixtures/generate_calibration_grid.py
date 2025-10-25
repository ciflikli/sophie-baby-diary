"""Generate calibration grid PDF for printer accuracy testing.

This tool creates a PDF with:
- 10mm grid pattern
- Rulers along edges
- Corner registration marks
- Test rectangles at known positions

Usage:
    python tests/fixtures/generate_calibration_grid.py

Output:
    tests/fixtures/calibration_grid.pdf

User Instructions:
    1. Print calibration_grid.pdf on target printer
       - IMPORTANT: Set printer to "Actual Size" or "100%" scale
       - Disable "Fit to Page" or any auto-scaling
    2. Measure printed grid squares with ruler
    3. Measure test rectangles and compare to expected dimensions
    4. Calculate scale factors: measured_mm / expected_mm
    5. Create printer_calibration.json with results
"""

from pathlib import Path

from reportlab.lib.units import mm as reportlab_mm
from reportlab.pdfgen import canvas


def generate_calibration_grid(
    output_path: str = "tests/fixtures/calibration_grid.pdf",
    paper_type: str = "A4",
) -> None:
    """Generate calibration grid PDF.
    
    Args:
        output_path: Where to save the PDF
        paper_type: Paper size (currently only A4 supported)
    """
    # A4 dimensions
    width_mm = 210
    height_mm = 297
    
    # Create canvas
    c = canvas.Canvas(
        output_path,
        pagesize=(width_mm * reportlab_mm, height_mm * reportlab_mm),
    )
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(
        width_mm / 2 * reportlab_mm,
        (height_mm - 15) * reportlab_mm,
        "Printer Calibration Grid",
    )
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(
        width_mm / 2 * reportlab_mm,
        (height_mm - 25) * reportlab_mm,
        "Print at ACTUAL SIZE (100% scale) - No scaling or 'Fit to Page'",
    )
    
    # Draw 10mm grid (light gray)
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(0.5)
    
    # Vertical lines
    for x in range(10, int(width_mm), 10):
        c.line(
            x * reportlab_mm,
            30 * reportlab_mm,
            x * reportlab_mm,
            (height_mm - 30) * reportlab_mm,
        )
    
    # Horizontal lines
    for y in range(30, int(height_mm - 30), 10):
        c.line(
            10 * reportlab_mm,
            y * reportlab_mm,
            (width_mm - 10) * reportlab_mm,
            y * reportlab_mm,
        )
    
    # Draw thicker lines every 50mm
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.setLineWidth(1)
    
    for x in range(10, int(width_mm), 50):
        c.line(
            x * reportlab_mm,
            30 * reportlab_mm,
            x * reportlab_mm,
            (height_mm - 30) * reportlab_mm,
        )
    
    for y in range(30, int(height_mm - 30), 50):
        c.line(
            10 * reportlab_mm,
            y * reportlab_mm,
            (width_mm - 10) * reportlab_mm,
            y * reportlab_mm,
        )
    
    # Border
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.5)
    c.rect(
        10 * reportlab_mm,
        30 * reportlab_mm,
        (width_mm - 20) * reportlab_mm,
        (height_mm - 60) * reportlab_mm,
    )
    
    # Rulers along edges
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0, 0, 0)
    
    # Horizontal ruler (top)
    for i in range(10, int(width_mm - 10), 10):
        # Tick mark
        c.line(
            i * reportlab_mm,
            (height_mm - 30) * reportlab_mm,
            i * reportlab_mm,
            (height_mm - 27) * reportlab_mm,
        )
        # Label
        c.drawString(
            (i - 3) * reportlab_mm,
            (height_mm - 26) * reportlab_mm,
            f"{i}",
        )
    
    # Vertical ruler (left)
    for i in range(30, int(height_mm - 30), 10):
        # Tick mark
        c.line(
            10 * reportlab_mm,
            i * reportlab_mm,
            13 * reportlab_mm,
            i * reportlab_mm,
        )
        # Label
        c.drawString(
            14 * reportlab_mm,
            (i - 2) * reportlab_mm,
            f"{i}",
        )
    
    # Corner registration marks (5mm radius circles)
    c.setLineWidth(1)
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(1, 1, 1)  # Hollow
    
    # Top-left
    c.circle(15 * reportlab_mm, (height_mm - 35) * reportlab_mm, 5 * reportlab_mm, stroke=1, fill=0)
    
    # Top-right
    c.circle((width_mm - 15) * reportlab_mm, (height_mm - 35) * reportlab_mm, 5 * reportlab_mm, stroke=1, fill=0)
    
    # Bottom-left
    c.circle(15 * reportlab_mm, 35 * reportlab_mm, 5 * reportlab_mm, stroke=1, fill=0)
    
    # Bottom-right
    c.circle((width_mm - 15) * reportlab_mm, 35 * reportlab_mm, 5 * reportlab_mm, stroke=1, fill=0)
    
    # Test rectangles at known positions
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    
    # Rectangle 1: 50x30mm at (60, 100) from bottom-left
    c.rect(
        60 * reportlab_mm,
        100 * reportlab_mm,
        50 * reportlab_mm,
        30 * reportlab_mm,
        stroke=1,
        fill=1,
    )
    
    # Label
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    c.drawString(
        62 * reportlab_mm,
        113 * reportlab_mm,
        "50x30mm",
    )
    
    # Rectangle 2: 40x40mm at (130, 100) from bottom-left
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.rect(
        130 * reportlab_mm,
        100 * reportlab_mm,
        40 * reportlab_mm,
        40 * reportlab_mm,
        stroke=1,
        fill=1,
    )
    
    # Label
    c.setFillColorRGB(0, 0, 0)
    c.drawString(
        132 * reportlab_mm,
        118 * reportlab_mm,
        "40x40mm",
    )
    
    # Instructions at bottom
    c.setFont("Helvetica", 9)
    c.drawString(
        10 * reportlab_mm,
        20 * reportlab_mm,
        "Instructions:",
    )
    
    c.setFont("Helvetica", 8)
    c.drawString(
        10 * reportlab_mm,
        15 * reportlab_mm,
        "1. Measure any 10mm grid square with a ruler",
    )
    c.drawString(
        10 * reportlab_mm,
        11 * reportlab_mm,
        "2. Measure the test rectangles (should be 50x30mm and 40x40mm)",
    )
    c.drawString(
        10 * reportlab_mm,
        7 * reportlab_mm,
        "3. Calculate scale_factor = measured_mm / expected_mm for X and Y",
    )
    
    # Save
    c.save()
    print(f"✓ Calibration grid saved to: {output_path}")
    print("\nNext steps:")
    print("1. Print this PDF at ACTUAL SIZE (no scaling)")
    print("2. Measure the printed grid with a ruler")
    print("3. Create printer_calibration.json with measurements")


if __name__ == "__main__":
    # Ensure output directory exists
    output_path = Path("tests/fixtures/calibration_grid.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    generate_calibration_grid(str(output_path))
