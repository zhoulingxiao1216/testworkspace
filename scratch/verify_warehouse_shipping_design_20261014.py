from pathlib import Path
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import re, json, yaml

root=Path(r'D:\test_workspace')
out=root/'测试项目/全球站数据统计报表/仓库发货统计表/测试文档'
h=yaml.safe_load((out/'执行交接清单.yaml').read_text(encoding='utf-8'))
sp=(out/'superpowers.md').read_text(encoding='utf-8')
meta=yaml.safe_load(sp.split('---',2)[1])
for k in ['name','description','version','domain','inherits','triggers']:
    assert k in meta,k
assert meta['inherits']=='superpowers-base'
assert re.findall(r'^## §(\d+)',sp,re.M)==[str(n) for n in range(4,14)]
text=(out/'仓库发货统计表测试用例.md').read_text(encoding='utf-8')
matches=list(re.finditer(r'^#### (TC-([A-Z]+)-(\d{3})) 【([^】]+)】(.+)$',text,re.M))
assert len(matches)==h['total_cases']==103
seen=set(); dist=Counter(); condition_ids=set()
for i,m in enumerate(matches):
    cid,mod,num,typ,title=m.groups()
    assert cid not in seen
    seen.add(cid)
    body=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
    rows=re.findall(r'^\| \*\*(.+?)\*\* \| (.*?) \|$',body,re.M)
    assert [k for k,v in rows]==['测试点','优先级','前置条件','操作步骤','预期结果'],cid
    d=dict(rows)
    assert all(d.values()),cid
    assert d['优先级'] in ['Critical','High','Medium','Low']
    dist[d['优先级']]+=1
    assert d['操作步骤'].startswith('1.') and d['预期结果'].startswith('1.'),cid
    assert '[SmokeTest]' in title if d['优先级']=='Critical' else '[SmokeTest]' not in title
    if '[条件执行]' in title: condition_ids.add(cid)
    assert cid in (out/'测试用例树状结构.md').read_text(encoding='utf-8'),cid
    assert re.search(r'\| '+mod+r' \|',sp),mod
assert dict(dist)=={k:v for k,v in h['priority_distribution'].items() if v}
regular=[cid for q in h['execution_queue'] for cid in q['case_ids']]
conditional=[cid for q in h['conditional_queue'] for cid in q['case_ids']]
assert len(regular)==len(set(regular))
assert len(conditional)==len(set(conditional))
assert set(regular).isdisjoint(conditional)
assert set(regular)|set(conditional)==seen
assert set(conditional)==condition_ids
assert len(conditional)==h['conditional_cases']==14
assert len(regular)==h['ready_definition_cases']==89
assert set(h['smoke_ids'])<=set(regular)
assert len(h['case_index'])==103
assert {c['id'] for c in h['case_index']}==seen
assert all(c['execution_status']=='NotRun' for c in h['case_index'])
assert h['mode']['execute_cases'] is False
for f in h['deliverables']:
    assert (out/f).is_file() and (out/f).stat().st_size>0,f
    if f.endswith('.md'):
        for line in (out/f).read_text(encoding='utf-8').splitlines():
            if line.startswith('|'):
                assert line.endswith('|'),(f,line)
                assert '\\n' not in line,(f,line)
assert h['estimated_time']['full_round_minutes']==sum({'Critical':12,'High':8,'Medium':5,'Low':3}[c['priority']] for c in h['case_index'])
q=lambda n: Decimal(n).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
assert q(Decimal(4)/3)==Decimal('1.33')
assert q(Decimal(7)/14)==Decimal('0.50')
assert q(Decimal(7)/15)==Decimal('0.47')
assert q(Decimal(100)/3)*3==Decimal('99.99')
print(json.dumps({'result':'PASS','files':len(h['deliverables']),'cases':len(seen),'regular_cases':len(regular),'conditional_cases':len(conditional),'priorities':dict(dist),'smoke_ids':len(h['smoke_ids']),'first_round_minutes':h['estimated_time']['full_round_minutes'],'checks':['YAML parse','frontmatter','sequential rules','five fields','unique IDs','module dictionary','queues partition','tree coverage','priority counts','NotRun state','fixture arithmetic']},ensure_ascii=False,indent=2))
