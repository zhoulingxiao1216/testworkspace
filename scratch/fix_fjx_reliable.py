import re

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# I will use a reliable regex to insert the fjx code right before the `return {"result": update_resp.text}`

pattern = r'(        update_resp = requests\.post\("https://api\.hubbuyer\.com/api_b2b/cartQuoteStep1/updateSkuNumberData", json=payload, headers=headers, timeout=10\)\n\s+return \{"result": update_resp\.text\})'

match = re.search(pattern, content)
if match:
    replacement = """        update_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateSkuNumberData", json=payload, headers=headers, timeout=10)
        
        fjx_payload = {
            "cart_detail_id_arr": [found_cart_detail_id],
            "check_config_uuid": "C25-0617-8133",
            "fjx_config_uuid_arr": ["F25-0821-5931"],
            "user_fjx_config_uuid_arr": []
        }
        fjx_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateCheckFjx", json=fjx_payload, headers=headers, timeout=10)
        
        return {"result": f"SKU: {update_resp.text} | FJX: {fjx_resp.text}"}"""
    
    content = content.replace(match.group(1), replacement)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: FJX code injected!")
else:
    print("FAILED: Could not find the injection point!")
