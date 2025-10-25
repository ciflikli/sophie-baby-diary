"""Command-line interface for Sophie Baby Diary placeholder processing.

Usage:
    # Full pipeline
    python cli.py pipeline scans/book.pdf my_book --image-dir=photos/

    # Step-by-step
    python cli.py detect scans/book.pdf --book-id=my_book
    python cli.py layout my_book --image-dir=photos/
    python cli.py render my_book --paper-type=A4
"""

import json
import sys
from pathlib import Path

import click

from modules.detection import DoclingDetector, detect_placeholders_in_pdf
from modules.layout import create_layout
from modules.rendering import render_pdf


@click.group()
def cli() -> None:
    """Sophie Baby Diary - Photo Placeholder Tool."""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--book-id", required=True, help="Unique identifier for this book")
def detect(pdf_path: str, book_id: str) -> None:
    """Detect placeholders in scanned book PDF.
    
    Args:
        pdf_path: Path to scanned PDF file
        book_id: Unique book identifier (used for output paths)
    
    Output:
        - Rasterized page images: pages/{book_id}/page_NNNN.png
        - Detection JSON: detections/{book_id}/page_NNNN.json
    """
    click.echo(f"🔍 Detecting placeholders in {pdf_path}...")
    
    detector = DoclingDetector()
    results = detect_placeholders_in_pdf(pdf_path, book_id, detector)
    
    total_placeholders = sum(len(r["placeholders"]) for r in results)  # type: ignore[misc,arg-type]
    click.echo(f"✓ Detected {total_placeholders} placeholders in {len(results)} pages")
    click.echo(f"📁 Detection JSON saved to: detections/{book_id}/")


@cli.command()
@click.argument("book_id")
@click.option("--image-dir", default="input_images", help="Directory containing user images")
@click.option("--scaling-mode", default="fill", type=click.Choice(["fill", "fit"]), help="Image scaling mode")
@click.option("--print-dpi", default=300, help="Target print DPI")
def layout(book_id: str, image_dir: str, scaling_mode: str, print_dpi: int) -> None:
    """Generate layout JSON from detections and images.
    
    Args:
        book_id: Book identifier (matches detection output)
        image_dir: Directory containing user images to place
        scaling_mode: How to scale images ("fill" or "fit")
        print_dpi: Target print resolution
    
    Output:
        - Layout JSON: layouts/{book_id}/page_NNNN.json
    """
    click.echo(f"📐 Generating layouts for book {book_id}...")
    
    # Find all detection JSONs for this book
    detection_dir = Path(f"detections/{book_id}")
    if not detection_dir.exists():
        click.echo(f"❌ Error: No detections found at {detection_dir}", err=True)
        click.echo(f"   Run 'detect' command first", err=True)
        sys.exit(1)
    
    detection_files = sorted(detection_dir.glob("page_*.json"))
    if not detection_files:
        click.echo(f"❌ Error: No detection JSON files in {detection_dir}", err=True)
        sys.exit(1)
    
    # Create layouts directory
    layout_dir = Path(f"layouts/{book_id}")
    layout_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each page
    for detection_path in detection_files:
        page_num = detection_path.stem  # e.g., "page_0001"
        
        try:
            layout_data = create_layout(
                str(detection_path),
                image_dir,
                scaling_mode=scaling_mode,
                print_dpi=print_dpi,
            )
            
            # Save layout JSON
            layout_path = layout_dir / f"{page_num}.json"
            layout_path.write_text(json.dumps(layout_data, indent=2))
            
            click.echo(f"  ✓ {page_num}: {len(layout_data['positioned_images'])} images")
            
        except FileNotFoundError as e:
            click.echo(f"  ⚠ {page_num}: {e}", err=True)
        except ValueError as e:
            click.echo(f"  ⚠ {page_num}: {e}", err=True)
    
    click.echo(f"✓ Generated {len(detection_files)} layouts")
    click.echo(f"📁 Layout JSON saved to: {layout_dir}/")


@cli.command()
@click.argument("book_id")
@click.option("--paper-type", default="A4", help="Paper type (A4, A5, etc.)")
def render(book_id: str, paper_type: str) -> None:
    """Render print-ready PDFs from layouts.
    
    Args:
        book_id: Book identifier (matches layout output)
        paper_type: Paper size from config.PAPER_TYPES
    
    Output:
        - Print-ready PDFs: output/{book_id}/page_NNNN.pdf
    """
    click.echo(f"🖨️  Rendering PDFs for book {book_id}...")
    
    # Find all layout JSONs for this book
    layout_dir = Path(f"layouts/{book_id}")
    if not layout_dir.exists():
        click.echo(f"❌ Error: No layouts found at {layout_dir}", err=True)
        click.echo(f"   Run 'layout' command first", err=True)
        sys.exit(1)
    
    layout_files = sorted(layout_dir.glob("page_*.json"))
    if not layout_files:
        click.echo(f"❌ Error: No layout JSON files in {layout_dir}", err=True)
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(f"output/{book_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Render each page
    for layout_path in layout_files:
        page_num = layout_path.stem  # e.g., "page_0001"
        output_path = output_dir / f"{page_num}.pdf"
        
        try:
            render_pdf(str(layout_path), paper_type, str(output_path))
            click.echo(f"  ✓ {page_num}.pdf")
        except Exception as e:
            click.echo(f"  ❌ {page_num}: {e}", err=True)
    
    click.echo(f"✓ Rendered {len(layout_files)} PDFs")
    click.echo(f"📁 Output PDFs saved to: {output_dir}/")


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.argument("book_id")
@click.option("--image-dir", default="input_images", help="Directory containing user images")
@click.option("--paper-type", default="A4", help="Paper type (A4, A5, etc.)")
@click.option("--scaling-mode", default="fill", type=click.Choice(["fill", "fit"]), help="Image scaling mode")
@click.pass_context
def pipeline(
    ctx: click.Context,
    pdf_path: str,
    book_id: str,
    image_dir: str,
    paper_type: str,
    scaling_mode: str,
) -> None:
    """Run full pipeline: detect → layout → render.
    
    Args:
        pdf_path: Path to scanned PDF file
        book_id: Unique book identifier
        image_dir: Directory containing user images
        paper_type: Paper size from config.PAPER_TYPES
        scaling_mode: Image scaling mode
    
    Output:
        - Detection JSON: detections/{book_id}/
        - Layout JSON: layouts/{book_id}/
        - Print-ready PDFs: output/{book_id}/
    """
    click.echo("=" * 60)
    click.echo("🎨 Sophie Baby Diary - Full Pipeline")
    click.echo("=" * 60)
    
    click.echo("\n📍 Phase 1: Detecting placeholders...")
    ctx.invoke(detect, pdf_path=pdf_path, book_id=book_id)
    
    click.echo("\n📍 Phase 2: Generating layouts...")
    ctx.invoke(layout, book_id=book_id, image_dir=image_dir, scaling_mode=scaling_mode)
    
    click.echo("\n📍 Phase 3: Rendering PDFs...")
    ctx.invoke(render, book_id=book_id, paper_type=paper_type)
    
    click.echo("\n" + "=" * 60)
    click.echo(f"✅ Pipeline complete! Check output/{book_id}/")
    click.echo("=" * 60)


if __name__ == "__main__":
    cli()
