import os

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# I will replace the entire code block for 8013_2
import re

# find the exact block for 8013_2
pattern = r"    - id: '8013_2'\s*type: custom\s*parentId: '8010'\s*data:\s*type: code\s*title: 更新用户SKU\s*variables:(.*?)\s*outputs:(.*?)\s*code_language: python3\s*code: \|(.*?)      position:"
# wait, regex with DOTALL is risky on big files, I'll use string finding.

start_marker = "    - id: '8013_2'\n      type: custom\n      parentId: '8010'\n      data:\n        type: code\n        title: 更新用户SKU"
if start_marker not in content:
    print("Cannot find 8013_2")
    exit()

code_start_marker = "        code_language: python3\n        code: |\n"
position_marker = "      position:\n        x: 1550"

idx_code_start = content.find(code_start_marker, content.find(start_marker)) + len(code_start_marker)
idx_position = content.find(position_marker, idx_code_start)

old_code = content[idx_code_start:idx_position]

new_code = """          import json, requests
          def main(cart_detail_id, mysku):
              if isinstance(mysku, list) and len(mysku) > 0: mysku = mysku[0]
              if isinstance(mysku, dict): 
                  sku_str = mysku.get('mysku', '')
                  item_id_to_find = str(mysku.get('item_id', ''))
              else: 
                  sku_str = ''
                  item_id_to_find = ''
              
              if not sku_str or not item_id_to_find:
                  return {"result": "skipped (no sku)"}
                  
              headers = {
                  "authorization": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgwNTI5NjEsIm5iZiI6MTc3ODA1Mjk2MSwiZXhwIjoxODA5ODQ4MTYxLCJ0dGwiOjE4NDEzODQxNjEsImxvZ2luX2V4cCI6MTgwOTU4ODk2MSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.s-OurAj0yooRFDNYWczUjry8AZb2u7fFw6zeB0lWkXY",
                  "userlogintoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgxMjI3MzUsIm5iZiI6MTc3ODEyMjczNSwiZXhwIjoxODA5OTE3OTM1LCJ0dGwiOjE4NDE0NTM5MzUsImxvZ2luX2V4cCI6MTgwOTY1ODczNSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.BUMfHiBm2WzoqTOdptC0kFDIOHsMbBm8vAu2jS-_dDk",
                  "content-type": "application/json"
              }
              
              try:
                  resp = requests.post("https://api.hubbuyer.com/api_b2b/cart/list", json={}, headers=headers, timeout=10)
                  cart_data = resp.json()
                  
                  found_cart_detail_id = 0
                  seller_data_list = cart_data.get('data', {}).get('seller_data', [])
                  for seller in seller_data_list:
                      for item in seller.get('data', []):
                          if str(item.get('item_id')) == item_id_to_find:
                              found_cart_detail_id = int(item.get('id', 0))
                              break
                      if found_cart_detail_id:
                          break
                          
                  if not found_cart_detail_id:
                      return {"result": "skipped (cart_detail_id not found)"}
                      
                  payload = {
                      "cart_detail_id": found_cart_detail_id,
                      "custom_sku": {"sku": sku_str},
                      "amazon_sku": {
                          "sku": sku_str,
                          "url": "",
                          "asin": "",
                          "fnsku": "",
                          "child_id": ""
                      },
                      "self_sku": []
                  }
                  
                  update_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateSkuNumberData", json=payload, headers=headers, timeout=10)
                  return {"result": update_resp.text}
              except Exception as e:
                  return {"result": str(e)}
"""

content = content[:idx_code_start] + new_code + content[idx_position:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("success code replacement!")
