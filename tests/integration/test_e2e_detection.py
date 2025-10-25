"""Integration tests for detection pipeline."""

import json
from pathlib import Path

import pytest

from modules.detection import DoclingDetector, detect_placeholders_in_pdf


class TestDetectionPipeline:
    """Test detection pipeline with synthetic PDF."""

    def test_detection_pipeline_synthetic_pdf(self) -> None:
        """
        Test detection pipeline: PDF → rasterize → detect → JSON.

        Uses sample_book_page.pdf with 2 known placeholders.
        Since DoclingDetector returns empty list (not implemented),
        this tests the pipeline infrastructure, not actual detection.
        """
        # Path to synthetic PDF
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        pdf_path = fixtures_dir / "sample_book_page.pdf"
        assert pdf_path.exists(), "sample_book_page.pdf fixture missing"

        # Run detection pipeline
        book_id = "test_synthetic"
        detector = DoclingDetector()

        results = detect_placeholders_in_pdf(str(pdf_path), book_id, detector)

        # Verify pipeline executed
        assert len(results) == 1, "Should process 1 page"

        result = results[0]
        assert result.page == 1
        assert result.book_id == "test_synthetic"
        assert result.scan_dpi == 600
        assert result.page_size_mm is not None

        # Verify A4 dimensions (approximately)
        page_size = result.page_size_mm
        assert abs(page_size["width"] - 210) < 5, f"Width {page_size['width']} not close to 210mm"
        assert abs(page_size["height"] - 297) < 5, f"Height {page_size['height']} not close to 297mm"

        # DoclingDetector returns empty list (not implemented yet)
        # So placeholders will be empty, validation_passed should be False
        assert isinstance(result.placeholders, list)
        assert result.validation_passed is False  # No placeholders detected

        # Verify detection JSON was saved
        detection_json_path = Path(f"detections/{book_id}/page_0001.json")
        assert detection_json_path.exists(), "Detection JSON not saved"

        # Verify JSON is valid
        detection_data = json.loads(detection_json_path.read_text())
        assert detection_data["schema_version"] == "1.0.0"
        assert detection_data["coordinate_system"] == "top_left_mm"

        # Cleanup
        detection_json_path.unlink()
        detection_json_path.parent.rmdir()

    def test_detection_pdf_not_found(self) -> None:
        """Test that missing PDF raises FileNotFoundError."""
        detector = DoclingDetector()

        with pytest.raises(FileNotFoundError, match="PDF not found"):
            detect_placeholders_in_pdf("nonexistent.pdf", "test", detector)

    def test_rasterization_creates_page_images(self) -> None:
        """Test that PDF rasterization creates page images."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        pdf_path = fixtures_dir / "sample_book_page.pdf"

        book_id = "test_rasterization"
        detector = DoclingDetector()

        results = detect_placeholders_in_pdf(str(pdf_path), book_id, detector)

        # Verify page image was created
        page_image_path = Path(f"pages/{book_id}/page_0001.png")
        assert page_image_path.exists(), "Page image not created during rasterization"

        # Cleanup
        page_image_path.unlink()
        page_image_path.parent.rmdir()

        # Cleanup detection JSON
        detection_json_path = Path(f"detections/{book_id}/page_0001.json")
        if detection_json_path.exists():
            detection_json_path.unlink()
            detection_json_path.parent.rmdir()
