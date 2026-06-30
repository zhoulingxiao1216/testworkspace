import yaml

file_paths = [
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_带附加项.yml",
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml"
]

class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

def fix_price_logic(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    for n in data['workflow']['graph']['nodes']:
        if n['id'] == '8012':
            old_code = n['data']['code']
            # We want to change:
            # try: api_price = float(best_match.get("consignPrice") or best_match.get("price") or 0)
            # to:
            # try: api_price = float(best_match.get("price") or best_match.get("consignPrice") or 0)
            new_code = old_code.replace(
                'try: api_price = float(best_match.get("consignPrice") or best_match.get("price") or 0)',
                'try: api_price = float(best_match.get("price") or best_match.get("consignPrice") or 0)'
            )
            n['data']['code'] = new_code

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Fixed price logic in {file_path}")

for fp in file_paths:
    fix_price_logic(fp)
