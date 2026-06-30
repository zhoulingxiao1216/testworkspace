import re

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change the node title from "更新用户SKU" to "更新SKU及附加项"
content = content.replace("title: 更新用户SKU", "title: 更新SKU及附加项")

# Update python code
old_code_block = """        update_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateSkuNumberData", json=payload, headers=headers, timeout=10)
        return {"result": update_resp.text}
    except Exception as e:"""

new_code_block = """        update_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateSkuNumberData", json=payload, headers=headers, timeout=10)
        
        fjx_payload = {
            "cart_detail_id_arr": [found_cart_detail_id],
            "check_config_uuid": "C25-0617-8133",
            "fjx_config_uuid_arr": ["F25-0821-5931"],
            "user_fjx_config_uuid_arr": []
        }
        fjx_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateCheckFjx", json=fjx_payload, headers=headers, timeout=10)
        
        return {"result": f"SKU: {update_resp.text} | FJX: {fjx_resp.text}"}
    except Exception as e:"""

content = content.replace(old_code_block, new_code_block)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("success updating fjx config!")
