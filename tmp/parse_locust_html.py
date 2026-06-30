# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path

html_path = Path(r"d:\test_workspace\全球站压测脚本\测试文档\2026-06-18\stress_main_47r_53v_10m_20260618_165027.html")
html = html_path.read_text(encoding="utf-8", errors="ignore")

# Locust 2.x embeds stats in template
m = re.search(r'"stats"\s*:\s*(\[.*?\])\s*,\s*"errors"', html, re.S)
if not m:
    m = re.search(r"window\.templateArgs\s*=\s*(\{.*?\})\s*;", html, re.S)

stats = None
if m:
    try:
        if m.group(0).startswith('"stats"'):
            stats = json.loads(m.group(1))
        else:
            data = json.loads(m.group(1))
            stats = data.get("stats")
    except json.JSONDecodeError as e:
        print("JSON error:", e)

if not stats:
    # brute force: find all name/avg_content_length pairs
    names = re.findall(r'"name"\s*:\s*"([^"]+)"', html)
    lengths = re.findall(r'"avg_content_length"\s*:\s*([\d.]+)', html)
    nums = re.findall(r'"num_requests"\s*:\s*(\d+)', html)
    print(f"fallback: names={len(names)} lengths={len(lengths)} nums={len(nums)}")
else:
    rows = []
    for s in stats:
        name = s.get("name", "")
        if not name or name == "Aggregated":
            continue
        n = s.get("num_requests", 0)
        avg_b = s.get("avg_content_length", 0) or 0
        rows.append({
            "name": name,
            "requests": n,
            "median_ms": s.get("median_response_time", 0),
            "avg_bytes": avg_b,
            "total_mb": avg_b * n / 1024 / 1024,
        })
    rows.sort(key=lambda x: x["total_mb"], reverse=True)
    print("=== Top interfaces by total downstream bytes ===")
    for r in rows[:20]:
        print(f"{r['name'][:45]:45} req={r['requests']:6} median={r['median_ms']:5}ms avg={r['avg_bytes']:10.0f}B total={r['total_mb']:8.1f}MB")
    total = sum(r["total_mb"] for r in rows)
    print(f"\nTotal estimated downstream: {total:.1f} MB in 10min")
    agg = next((s for s in stats if s.get("name") == "Aggregated"), None)
    if agg:
        print(f"Aggregated: {agg.get('num_requests')} req, avg_bytes={agg.get('avg_content_length',0):.0f}")
