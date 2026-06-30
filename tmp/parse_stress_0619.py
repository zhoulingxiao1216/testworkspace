# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path


def parse_html(path):
    html = Path(path).read_text(encoding="utf-8", errors="ignore")
    marker = "window.templateArgs = "
    idx = html.find(marker)
    if idx < 0:
        return None
    start = idx + len(marker)
    depth = 0
    end = start
    for i, ch in enumerate(html[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    data = json.loads(html[start:end])
    stats = data.get("stats") or data.get("requests_statistics", [])
    agg = next((s for s in stats if s.get("name") == "Aggregated"), {})
    return {
        "duration": data.get("duration"),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "agg": agg,
        "stats": [s for s in stats if s.get("name") and s.get("name") != "Aggregated"],
        "failures": data.get("failures_statistics", []),
    }


def main():
    files = [
        r"d:\test_workspace\全球站压测脚本\测试文档\2026-06-19\stress_main_47r_53v_10m_20260622_170347.html",
        r"d:\test_workspace\全球站压测脚本\测试文档\2026-06-19\stress_main_47r_53v_30m_20260622_172307.html",
    ]
    for f in files:
        d = parse_html(f)
        print("=" * 80)
        print(Path(f).name)
        print("duration:", d["duration"], "start:", d["start_time"], "end:", d["end_time"])
        a = d["agg"]
        n = a.get("num_requests", 0)
        fails = a.get("num_failures", 0)
        fr = fails / n * 100 if n else 0
        dur_sec = a.get("total_response_time", 0) / n if n else 0
        rps = n / (10 * 60) if "10" in d["duration"] else n / (30 * 60)
        print(
            f"Aggregated: req={n} fail={fails} fail_rate={fr:.4f}% "
            f"avg={a.get('avg_response_time')} p50={a.get('median_response_time')} "
            f"p95={a.get('response_time_percentile_0.95')} p99={a.get('response_time_percentile_0.99')} "
            f"max={a.get('max_response_time')} est_rps={rps:.1f}"
        )
        print("Failures:")
        for ff in d["failures"]:
            print(f"  {ff.get('name')}: {ff.get('error')} x{ff.get('occurrences')}")
        print("All stats:")
        for s in sorted(d["stats"], key=lambda x: -x.get("num_requests", 0)):
            print(
                f"  {s['name']}: req={s['num_requests']} fail={s['num_failures']} "
                f"avg={s['avg_response_time']} p95={s.get('response_time_percentile_0.95')} "
                f"max={s['max_response_time']}"
            )


if __name__ == "__main__":
    main()
