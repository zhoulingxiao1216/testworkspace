import json
import sys

with open('c:/Users/23282/Desktop/AI/项目/global-v2/docs/pm/fields.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for page, fields in data.items():
    if "基础库" in page or "定价" in page or "管理" in page or "详情" in page:
        print(f"--- {page} ---")
        for field in fields:
            if "：" in field or ":" in field or "日期" in field or "状态" in field:
                print(field)
