"""
Standard Markdown to PDF converter for online acceptance test reports.

Usage:
  python md_to_pdf.py <markdown_path> [pdf_path]

If pdf_path is omitted, the PDF is written next to the Markdown file.
The visual style follows the procurement-account acceptance report baseline.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import markdown2
from playwright.sync_api import sync_playwright


CSS_TEMPLATE = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: #2d3748;
    background: #fff;
    padding: 0;
}

h1 {
    font-size: 24px;
    font-weight: 700;
    color: #1a365d;
    border-bottom: 3px solid #2b6cb0;
    padding-bottom: 10px;
    margin: 0 0 18px 0;
    line-height: 1.4;
}

h2 {
    font-size: 16px;
    font-weight: 700;
    color: #1a365d;
    border-left: 5px solid #2b6cb0;
    padding-left: 12px;
    margin: 24px 0 12px 0;
    line-height: 1.5;
    page-break-after: avoid;
}

h3 {
    font-size: 14px;
    font-weight: 700;
    color: #2d3748;
    margin: 18px 0 8px 0;
    page-break-after: avoid;
}

h1 + blockquote,
h1 + p + blockquote {
    background: #f0f4f8;
    border: 1px solid #d2dce6;
    border-radius: 6px;
    padding: 14px 18px;
    margin: 0 0 10px 0;
    color: #2d3748;
    font-style: normal;
    font-size: 13px;
    page-break-inside: avoid;
}

blockquote {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 10px 14px;
    margin: 0 0 12px 0;
    color: #718096;
    font-size: 12px;
    font-style: italic;
}

blockquote p {
    margin: 0 0 4px 0;
}

blockquote p:last-child {
    margin: 0;
}

blockquote ul,
blockquote ol {
    margin: 4px 0 0 18px;
    padding: 0;
}

blockquote li {
    margin-bottom: 3px;
    font-style: normal;
    color: #2d3748;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 16px 0;
    font-size: 12.5px;
    page-break-inside: avoid;
}

th,
td {
    border: 1px solid #cbd5e0;
    padding: 7px 10px;
    text-align: left;
    vertical-align: top;
    line-height: 1.5;
}

th {
    background: #edf2f7;
    color: #1a365d;
    font-weight: 700;
    font-size: 12.5px;
    white-space: nowrap;
}

tr:nth-child(even) {
    background: #f7fafc;
}

ul,
ol {
    margin: 4px 0 12px 22px;
    padding: 0;
}

li {
    margin-bottom: 4px;
    line-height: 1.6;
}

li > ul,
li > ol {
    margin-top: 3px;
    margin-bottom: 3px;
}

p {
    margin: 0 0 8px 0;
}

code {
    font-family: 'Consolas', 'Courier New', monospace;
    background: #edf2f7;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 12px;
    color: #c53030;
}

hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 6px 0;
}

strong {
    font-weight: 700;
    color: #1a202c;
}

.pass {
    color: #16a34a;
    font-weight: 700;
}

.fail {
    color: #dc2626;
    font-weight: 700;
}

.warn {
    color: #d97706;
    font-weight: 700;
}

.muted {
    color: #718096;
}

h2,
h3 {
    page-break-after: avoid;
}

table,
blockquote {
    page-break-inside: avoid;
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Online Acceptance Test Report</title>
<style>
{css}
</style>
</head>
<body>
{content}
</body>
</html>"""


def md_to_pdf(md_path: str | os.PathLike[str], pdf_path: str | os.PathLike[str] | None = None) -> Path:
    """Convert a Markdown file to a styled PDF."""
    source = Path(md_path).resolve()
    if pdf_path is None:
        target = source.with_suffix(".pdf")
    else:
        target = Path(pdf_path).resolve()

    if not source.exists():
        raise FileNotFoundError(f"Markdown file not found: {source}")

    target.parent.mkdir(parents=True, exist_ok=True)
    md_content = source.read_text(encoding="utf-8")
    html_body = markdown2.markdown(
        md_content,
        extras=["tables", "fenced-code-blocks", "cuddled-lists", "break-on-newline"],
    )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    full_html = HTML_TEMPLATE.format(css=CSS_TEMPLATE, content=html_body)
    temp_html = source.parent / "_temp_report.html"

    try:
        temp_html.write_text(full_html, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(temp_html.as_uri(), wait_until="networkidle")
            page.pdf(
                path=str(target),
                format="A4",
                print_background=True,
                margin={
                    "top": "2cm",
                    "right": "2cm",
                    "bottom": "2.5cm",
                    "left": "2cm",
                },
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=f"""
                <div style="width:100%; text-align:center; font-size:9px; color:#999;
                            font-family: Segoe UI, PingFang SC, Microsoft YaHei, sans-serif;">
                    (c) 2026 Antigravity Test Engine - Generated: {timestamp}
                </div>""",
            )
            browser.close()
    finally:
        if temp_html.exists():
            temp_html.unlink()

    print(f"[OK] PDF saved: {target}")
    return target


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    md_file = sys.argv[1]
    pdf_file = sys.argv[2] if len(sys.argv) > 2 else None
    md_to_pdf(md_file, pdf_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
