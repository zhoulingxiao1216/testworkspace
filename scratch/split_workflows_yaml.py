import yaml

source_file = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
without_fjx_file = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml"

with open(source_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

for n in data['workflow']['graph']['nodes']:
    if n['id'] == '8013_2':
        code = n['data']['code']
        # Strip the FJX payload part
        if "fjx_payload =" in code:
            parts = code.split("fjx_payload =")
            before = parts[0]
            # Now we just need to return update_resp.text
            new_code = before + "return {\"result\": update_resp.text}\n    except Exception as e:\n        return {\"result\": str(e)}\n"
            n['data']['code'] = new_code
            n['data']['title'] = "更新用户SKU"

class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

with open(without_fjx_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)

print(f"Created: {without_fjx_file}")
