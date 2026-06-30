import sqlite3

DB = r"d:\test_workspace\测试平台自建\test_mission.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

r = conn.execute(
    "SELECT id, tc_id, title, status, actual_result, source_file FROM test_cases WHERE id=1384"
).fetchone()
print("1384:", dict(r) if r else None)

rows = conn.execute(
    "SELECT id, tc_id, status, title FROM test_cases WHERE tc_id LIKE 'TC-SEC-%' ORDER BY tc_id"
).fetchall()
print("TC-SEC count:", len(rows))
for x in rows:
    print(dict(x))
