"""Generate test fixtures for Phase 2 vertical slice."""

import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def generate_golden_detection() -> None:
    """Generate golden_detection.json fixture."""
    fixture = {
        "schema_version": "1.0.0",
        "page": 1,
        "book_id": "test_book",
        "scan_dpi": 600,
        "page_size_mm": {"width": 210, "height": 297},
        "coordinate_system": "top_left_mm",
        "placeholders": [
            {
                "id": "page_001_ph_01",
                "bbox_mm": {"x": 20, "y": 40, "width": 80, "height": 60},
                "detection_method": "manual",
                "confidence": 1.0,
                "notes": "test_placeholder",
            }
        ],
        "validation_passed": True,
        "detected_at": datetime.now().isoformat(),
    }

    output_path = Path(__file__).parent / "golden_detection.json"
    output_path.write_text(json.dumps(fixture, indent=2))
    print(f"✓ Generated {output_path}")


def generate_test_image() -> None:
    """Generate test_image_800x600.jpg fixture."""
    # Create 800x600 image with blue gradient background
    img = Image.new("RGB", (800, 600), color=(100, 150, 200))
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle([(10, 10), (790, 590)], outline=(255, 255, 255), width=3)

    # Draw text in center
    text = "Test Image"
    # Get text bounding box for centering (approximate)
    text_width = len(text) * 20  # Rough estimate
    text_x = (800 - text_width) // 2
    text_y = 280

    draw.text((text_x, text_y), text, fill=(255, 255, 255))

    # Draw dimensions text
    dim_text = "800x600"
    draw.text((350, 320), dim_text, fill=(200, 200, 200))

    output_path = Path(__file__).parent / "test_image_800x600.jpg"
    img.save(output_path, "JPEG", quality=95)
    print(f"✓ Generated {output_path}")


if __name__ == "__main__":
    generate_golden_detection()
    generate_test_image()
    print("\n✓ All fixtures generated successfully")
