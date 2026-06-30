import os
from playwright.sync_api import sync_playwright

mermaid_code = """
graph TD
    classDef agent1 fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px,color:#0d47a1,font-weight:bold;
    classDef agent2 fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20,font-weight:bold;
    classDef io fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,color:#212121;
    classDef review fill:#fff3e0,stroke:#fb8c00,stroke-width:2px,color:#e65100;

    PRD["📄 需求资料输入 (PRD/原型/会议纪要)"]:::io

    subgraph "🤖 Agent 1: 测试设计师"
        A1_1["🔍 需求解析 & 7维度风险审计"]:::agent1
        A1_2["🛡️ 提取高危业务规则 (superpowers.md)"]:::agent1
        A1_3["📝 生成测试点大纲与测试用例"]:::agent1
        A1_4["⏱️ 评估工期 & 输出执行交接清单"]:::agent1
        A1_1 --> A1_2 --> A1_3 --> A1_4
    end

    PRD --> A1_1
    A1_4 -- "输出测试用例集" --> CrossReview

    CrossReview{"🔄 交叉评审工作流<br>(Cross-Agent Review)"}:::review

    subgraph "⚙️ Agent 2: 测试执行官"
        A2_1["🔧 E1-E2: 测试环境预检 & 队列编排"]:::agent2
        A2_2["🚀 E3: 混合执行 (API+Playwright+Browser)"]:::agent2
        A2_3["🛡️ 前置数据自愈 & 数据库只读"]:::agent2
        A2_4["📊 E4-E5: 结果判定、截图留证与生成报告"]:::agent2
        A2_1 --> A2_2
        A2_2 <--> A2_3
        A2_2 --> A2_4
    end

    CrossReview -- "评审通过" --> A2_1
    CrossReview -. "反馈修补建议" .-> A1_3

    Output["📉 最终验收交付<br>(执行报告 & 缺陷单)"]:::io
    A2_4 --> Output
"""

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

html_path = "mermaid_temp.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("Rendering mermaid diagram via Playwright...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Set viewport to something large enough to fit the diagram
        page.set_viewport_size({"width": 1200, "height": 1600})
        page.goto(f"file:///{os.path.abspath(html_path).replace(chr(92), '/')}", wait_until="networkidle")
        page.wait_for_selector('svg')
        page.wait_for_timeout(2000)
        
        # Take screenshot of the diagram
        element = page.query_selector('.mermaid')
        element.screenshot(path=r"D:\test_workspace\assets\dual_agent_workflow.png")
        browser.close()
    print("Mermaid diagram successfully saved to D:\\test_workspace\\assets\\dual_agent_workflow.png")
except Exception as e:
    print(f"Error: {e}")
