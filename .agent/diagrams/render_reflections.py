import os
from playwright.sync_api import sync_playwright

# Load mermaid source from file
mmd_path = os.path.join(os.path.dirname(__file__), 'reflections_memory_evolution.mmd')
with open(mmd_path, 'r', encoding='utf-8') as f:
    mermaid_code = f.read()

html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ 
        startOnLoad: true,
        theme: 'base',
        themeVariables: {{
            fontFamily: 'Microsoft YaHei',
            fontSize: '16px'
        }},
        flowchart: {{
            htmlLabels: true,
            curve: 'basis'
        }}
    }});
  </script>
  <style>
    body {{
      background: white;
      margin: 0;
      padding: 40px;
      display: inline-block;
    }}
    .mermaid {{
      background: white;
      padding: 20px;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="mermaid">
{mermaid_code}
  </div>
</body>
</html>
"""

html_path = os.path.join(os.path.dirname(__file__), 'mermaid_temp_reflections.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
os.makedirs(output_dir, exist_ok=True)
output_png_path = os.path.join(output_dir, 'reflections_memory_evolution.png')
output_png_hq_path = os.path.join(output_dir, 'reflections_memory_evolution@2x.png')
output_svg_path = os.path.join(output_dir, 'reflections_memory_evolution.svg')

print(f"Rendering mermaid diagram to: {output_svg_path} and {output_png_hq_path}")
try:
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1200, "height": 1600})
    file_url = f"file:///{html_path.replace('\\', '/')}"
    page.goto(file_url, wait_until="networkidle")
    page.wait_for_selector('svg', timeout=10000)
    page.wait_for_timeout(500)

    svg_el = page.query_selector('svg')
    if svg_el:
      # Export SVG source (vector, scales without blur)
      try:
        svg_html = page.evaluate('(el) => el.outerHTML', svg_el)
        # Ensure xmlns present for standalone SVG
        if 'xmlns="http' not in svg_html:
          svg_html = svg_html.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
        with open(output_svg_path, 'w', encoding='utf-8') as f:
          f.write('<?xml version="1.0" encoding="utf-8"?>\n')
          f.write(svg_html)
        print('Saved SVG:', output_svg_path)
      except Exception as e:
        print('Failed to extract SVG:', e)

      # Save high-resolution PNG by increasing viewport and screenshotting the element
      try:
        bbox = svg_el.bounding_box()
        if bbox:
          # Increase scale for higher DPI
          scale = 2
          width = int(bbox['width'] * scale)
          height = int(bbox['height'] * scale)
          page.set_viewport_size({"width": max(1200, width), "height": height + 200})
          page.wait_for_timeout(300)
          # Screenshot the SVG element (rasterized at larger viewport)
          svg_el.screenshot(path=output_png_hq_path)
          print('Saved high-res PNG:', output_png_hq_path)
        else:
          # Fallback: full-page screenshot of mermaid container
          container = page.query_selector('.mermaid')
          if container:
            container.screenshot(path=output_png_hq_path)
            print('Saved fallback high-res PNG:', output_png_hq_path)
      except Exception as e:
        print('Failed to save high-res PNG:', e)
    else:
      print('SVG element not found; no output saved.')

    browser.close()
except Exception as e:
  print('Error rendering diagram:', e)
