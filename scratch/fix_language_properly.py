import re

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the specific newline sequence for content-type
content = re.sub(
    r'\n\n\s*content-type:application/json\'', 
    r'\nlanguage:korean\nnation:Korea\ncontent-type:application/json\'', 
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("success fixing language headers properly!")
