import yaml
import re

file_paths = [
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_带附加项.yml",
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml"
]

class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

def add_moq_check(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    for n in data['workflow']['graph']['nodes']:
        if n['id'] == '8012':
            old_code = n['data']['code']
            
            # 1. Add moq extraction
            if "uuid = str(inner.get(" not in old_code:
                print("Could not find insertion point for MOQ extraction!")
                continue
                
            if "moq = int(inner.get(\"minOrderQuantity\", 1))" not in old_code:
                old_code = old_code.replace(
                    '    uuid = str(inner.get("product_index_uuid", ""))',
                    '    moq = int(inner.get("minOrderQuantity", 1))\n    excel_qty = int(excel_item.get("quantity", 1)) if isinstance(excel_item, dict) else 1\n    uuid = str(inner.get("product_index_uuid", ""))'
                )

            # 2. Add MOQ check logic before price logic
            if "低于起批量" not in old_code:
                moq_check_code = '''        # MOQ拦截逻辑
        if excel_qty < moq:
            return {
                "final_sku_id": -1,
                "final_spec_id": str(best_match.get("specId") or ""),
                "product_index_uuid": uuid,
                "status": f"低于起批量 (需求:{excel_qty} MOQ:{moq})",
                "api_price": api_price,
                "excel_price": excel_price
            }
        
        # 比价拦截逻辑'''
                
                old_code = old_code.replace('        # 比价拦截逻辑', moq_check_code)

            n['data']['code'] = old_code

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Added MOQ check logic in {file_path}")

for fp in file_paths:
    add_moq_check(fp)
