# Implementation Plan - Sophie Baby Diary

**Goal:** Incremental, testable implementation with early validation of critical assumptions.

## Strategy

1. **Thin vertical slice first:** Prove end-to-end rendering (hardcoded detection → PDF) before building detection
2. **Test fixtures early:** Create synthetic test data to validate architecture before real scans
3. **Bottom-up for utilities, top-down for features:** Build `coordinates.py` and `validation.py` first (testable in isolation), then integrate into detection/rendering

---

## Phase 0: Project Setup

**Goal:** Runnable Python environment with dependencies.

### Steps

1. **Initialize project structure**
   ```bash
   mkdir -p modules tests/{unit,integration,fixtures} {pages,detections,layout,output,logs,input_images}
   touch modules/__init__.py tests/__init__.py
   ```

2. **Create `.gitignore`**
   ```
   # Data directories (runtime-generated)
   pages/
   detections/
   layout/
   output/
   logs/
   
   # Python
   venv/
   __pycache__/
   *.pyc
   *.pyo
   *.egg-info/
   .pytest_cache/
   .coverage
   htmlcov/
   
   # IDE
   .vscode/
   .idea/
   *.swp
   *.swo
   .DS_Store
   ```

3. **Create `pyproject.toml`** (or `requirements.txt`)
   ```toml
   [project]
   name = "sophie-baby-diary"
   version = "0.1.0"
   requires-python = ">=3.10"
   dependencies = [
       "pymupdf>=1.23.0",      # PDF → image rasterization
       "pillow>=10.0.0",       # Image processing
       "reportlab>=4.0.0",     # PDF generation
       "pydantic>=2.0.0",      # Schema validation
       "docling>=2.58.0",      # Layout detection (primary) - latest as of Oct 2025
       "click>=8.0.0",         # CLI framework
       "pytest>=7.4.0",        # Testing
       "pytest-cov>=4.1.0"     # Coverage
   ]
   
   [project.optional-dependencies]
   yolo = ["ultralytics==8.1.0", "torch>=2.0.0"]  # Only if docling fails
   ```

4. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .  # or: pip install -r requirements.txt
   ```

5. **Verify imports**
   ```bash
   python -c "import fitz, PIL, reportlab, pydantic, docling, click; print('✓ All deps installed')"
   ```

**Milestone 0 Validation:**
- [ ] `pytest --collect-only` runs without import errors
- [ ] Directory structure matches PROJECT_PLAN.md architecture

**Commit:** `feat: project setup with dependencies`

---

## Phase 1: Foundation (Coordinates + Validation)

**Goal:** Build and test coordinate transforms and schema validation in isolation.

### Step 1.1: `config.py`

**File:** `config.py`

```python
"""Centralized configuration constants."""

# DPI settings
SCAN_DPI = 600
PRINT_DPI = 300

# Detection thresholds
MIN_DETECTION_CONFIDENCE = 0.70
TARGET_RECALL = 0.90
MAX_PLACEHOLDERS_PER_PAGE = 6
MIN_TRAINING_SAMPLES = 30

# Coordinate system
COORDINATE_SYSTEM = "top_left_mm"
SCHEMA_VERSION = "1.0.0"

# Scaling modes
DEFAULT_SCALING_MODE = "fill"  # fill | fit | center_crop

# Paper types
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
    }
}
```

### Step 1.2: `modules/coordinates.py`

**Responsibilities:**
- DPI conversions (px ↔ mm)
- Coordinate system transforms (top-left mm → ReportLab bottom-left points)
- PDF rasterization (using PyMuPDF)

**Key functions:**
```python
def px_to_mm(px: float, dpi: int) -> float
def mm_to_px(mm: float, dpi: int) -> float
def mm_to_pdf_coords(x_mm: float, y_mm: float, page_height_mm: float) -> tuple[float, float]
def rasterize_pdf(pdf_path: str, output_dir: str, dpi: int, book_id: str) -> list[dict]
```

**Tests:** `tests/unit/test_coordinates.py`
```python
def test_px_to_mm_600dpi():
    assert px_to_mm(600, 600) == pytest.approx(25.4)  # 1 inch

def test_mm_to_px_300dpi():
    assert mm_to_px(25.4, 300) == pytest.approx(300)

def test_roundtrip():
    px = 1234.5
    assert mm_to_px(px_to_mm(px, 600), 600) == pytest.approx(px)

def test_mm_to_pdf_coords_flip_y():
    # Top-left (10mm, 20mm) on 297mm page → bottom-left (28.34pt, 785.42pt)
    x_pt, y_pt = mm_to_pdf_coords(10, 20, 297)
    assert x_pt == pytest.approx(10 * 2.834)
    assert y_pt == pytest.approx((297 - 20) * 2.834)
```

### Step 1.3: `modules/validation.py`

**Responsibilities:**
- Pydantic models for all JSON schemas
- Validation functions (bbox in bounds, overlap detection)
- Error logging

**Key models:**
```python
from pydantic import BaseModel, Field, field_validator

class BBoxMM(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)

class Placeholder(BaseModel):
    id: str
    bbox_mm: BBoxMM
    detection_method: str
    confidence: float = Field(ge=0, le=1)
    notes: str = ""

class DetectionOutput(BaseModel):
    schema_version: str = "1.0.0"
    page: int = Field(ge=1)
    book_id: str
    scan_dpi: int
    page_size_mm: dict[str, float]
    coordinate_system: str = "top_left_mm"
    placeholders: list[Placeholder]
    validation_passed: bool
    detected_at: str
    
    @field_validator('placeholders')
    @classmethod
    def check_count(cls, v):
        if not (0 < len(v) <= MAX_PLACEHOLDERS_PER_PAGE):
            raise ValueError(f"Placeholder count must be 1-{MAX_PLACEHOLDERS_PER_PAGE}")
        return v
```

**Tests:** `tests/unit/test_validation.py`
```python
def test_bbox_negative_x_raises():
    with pytest.raises(ValidationError):
        BBoxMM(x=-1, y=0, width=10, height=10)

def test_placeholder_count_validation():
    data = {..., "placeholders": []}  # Empty
    with pytest.raises(ValidationError):
        DetectionOutput(**data)

# Note: IoU calculation will be added in Phase 3 when needed for detection validation
```

**Milestone 1 Validation:**
- [ ] `pytest tests/unit/test_coordinates.py -v` → 100% pass
- [ ] `pytest tests/unit/test_validation.py -v` → 100% pass
- [ ] Coverage ≥80% on `coordinates.py` and `validation.py` (MVP target)
- [ ] `mypy modules/ --strict` passes (type hints required from Phase 1)

**Commit:** `feat: coordinate transforms and schema validation with tests`

---

## Phase 2: Vertical Slice (Hardcoded Detection → PDF)

**Goal:** Prove rendering pipeline works before building detection. Use hardcoded detection JSON.

### Step 2.1: Create test fixtures

**Script:** `tests/fixtures/generate_fixtures.py`
```python
"""Generate test fixtures for Phase 2 vertical slice."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from datetime import datetime

def generate_golden_detection() -> None:
    """Generate golden_detection.json."""
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
                "notes": "test_placeholder"
            }
        ],
        "validation_passed": True,
        "detected_at": datetime.now().isoformat()
    }
    Path("golden_detection.json").write_text(json.dumps(fixture, indent=2))
    print("✓ Generated golden_detection.json")

def generate_test_image() -> None:
    """Generate test_image_800x600.jpg."""
    img = Image.new('RGB', (800, 600), color=(100, 150, 200))
    draw = ImageDraw.Draw(img)
    # Draw text in center
    draw.text((350, 280), "Test Image", fill=(255, 255, 255))
    img.save("test_image_800x600.jpg", "JPEG", quality=95)
    print("✓ Generated test_image_800x600.jpg")

if __name__ == "__main__":
    generate_golden_detection()
    generate_test_image()
```

**Run:** `cd tests/fixtures && python generate_fixtures.py`

### Step 2.2: `modules/layout.py` (minimal)

**Responsibilities:**
- Map images to placeholders (auto mode only for now)
- Calculate scale/crop transforms

**Key function:**
```python
def create_layout(
    detection_json_path: str,
    image_dir: str,
    scaling_mode: str = "fill"
) -> dict:
    """Generate layout JSON from detection + images."""
    # Load detection, glob images, sort by size, zip pairs
    # Calculate transforms using coordinates.py functions
    # Return PositionedImages schema
```

**Tests:** `tests/unit/test_layout.py`
```python
def test_auto_mapping_largest_first():
    # 2 placeholders (100x100, 50x50), 2 images (a.jpg, b.jpg)
    # Should map largest placeholder → first image alphabetically
    ...

def test_fill_mode_crop_calculation():
    # Placeholder: 80x60mm @ 300 DPI → 945x709 px
    # Image: 1600x1200 px (4:3 aspect ratio)
    # Should crop to 1600x1200 → scale to 945x709
    ...
```

### Step 2.3: `modules/rendering.py` (core only)

**Responsibilities:**
- Generate PDF from layout JSON
- Embed images using ReportLab

**Key function:**
```python
def render_pdf(
    layout_json_path: str,
    paper_type: str,
    output_path: str
) -> None:
    """Generate print-ready PDF."""
    # Load layout JSON
    # Create ReportLab canvas
    # For each positioned_image:
    #   - Load source image with PIL
    #   - Apply crop/scale transform
    #   - Convert mm → PDF coords
    #   - Draw image on canvas
    # Save PDF
```

**Tests:** `tests/integration/test_e2e_rendering.py`
```python
def test_vertical_slice_hardcoded_to_pdf(tmp_path):
    """
    Vertical slice test: hardcoded detection JSON → layout → PDF → verify
    """
    # 1. Load golden_detection.json
    detection_path = "tests/fixtures/golden_detection.json"
    
    # 2. Create layout
    layout = create_layout(detection_path, "tests/fixtures/", scaling_mode="fill")
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(json.dumps(layout))
    
    # 3. Render PDF
    pdf_path = tmp_path / "output.pdf"
    render_pdf(str(layout_path), "A4", str(pdf_path))
    
    # 4. Verify PDF exists and has correct page count
    assert pdf_path.exists()
    doc = fitz.open(pdf_path)
    assert len(doc) == 1
    
    # 5. Extract image from PDF and check position (approximate)
    page = doc[0]
    images = page.get_images()
    assert len(images) == 1  # One embedded image
    
    # 6. Check image dimensions match expected (within tolerance)
    # Convert 80x60mm @ 300 DPI → ~945x709 px
    xref = images[0][0]
    pix = fitz.Pixmap(doc, xref)
    assert abs(pix.width - 945) < 20  # Allow ±20px tolerance
    assert abs(pix.height - 709) < 20
```

**Milestone 2 Validation:**
- [ ] Integration test passes: hardcoded detection → PDF with embedded image
- [ ] Manual inspection: open PDF in Preview.app, image is positioned correctly (approximate)
- [ ] No errors logged

**Commit:** `feat: vertical slice - hardcoded detection to PDF rendering`

---

## Phase 3: Detection (Docling Integration)

**Goal:** Replace hardcoded detection JSON with real docling output.

### Step 3.1: Create synthetic test PDF

**File:** `tests/fixtures/sample_book_page.pdf`

Generate using ReportLab:
- A4 page with 2 placeholder rectangles (unfilled, stroked border)
- Rectangles at known coordinates: (20mm, 40mm, 80x60mm), (120mm, 40mm, 60x80mm)
- Save as `sample_book_page.pdf`

**Script:** `tests/fixtures/generate_sample_page.py`
```python
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

c = canvas.Canvas("sample_book_page.pdf", pagesize=(210*mm, 297*mm))
c.setStrokeColorRGB(0, 0, 0)
c.setFillColorRGB(0.9, 0.9, 0.9)  # Light gray fill
c.rect(20*mm, (297-40-60)*mm, 80*mm, 60*mm, stroke=1, fill=1)  # Note: Y-flip
c.rect(120*mm, (297-40-80)*mm, 60*mm, 80*mm, stroke=1, fill=1)
c.save()
```

### Step 3.2: `modules/detection.py`

**Responsibilities:**
- Abstract `Detector` base class
- `DoclingDetector` implementation
- Fallback to manual annotation (stub for now)

**Key classes:**
```python
from abc import ABC, abstractmethod

class Detector(ABC):
    @abstractmethod
    def detect(self, page_image_path: str, page_num: int) -> list[Placeholder]:
        """Detect placeholders in a page image."""
        raise NotImplementedError

class DoclingDetector(Detector):
    def __init__(self):
        # Initialize docling client
        raise NotImplementedError("TODO: Initialize docling")
    
    def detect(self, page_image_path: str, page_num: int) -> list[Placeholder]:
        # Call docling API
        # Convert docling bbox output (likely in pixels or PDF points) → mm
        # Filter by confidence, figure/image type
        # Return list of Placeholder objects
        raise NotImplementedError("TODO: Implement docling detection")

def detect_placeholders_in_pdf(
    pdf_path: str,
    book_id: str,
    detector: Detector
) -> list[dict]:
    """
    Full pipeline: PDF → rasterize → detect → validate → save JSON
    """
    # 1. Rasterize using coordinates.py
    pages_metadata = rasterize_pdf(pdf_path, f"pages/{book_id}", SCAN_DPI, book_id)
    
    # 2. For each page:
    results = []
    for meta in pages_metadata:
        placeholders = detector.detect(meta["image_path"], meta["page_num"])
        
        # 3. Build DetectionOutput schema
        detection = DetectionOutput(
            page=meta["page_num"],
            book_id=book_id,
            scan_dpi=SCAN_DPI,
            page_size_mm={
                "width": px_to_mm(meta["width_px"], SCAN_DPI),
                "height": px_to_mm(meta["height_px"], SCAN_DPI)
            },
            placeholders=placeholders,
            validation_passed=True,  # Will be set by validator
            detected_at=datetime.now().isoformat()
        )
        
        # 4. Validate
        try:
            # Re-parse to trigger Pydantic validators
            DetectionOutput.model_validate(detection.model_dump())
            detection.validation_passed = True
        except ValidationError as e:
            logger.error(f"Validation failed for page {meta['page_num']}: {e}")
            detection.validation_passed = False
        
        # 5. Save JSON
        output_path = f"detections/{book_id}/page_{meta['page_num']:04d}.json"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(detection.model_dump_json(indent=2))
        
        results.append(detection.model_dump())
    
    return results
```

**Tests:** `tests/integration/test_e2e_detection.py`
```python
def test_docling_on_synthetic_pdf():
    """
    Integration test: synthetic PDF with 2 known placeholders → docling → JSON
    """
    pdf_path = "tests/fixtures/sample_book_page.pdf"
    book_id = "test_synthetic"
    
    detector = DoclingDetector()
    results = detect_placeholders_in_pdf(pdf_path, book_id, detector)
    
    assert len(results) == 1  # 1 page
    assert len(results[0]["placeholders"]) == 2  # 2 placeholders
    
    # Check approximate positions (docling may not be pixel-perfect)
    ph1 = results[0]["placeholders"][0]
    assert abs(ph1["bbox_mm"]["x"] - 20) < 5  # Within 5mm
    assert abs(ph1["bbox_mm"]["y"] - 40) < 5
    assert abs(ph1["bbox_mm"]["width"] - 80) < 5
    assert abs(ph1["bbox_mm"]["height"] - 60) < 5
```

**Milestone 3 Validation:**
- [ ] Docling detects 2 placeholders in `sample_book_page.pdf`
- [ ] Detection JSON validates against Pydantic schema
- [ ] Positions within ±5mm of expected (acceptable for MVP)
- [ ] If docling fails: document issue, prepare YOLO path (see Phase 3b below)

**Commit:** `feat: docling-based placeholder detection`

---

## Phase 3b: YOLO Fallback (Conditional)

**Trigger:** Docling recall < 0.90 on synthetic test OR fails on real book scans.

### Steps

1. **Label 30 pages** using Label Studio
   - Export annotations in YOLO format
   - Save to `data/yolo/labels/`

2. **Train YOLOv8**
   ```python
   from ultralytics import YOLO
   
   model = YOLO("yolov8n.pt")  # Nano model for speed
   model.train(data="data/yolo/dataset.yaml", epochs=50, imgsz=640)
   ```

3. **Implement `YOLODetector`**
   ```python
   class YOLODetector(Detector):
       def __init__(self, model_path: str):
           self.model = YOLO(model_path)
       
       def detect(self, page_image_path: str, page_num: int) -> list[Placeholder]:
           results = self.model(page_image_path)
           # Convert YOLO bboxes (normalized x_center, y_center, w, h) → top-left mm
           ...
   ```

4. **Re-run integration test** with `YOLODetector` instead of `DoclingDetector`

**Milestone 3b Validation:**
- [ ] YOLO recall ≥ 0.90 on 5 test pages
- [ ] Inference time < 2s per page on MacBook (CPU/MPS)

**Commit:** `feat: YOLO fallback detector`

---

## Phase 4: Full Pipeline Integration

**Goal:** Wire all modules together into a single CLI command.

### Step 4.1: CLI script

**File:** `cli.py`

```python
import click
from pathlib import Path
from modules.detection import DoclingDetector, detect_placeholders_in_pdf
from modules.layout import create_layout
from modules.rendering import render_pdf

@click.group()
def cli():
    """Sophie Baby Diary - Photo Placeholder Tool"""
    pass

@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--book-id", required=True)
def detect(pdf_path, book_id):
    """Detect placeholders in scanned book PDF."""
    detector = DoclingDetector()
    results = detect_placeholders_in_pdf(pdf_path, book_id, detector)
    click.echo(f"✓ Detected placeholders in {len(results)} pages")

@cli.command()
@click.argument("book_id")
@click.option("--image-dir", default="input_images")
@click.option("--scaling-mode", default="fill")
def layout(book_id, image_dir, scaling_mode):
    """Generate layout JSON from detections and images."""
    # Glob detection JSONs for book_id
    # Call create_layout for each page
    click.echo(f"✓ Generated layouts for {book_id}")

@cli.command()
@click.argument("book_id")
@click.option("--paper-type", default="A4")
def render(book_id, paper_type):
    """Render print-ready PDFs from layouts."""
    # Glob layout JSONs for book_id
    # Call render_pdf for each page
    click.echo(f"✓ Rendered PDFs to output/{book_id}/")

@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.argument("book_id")
@click.option("--image-dir", default="input_images")
@click.option("--paper-type", default="A4")
@click.pass_context
def pipeline(ctx, pdf_path, book_id, image_dir, paper_type):
    """Run full pipeline: detect → layout → render."""
    click.echo("Phase 1: Detecting placeholders...")
    ctx.invoke(detect, pdf_path=pdf_path, book_id=book_id)
    
    click.echo("Phase 2: Generating layouts...")
    ctx.invoke(layout, book_id=book_id, image_dir=image_dir, scaling_mode="fill")
    
    click.echo("Phase 3: Rendering PDFs...")
    ctx.invoke(render, book_id=book_id, paper_type=paper_type)
    
    click.echo(f"✓ Pipeline complete! Check output/{book_id}/")

if __name__ == "__main__":
    cli()
```

**Usage:**
```bash
# Full pipeline
python cli.py pipeline scans/sophie_book.pdf sophie_2024 --image-dir=photos/

# Or step-by-step
python cli.py detect scans/sophie_book.pdf --book-id=sophie_2024
python cli.py layout sophie_2024 --image-dir=photos/
python cli.py render sophie_2024 --paper-type=A4
```

**Milestone 4 Validation:**
- [ ] CLI runs full pipeline on synthetic PDF without errors
- [ ] Output PDFs match expected (manual inspection)
- [ ] Logs written to `logs/{book_id}/pipeline_{timestamp}.log`

**Commit:** `feat: CLI for full pipeline`

---

## Phase 5: Calibration & Real-World Testing

### Step 5.1: Generate calibration grid

**File:** `tests/fixtures/generate_calibration_grid.py`

```python
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

def generate_calibration_grid(output_path: str, paper_type: str = "A4"):
    width_mm, height_mm = 210, 297  # A4
    c = canvas.Canvas(output_path, pagesize=(width_mm*mm, height_mm*mm))
    
    # Draw 10mm grid
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    for x in range(0, int(width_mm), 10):
        c.line(x*mm, 0, x*mm, height_mm*mm)
    for y in range(0, int(height_mm), 10):
        c.line(0, y*mm, width_mm*mm, y*mm)
    
    # Draw rulers along edges
    c.setStrokeColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    for i in range(0, int(width_mm), 10):
        c.drawString(i*mm + 2, 5, f"{i}")
    
    # Corner registration marks
    c.circle(10*mm, (height_mm-10)*mm, 3*mm, stroke=1, fill=0)
    c.circle((width_mm-10)*mm, (height_mm-10)*mm, 3*mm, stroke=1, fill=0)
    
    # Title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(width_mm/2*mm - 50, height_mm/2*mm, "Calibration Grid - 10mm squares")
    
    c.save()

if __name__ == "__main__":
    generate_calibration_grid("tests/fixtures/calibration_grid.pdf")
```

**Instructions for user:**
1. Print `calibration_grid.pdf` on target printer (settings: "Actual Size", no scaling)
2. Measure printed grid with ruler
3. Calculate scale factors: `measured_mm / expected_mm`
4. Save to `printer_calibration.json`

### Step 5.2: Apply calibration in rendering

**Modify:** `modules/rendering.py`

```python
def load_calibration(printer_name: str, paper_type: str) -> dict | None:
    """Load calibration offsets if available."""
    calib_path = Path(f"printer_calibration_{printer_name}_{paper_type}.json")
    if calib_path.exists():
        return json.loads(calib_path.read_text())
    return None

def render_pdf(layout_json_path: str, paper_type: str, output_path: str, printer: str = "default"):
    # Load calibration
    calibration = load_calibration(printer, paper_type)
    
    # Apply scale factors and offsets to all bbox_mm before rendering
    if calibration:
        for img in positioned_images:
            bbox = img["target_bbox_mm"]
            bbox["x"] = bbox["x"] * calibration["scale_factor_x"] + calibration["offset_mm"]["x"]
            bbox["y"] = bbox["y"] * calibration["scale_factor_y"] + calibration["offset_mm"]["y"]
            bbox["width"] *= calibration["scale_factor_x"]
            bbox["height"] *= calibration["scale_factor_y"]
    
    # Continue with normal rendering...
```

**Milestone 5 Validation:**
- [ ] Calibration grid prints correctly (visual inspection)
- [ ] Measured vs expected dimensions documented
- [ ] Test print with calibration applied: alignment within ±1mm

**Commit:** `feat: printer calibration support`

---

## Phase 6: Polish & Documentation

### Tasks

1. **Add logging to all modules**
   - Console output at INFO level
   - File logs at DEBUG level (`logs/{book_id}/pipeline_{timestamp}.log`)
   - Metrics JSON (`logs/{book_id}/metrics.json`)

2. **Preview mode in rendering**
   - Generate 150 DPI PNG with placeholder outlines overlaid
   - Save to `output/{book_id}/preview/page_{N:04d}_preview.png`

3. **README.md** with:
   - Quick start guide
   - CLI usage examples
   - Troubleshooting (common errors)
   - Calibration procedure

4. **Code cleanup**
   - Run `ruff` or `black` formatter
   - Add type hints to all public functions
   - Docstrings in Google style

**Milestone 6 Validation:**
- [ ] All acceptance criteria from PROJECT_PLAN.md Phase 4 met
- [ ] README clear enough for non-developer user
- [ ] `pytest --cov` shows ≥80% coverage

**Commit:** `docs: add README and polish code`

---

## Rollout Checklist

**Before first real use:**

- [ ] Unit tests: 100% pass
- [ ] Integration tests: 100% pass
- [ ] Synthetic PDF test: detection + rendering works
- [ ] Real book scan test (1 page): detection ≥90% recall
- [ ] Calibration documented for primary printer
- [ ] User can run pipeline in <5 min (timed)
- [ ] Output PDF printed and physically aligned with book (±1mm)

**If any checklist item fails:** Stop, debug, re-test before proceeding.

---

## Estimated Timeline

| Phase | Complexity | Time (hours) | Dependencies |
|-------|-----------|--------------|--------------|
| 0. Setup | Low | 1 | None |
| 1. Foundation | Low | 3 | Phase 0 |
| 2. Vertical Slice | Medium | 4 | Phase 1 |
| 3. Detection | High | 6 | Phase 2 |
| 3b. YOLO (if needed) | High | 8 | Phase 3 fails |
| 4. CLI Integration | Low | 2 | Phase 3 |
| 5. Calibration | Medium | 3 | Phase 4 |
| 6. Polish | Low | 2 | Phase 5 |

**Total (without YOLO):** ~21 hours  
**Total (with YOLO):** ~29 hours

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Docling doesn't detect placeholders | Medium | High | Synthetic test first; YOLO fallback planned |
| Printer scaling breaks alignment | High | High | Calibration grid mandatory before real use |
| Coordinate transform bugs | Low | High | Extensive unit tests, roundtrip validation |
| DPI mismatch in scans | Medium | Medium | Validate scan DPI in metadata, resample if wrong |
| User doesn't have 600 DPI scanner | High | Low | Document resampling procedure |

---

## Next Steps

1. **Immediate:** Start Phase 0 (project setup)
2. **After Phase 1:** Review coordinate transform tests with stakeholder
3. **After Phase 2:** Demo vertical slice (hardcoded → PDF) to validate rendering quality
4. **After Phase 3:** Decision point: docling sufficient or train YOLO?
5. **After Phase 5:** Real-world test with actual book before production use
