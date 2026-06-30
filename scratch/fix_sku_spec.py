import re

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update variables section of 8013_2
old_variables = """        variables:
        - variable: cart_detail_id
          value_selector:
          - '8013_1'
          - cart_detail_id
        - variable: mysku
          value_selector:
          - '8010'
          - item"""

new_variables = """        variables:
        - variable: mysku
          value_selector:
          - '8010'
          - item
        - variable: final_spec_id
          value_selector:
          - '8012'
          - final_spec_id"""

content = content.replace(old_variables, new_variables)

# 2. Update python code of 8013_2
old_code_start = """        code_language: python3
        code: |
          import json, requests
          def main(cart_detail_id, mysku):
              if isinstance(mysku, list) and len(mysku) > 0: mysku = mysku[0]
              if isinstance(mysku, dict): 
                  sku_str = mysku.get('mysku', '')
                  item_id_to_find = str(mysku.get('item_id', ''))
              else: 
                  sku_str = ''
                  item_id_to_find = ''
              
              if not sku_str or not item_id_to_find:
                  return {"result": "skipped (no sku)"}"""

new_code_start = """        code_language: python3
        code: |
          import json, requests
          def main(mysku, final_spec_id):
              if isinstance(mysku, list) and len(mysku) > 0: mysku = mysku[0]
              if isinstance(mysku, dict): 
                  sku_str = mysku.get('mysku', '')
                  item_id_to_find = str(mysku.get('item_id', ''))
              else: 
                  sku_str = ''
                  item_id_to_find = ''
              
              spec_id_to_find = str(final_spec_id) if final_spec_id else ''
              
              if not sku_str or not item_id_to_find or not spec_id_to_find:
                  return {"result": "skipped (missing info)"}"""

content = content.replace(old_code_start, new_code_start)

old_match_logic = """                  for seller in seller_data_list:
                      for item in seller.get('data', []):
                          if str(item.get('item_id')) == item_id_to_find:
                              found_cart_detail_id = int(item.get('id', 0))
                              break
                      if found_cart_detail_id:
                          break"""

new_match_logic = """                  for seller in seller_data_list:
                      for item in seller.get('data', []):
                          item_match = str(item.get('item_id')) == item_id_to_find
                          spec_match = str(item.get('attribute', {}).get('specId')) == spec_id_to_find
                          
                          if item_match and spec_match:
                              found_cart_detail_id = int(item.get('id', 0))
                              break
                      if found_cart_detail_id:
                          break"""

content = content.replace(old_match_logic, new_match_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("success code replacement 2!")
