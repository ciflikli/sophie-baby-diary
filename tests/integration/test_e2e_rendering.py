"""Integration tests for end-to-end rendering pipeline."""

import json
from pathlib import Path

import fitz  # type: ignore[import-untyped]  # PyMuPDF
import pytest

from modules.layout import create_layout
from modules.rendering import render_pdf


class TestVerticalSlice:
    """Test vertical slice: hardcoded detection → layout → PDF."""

    def test_vertical_slice_hardcoded_to_pdf(self, tmp_path: Path) -> None:
        """
        Vertical slice test: golden_detection.json → layout → PDF → verify.

        This tests the complete pipeline without detection:
        1. Load golden_detection.json (hardcoded placeholder)
        2. Create layout with test_image_800x600.jpg
        3. Render PDF
        4. Verify PDF structure and embedded image
        """
        # 1. Paths to fixtures
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        detection_path = fixtures_dir / "golden_detection.json"
        assert detection_path.exists(), "golden_detection.json fixture missing"

        # 2. Create layout
        layout = create_layout(
            str(detection_path),
            str(fixtures_dir),  # test_image_800x600.jpg is here
            scaling_mode="fill",
            print_dpi=300,
        )

        # Verify layout structure
        assert layout["schema_version"] == "1.0.0"
        assert layout["page"] == 1
        assert layout["book_id"] == "test_book"
        assert len(layout["positioned_images"]) == 1

        positioned_image = layout["positioned_images"][0]
        assert positioned_image["placeholder_id"] == "page_001_ph_01"
        assert positioned_image["scaling_mode"] == "fill"
        assert "transform" in positioned_image
        assert positioned_image["transform"]["scale_factor"] > 0

        # Save layout JSON for debugging
        layout_path = tmp_path / "layout.json"
        layout_path.write_text(json.dumps(layout, indent=2))

        # 3. Render PDF
        pdf_path = tmp_path / "output.pdf"
        render_pdf(str(layout_path), "A4", str(pdf_path))

        # 4. Verify PDF exists
        assert pdf_path.exists(), "PDF was not created"
        assert pdf_path.stat().st_size > 0, "PDF is empty"

        # 5. Open PDF and verify structure
        doc = fitz.open(str(pdf_path))
        assert len(doc) == 1, "PDF should have exactly 1 page"

        page = doc[0]

        # Verify page size (A4: 210x297mm = 595x842 points)
        page_rect = page.rect
        assert abs(page_rect.width - 595) < 5, f"Page width incorrect: {page_rect.width}"
        assert abs(page_rect.height - 842) < 5, f"Page height incorrect: {page_rect.height}"

        # 6. Extract embedded images
        images = page.get_images()
        assert len(images) >= 1, "No images embedded in PDF"

        # Get first image
        xref = images[0][0]
        pix = fitz.Pixmap(doc, xref)

        # 7. Verify image dimensions
        # Placeholder: 80x60mm @ 300 DPI
        # Expected: (80/25.4)*300 ≈ 945px wide, (60/25.4)*300 ≈ 709px tall
        expected_width = int((80 / 25.4) * 300)
        expected_height = int((60 / 25.4) * 300)

        # Allow ±20px tolerance for scaling/rounding
        assert (
            abs(pix.width - expected_width) < 20
        ), f"Image width {pix.width} not close to {expected_width}"
        assert (
            abs(pix.height - expected_height) < 20
        ), f"Image height {pix.height} not close to {expected_height}"

        doc.close()

    def test_render_pdf_missing_layout(self, tmp_path: Path) -> None:
        """Test that missing layout JSON raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Layout JSON not found"):
            render_pdf("nonexistent.json", "A4", str(tmp_path / "output.pdf"))

    def test_render_pdf_invalid_paper_type(self, tmp_path: Path) -> None:
        """Test that invalid paper type raises KeyError."""
        # Create minimal layout JSON
        layout = {
            "schema_version": "1.0.0",
            "page": 1,
            "book_id": "test",
            "positioned_images": [],
        }
        layout_path = tmp_path / "layout.json"
        layout_path.write_text(json.dumps(layout))

        with pytest.raises(KeyError, match="Unknown paper type"):
            render_pdf(str(layout_path), "INVALID", str(tmp_path / "output.pdf"))
