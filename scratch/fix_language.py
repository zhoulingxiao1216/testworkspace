import os

file_path = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix headers for 8011 and 8013 HTTP nodes
# We find:
#             content-type:application/json'
# And replace with:
#             language: korean
#             nation: Korea
#             content-type:application/json'

old_header_line = "            content-type:application/json'"
new_header_line = "            language: korean\n            nation: Korea\n            content-type:application/json'"

content = content.replace(old_header_line, new_header_line)

# Also fix 8013_2 Python script headers to include language and nation
old_py_headers = """                  "content-type": "application/json"
              }"""

new_py_headers = """                  "content-type": "application/json",
                  "language": "korean",
                  "nation": "Korea"
              }"""

content = content.replace(old_py_headers, new_py_headers)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("success fixing language headers!")
