"""Placeholder detection using document layout analysis.

This module provides:
- Abstract Detector interface for pluggable detection backends
- DoclingDetector implementation using docling library
- Full pipeline: PDF → rasterize → detect → validate → save JSON
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from docling.document_converter import DocumentConverter

from modules.config import SCAN_DPI
from modules.coordinates import px_to_mm, rasterize_pdf
from modules.validation import BBoxMM, DetectionOutput, Placeholder

logger = logging.getLogger(__name__)


class Detector(ABC):
    """Abstract base class for placeholder detection."""

    @abstractmethod
    def detect(self, page_image_path: str, page_num: int, page_width_px: int, page_height_px: int) -> list[Placeholder]:
        """Detect placeholders in a rasterized page image.

        Args:
            page_image_path: Path to rasterized page image
            page_num: Page number (1-indexed)
            page_width_px: Page width in pixels
            page_height_px: Page height in pixels

        Returns:
            List of detected Placeholder objects with bbox in mm (top-left origin)
        """
        raise NotImplementedError


class DoclingDetector(Detector):
    """Detector using docling for layout analysis."""

    def __init__(self) -> None:
        """Initialize docling document converter."""
        self.converter = DocumentConverter()
        logger.info("DoclingDetector initialized")

    def detect(self, page_image_path: str, page_num: int, page_width_px: int, page_height_px: int) -> list[Placeholder]:
        """Detect placeholders using docling's layout detection.

        Docling detects figures/images in PDF layout. We treat these as placeholders.

        Args:
            page_image_path: Path to rasterized page image (not used by docling)
            page_num: Page number for placeholder ID generation
            page_width_px: Page width in pixels for coordinate conversion
            page_height_px: Page height in pixels for coordinate conversion

        Returns:
            List of Placeholder objects detected by docling

        Note:
            This is a simplified implementation for Phase 3 MVP.
            Full implementation would parse docling's layout structure.
            For now, returns empty list to unblock integration testing.
            Real docling integration deferred to future work.
        """
        # TODO: Implement real docling detection
        # For Phase 3 MVP, we'll use a manual fallback approach
        # Docling 2.58.0 API needs investigation for figure/image detection

        logger.warning(
            "DoclingDetector.detect() not fully implemented - "
            "returning empty list. Use manual annotation for Phase 3."
        )
        return []


def detect_placeholders_in_pdf(
    pdf_path: str,
    book_id: str,
    detector: Detector,
) -> list[dict[str, object]]:
    """Full detection pipeline: PDF → rasterize → detect → validate → save JSON.

    Args:
        pdf_path: Path to input PDF file
        book_id: Identifier for this book (used in output paths)
        detector: Detector instance to use for placeholder detection

    Returns:
        List of detection result dicts (one per page)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        RuntimeError: If PDF rasterization fails

    Note:
        - Rasterizes PDF at SCAN_DPI from config
        - Saves detection JSON to detections/{book_id}/page_{N:04d}.json
        - Validates results with Pydantic before saving
    """
    # 1. Rasterize PDF
    logger.info(f"Rasterizing PDF: {pdf_path}")
    pages_metadata = rasterize_pdf(pdf_path, f"pages/{book_id}", SCAN_DPI, book_id)
    logger.info(f"Rasterized {len(pages_metadata)} pages")

    results: list[dict[str, object]] = []

    # 2. Detect placeholders in each page
    for meta in pages_metadata:
        logger.info(f"Detecting placeholders on page {meta['page_num']}")

        placeholders = detector.detect(
            meta["image_path"],
            meta["page_num"],
            meta["width_px"],
            meta["height_px"]
        )

        logger.info(f"Found {len(placeholders)} placeholders on page {meta['page_num']}")

        # 3. Build DetectionOutput schema
        page_width_mm = px_to_mm(meta["width_px"], SCAN_DPI)
        page_height_mm = px_to_mm(meta["height_px"], SCAN_DPI)

        detection = DetectionOutput(
            page=meta["page_num"],
            book_id=book_id,
            scan_dpi=SCAN_DPI,
            page_size_mm={"width": page_width_mm, "height": page_height_mm},
            placeholders=placeholders if placeholders else [],  # Empty list if no detections
            validation_passed=True,  # Will be set by validator
            detected_at=datetime.now().isoformat(),
        )

        # 4. Validate (Pydantic will raise ValidationError if invalid)
        try:
            # Pydantic v2: model_validate checks the model
            DetectionOutput.model_validate(detection.model_dump())
            detection.validation_passed = True
            logger.info(f"Validation passed for page {meta['page_num']}")
        except Exception as e:
            logger.error(f"Validation failed for page {meta['page_num']}: {e}")
            detection.validation_passed = False

        # 5. Save JSON
        output_dir = Path(f"detections/{book_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"page_{meta['page_num']:04d}.json"

        output_path.write_text(detection.model_dump_json(indent=2))
        logger.info(f"Saved detection to {output_path}")

        results.append(detection.model_dump())

    return results
