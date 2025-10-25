"""Schema validation using Pydantic models.

This module defines:
- Pydantic models for all JSON schemas
- Validation functions for bounding boxes
- IoU (Intersection over Union) calculation for overlap detection
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from modules.config import MAX_PLACEHOLDERS_PER_PAGE


class BBoxMM(BaseModel):
    """Bounding box in millimeters (top-left origin)."""

    x: float = Field(ge=0, description="X coordinate from top-left (mm)")
    y: float = Field(ge=0, description="Y coordinate from top-left (mm)")
    width: float = Field(gt=0, description="Width in millimeters")
    height: float = Field(gt=0, description="Height in millimeters")


class Placeholder(BaseModel):
    """Detected placeholder metadata."""

    id: str = Field(description="Unique identifier for this placeholder")
    bbox_mm: BBoxMM
    detection_method: str = Field(description="Method used: docling | yolo | manual | llm_vision")
    confidence: float = Field(ge=0, le=1, description="Detection confidence score")
    notes: str = Field(default="", description="Optional notes about this placeholder")


class DetectionOutput(BaseModel):
    """Complete detection output for a single page."""

    schema_version: str = Field(default="1.0.0", description="JSON schema version")
    page: int = Field(ge=1, description="Page number (1-indexed)")
    book_id: str = Field(description="Book identifier")
    scan_dpi: int = Field(gt=0, description="Scan resolution in DPI")
    page_size_mm: dict[str, float] = Field(description="Page dimensions: width, height in mm")
    coordinate_system: str = Field(
        default="top_left_mm", description="Coordinate system used"
    )
    placeholders: list[Placeholder]
    validation_passed: bool = Field(description="Whether validation checks passed")
    detected_at: str = Field(description="ISO 8601 timestamp of detection")

    @field_validator("placeholders")
    @classmethod
    def check_count(cls, v: list[Placeholder]) -> list[Placeholder]:
        """Validate placeholder count is within acceptable range.
        
        Note: Empty list is allowed for failed detection cases (validation_passed=False).
        """
        if len(v) > MAX_PLACEHOLDERS_PER_PAGE:
            raise ValueError(
                f"Placeholder count must be 0-{MAX_PLACEHOLDERS_PER_PAGE}, got {len(v)}"
            )
        return v

    @field_validator("detected_at")
    @classmethod
    def check_timestamp_format(cls, v: str) -> str:
        """Validate timestamp is valid ISO 8601 format."""
        try:
            datetime.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from e
        return v


def calculate_iou(bbox1: BBoxMM, bbox2: BBoxMM) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box

    Returns:
        IoU score between 0 and 1, where:
        - 0 = no overlap
        - 1 = perfect overlap

    Note:
        IoU = Area of Intersection / Area of Union
    """
    # Calculate intersection rectangle
    x1_inter = max(bbox1.x, bbox2.x)
    y1_inter = max(bbox1.y, bbox2.y)
    x2_inter = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
    y2_inter = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)

    # Check if there's any intersection
    if x2_inter < x1_inter or y2_inter < y1_inter:
        return 0.0

    # Calculate areas
    intersection_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
    area1 = bbox1.width * bbox1.height
    area2 = bbox2.width * bbox2.height
    union_area = area1 + area2 - intersection_area

    return intersection_area / union_area if union_area > 0 else 0.0


def check_bbox_within_page(bbox: BBoxMM, page_width_mm: float, page_height_mm: float) -> bool:
    """Check if bounding box is fully within page boundaries.

    Args:
        bbox: Bounding box to check
        page_width_mm: Page width in millimeters
        page_height_mm: Page height in millimeters

    Returns:
        True if bbox is fully within page, False otherwise
    """
    return (
        bbox.x >= 0
        and bbox.y >= 0
        and bbox.x + bbox.width <= page_width_mm
        and bbox.y + bbox.height <= page_height_mm
    )


def check_placeholders_overlap(placeholders: list[Placeholder], iou_threshold: float = 0.1) -> bool:
    """Check if any placeholders overlap significantly.

    Args:
        placeholders: List of placeholders to check
        iou_threshold: Maximum acceptable IoU (default 0.1 = 10% overlap)

    Returns:
        True if no significant overlaps found, False if overlap exceeds threshold
    """
    for i, ph1 in enumerate(placeholders):
        for ph2 in placeholders[i + 1 :]:
            iou = calculate_iou(ph1.bbox_mm, ph2.bbox_mm)
            if iou > iou_threshold:
                return False
    return True
