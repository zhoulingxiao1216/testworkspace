import os

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_str = """                  "custom_sku": {"sku": ""},
                  "amazon_sku": {
                      "sku": sku_str,"""
new_str = """                  "custom_sku": {"sku": sku_str},
                  "amazon_sku": {
                      "sku": sku_str,"""

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replace success!")
else:
    print("String not found!")
