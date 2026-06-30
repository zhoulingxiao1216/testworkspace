"""
Render selected PDF pages to PNG files for visual QA.

Usage:
  python render_pdf_pages.py <pdf_path> <output_dir> [pages]

Examples:
  python render_pdf_pages.py report.pdf tmp/rendered
  python render_pdf_pages.py report.pdf tmp/rendered 1,2,5
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def parse_pages(raw_pages: str | None, page_count: int) -> list[int]:
    """Return zero-based page indexes."""
    if not raw_pages:
        return list(range(page_count))

    indexes: list[int] = []
    for token in raw_pages.split(","):
        token = token.strip()
        if not token:
            continue
        page_no = int(token)
        if page_no < 1 or page_no > page_count:
            raise ValueError(f"Page out of range: {page_no}; PDF has {page_count} pages")
        indexes.append(page_no - 1)
    return indexes


def load_pdfium():
    """Import pypdfium2, retrying once with the workspace virtualenv."""
    try:
        import pypdfium2 as pdfium

        return pdfium
    except ModuleNotFoundError:
        if os.environ.get("REPORT_RENDER_REEXEC") == "1":
            raise

        current_file = Path(__file__).resolve()
        for parent in current_file.parents:
            candidate = parent / ".venv" / "Scripts" / "python.exe"
            if candidate.exists():
                env = os.environ.copy()
                env["REPORT_RENDER_REEXEC"] = "1"
                raise SystemExit(subprocess.call([str(candidate), str(current_file), *sys.argv[1:]], env=env))

        raise ModuleNotFoundError(
            "pypdfium2 is required for PDF rendering. Run with the workspace virtualenv "
            "or install pypdfium2 in the active Python environment."
        )


def render_pdf_pages(pdf_path: str, output_dir: str, raw_pages: str | None = None, scale: float = 2.0) -> list[Path]:
    pdfium = load_pdfium()
    source = Path(pdf_path).resolve()
    target_dir = Path(output_dir).resolve()
    if not source.exists():
        raise FileNotFoundError(f"PDF file not found: {source}")

    target_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(source))
    page_indexes = parse_pages(raw_pages, len(pdf))
    outputs: list[Path] = []

    for page_index in page_indexes:
        page = pdf[page_index]
        image = page.render(scale=scale).to_pil()
        output = target_dir / f"{source.stem}_page_{page_index + 1:02d}.png"
        image.save(output)
        outputs.append(output)
        print(f"[OK] Rendered page {page_index + 1}: {output}")

    return outputs


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    pages = sys.argv[3] if len(sys.argv) > 3 else None
    render_pdf_pages(sys.argv[1], sys.argv[2], pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
