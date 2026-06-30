from md_parser import parse_md_text
from pathlib import Path

text = Path("测试用例.md").read_text(encoding="utf-8")
records = parse_md_text(text)
print(f"Total: {len(records)}")
for r in records[:5]:
    print(f"  {r['tc_id']:20s} test_point={r.get('test_point','')!r}")
print("...")
for r in records[-3:]:
    print(f"  {r['tc_id']:20s} test_point={r.get('test_point','')!r}")

# Verify hierarchy mapping
import sys; sys.path.insert(0, ".")
from app import _resolve_hierarchy
for r in records[:3]:
    side, mg = _resolve_hierarchy(r["tc_id"])
    print(f"  {r['tc_id']} => side={side!r}, mg={mg!r}")
for r in records[-3:]:
    side, mg = _resolve_hierarchy(r["tc_id"])
    print(f"  {r['tc_id']} => side={side!r}, mg={mg!r}")
