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


def dump(path, out):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    stats = extract_json_array(text, "requests_statistics")
    failures = extract_json_array(text, "failures_statistics")
    data = {"file": Path(path).name, "stats": stats, "failures": failures}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    base = Path(r"D:/test_workspace/全球站压测脚本/测试文档/2026-06-17")
    out = Path(r"D:/test_workspace/tmp/locust_0617.json")
    all_data = []
    for name in sorted(base.glob("stress_*.html")):
        text = name.read_text(encoding="utf-8", errors="replace")
        all_data.append({
            "file": name.name,
            "stats": extract_json_array(text, "requests_statistics"),
            "failures": extract_json_array(text, "failures_statistics"),
        })
    out.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("written", out)
