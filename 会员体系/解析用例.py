import re

def main():
    with open(r'd:\test_workspace\会员体系\测试文档\会员体系优化测试用例集.md', 'r', encoding='utf-8') as f:
        text = f.read()

    cases = []
    blocks = re.split(r'#{4} (TC-[\w\-]+)', text)
    if len(blocks) < 2:
        print("No cases found")
        return
        
    for i in range(1, len(blocks), 2):
        tc_id = blocks[i].strip()
        content = blocks[i+1]
        title_match = re.search(r'(.*)', content)
        title = title_match.group(1).strip() if title_match else ''
        priority_match = re.search(r'\|\s*\*\*优先级\*\*\s*\|\s*(Critical|High|Medium|Low)', content, re.IGNORECASE)
        priority = priority_match.group(1).strip().capitalize() if priority_match else 'Medium'
        
        cases.append({
            'id': tc_id,
            'title': title,
            'priority': priority
        })

    priority_map = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
    cases.sort(key=lambda x: priority_map.get(x['priority'], 5))

    with open(r'd:\test_workspace\会员体系\测试文档\执行队列清单.md', 'w', encoding='utf-8') as fw:
        fw.write('# Agent 2 执行队列\n\n')
        fw.write('| 用例编号 | 优先级 | 用例标题 |\n')
        fw.write('|:---|:---|:---|\n')
        for c in cases:
            fw.write(f'| {c["id"]} | {c["priority"]} | {c["title"]} |\n')

    print(f'Successfully wrote {len(cases)} cases to 执行队列清单.md')

if __name__ == "__main__":
    main()
