# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path


def extract_json_array(text, key):
    m = re.search(rf'"{key}"\s*:\s*(\[)', text)
    if not m:
        return None
    start = m.start(1)
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    return None


def print_report(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    stats = extract_json_array(text, "requests_statistics")
    if not stats:
        print("NO requests_statistics in", path)
        return
    print("===", Path(path).name, "===")
    for row in stats:
        if row.get("name") == "Aggregated":
            req = row["num_requests"]
            fail = row["num_failures"]
            mins = 10 if "10m" in Path(path).name else 30
            rps = req / (mins * 60)
            print(
                f"AGG: req={req} fail={fail} fail_rate={fail/req*100:.3f}% "
                f"avg_rps={rps:.1f} total_rps={row.get('total_rps',0):.1f} "
                f"avg={row['avg_response_time']:.0f}ms p50={row['median_response_time']} "
                f"p95={row['response_time_percentile_0.95']} p99={row['response_time_percentile_0.99']} "
                f"max={row['max_response_time']:.0f}"
            )
    print("--- failures ---")
    for row in stats:
        if row.get("num_failures", 0) > 0 and row.get("name") != "Aggregated":
            n, r, f = row["name"], row["num_requests"], row["num_failures"]
            print(
                f"{n} | {f}/{r} ({f/r*100:.3f}%) | avg={row['avg_response_time']:.0f} "
                f"p95={row['response_time_percentile_0.95']} max={row['max_response_time']:.0f}"
            )
    print("--- all endpoints ---")
    for row in stats:
        if row.get("name") == "Aggregated":
            continue
        n = row["name"]
        print(
            f"{n} | req={row['num_requests']} fail={row['num_failures']} "
            f"avg={row['avg_response_time']:.0f} p95={row['response_time_percentile_0.95']} "
            f"p99={row['response_time_percentile_0.99']} max={row['max_response_time']:.0f}"
        )

    failures = extract_json_array(text, "failures_statistics")
    if failures:
        print("--- failure messages ---")
        for row in failures:
            print(row)
    print()


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "全球站压测脚本" / "测试文档" / "2026-06-17"
    for name in sorted(base.glob("stress_*.html")):
        print_report(name)
