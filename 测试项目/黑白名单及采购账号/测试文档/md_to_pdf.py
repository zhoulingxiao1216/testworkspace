"""
标准化 MD → PDF 报告生成器
===========================
使用 markdown2 + Playwright (Chromium) 将 Markdown 报告转为高质量 PDF。
CSS 样式对齐 v2 基准 PDF 格式，可复用于所有后续项目的上线验收测试报告。

用法：
  python md_to_pdf.py <md文件路径> [pdf输出路径]

  - 如不指定 pdf 路径，将与 md 同名输出 .pdf

示例：
  python md_to_pdf.py 上线验收测试报告_20260428.md
  python md_to_pdf.py 上线验收测试报告_20260428.md output.pdf
"""
import sys
import os
import markdown2
from playwright.sync_api import sync_playwright
from datetime import datetime

# ============================================================
# CSS 样式模板 —— 对齐 v2 PDF 基准格式
# ============================================================
CSS_TEMPLATE = """
@page {
    size: A4;
    margin: 2cm 2cm 2.5cm 2cm;
    @bottom-center {
        content: "© 2026 Antigravity Test Engine · Generated: TIMESTAMP_PLACEHOLDER";
        font-size: 9px;
        color: #999;
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
}

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

/* ── 主标题 H1 ─────────────────────────── */
h1 {
    font-size: 24px;
    font-weight: 700;
    color: #1a365d;
    border-bottom: 3px solid #2b6cb0;
    padding-bottom: 10px;
    margin: 0 0 18px 0;
    line-height: 1.4;
}

/* ── 章节标题 H2 —— 左侧蓝色竖条 ───────── */
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

/* ── 子章节标题 H3 ─────────────────────── */
h3 {
    font-size: 14px;
    font-weight: 700;
    color: #2d3748;
    margin: 18px 0 8px 0;
    page-break-after: avoid;
}

/* ── H1 后紧跟的第一个 blockquote = 报告摘要框 ── */
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

/* ── 普通 blockquote（依据来源等） ──────── */
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

/* 摘要框中的列表 */
blockquote ul, blockquote ol {
    margin: 4px 0 0 18px;
    padding: 0;
}
blockquote li {
    margin-bottom: 3px;
    font-style: normal;
    color: #2d3748;
}

/* ── 表格 ──────────────────────────────── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 16px 0;
    font-size: 12.5px;
    page-break-inside: avoid;
}

th, td {
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

/* ── 列表 ──────────────────────────────── */
ul, ol {
    margin: 4px 0 12px 22px;
    padding: 0;
}

li {
    margin-bottom: 4px;
    line-height: 1.6;
}

li > ul, li > ol {
    margin-top: 3px;
    margin-bottom: 3px;
}

/* ── 段落 ──────────────────────────────── */
p {
    margin: 0 0 8px 0;
}

/* ── 行内代码 ──────────────────────────── */
code {
    font-family: 'Consolas', 'Courier New', monospace;
    background: #edf2f7;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 12px;
    color: #c53030;
}

/* ── 分割线（隐藏，用 h2 的 margin 替代） ── */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 6px 0;
}

/* ── 加粗 ──────────────────────────────── */
strong {
    font-weight: 700;
    color: #1a202c;
}

/* ── 打印优化 ──────────────────────────── */
h2, h3 {
    page-break-after: avoid;
}
table, blockquote {
    page-break-inside: avoid;
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>上线验收测试报告</title>
<style>
{css}
</style>
</head>
<body>
{content}
</body>
</html>"""


def md_to_pdf(md_path, pdf_path=None):
    """Convert a Markdown file to a styled PDF matching v2 format."""
    if pdf_path is None:
        pdf_path = os.path.splitext(md_path)[0] + '.pdf'

    # Read MD
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert MD → HTML
    html_body = markdown2.markdown(
        md_content,
        extras=['tables', 'fenced-code-blocks', 'cuddled-lists', 'break-on-newline']
    )

    # Inject timestamp into CSS
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    css = CSS_TEMPLATE.replace('TIMESTAMP_PLACEHOLDER', timestamp)

    # Build full HTML
    full_html = HTML_TEMPLATE.format(css=css, content=html_body)

    # Write temp HTML
    temp_html = os.path.join(os.path.dirname(os.path.abspath(md_path)), '_temp_report.html')
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(full_html)

    # HTML → PDF via Playwright Chromium
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            file_url = 'file:///' + os.path.abspath(temp_html).replace('\\', '/')
            page.goto(file_url, wait_until='networkidle')

            page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                margin={
                    'top': '2cm',
                    'right': '2cm',
                    'bottom': '2.5cm',
                    'left': '2cm'
                },
                display_header_footer=True,
                header_template='<span></span>',
                footer_template=f'''
                <div style="width:100%; text-align:center; font-size:9px; color:#999;
                            font-family: Segoe UI, PingFang SC, Microsoft YaHei, sans-serif;">
                    © 2026 Antigravity Test Engine · Generated: {timestamp}
                </div>'''
            )
            browser.close()
        print(f'[OK] PDF saved: {pdf_path}')
    except Exception as e:
        print(f'[ERROR] PDF generation failed: {e}')
        raise
    finally:
        if os.path.exists(temp_html):
            os.remove(temp_html)

    return pdf_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    md_file = sys.argv[1]
    pdf_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(md_file):
        print(f'[ERROR] File not found: {md_file}')
        sys.exit(1)

    md_to_pdf(md_file, pdf_file)
