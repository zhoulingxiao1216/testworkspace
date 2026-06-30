import yaml
import copy

file_paths = [
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_带附加项.yml",
    r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml"
]

class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

def inject_login_flow(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    nodes = data['workflow']['graph']['nodes']
    edges = data['workflow']['graph']['edges']
    
    # 1. Add input variables to Start node (8001)
    for n in nodes:
        if n['id'] == '8001':
            vars_list = n['data'].get('variables', [])
            vars_list.append({
                'max_length': 48,
                'options': [],
                'required': True,
                'type': 'text-input',
                'variable': 'login_email',
                'label': '登录邮箱'
            })
            vars_list.append({
                'max_length': 48,
                'options': [],
                'required': True,
                'type': 'text-input',
                'variable': 'login_password',
                'label': '登录密码'
            })
            n['data']['variables'] = vars_list

    # 2. Add login_api node
    login_node = {
        'id': 'login_api',
        'type': 'custom',
        'data': {
            'type': 'http-request',
            'title': 'API自动登录',
            'method': 'post',
            'url': 'https://api.hubbuyer.com/api/login/login',
            'authorization': {'config': None, 'type': 'no-auth'},
            'params': '',
            'headers': 'content-type:application/json\nlanguage:korean\nnation:Korea\nlogintype:user',
            'body': {
                'type': 'json',
                'data': [{
                    'id': 'b1',
                    'key': '',
                    'type': 'text',
                    'value': '{"email":"{{#8001.login_email#}}","password":"{{#8001.login_password#}}","code":"","jump_url":""}'
                }]
            }
        },
        'position': {'x': 300, 'y': 382},
        'positionAbsolute': {'x': 300, 'y': 382},
        'width': 242,
        'height': 100,
        'selected': False,
        'sourcePosition': 'right',
        'targetPosition': 'left'
    }
    
    # 3. Add extract_token node
    extract_node = {
        'id': 'extract_token',
        'type': 'custom',
        'data': {
            'type': 'code',
            'title': '提取Token',
            'variables': [{
                'variable': 'login_body',
                'value_selector': ['login_api', 'body']
            }],
            'outputs': {'token': {'type': 'string'}},
            'code_language': 'python3',
            'code': "import json\ndef main(login_body):\n    try:\n        data = json.loads(login_body)\n        token = data.get('data', {}).get('login_token', '')\n        return {'token': token}\n    except:\n        return {'token': ''}"
        },
        'position': {'x': 550, 'y': 382},
        'positionAbsolute': {'x': 550, 'y': 382},
        'width': 242,
        'height': 100,
        'selected': False,
        'sourcePosition': 'right',
        'targetPosition': 'left'
    }
    
    nodes.append(login_node)
    nodes.append(extract_node)
    
    # 4. Add edges
    edges.append({
        'id': '8001-login_api',
        'source': '8001',
        'target': 'login_api',
        'sourceHandle': 'source',
        'targetHandle': 'target',
        'type': 'custom',
        'data': {'sourceType': 'custom'}
    })
    edges.append({
        'id': 'login_api-extract_token',
        'source': 'login_api',
        'target': 'extract_token',
        'sourceHandle': 'source',
        'targetHandle': 'target',
        'type': 'custom',
        'data': {'sourceType': 'custom'}
    })

    # 5. Modify 8011 and 8013 headers
    for n in nodes:
        if n['id'] == '8011':
            n['data']['headers'] = "authorization:{{#extract_token.token#}}\nlanguage:korean\nnation:Korea\ncontent-type:application/json"
        elif n['id'] == '8013':
            n['data']['headers'] = "authorization:{{#extract_token.token#}}\nuserlogintoken:{{#extract_token.token#}}\nlanguage:korean\nnation:Korea\ncontent-type:application/json"
        elif n['id'] == '8013_2':
            # Add variable
            n['data']['variables'].append({
                'variable': 'auth_token',
                'value_selector': ['extract_token', 'token']
            })
            # Update code
            old_code = n['data']['code']
            # Change def main signature
            new_code = old_code.replace("def main(mysku, final_spec_id):", "def main(mysku, final_spec_id, auth_token):")
            
            # Replace the hardcoded headers with dynamic ones
            import re
            headers_pattern = r'    headers = \{\s*"authorization": ".*?",\s*"userlogintoken": ".*?",\s*"content-type": "application/json",\s*"language": "korean",\s*"nation": "Korea"\s*\}'
            new_headers = '    headers = {\n        "authorization": auth_token,\n        "userlogintoken": auth_token,\n        "content-type": "application/json",\n        "language": "korean",\n        "nation": "Korea"\n    }'
            
            new_code = re.sub(headers_pattern, new_headers, new_code, flags=re.DOTALL)
            n['data']['code'] = new_code

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Successfully injected dynamic login into {file_path}")

for fp in file_paths:
    inject_login_flow(fp)
