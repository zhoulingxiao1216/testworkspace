import yaml

with open(r'd:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

for n in data['workflow']['graph']['nodes']:
    if n['id'] in ['extract_token', '8013_2', '8011']:
        print(f"Node: {n['id']}")
        if n['id'] == 'extract_token':
            print("outputs:", n['data'].get('outputs'))
        if n['id'] == '8013_2':
            print("variables:", n['data'].get('variables'))
