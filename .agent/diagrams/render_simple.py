import os
from playwright.sync_api import sync_playwright

mmd_path = os.path.join(os.path.dirname(__file__), 'simple_reflections.mmd')
with open(mmd_path, 'r', encoding='utf-8') as f:
    mermaid_code = f.read()

html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad:true, theme:'base', flowchart:{{htmlLabels:true}} }});
  </script>
  <style>body{{font-family:Microsoft YaHei;padding:20px}}.mermaid{{padding:10px;border-radius:6px}}</style>
</head>
<body>
  <div class="mermaid">{mermaid_code}</div>
</body>
</html>
"""

html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'mermaid_temp_simple.html'))
from pathlib import Path
file_url = Path(html_path).as_uri()
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
os.makedirs(output_dir, exist_ok=True)
output_svg = os.path.join(output_dir, 'simple_reflections.svg')
output_png = os.path.join(output_dir, 'simple_reflections@2x.png')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 800, "height": 600})
    page.goto(file_url, wait_until='networkidle')
    page.wait_for_selector('svg', timeout=5000)
    page.wait_for_timeout(300)
    svg_el = page.query_selector('svg')
    if svg_el:
        svg_html = page.evaluate('(el) => el.outerHTML', svg_el)
        if 'xmlns="http' not in svg_html:
            svg_html = svg_html.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
        with open(output_svg, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write(svg_html)
        bbox = svg_el.bounding_box()
        if bbox:
            scale = 2
            page.set_viewport_size({"width": max(800, int(bbox['width']*scale)), "height": int(bbox['height']*scale)+100})
            page.wait_for_timeout(200)
            svg_el.screenshot(path=output_png)
    browser.close()

print('Saved:', output_svg, output_png)
