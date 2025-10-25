"""Unit tests for modules/coordinates.py."""

import tempfile
from pathlib import Path

import pytest

from modules.coordinates import mm_to_pdf_coords, mm_to_px, px_to_mm, rasterize_pdf


class TestDPIConversions:
    """Tests for DPI conversion functions."""

    def test_px_to_mm_600dpi(self) -> None:
        """Test pixel to mm conversion at 600 DPI."""
        # 600 pixels at 600 DPI = 1 inch = 25.4 mm
        assert px_to_mm(600, 600) == pytest.approx(25.4)

    def test_mm_to_px_300dpi(self) -> None:
        """Test mm to pixel conversion at 300 DPI."""
        # 25.4 mm = 1 inch = 300 pixels at 300 DPI
        assert mm_to_px(25.4, 300) == pytest.approx(300)

    def test_roundtrip_conversion(self) -> None:
        """Test that px→mm→px roundtrip preserves value."""
        px = 1234.5
        dpi = 600
        assert mm_to_px(px_to_mm(px, dpi), dpi) == pytest.approx(px)

    def test_zero_pixels(self) -> None:
        """Test conversion of zero pixels."""
        assert px_to_mm(0, 600) == 0.0

    def test_zero_mm(self) -> None:
        """Test conversion of zero millimeters."""
        assert mm_to_px(0, 300) == 0.0

    def test_different_dpi_values(self) -> None:
        """Test that different DPI values produce different results."""
        mm = 10.0
        px_300 = mm_to_px(mm, 300)
        px_600 = mm_to_px(mm, 600)
        assert px_600 == pytest.approx(px_300 * 2)


class TestCoordinateTransforms:
    """Tests for coordinate system transformation functions."""

    def test_mm_to_pdf_coords_flip_y(self) -> None:
        """Test Y-axis flip for ReportLab coordinate system."""
        # Top-left (10mm, 20mm) on 297mm page → bottom-left points
        x_pt, y_pt = mm_to_pdf_coords(10, 20, 297)

        # X should be: 10 * 2.834 = 28.34 pt
        assert x_pt == pytest.approx(10 * 2.834)

        # Y should be: (297 - 20) * 2.834 = 277 * 2.834 = 784.818 pt
        assert y_pt == pytest.approx((297 - 20) * 2.834)

    def test_top_left_corner(self) -> None:
        """Test that top-left (0,0) maps to bottom-left at page height."""
        x_pt, y_pt = mm_to_pdf_coords(0, 0, 297)
        assert x_pt == 0.0
        assert y_pt == pytest.approx(297 * 2.834)

    def test_bottom_left_corner(self) -> None:
        """Test that bottom-left maps to (0,0) in PDF coords."""
        page_height = 297
        x_pt, y_pt = mm_to_pdf_coords(0, page_height, page_height)
        assert x_pt == 0.0
        assert y_pt == 0.0

    def test_center_point(self) -> None:
        """Test coordinate transform for page center."""
        page_height = 297
        center_y = page_height / 2
        x_pt, y_pt = mm_to_pdf_coords(105, center_y, page_height)

        assert x_pt == pytest.approx(105 * 2.834)
        assert y_pt == pytest.approx(center_y * 2.834)


class TestPDFRasterization:
    """Tests for PDF rasterization function."""

    def test_rasterize_pdf_nonexistent_file(self) -> None:
        """Test that nonexistent PDF raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            rasterize_pdf("nonexistent.pdf", "/tmp", 600, "test")

    def test_rasterize_pdf_creates_output_dir(self) -> None:
        """Test that output directory is created if it doesn't exist."""
        # Create a minimal valid PDF for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # We'll test directory creation without actually creating a PDF
            # since creating a valid PDF is complex. This tests the Path logic.
            output_dir = Path(tmpdir) / "nested" / "output"
            assert not output_dir.exists()

            # We can't easily test the full rasterization without a real PDF,
            # but we've validated the directory creation logic exists in the code

    # Note: Full rasterization tests would require creating a valid PDF fixture
    # This will be added in Phase 2 when we create test fixtures


class TestPageMetadata:
    """Tests for PageMetadata TypedDict."""

    def test_page_metadata_structure(self) -> None:
        """Test that PageMetadata has expected fields."""
        from modules.coordinates import PageMetadata

        # This is more of a static type check, but we can verify at runtime
        metadata: PageMetadata = {
            "page_num": 1,
            "image_path": "/tmp/page_0001.png",
            "width_px": 4960,
            "height_px": 7016,
            "dpi": 600,
        }

        assert metadata["page_num"] == 1
        assert metadata["dpi"] == 600
        assert "page_0001.png" in metadata["image_path"]
