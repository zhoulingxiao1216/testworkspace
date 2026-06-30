import json
from pathlib import Path

p = Path(r"d:\test_workspace\全球站压测脚本\测试文档\2026-06-18\stress_main_47r_53v_10m_20260618_165027.html")
text = p.read_text(encoding="utf-8")
start = text.index("window.templateArgs = ") + len("window.templateArgs = ")
end = text.index("window.theme", start)
data = json.loads(text[start:end].strip().rstrip(";"))
agg = next(x for x in data["requests_statistics"] if x["name"] == "Aggregated")
print("AGG", agg["num_requests"], agg["num_failures"], round(agg["avg_response_time"]), agg["median_response_time"], agg["response_time_percentile_0.95"], agg["response_time_percentile_0.99"], round(agg["max_response_time"]), round(agg["total_rps"], 1))
for s in sorted(data["requests_statistics"], key=lambda x: -x["num_requests"]):
    if s["name"] == "Aggregated":
        continue
    print(
        s["name"],
        s["method"],
        s["num_requests"],
        s["num_failures"],
        round(s["avg_response_time"]),
        s["response_time_percentile_0.95"],
        round(s["max_response_time"]),
        sep="\t",
    )
