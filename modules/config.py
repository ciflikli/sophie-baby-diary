"""Centralized configuration constants for sophie-baby-diary."""

# DPI settings
SCAN_DPI = 600  # Fixed DPI for all book scans
PRINT_DPI = 300  # Target print resolution

# Detection thresholds
MIN_DETECTION_CONFIDENCE = 0.70  # Minimum confidence for detected placeholders
TARGET_RECALL = 0.90  # Realistic target for decorative book pages
MAX_PLACEHOLDERS_PER_PAGE = 6  # Maximum expected placeholders per page
MIN_TRAINING_SAMPLES = 30  # Minimum samples needed for YOLO training

# Coordinate system
COORDINATE_SYSTEM = "top_left_mm"  # Origin: top-left corner, units: millimeters
SCHEMA_VERSION = "1.0.0"  # JSON schema version

# Scaling modes
DEFAULT_SCALING_MODE = "fill"  # fill | fit | center_crop

# Paper types
PAPER_TYPES = {
    "A4": {
        "width_mm": 210,
        "height_mm": 297,
        "printable_margin_mm": 5,
        "bleed_mm": 0,
    },
    "7x10_photo": {
        "width_mm": 177.8,
        "height_mm": 254,
        "printable_margin_mm": 3,
        "bleed_mm": 0,
    },
}
