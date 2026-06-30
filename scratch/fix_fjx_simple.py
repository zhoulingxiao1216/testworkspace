import yaml

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"

with open(file_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

for n in data['workflow']['graph']['nodes']:
    if n['id'] == '8013_2':
        old_code = n['data']['code']
        
        # We find the exact line to replace
        search_str = 'return {"result": update_resp.text}'
        
        if search_str in old_code:
            new_code = old_code.replace(
                search_str,
                """fjx_payload = {
            "cart_detail_id_arr": [found_cart_detail_id],
            "check_config_uuid": "C25-0617-8133",
            "fjx_config_uuid_arr": ["F25-0821-5931"],
            "user_fjx_config_uuid_arr": []
        }
        fjx_resp = requests.post("https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateCheckFjx", json=fjx_payload, headers=headers, timeout=10)
        return {"result": f"SKU: {update_resp.text} | FJX: {fjx_resp.text}"}"""
            )
            n['data']['code'] = new_code
            print("Successfully replaced code in memory!")
        else:
            print("Could not find search_str in old_code!")

# Save back using yaml.dump
class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

with open(file_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("Saved YAML!")
