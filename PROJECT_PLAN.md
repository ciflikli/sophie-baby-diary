# Sophie the Giraffe Baby Diary - Project Plan

## Project Goal

Automate detection of photo placeholder areas in "Sophie the Giraffe - My Baby's Diary" book scans, then scale and align user images to fit these placeholders for printing on various paper types.

## Architecture Overview

```
modules/
  detection.py      # Abstract Detector + concrete implementations
  coordinates.py    # DPI handling, px↔mm transforms, coordinate system utils
  layout.py         # Placeholder-to-image mapping, positioning logic
  rendering.py      # PDF generation from positioned images
  validation.py     # Schema validation, QA checks, error handling
config.py           # Centralized constants, paper types, thresholds
tests/
  unit/             # Module-level tests
  integration/      # End-to-end pipeline tests
  fixtures/         # Synthetic test PDFs, golden-file detections
```

## Constants (config.py)

```python
SCAN_DPI = 600              # Fixed DPI for all scans
PRINT_DPI = 300             # Target print resolution
MIN_DETECTION_CONFIDENCE = 0.70
TARGET_RECALL = 0.90        # Realistic target for decorative book pages
MAX_PLACEHOLDERS_PER_PAGE = 6
MIN_TRAINING_SAMPLES = 30   # For YOLO if needed
COORDINATE_SYSTEM = "top_left_mm"  # Origin: top-left corner, units: millimeters
SCHEMA_VERSION = "1.0.0"
```

## Phase 1: Automatic Placeholder Detection (MVP)

### Strategy
**Start with docling (pre-trained layout parser)** → validate on 5 sample pages → decide if YOLO training is needed.

**Why docling first:**
- Zero custom training required
- Handles PDF→layout→bbox natively
- Faster time-to-feedback than labeling 30+ pages for YOLO
- If it achieves ≥90% recall on sample pages, skip YOLO entirely

### Prerequisites
- **Scan acquisition:** Obtain book scans at exactly 600 DPI as PDF or PNG/TIFF. If source DPI differs, resample to 600 DPI and document original DPI in metadata.
- **Copyright notice:** If using LLM vision for labeling/fallback, do NOT send copyrighted book scans to external APIs without legal review. Prefer local-only solutions.

### Detection Pipeline

1. **PDF → Images** (`coordinates.py`)
   - Use PyMuPDF (`fitz`) to rasterize each page at SCAN_DPI
   - Output: `pages/{book_id}/page_{N:04d}.png` + metadata JSON with `{"dpi": 600, "width_px": W, "height_px": H}`

2. **Placeholder Detection** (`detection.py`)
   - **Primary:** docling with figure/image block extraction
   - **Fallback (manual):** If docling fails on a page, user manually annotates placeholders via simple GUI/CLI tool
   - Output: `detections/{book_id}/page_{N:04d}.json` (schema below)

3. **Validation** (`validation.py`)
   - Check: `0 < len(placeholders) <= MAX_PLACEHOLDERS_PER_PAGE`
   - Check: all bbox coordinates within page bounds
   - Check: confidence ≥ MIN_DETECTION_CONFIDENCE
   - Check: no overlapping placeholders (IoU < 0.1)
   - Log failures to `detections/{book_id}/validation_errors.jsonl`

### Detection Schema (v1.0.0)

**Canonical representation: millimeters from top-left origin.**

```json
{
  "schema_version": "1.0.0",
  "page": 1,
  "book_id": "sophie_diary_2024",
  "scan_dpi": 600,
  "page_size_mm": {"width": 210, "height": 297},
  "coordinate_system": "top_left_mm",
  "placeholders": [
    {
      "id": "page_001_ph_01",
      "bbox_mm": {"x": 25.4, "y": 50.8, "width": 80.0, "height": 60.0},
      "detection_method": "docling",
      "confidence": 0.92,
      "notes": "rounded_corners"
    }
  ],
  "validation_passed": true,
  "detected_at": "2025-10-25T10:30:00Z"
}
```

**Schema notes:**
- `bbox_mm`: `{x, y}` = top-left corner in mm from page top-left; `{width, height}` in mm
- No redundant normalized coords—recalculate if needed: `x_norm = x_mm / page_width_mm`
- Pixel→mm conversion: `mm = (px / SCAN_DPI) * 25.4`
- `detection_method`: `docling | yolo | manual | llm_vision`
- `confidence`: detector confidence score; 1.0 for manual/fallback

### Evaluation (5 sample pages)

**Metrics:**
- Per-page recall: detected_correct / total_placeholders
- Per-page precision: detected_correct / total_detected
- Mean IoU: overlap between detected and ground-truth bboxes

**Acceptance criteria:**
- Recall ≥ 0.90 (okay to miss decorative elements)
- Precision ≥ 0.85 (some false positives acceptable, will be filtered by user)
- Mean IoU ≥ 0.80 for detected placeholders

**If docling fails:** Label 30 pages using Label Studio → train YOLOv8 → re-evaluate.

### Future YOLO Path (only if needed)

- Library: `ultralytics` (pin: `ultralytics==8.1.0`, `torch>=2.0.0` for MPS support)
- Single class: `placeholder`
- Training: 30-200 labeled pages, 80/20 train/val split
- Inference output: same schema as docling, `detection_method: "yolo"`

## Phase 2: Image-to-Placeholder Mapping (`layout.py`)

### Goal
Match user-provided images to detected placeholders and calculate positioning/scaling.

### Input
- Detection JSON files: `detections/{book_id}/page_*.json`
- User images: `input_images/*.jpg` (arbitrary filenames)
- Mapping strategy: `auto | manual | config_file`

### Mapping Strategies

1. **Auto (simple):** Sort placeholders by size (largest first), sort images by filename, zip pairs
2. **Config file:** User provides `mapping.json`:
```json
{
  "schema_version": "1.0.0",
  "mappings": [
    {"page": 1, "placeholder_id": "page_001_ph_01", "image": "baby_photo_1.jpg"},
    {"page": 1, "placeholder_id": "page_001_ph_02", "image": "family_pic.jpg"}
  ]
}
```
3. **Manual (CLI):** Interactive prompt showing placeholder preview + image thumbnails

### Scaling Strategies (per placeholder)

Defined in `config.py`:
```python
DEFAULT_SCALING_MODE = "fill"  # fill | fit | center_crop
```

- **fill:** Scale to cover placeholder completely (may crop edges); preserves aspect ratio
- **fit:** Scale to fit within placeholder (may have borders); preserves aspect ratio
- **center_crop:** Crop from center to match placeholder aspect ratio, then scale to fill

### Output Schema (`layout/{book_id}/page_{N:04d}_layout.json`)

```json
{
  "schema_version": "1.0.0",
  "page": 1,
  "book_id": "sophie_diary_2024",
  "positioned_images": [
    {
      "placeholder_id": "page_001_ph_01",
      "source_image": "input_images/baby_photo_1.jpg",
      "target_bbox_mm": {"x": 25.4, "y": 50.8, "width": 80.0, "height": 60.0},
      "scaling_mode": "fill",
      "transform": {
        "scale_factor": 1.25,
        "crop_rect_px": {"x": 100, "y": 50, "width": 2000, "height": 1500}
      }
    }
  ]
}
```

**Transform calculation (`coordinates.py`):**
- Load source image, get dimensions in pixels
- Convert placeholder `bbox_mm` → pixels at PRINT_DPI: `px = (mm / 25.4) * PRINT_DPI`
- Calculate scale factor and crop rect based on `scaling_mode`
- Validate final image resolution ≥ PRINT_DPI at target size

---

## Phase 3: PDF Rendering (`rendering.py`)

### Goal
Generate print-ready PDF with positioned images for each page.

### Paper Type Configuration (`config.py`)

```python
PAPER_TYPES = {
    "A4": {
        "width_mm": 210,
        "height_mm": 297,
        "printable_margin_mm": 5,
        "bleed_mm": 0
    },
    "7x10_photo": {
        "width_mm": 177.8,
        "height_mm": 254,
        "printable_margin_mm": 3,
        "bleed_mm": 0
    },
    "custom": {  # User-defined via CLI args
        "width_mm": None,
        "height_mm": None,
        "printable_margin_mm": 5,
        "bleed_mm": 0
    }
}
```

### Rendering Pipeline

1. **Input:** Layout JSON + paper type selection
2. **Library:** ReportLab (Python native, good DPI control)
3. **Process:**
   - Create PDF canvas at paper size, PRINT_DPI
   - For each `positioned_image`:
     - Load source image
     - Apply transform (crop + scale) using Pillow
     - Embed at `target_bbox_mm` coordinates (convert mm→points: `pt = mm * 2.834`)
   - Add optional: registration marks, crop guides, page numbers
4. **Output:** `output/{book_id}/page_{N:04d}_print.pdf`
5. **Validation (`validation.py`):**
   - Check all images within printable area (accounting for margins)
   - Verify embedded image DPI ≥ PRINT_DPI
   - Check file size < 50MB per page (flag if too large)

### Preview Mode
- Generate low-res PNG preview (150 DPI) with placeholder outlines overlaid
- Output: `output/{book_id}/preview/page_{N:04d}_preview.png`
- User reviews before printing

---

## Phase 4: Printer Calibration & Testing

### Problem
Printers often apply hidden scaling ("fit to page", margins). Need calibration.

### Calibration Procedure

1. **Generate test page:**
   - Create PDF with 10mm grid, rulers along edges, corner registration marks
   - Mark expected dimensions (e.g., "200mm × 287mm printable area")
   - Output: `tests/fixtures/calibration_grid.pdf`

2. **Print test page:**
   - User prints on target printer + paper type
   - Printer settings: **"Actual Size" / "100% scale" / "No margins"** (printer-specific)

3. **Measure physical output:**
   - Use ruler to measure grid spacing, overall dimensions
   - Calculate scale error: `measured_mm / expected_mm`

4. **Document calibration offset:**
   ```json
   // printer_calibration.json
   {
     "printer": "HP LaserJet Pro",
     "paper_type": "A4",
     "scale_factor_x": 0.98,  // Apply this to all X coordinates
     "scale_factor_y": 0.99,
     "offset_mm": {"x": 2.0, "y": 1.5}  // Shift all content by this amount
   }
   ```

5. **Apply calibration in rendering:**
   - Before rendering, multiply all `bbox_mm` by scale factors + add offset
   - Re-test with single-page print

### Test Suite

**Unit tests (`tests/unit/`):**
- `test_coordinates.py`: px↔mm conversions, DPI handling
- `test_validation.py`: schema validation, bbox overlap detection
- `test_layout.py`: image scaling calculations, aspect ratio math

**Integration tests (`tests/integration/`):**
- `test_e2e_detection.py`: synthetic PDF → detection JSON (golden file comparison)
- `test_e2e_rendering.py`: layout JSON → PDF → extract images and verify positions

**Fixtures (`tests/fixtures/`):**
- `sample_book_page.pdf`: 1-page PDF with 2 known placeholders at specific coordinates
- `golden_detection.json`: expected output from detection
- `test_images/`: 10 sample photos for layout testing

### Acceptance Criteria (before production use)

- [ ] Unit tests: 100% pass
- [ ] Integration tests: 100% pass  
- [ ] 5 sample pages detected with ≥90% recall, ≥85% precision
- [ ] Test print on 2 paper types: physical dimensions within ±1mm of expected
- [ ] Calibration offsets documented for primary printer
- [ ] User can run full pipeline (scan → detect → map → render → print) on 1 page in <5 min

---

## Technical Precision Requirements

### DPI Handling (centralized in `coordinates.py`)

```python
def px_to_mm(px: float, dpi: int) -> float:
    """Convert pixels to millimeters. 1 inch = 25.4 mm."""
    return (px / dpi) * 25.4

def mm_to_px(mm: float, dpi: int) -> float:
    """Convert millimeters to pixels."""
    return (mm / 25.4) * dpi
```

**Critical rule:** All intermediate calculations in `float`; round only at final pixel output using `round()` (not floor/ceil).

### Coordinate System Enforcement

- **Scans/Detection:** Top-left origin, millimeters
- **PDF rendering:** ReportLab uses bottom-left origin, points (1pt = 1/72 inch)
- **Conversion (in `rendering.py`):**
  ```python
  def mm_to_pdf_coords(x_mm, y_mm, page_height_mm):
      x_pt = x_mm * 2.834  # mm to points
      y_pt = (page_height_mm - y_mm) * 2.834  # flip Y axis
      return x_pt, y_pt
  ```

### Error Propagation

Worst-case error stack:
1. Scan distortion: ±0.5mm
2. Detection bbox error: ±1.0mm (from docling quantization)
3. Printer scaling: ±0.5mm
4. Manual cutting: ±2.0mm

**Total:** ±4mm. Placeholder borders should be ≥5mm to absorb this.

---

## Logging & Observability

**All modules use Python `logging`:**

```python
import logging
logger = logging.getLogger(__name__)

# In each phase:
logger.info(f"Detected {len(placeholders)} placeholders on page {page_num}")
logger.warning(f"Low confidence ({conf:.2f}) for placeholder {ph_id}")
logger.error(f"Validation failed: {error_msg}")
```

**Output:**
- Console: INFO level
- File: `logs/{book_id}/pipeline_{timestamp}.log` (DEBUG level)
- Metrics: `logs/{book_id}/metrics.json` (detection recall/precision per page)

---

## Deferred Features (Post-MVP)

- Batch processing CLI (process full book in one command)
- GUI for manual placeholder annotation
- Image enhancement (auto-rotate, brightness/contrast adjustment)
- Multi-image collages (fit 2+ user images into 1 placeholder)
- Cloud service for detection (upload PDF → get detection JSON)
- Community template sharing (book-specific detection models)
