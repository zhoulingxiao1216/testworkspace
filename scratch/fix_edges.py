import yaml

file_paths = [
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_带附加项.yml",
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml"
]

class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

def fix_edges(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    edges = data['workflow']['graph']['edges']
    
    # We want the chain to be 8001 -> login_api -> extract_token -> 8002
    # So we remove any edge from 8001 to 8002
    edges = [e for e in edges if not (e['source'] == '8001' and e['target'] == '8002')]
    
    # Check if extract_token -> 8002 exists
    has_extract_to_8002 = any(e['source'] == 'extract_token' and e['target'] == '8002' for e in edges)
    if not has_extract_to_8002:
        edges.append({
            'id': 'extract_token-8002',
            'source': 'extract_token',
            'target': '8002',
            'sourceHandle': 'source',
            'targetHandle': 'target',
            'type': 'custom',
            'data': {'sourceType': 'custom'}
        })
        
    data['workflow']['graph']['edges'] = edges

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Fixed edges in {file_path}")

for fp in file_paths:
    fix_edges(fp)
