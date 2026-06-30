import shutil

source_file = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_比价版_修复死锁.yml"
with_fjx_file = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_带附加项.yml"
without_fjx_file = r"d:\test_workspace\dify工作流文档\加购工作流\dify_workflow_批量加购_无附加项.yml"

# Create the one WITHOUT add-ons
with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to remove the fjx_payload and fjx_resp part from the python code of 8013_2
start_str = "fjx_payload = {"
end_str = "        return {\"result\": f\"SKU: {update_resp.text} | FJX: {fjx_resp.text}\"}"

if start_str in content and end_str in content:
    idx_start = content.find(start_str)
    idx_end = content.find(end_str) + len(end_str)
    
    # We replace the entire block with just the SKU return
    before = content[:idx_start]
    after = content[idx_end:]
    
    replacement = "return {\"result\": f\"SKU: {update_resp.text}\"}"
    new_content = before + replacement + after
    
    # Change the node title back from 更新SKU及附加项 to 更新用户SKU
    new_content = new_content.replace("title: 更新SKU及附加项", "title: 更新用户SKU")
    
    with open(without_fjx_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Created: {without_fjx_file}")
else:
    print("Failed to find fjx block to remove!")
