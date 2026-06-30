import os
import markdown2
from playwright.sync_api import sync_playwright

workspace_dir = r"d:\test_workspace\表单下载\测试文档"
os.chdir(workspace_dir)

md_path = "上线验收测试报告_2026-05-20.md"
html_path = "temp_report.html"
pdf_path = "表单下载_上线验收测试报告.pdf"

with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Convert Markdown to HTML
html = markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])

# Basic CSS for layout
html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 14px;
        color: #333333;
        line-height: 1.6;
        padding: 20px;
    }}
    h1 {{
        color: #1a202c;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.3em;
        text-align: center;
    }}
    h2 {{
        color: #2d3748;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0.2em;
        margin-top: 1.5em;
    }}
    h3 {{
        color: #4a5568;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }}
    th, td {{
        border: 1px solid #cbd5e0;
        padding: 8px 12px;
        text-align: left;
    }}
    th {{
        background-color: #edf2f7;
        font-weight: bold;
    }}
    blockquote {{
        border-left: 4px solid #4299e1;
        margin: 1em 0;
        padding: 0.5em 1em;
        background-color: #ebf8ff;
        color: #2b6cb0;
    }}
</style>
</head>
<body>
{html}
</body>
</html>
"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Generating PDF via Playwright...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        abs_html_path = "file:///" + os.path.abspath(html_path).replace("\\", "/")
        page.goto(abs_html_path, wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True, margin={"top":"1.5cm","right":"1.5cm","bottom":"1.5cm","left":"1.5cm"})
        browser.close()
    print(f"PDF successfully generated at: {os.path.abspath(pdf_path)}")
except Exception as e:
    import traceback
    traceback.print_exc()
