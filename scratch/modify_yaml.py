import os

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace edge
old_edge = """    - id: 8013-source-8014-target
      source: '8013'
      target: '8014'
      sourceHandle: source
      targetHandle: target
      type: custom
      data:
        isInIteration: true
        iteration_id: '8010'
      zIndex: 1002"""

new_edge = """    - id: 8013-source-8013_1-target
      source: '8013'
      target: '8013_1'
      sourceHandle: source
      targetHandle: target
      type: custom
      data:
        isInIteration: true
        iteration_id: '8010'
      zIndex: 1002
    - id: 8013_1-source-8013_2-target
      source: '8013_1'
      target: '8013_2'
      sourceHandle: source
      targetHandle: target
      type: custom
      data:
        isInIteration: true
        iteration_id: '8010'
      zIndex: 1002
    - id: 8013_2-source-8014-target
      source: '8013_2'
      target: '8014'
      sourceHandle: source
      targetHandle: target
      type: custom
      data:
        isInIteration: true
        iteration_id: '8010'
      zIndex: 1002"""

content = content.replace(old_edge, new_edge)

# Prepare nodes
new_nodes = """    - id: '8013_1'
      type: custom
      parentId: '8010'
      data:
        type: code
        title: 提取加购ID
        variables:
        - variable: cart_body
          value_selector:
          - '8013'
          - body
        - variable: status
          value_selector:
          - '8012'
          - status
        outputs:
          cart_detail_id:
            type: number
        code_language: python3
        code: |
          import json
          def main(cart_body, status):
              if status == 'PRICE_CHANGED':
                  return {"cart_detail_id": 0}
              try:
                  if isinstance(cart_body, str):
                      db = json.loads(cart_body)
                  else:
                      db = cart_body
                  if not isinstance(db, dict): db = {}
                  inner = db.get("data", {})
                  if not isinstance(inner, dict): inner = {}
                  
                  ids = inner.get("cart_detail_ids", [])
                  if isinstance(ids, list) and len(ids) > 0:
                      return {"cart_detail_id": int(ids[0])}
                  
                  cart_id = inner.get("cart_detail_id", 0)
                  return {"cart_detail_id": int(cart_id) if cart_id else 0}
              except:
                  return {"cart_detail_id": 0}
      position:
        x: 1250
        y: 100
      positionAbsolute:
        x: 2250
        y: 382
      width: 242
      height: 100
      selected: false
      sourcePosition: right
      targetPosition: left
    - id: '8013_2'
      type: custom
      parentId: '8010'
      data:
        type: code
        title: 更新用户SKU
        variables:
        - variable: cart_detail_id
          value_selector:
          - '8013_1'
          - cart_detail_id
        - variable: mysku
          value_selector:
          - '8010'
          - item
        outputs:
          result:
            type: string
        code_language: python3
        code: |
          import json, requests
          def main(cart_detail_id, mysku):
              if isinstance(mysku, list) and len(mysku) > 0: mysku = mysku[0]
              if isinstance(mysku, dict): sku_str = mysku.get('mysku', '')
              else: sku_str = ''
              
              if not cart_detail_id or cart_detail_id <= 0 or not sku_str:
                  return {"result": "skipped"}
                  
              url = "https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateSkuNumberData"
              headers = {
                  "authorization": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgwNTI5NjEsIm5iZiI6MTc3ODA1Mjk2MSwiZXhwIjoxODA5ODQ4MTYxLCJ0dGwiOjE4NDEzODQxNjEsImxvZ2luX2V4cCI6MTgwOTU4ODk2MSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.s-OurAj0yooRFDNYWczUjry8AZb2u7fFw6zeB0lWkXY",
                  "userlogintoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgxMjI3MzUsIm5iZiI6MTc3ODEyMjczNSwiZXhwIjoxODA5OTE3OTM1LCJ0dGwiOjE4NDE0NTM5MzUsImxvZ2luX2V4cCI6MTgwOTY1ODczNSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.BUMfHiBm2WzoqTOdptC0kFDIOHsMbBm8vAu2jS-_dDk",
                  "adminlogintoken": "",
                  "content-type": "application/json"
              }
              payload = {
                  "cart_detail_id": cart_detail_id,
                  "custom_sku": {"sku": ""},
                  "amazon_sku": {
                      "sku": sku_str,
                      "url": "",
                      "asin": "",
                      "fnsku": "",
                      "child_id": ""
                  },
                  "self_sku": []
              }
              try:
                  resp = requests.post(url, json=payload, headers=headers, timeout=10)
                  return {"result": resp.text}
              except Exception as e:
                  return {"result": str(e)}
      position:
        x: 1550
        y: 100
      positionAbsolute:
        x: 2550
        y: 382
      width: 242
      height: 100
      selected: false
      sourcePosition: right
      targetPosition: left
"""

old_node_8014 = "    - id: '8014'"
content = content.replace(old_node_8014, new_nodes + old_node_8014)

# We need to shift X positions for 8014 and the loop's end so they don't overlap visually
content = content.replace(
"""    - id: '8014'
      type: custom
      parentId: '8010'
      data:
        type: code
        title: 行结果汇总""",
"""    - id: '8014'
      type: custom
      parentId: '8010'
      data:
        type: code
        title: 行结果汇总"""
)
# Update positions for 8014 to avoid overlapping (originally x: 1250 -> 1850)
content = content.replace(
"""      position:
        x: 1250
        y: 100
      positionAbsolute:
        x: 2250
        y: 382
      width: 242
      height: 100
      selected: false
      sourcePosition: right
      targetPosition: left
    - id: '8030'""",
"""      position:
        x: 1850
        y: 100
      positionAbsolute:
        x: 2850
        y: 382
      width: 242
      height: 100
      selected: false
      sourcePosition: right
      targetPosition: left
    - id: '8030'"""
)

# And expand the iteration node width to fit the new nodes
content = content.replace(
"""    - id: '8010'
      type: custom
      data:
        type: iteration
        title: 循环加购与比价
        iterator_selector:
        - '8003'
        - order_list
        output_selector:
        - '8014'
        - result
        start_node_id: 8010start
      position:
        x: 1130
        y: 282
      positionAbsolute:
        x: 1130
        y: 282
      width: 1200""",
"""    - id: '8010'
      type: custom
      data:
        type: iteration
        title: 循环加购与比价
        iterator_selector:
        - '8003'
        - order_list
        output_selector:
        - '8014'
        - result
        start_node_id: 8010start
      position:
        x: 1130
        y: 282
      positionAbsolute:
        x: 1130
        y: 282
      width: 1800"""
)

# Also shift 8030 and 8099 x positions
content = content.replace(
"""    - id: '8030'
      type: custom
      data:
        type: code
        title: 生成比价与执行报告
        variables:
        - variable: results_array
          value_selector:
          - '8010'
          - output
        - variable: total
          value_selector:
          - '8003'
          - total
        - variable: parse_msg
          value_selector:
          - '8003'
          - message
        outputs:
          report:
            type: string
        code_language: python3
        code: "import json\\ndef main(results_array, total, parse_msg):\\n    success\\
          \\ = 0\\n    fail = 0\\n    intercepted = 0\\n    \\n    rows_detail = []\\n \\
          \\   \\n    for r in (results_array or []):\\n        try:\\n            if\\
          \\ isinstance(r, str): item = json.loads(r)\\n            else: item = r\\n\\
          \\            if not isinstance(item, dict): continue\\n            \\n   \\
          \\         row_idx = item.get(\\\"row\\\", \\\"-\\\")\\n            url = item.get(\\\"\\
          url\\\", \\\"\\\")\\n            msg = item.get(\\\"msg\\\", \\\"\\\")\\n            \\n\\
          \\            url_md = f\\\"[1688商品]({url})\\\" if url else \\\"-\\\"\\n         \\
          \\   \\n            if item.get(\\\"success\\\"):\\n                success +=\\
          \\ 1\\n                rows_detail.append(f\\\"| {row_idx} | {url_md} | ✅ 成功\\
          \\ | {msg} |\\\")\\n            else:\\n                if \\\"拦截\\\" in msg:\\n \\
          \\                   intercepted += 1\\n                    rows_detail.append(f\\\"\\
          | {row_idx} | {url_md} | ⚠️ 拦截 | {msg} |\\\")\\n                else:\\n   \\
          \\                 fail += 1\\n                    rows_detail.append(f\\\"\\
          | {row_idx} | {url_md} | ❌ 失败 | {msg} |\\\")\\n        except:\\n          \\
          \\  fail += 1\\n            \\n    rate = round(success / max(total, 1) * 100,\\
          \\ 1) if total > 0 else 0\\n    \\n    report = f\\\"\\\"\\\"## 批量加购执行报告\\n\\n| 指标\\
          \\ | 数值 |\\n|:--|:--|\\n| 解析结果 | {parse_msg} |\\n| 总行数 | {total} |\\n| 成功加购 |\\
          \\ {success} ✅ |\\n| **比价拦截** | **{intercepted} ⚠️** |\\n| 异常失败 | {fail} ❌\\
          \\ |\\n| 加购成功率 | {rate}% |\\n\\n### 执行明细\\n\\n| 行号 | 商品链接 | 状态 | 说明 |\\n|:--|:--|:--|:--|\\n\\
          \\\"\\\"\\\"\\n    report += \\\"\\\\n\\\".join(rows_detail)\\n    \\n    return {\\\"report\\\"\\
          : report}\"
      position:
        x: 1480
        y: 282
      positionAbsolute:
        x: 1480
        y: 282""",
"""    - id: '8030'
      type: custom
      data:
        type: code
        title: 生成比价与执行报告
        variables:
        - variable: results_array
          value_selector:
          - '8010'
          - output
        - variable: total
          value_selector:
          - '8003'
          - total
        - variable: parse_msg
          value_selector:
          - '8003'
          - message
        outputs:
          report:
            type: string
        code_language: python3
        code: "import json\\ndef main(results_array, total, parse_msg):\\n    success\\
          \\ = 0\\n    fail = 0\\n    intercepted = 0\\n    \\n    rows_detail = []\\n \\
          \\   \\n    for r in (results_array or []):\\n        try:\\n            if\\
          \\ isinstance(r, str): item = json.loads(r)\\n            else: item = r\\n\\
          \\            if not isinstance(item, dict): continue\\n            \\n   \\
          \\         row_idx = item.get(\\\"row\\\", \\\"-\\\")\\n            url = item.get(\\\"\\
          url\\\", \\\"\\\")\\n            msg = item.get(\\\"msg\\\", \\\"\\\")\\n            \\n\\
          \\            url_md = f\\\"[1688商品]({url})\\\" if url else \\\"-\\\"\\n         \\
          \\   \\n            if item.get(\\\"success\\\"):\\n                success +=\\
          \\ 1\\n                rows_detail.append(f\\\"| {row_idx} | {url_md} | ✅ 成功\\
          \\ | {msg} |\\\")\\n            else:\\n                if \\\"拦截\\\" in msg:\\n \\
          \\                   intercepted += 1\\n                    rows_detail.append(f\\\"\\
          | {row_idx} | {url_md} | ⚠️ 拦截 | {msg} |\\\")\\n                else:\\n   \\
          \\                 fail += 1\\n                    rows_detail.append(f\\\"\\
          | {row_idx} | {url_md} | ❌ 失败 | {msg} |\\\")\\n        except:\\n          \\
          \\  fail += 1\\n            \\n    rate = round(success / max(total, 1) * 100,\\
          \\ 1) if total > 0 else 0\\n    \\n    report = f\\\"\\\"\\\"## 批量加购执行报告\\n\\n| 指标\\
          \\ | 数值 |\\n|:--|:--|\\n| 解析结果 | {parse_msg} |\\n| 总行数 | {total} |\\n| 成功加购 |\\
          \\ {success} ✅ |\\n| **比价拦截** | **{intercepted} ⚠️** |\\n| 异常失败 | {fail} ❌\\
          \\ |\\n| 加购成功率 | {rate}% |\\n\\n### 执行明细\\n\\n| 行号 | 商品链接 | 状态 | 说明 |\\n|:--|:--|:--|:--|\\n\\
          \\\"\\\"\\\"\\n    report += \\\"\\\\n\\\".join(rows_detail)\\n    \\n    return {\\\"report\\\"\\
          : report}\"
      position:
        x: 2080
        y: 282
      positionAbsolute:
        x: 2080
        y: 282"""
)

content = content.replace(
"""    - id: '8099'
      type: custom
      data:
        type: end
        title: 结束
        outputs:
        - variable: report
          value_selector:
          - '8030'
          - report
      position:
        x: 1830
        y: 282
      positionAbsolute:
        x: 1830
        y: 282""",
"""    - id: '8099'
      type: custom
      data:
        type: end
        title: 结束
        outputs:
        - variable: report
          value_selector:
          - '8030'
          - report
      position:
        x: 2430
        y: 282
      positionAbsolute:
        x: 2430
        y: 282"""
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("success!")
