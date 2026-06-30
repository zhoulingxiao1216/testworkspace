import yaml

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"

with open(file_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Find node 8011 and 8013 and update their headers securely
nodes = data['workflow']['graph']['nodes']
for node in nodes:
    if node['id'] in ['8011', '8013']:
        headers_str = node['data'].get('headers', '')
        # Clean up any previous bad headers
        headers_str = headers_str.replace("language:korean\nnation:Korea\n", "")
        headers_str = headers_str.replace("language: korean\nnation: Korea\n", "")
        headers_str = headers_str.replace("\\'", "'")
        
        lines = [line for line in headers_str.split('\n') if line.strip() and not line.startswith('language:') and not line.startswith('nation:')]
        
        # ensure content-type is at the end or wherever, just add the two headers
        new_lines = []
        for line in lines:
            if 'content-type' in line.lower():
                new_lines.append('language:korean')
                new_lines.append('nation:Korea')
            new_lines.append(line)
            
        if 'language:korean' not in new_lines:
            new_lines.append('language:korean')
            new_lines.append('nation:Korea')
            
        node['data']['headers'] = '\n'.join(new_lines)

# Save back using yaml.dump
class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

with open(file_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, Dumper=Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("success fixing YAML structure!")
