import json, os

# 分析两次结果
result_files = sorted(
    [f for f in os.listdir('.') if f.startswith('load_test_result_') and f.endswith('.json')],
    reverse=True
)

for i, fname in enumerate(result_files[:2]):
    with open(fname, encoding='utf-8') as f:
        data = json.load(f)
    records = data['records']
    quota_hits = [r for r in records if '429' in r['response_snippet']]
    ok_hits    = [r for r in records if '429' not in r['response_snippet']]

    # 找到哪些429是rate_limit（QPS）还是quota（额度）
    rate_limit_hits = [r for r in quota_hits if 'rate_limit_per_second' in r['response_snippet']]
    quota_exhaust   = [r for r in quota_hits if 'rate_limit_per_second' not in r['response_snippet']]

    print(f"\n{'='*60}")
    print(f"第 {2-i} 次压测: {fname}")
    print(f"  总发送={len(records)}  正常={len(ok_hits)}  被限={len(quota_hits)}")
    print(f"  QPS限流(rate_limit_per_second)={len(rate_limit_hits)}")
    print(f"  其他限制(额度耗尽?)           ={len(quota_exhaust)}")
    if quota_hits:
        # 打出第一条完整响应
        sample = quota_hits[0]
        print(f"\n  首条限流响应 seq={sample['seq']}:")
        print(f"  {sample['response_snippet']}")
