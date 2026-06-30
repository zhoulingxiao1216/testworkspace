import os
import markdown2
import base64
from playwright.sync_api import sync_playwright
import re

workspace_dir = r"D:\test_workspace"
os.chdir(workspace_dir)

md_path = "test_workspace_两月工作述职报告.md"
html_path = "temp_report.html"
pdf_path = "test_workspace_两月工作述职报告.pdf"

with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Convert Markdown to HTML
html = markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])

# Embed images as base64 to avoid local file CORS issues in Playwright
def embed_image(match):
    src = match.group(1)
    if not src.startswith("http") and not src.startswith("data:"):
        # Resolve path
        img_path = src if os.path.isabs(src) else os.path.join(workspace_dir, src)
        if os.path.exists(img_path):
            with open(img_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
            ext = os.path.splitext(img_path)[1][1:].lower()
            if ext == "jpg": ext = "jpeg"
            return f'src="data:image/{ext};base64,{encoded}"'
        else:
            print(f"Warning: Image not found: {img_path}")
            return f'src="{src}" style="border: 2px dashed red;" alt="MISSING IMAGE: {src}"'
    return match.group(0)

html = re.sub(r'src="([^"]+)"', embed_image, html)

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
    img {{
        max-width: 100%;
        max-height: 400px;
        display: block;
        margin: 10px auto;
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
    code {{
        background-color: #f7fafc;
        padding: 2px 4px;
        border-radius: 4px;
        font-family: "Consolas", monospace;
        color: #e53e3e;
    }}
</style>
</head>
<body>
{html}
</body>
</html>
"""

# Write HTML to a temporary file
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Generating PDF via Playwright...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--allow-file-access-from-files"])
        page = browser.new_page()
        # file:/// scheme for absolute path
        abs_html_path = "file:///" + os.path.abspath(html_path).replace("\\", "/")
        page.goto(abs_html_path, wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True, margin={"top":"1.5cm","right":"1.5cm","bottom":"1.5cm","left":"1.5cm"})
        browser.close()
    print(f"PDF successfully generated at: {os.path.abspath(pdf_path)}")
except Exception as e:
    print(f"Failed to generate PDF with Playwright: {e}")
