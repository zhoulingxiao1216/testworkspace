import json

with open('load_test_result_20260702_140824.json', encoding='utf-8') as f:
    data = json.load(f)
records = data['records']

# 按 seq 排序
records_sorted = sorted(records, key=lambda x: x['seq'])

# 正常成功的
ok_hits = [r for r in records_sorted if '429' not in r['response_snippet']]
print("第2次 正常请求数:", len(ok_hits))
if ok_hits:
    seqs = [r['seq'] for r in ok_hits]
    print("seq 范围:", min(seqs), "~", max(seqs))
    print("\n最后5条正常响应:")
    for r in ok_hits[-5:]:
        print("  seq=%4d  %s" % (r['seq'], r['response_snippet'][:80]))

# 含 429 但不含 rate_limit_per_second 的
quota_exhaust = [r for r in records_sorted if '429' in r['response_snippet'] and 'rate_limit_per_second' not in r['response_snippet']]
print("\n额度耗尽类响应数:", len(quota_exhaust))
if quota_exhaust:
    print("首条样本:")
    try:
        body = json.loads(quota_exhaust[0]['response_snippet'])
        print(json.dumps(body, ensure_ascii=False, indent=2))
    except Exception:
        print(quota_exhaust[0]['response_snippet'])
    print("\n最后5条:")
    for r in quota_exhaust[-5:]:
        print("  seq=%4d  %s" % (r['seq'], r['response_snippet'][:100]))
