import yaml
import re

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"

with open(file_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Find node 8011 and 8013 and update their headers securely
nodes = data['workflow']['graph']['nodes']
for node in nodes:
    if node['id'] in ['8011', '8013']:
        headers_str = node['data'].get('headers', '')
        
        # We need to completely rewrite the headers string to be safe
        # It should just have authorization, language, nation, content-type
        
        # Extract authorization token using regex
        auth_token = ''
        auth_match = re.search(r'authorization:\s*([^\s\n]+)', headers_str)
        if auth_match:
            auth_token = auth_match.group(1).strip().replace("\\'", "").replace("'", "")
            
        clean_headers = f"authorization:{auth_token}\nlanguage:korean\nnation:Korea\ncontent-type:application/json"
        
        node['data']['headers'] = clean_headers

# Save back using yaml.dump
class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

with open(file_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("success rewriting headers from scratch!")
