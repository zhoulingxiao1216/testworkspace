import os
from playwright.sync_api import sync_playwright

svgs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'reflections_memory_evolution.svg')),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'simple_reflections.svg')),
]

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
scale = 4

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for svg in svgs:
        name = os.path.splitext(os.path.basename(svg))[0]
        out_png = os.path.join(output_dir, f"{name}@{scale}x.png")
        file_url = f"file:///{svg.replace('\\', '/')}"
        page.goto(file_url, wait_until='networkidle')
        page.wait_for_selector('svg', timeout=10000)
        svg_el = page.query_selector('svg')
        if not svg_el:
            print('SVG element not found for', svg)
            continue
        bbox = svg_el.bounding_box()
        if not bbox:
            print('Could not get bbox for', svg)
            continue
        width = int(bbox['width'] * scale)
        height = int(bbox['height'] * scale)
        page.set_viewport_size({"width": max(1200, width), "height": height + 200})
        page.wait_for_timeout(300)
        # Use screenshot of svg element for clean crop
        svg_el.screenshot(path=out_png)
        print('Saved', out_png)
    browser.close()

print('Done')
