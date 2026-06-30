#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, sys, os

def decode_rtf_unicode(text):
    def replace_unicode(match):
        try: return chr(int(match.group(1)))
        except: return ''
    text = re.sub(r'\\uc0\\u(\d+)\s?', replace_unicode, text)
    text = re.sub(r'\\u(\d+)\s?', replace_unicode, text)
    return text

def extract_cells(rtf_content):
    cell_pattern = re.compile(r'\{\\pard\s+\\intbl\s+(.*?)\\cell\s+\\pard\s+\}', re.DOTALL)
    cells = cell_pattern.findall(rtf_content)
    result = []
    for cell in cells:
        cell = re.sub(r'\{\\pict[^}]*\}', '', cell, flags=re.DOTALL)
        text = decode_rtf_unicode(cell)
        text = re.sub(r'\\[a-zA-Z]+[-]?\d*\s?', '', text)
        text = re.sub(r'\\[^a-zA-Z]', '', text)
        text = re.sub(r'[{}]', '', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'\s+', ' ', text).strip()
        result.append(text)
    return result

def parse_bugs(cells):
    bugs = []
    i = 0
    while i < len(cells):
        if cells[i].strip() == 'ID' and i + 1 < len(cells):
            bug_id = cells[i + 1].strip()
            if bug_id.isdigit():
                title_idx = i - 9
                title = cells[title_idx].strip() if title_idx >= 0 else ''
                severity_idx = i - 5
                severity = cells[severity_idx].strip() if severity_idx >= 0 else ''
                status_idx = i + 3
                status = cells[status_idx].strip() if status_idx < len(cells) else ''
                desc_idx = i + 2
                desc = cells[desc_idx].strip() if desc_idx < len(cells) else ''

                bug_type_idx = title_idx + 2
                bug_type_val = cells[bug_type_idx].strip() if bug_type_idx < len(cells) else ''
                if 'BUG' in bug_type_val.upper() or 'bug' in bug_type_val.lower():
                    bug_type = 'Bug'
                elif '优化' in bug_type_val:
                    bug_type = '体验优化'
                else:
                    bug_type = 'Bug'
                    
                # 状态映射
                status_map = {
                    '已拒绝': '拒绝处理',
                    '已关闭': '已修复',
                    '未开始': '待处理',
                    '修复中': '修复中',
                    '已解决': '已修复',
                    '重新打开': '待处理',
                    '测试中': '修复中',
                }
                status_cn = status_map.get(status, status)

                # 推断角色
                infer_role = "未知"
                title_desc = title + " " + desc
                if "上传" in title_desc or "图片" in title_desc or "截图" in title_desc or "询盘" in title_desc or "报错" in desc and "业务" in desc:
                    infer_role = "业务员"
                elif "客服" in title_desc or "已读" in title_desc or "未读" in title_desc or "回执" in title_desc or "切换会话" in title_desc:
                    infer_role = "客服人员"
                elif "采购" in title_desc or "黑白名单" in title_desc or "账号" in title_desc:
                    infer_role = "采购员"
                elif "入库" in title_desc or "出库" in title_desc or "仓库" in title_desc:
                    infer_role = "仓库管理员"
                elif "IM" in title:
                    infer_role = "客服/业务员"
                elif "测试" in title_desc or "巡测" in title_desc or "中间件" in title_desc or "崩溃" in title_desc:
                    infer_role = "测试/IT人员"

                bugs.append({
                    'id': bug_id, 
                    'title': title,
                    'severity': severity, 
                    'status': status,
                    'status_cn': status_cn,
                    'bug_type': bug_type, 
                    'desc': desc[:150],
                    'infer_role': infer_role
                })
                i += 2
            else:
                i += 1
        else:
            i += 1
    return bugs

filepath = r"D:\test_workspace\00_全局测试规约库\用户行为规律库\_原始反馈\_TAPD导出\协润进出口_缺陷_20260421103630.rtf"
with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

cells = extract_cells(content)
bugs = parse_bugs(cells)

# 过滤掉 已拒绝 的记录
filtered_bugs = [b for b in bugs if b['status'] != '已拒绝' and b['status_cn'] != '拒绝处理']

# 保存 JSON
out_path = r"C:\tmp\parsed_bugs.json"
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({'total': len(bugs), 'filtered': len(filtered_bugs), 'bugs': filtered_bugs}, f, ensure_ascii=False, indent=2)

print(f"Total: {len(bugs)}, Filtered: {len(filtered_bugs)}")
