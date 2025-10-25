"""Unit tests for modules/validation.py."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from modules.validation import (
    BBoxMM,
    DetectionOutput,
    Placeholder,
    calculate_iou,
    check_bbox_within_page,
    check_placeholders_overlap,
)


class TestBBoxMM:
    """Tests for BBoxMM model."""

    def test_valid_bbox(self) -> None:
        """Test creating a valid bounding box."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 80
        assert bbox.height == 60

    def test_negative_x_raises(self) -> None:
        """Test that negative X coordinate raises ValidationError."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            BBoxMM(x=-1, y=0, width=10, height=10)

    def test_negative_y_raises(self) -> None:
        """Test that negative Y coordinate raises ValidationError."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            BBoxMM(x=0, y=-1, width=10, height=10)

    def test_zero_width_raises(self) -> None:
        """Test that zero width raises ValidationError."""
        with pytest.raises(ValidationError, match="greater than 0"):
            BBoxMM(x=0, y=0, width=0, height=10)

    def test_zero_height_raises(self) -> None:
        """Test that zero height raises ValidationError."""
        with pytest.raises(ValidationError, match="greater than 0"):
            BBoxMM(x=0, y=0, width=10, height=0)

    def test_negative_width_raises(self) -> None:
        """Test that negative width raises ValidationError."""
        with pytest.raises(ValidationError, match="greater than 0"):
            BBoxMM(x=0, y=0, width=-10, height=10)


class TestPlaceholder:
    """Tests for Placeholder model."""

    def test_valid_placeholder(self) -> None:
        """Test creating a valid placeholder."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        placeholder = Placeholder(
            id="ph_001",
            bbox_mm=bbox,
            detection_method="docling",
            confidence=0.95,
            notes="test placeholder",
        )
        assert placeholder.id == "ph_001"
        assert placeholder.confidence == 0.95
        assert placeholder.notes == "test placeholder"

    def test_confidence_out_of_range_raises(self) -> None:
        """Test that confidence > 1 raises ValidationError."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            Placeholder(
                id="ph_001", bbox_mm=bbox, detection_method="docling", confidence=1.5
            )

    def test_default_notes(self) -> None:
        """Test that notes default to empty string."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        placeholder = Placeholder(
            id="ph_001", bbox_mm=bbox, detection_method="manual", confidence=1.0
        )
        assert placeholder.notes == ""


class TestDetectionOutput:
    """Tests for DetectionOutput model."""

    def test_valid_detection_output(self) -> None:
        """Test creating a valid detection output."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        placeholder = Placeholder(
            id="ph_001", bbox_mm=bbox, detection_method="docling", confidence=0.95
        )

        detection = DetectionOutput(
            page=1,
            book_id="test_book",
            scan_dpi=600,
            page_size_mm={"width": 210, "height": 297},
            placeholders=[placeholder],
            validation_passed=True,
            detected_at=datetime.now().isoformat(),
        )

        assert detection.page == 1
        assert detection.schema_version == "1.0.0"
        assert len(detection.placeholders) == 1

    def test_empty_placeholders_allowed(self) -> None:
        """Test that empty placeholders list is allowed (for failed detection)."""
        detection = DetectionOutput(
            page=1,
            book_id="test_book",
            scan_dpi=600,
            page_size_mm={"width": 210, "height": 297},
            placeholders=[],
            validation_passed=False,  # Empty is OK if validation_passed=False
            detected_at=datetime.now().isoformat(),
        )
        assert len(detection.placeholders) == 0
        assert detection.validation_passed is False

    def test_too_many_placeholders_raises(self) -> None:
        """Test that >6 placeholders raises ValidationError."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        placeholders = [
            Placeholder(
                id=f"ph_{i:03d}",
                bbox_mm=bbox,
                detection_method="docling",
                confidence=0.9,
            )
            for i in range(7)
        ]

        with pytest.raises(ValidationError, match="Placeholder count must be 0-6"):
            DetectionOutput(
                page=1,
                book_id="test_book",
                scan_dpi=600,
                page_size_mm={"width": 210, "height": 297},
                placeholders=placeholders,
                validation_passed=True,
                detected_at=datetime.now().isoformat(),
            )

    def test_invalid_timestamp_raises(self) -> None:
        """Test that invalid ISO timestamp raises ValidationError."""
        bbox = BBoxMM(x=10, y=20, width=80, height=60)
        placeholder = Placeholder(
            id="ph_001", bbox_mm=bbox, detection_method="docling", confidence=0.95
        )

        with pytest.raises(ValidationError, match="Invalid ISO 8601 timestamp"):
            DetectionOutput(
                page=1,
                book_id="test_book",
                scan_dpi=600,
                page_size_mm={"width": 210, "height": 297},
                placeholders=[placeholder],
                validation_passed=True,
                detected_at="not-a-timestamp",
            )


class TestCalculateIoU:
    """Tests for IoU calculation."""

    def test_no_overlap(self) -> None:
        """Test IoU for non-overlapping boxes."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=20, y=20, width=10, height=10)
        assert calculate_iou(bbox1, bbox2) == 0.0

    def test_perfect_overlap(self) -> None:
        """Test IoU for identical boxes."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=0, y=0, width=10, height=10)
        assert calculate_iou(bbox1, bbox2) == pytest.approx(1.0)

    def test_partial_overlap(self) -> None:
        """Test IoU for partially overlapping boxes."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=5, y=5, width=10, height=10)

        # Intersection: 5x5 = 25
        # Union: 100 + 100 - 25 = 175
        # IoU: 25/175 ≈ 0.143
        assert calculate_iou(bbox1, bbox2) == pytest.approx(0.143, abs=0.01)

    def test_touching_edges(self) -> None:
        """Test IoU for boxes that just touch at edges."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=10, y=0, width=10, height=10)
        assert calculate_iou(bbox1, bbox2) == 0.0


class TestCheckBBoxWithinPage:
    """Tests for page boundary checking."""

    def test_bbox_fully_within_page(self) -> None:
        """Test bbox that is fully within page boundaries."""
        bbox = BBoxMM(x=10, y=10, width=80, height=60)
        assert check_bbox_within_page(bbox, 210, 297) is True

    def test_bbox_exceeds_right_edge(self) -> None:
        """Test bbox that exceeds right page edge."""
        bbox = BBoxMM(x=150, y=10, width=80, height=60)
        assert check_bbox_within_page(bbox, 210, 297) is False

    def test_bbox_exceeds_bottom_edge(self) -> None:
        """Test bbox that exceeds bottom page edge."""
        bbox = BBoxMM(x=10, y=250, width=80, height=60)
        assert check_bbox_within_page(bbox, 210, 297) is False

    def test_bbox_at_page_corner(self) -> None:
        """Test bbox that exactly fits at page corner."""
        bbox = BBoxMM(x=0, y=0, width=210, height=297)
        assert check_bbox_within_page(bbox, 210, 297) is True


class TestCheckPlaceholdersOverlap:
    """Tests for placeholder overlap detection."""

    def test_no_overlap(self) -> None:
        """Test placeholders with no overlap."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=20, y=20, width=10, height=10)

        ph1 = Placeholder(
            id="ph1", bbox_mm=bbox1, detection_method="manual", confidence=1.0
        )
        ph2 = Placeholder(
            id="ph2", bbox_mm=bbox2, detection_method="manual", confidence=1.0
        )

        assert check_placeholders_overlap([ph1, ph2]) is True

    def test_significant_overlap_detected(self) -> None:
        """Test detection of significant overlap (>10%)."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=5, y=5, width=10, height=10)  # ~14% IoU

        ph1 = Placeholder(
            id="ph1", bbox_mm=bbox1, detection_method="manual", confidence=1.0
        )
        ph2 = Placeholder(
            id="ph2", bbox_mm=bbox2, detection_method="manual", confidence=1.0
        )

        assert check_placeholders_overlap([ph1, ph2], iou_threshold=0.1) is False

    def test_minor_overlap_allowed(self) -> None:
        """Test that minor overlap (<10%) is allowed."""
        bbox1 = BBoxMM(x=0, y=0, width=10, height=10)
        bbox2 = BBoxMM(x=9, y=9, width=10, height=10)  # ~1% IoU

        ph1 = Placeholder(
            id="ph1", bbox_mm=bbox1, detection_method="manual", confidence=1.0
        )
        ph2 = Placeholder(
            id="ph2", bbox_mm=bbox2, detection_method="manual", confidence=1.0
        )

        assert check_placeholders_overlap([ph1, ph2], iou_threshold=0.1) is True
