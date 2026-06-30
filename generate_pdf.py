import os
import markdown
from playwright.sync_api import sync_playwright

md_path = r'd:\test_workspace\test_workspace_两月工作述职报告.md'
html_path = r'd:\test_workspace\temp_report.html'
pdf_path = r'd:\test_workspace\test_workspace_两月工作述职报告.pdf'

with open(md_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace local paths to absolute file URIs
text = text.replace('assets/', f'file:///{os.path.abspath("d:/test_workspace/assets/").replace(chr(92), "/")}/')
text = text.replace('会员体系/', f'file:///{os.path.abspath("d:/test_workspace/会员体系/").replace(chr(92), "/")}/')

html_body = markdown.markdown(text, extensions=['tables'])

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Arial, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px; 
        }}
        h1, h2, h3 {{ 
            color: #2c3e50; 
            border-bottom: 1px solid #eee; 
            padding-bottom: 5px; 
            margin-top: 25px;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin-bottom: 20px; 
            font-size: 14px; 
        }}
        th, td {{ 
            border: 1px solid #ddd; 
            padding: 10px; 
            text-align: left; 
        }}
        th {{ 
            background-color: #f8f9fa; 
        }}
        img {{ 
            max-width: 100%; 
            height: auto; 
            display: block; 
            margin: 20px auto; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
            border-radius: 6px; 
        }}
        blockquote {{ 
            border-left: 4px solid #007bff; 
            background: #f8f9fa; 
            margin-left: 0; 
            padding: 12px 16px; 
            color: #555; 
            border-radius: 0 4px 4px 0; 
        }}
        code {{ 
            background: #f4f4f4; 
            padding: 2px 4px; 
            border-radius: 4px; 
            font-family: Consolas, monospace; 
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("HTML generated, starting Playwright PDF generation...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f'file:///{html_path.replace(chr(92), "/")}')
    page.wait_for_load_state('networkidle')
    page.pdf(
        path=pdf_path, 
        format='A4', 
        print_background=True, 
        margin={'top': '20mm', 'bottom': '20mm', 'left': '20mm', 'right': '20mm'}
    )
    browser.close()

if os.path.exists(html_path):
    os.remove(html_path)

print(f"PDF generated successfully at {pdf_path}")
