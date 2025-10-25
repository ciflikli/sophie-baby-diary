# Printer Calibration Guide

This guide explains how to calibrate your printer for accurate photo placement in Sophie Baby Diary.

## Why Calibrate?

Printers may introduce small scaling errors or positioning offsets when printing. These errors can cause photos to be misaligned with the diary's photo placeholders by 1-3mm, which is noticeable when pasted into the physical book.

Calibration measures and corrects these errors, ensuring ±1mm accuracy.

## Prerequisites

- A ruler (metric, preferably with 0.5mm markings)
- Your target printer
- The ability to print PDFs at "Actual Size" or "100% scale"

## Step 1: Generate Calibration Grid

Generate a calibration test page:

```bash
python tests/fixtures/generate_calibration_grid.py
```

This creates `tests/fixtures/calibration_grid.pdf` with:
- 10mm grid pattern
- Two test rectangles (50×30mm and 40×40mm)
- Corner registration marks
- Rulers for easy measurement

## Step 2: Print Calibration Grid

**CRITICAL**: Print settings must be correct:

1. Open `tests/fixtures/calibration_grid.pdf`
2. Print with these settings:
   - **Scale:** "Actual Size" or "100%" (NOT "Fit to Page")
   - **Paper size:** A4 (210×297mm)
   - **Margins:** None or minimal
   - **Quality:** Normal (not draft)

3. Let the print dry completely before measuring

## Step 3: Measure Printed Grid

Use your ruler to measure the printed output:

### Measurement 1: Grid squares
Measure several 10mm×10mm grid squares in different areas:
- Top-left corner
- Top-right corner
- Center
- Bottom corners

Record the measurements. Example:
```
Top-left:    10.2mm × 9.8mm
Top-right:   10.1mm × 9.8mm
Center:      10.2mm × 9.9mm
Bottom-left: 10.1mm × 9.7mm
```

### Measurement 2: Test rectangles
Measure both test rectangles:

**Rectangle 1** (labeled "50×30mm"):
- Expected: 50mm wide × 30mm tall
- Your measurement: ___mm × ___mm

**Rectangle 2** (labeled "40×40mm"):
- Expected: 40mm × 40mm
- Your measurement: ___mm × ___mm

## Step 4: Calculate Scale Factors

Calculate the average scale factors:

### Scale Factor X (horizontal)
```
scale_factor_x = (measured_width / expected_width)
```

Example:
- Grid squares measured ~10.2mm wide (expected: 10mm)
- Rectangle 1 measured 51mm wide (expected: 50mm)
- Average: (10.2/10 + 51/50) / 2 = 1.02

### Scale Factor Y (vertical)
```
scale_factor_y = (measured_height / expected_height)
```

Example:
- Grid squares measured ~9.8mm tall (expected: 10mm)
- Rectangle 1 measured 29.5mm tall (expected: 30mm)
- Average: (9.8/10 + 29.5/30) / 2 = 0.98

## Step 5: Measure Position Offsets (Optional)

If your printer consistently shifts output:

1. Measure distance from paper edge to first grid line (should be 10mm)
2. Calculate offset: `measured_distance - 10mm`
3. Repeat for all four edges

Most home printers have negligible offsets (< 0.5mm), so you can skip this and use `0.0` for both X and Y offsets.

## Step 6: Create Calibration File

Create a JSON file named `printer_calibration_{printer_name}_{paper_type}.json` in the project root.

Example: `printer_calibration_hp_laserjet_A4.json`

```json
{
  "printer_name": "hp_laserjet",
  "paper_type": "A4",
  "scale_factor_x": 1.02,
  "scale_factor_y": 0.98,
  "offset_mm": {
    "x": 0.0,
    "y": 0.0
  },
  "notes": "Measured 2025-10-25 using HP LaserJet Pro M404n"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `printer_name` | string | Identifier for your printer (used in CLI `--printer` flag) |
| `paper_type` | string | Paper size (e.g., "A4", "7x10_photo") |
| `scale_factor_x` | float | Horizontal scale correction (1.0 = no correction) |
| `scale_factor_y` | float | Vertical scale correction (1.0 = no correction) |
| `offset_mm.x` | float | Horizontal offset in mm (positive = shift right) |
| `offset_mm.y` | float | Vertical offset in mm (positive = shift down) |
| `notes` | string | Documentation (date, printer model, etc.) |

## Step 7: Use Calibration

When rendering PDFs, specify your printer name:

```bash
# With calibration
python cli.py render my_book --paper-type=A4 --printer=hp_laserjet

# Full pipeline with calibration
python cli.py pipeline scans/book.pdf my_book \
  --image-dir=photos/ \
  --paper-type=A4 \
  --printer=hp_laserjet
```

The system will:
1. Look for `printer_calibration_hp_laserjet_A4.json`
2. If found, apply scale factors and offsets to all image positions
3. If not found, render without calibration (you'll see a log message)

## Step 8: Verify Calibration

After creating your calibration file:

1. Run a test render with your calibration
2. Print one test page
3. Hold the printout up to a ruler or the original book
4. Verify alignment is within ±1mm

If alignment is still off:
- Re-measure more carefully (lighting, ruler position)
- Check printer settings (ensure no auto-scaling)
- Try a different paper type or printer mode

## Tips

- **Humidity matters**: Paper expands/contracts with humidity. Measure in the same environment where you'll print final pages.
- **Consistent settings**: Always use the same print quality, paper type, and tray for both calibration and final prints.
- **Multiple printers**: Create separate calibration files for each printer.
- **Paper types**: Create separate calibrations for different paper types (e.g., photo paper vs plain paper).

## Troubleshooting

### "No calibration found" message
- Check filename matches pattern: `printer_calibration_{printer}_{paper}.json`
- Ensure JSON file is in project root (same directory as `cli.py`)
- Verify printer name matches exactly (case-sensitive)

### Calibration makes alignment worse
- Check scale factor calculation (should be close to 1.0, typically 0.95-1.05)
- Verify offset signs (positive X = right, positive Y = down from top-left)
- Re-measure with better lighting and a more precise ruler

### Different results for X vs Y
- This is normal! Printers often scale X and Y differently
- Paper feed mechanisms can introduce Y-axis variations
- Use separate scale factors for each axis

## Example: Complete Workflow

```bash
# 1. Generate calibration grid
python tests/fixtures/generate_calibration_grid.py

# 2. Print tests/fixtures/calibration_grid.pdf at 100% scale

# 3. Measure and create calibration file
cat > printer_calibration_myprinter_A4.json <<EOF
{
  "printer_name": "myprinter",
  "paper_type": "A4",
  "scale_factor_x": 1.01,
  "scale_factor_y": 0.99,
  "offset_mm": {"x": 0.0, "y": 0.0},
  "notes": "Canon PIXMA measured 2025-10-25"
}
EOF

# 4. Use calibration in your workflow
python cli.py pipeline scans/sophie_book.pdf sophie_2024 \
  --image-dir=photos/ \
  --printer=myprinter
```

## When to Re-Calibrate

- Using a different printer
- Switching paper types (e.g., plain → photo paper)
- After printer maintenance or repairs
- If alignment degrades over time (printer aging)

---

**Note**: Calibration is optional but highly recommended for best results. Without calibration, alignment errors of 1-3mm are common, which may be noticeable in the final diary.
