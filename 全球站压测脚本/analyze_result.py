import json, sys, os

result_files = [f for f in os.listdir('.') if f.startswith('load_test_result_') and f.endswith('.json')]
result_files.sort(reverse=True)
fname = result_files[0]
print("分析文件:", fname)

with open(fname, encoding='utf-8') as f:
    data = json.load(f)

records = data['records']

# 区分正常与限流响应
quota_hits = [r for r in records if '429' in r['response_snippet']]
ok_hits    = [r for r in records if '429' not in r['response_snippet']]

print(f"\n触发限流(code=429)记录数: {len(quota_hits)}")
print(f"正常响应记录数           : {len(ok_hits)}")

if quota_hits:
    seqs = [r['seq'] for r in quota_hits]
    print(f"\n限流触发 seq 范围: {min(seqs)} ~ {max(seqs)}")
    print("\n前 10 条限流样本:")
    for r in quota_hits[:10]:
        print(f"  seq={r['seq']:>4}  {r['time']}  {r['response_snippet'][:110]}")

if ok_hits:
    print("\n前 3 条正常样本:")
    for r in ok_hits[:3]:
        print(f"  seq={r['seq']:>4}  elapsed={r['elapsed_ms']}ms  {r['response_snippet'][:100]}")

print("\n汇总:", json.dumps(data['summary'], ensure_ascii=False, indent=2))
