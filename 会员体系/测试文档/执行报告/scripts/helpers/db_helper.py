"""
Layer 1-DB: 数据库只读查询助手 (SSH 隧道)

⚠️ DATABASE IRON LAW ⚠️
此脚本仅允许执行 SELECT 查询。
绝对禁止任何修改数据库内容或结构的操作。
违反此规则等同于最高严重级别的安全事故。
"""

import sys
import os
import json
import re
import io
import pymysql
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

# Windows 终端 UTF-8 输出
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# 加载 .env — 逐级向上查找
_dir = os.path.dirname(os.path.abspath(__file__))
for _ in range(5):
    _env = os.path.join(_dir, '.env')
    if os.path.exists(_env):
        load_dotenv(_env)
        break
    _dir = os.path.dirname(_dir)
else:
    # 最终 fallback：硬编码路径
    load_dotenv(r'd:\test_workspace\会员体系\测试文档\.env')

# ============================================================
# SAFETY: 硬编码的写操作关键词黑名单
# ============================================================
FORBIDDEN_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
    'TRUNCATE', 'REPLACE', 'MERGE', 'RENAME', 'GRANT', 'REVOKE',
    'CALL', 'EXEC', 'EXECUTE', 'SET ', 'LOCK', 'UNLOCK',
    'LOAD DATA', 'INTO OUTFILE', 'INTO DUMPFILE',
]


def _validate_query(sql: str):
    """严格校验 SQL 是否为只读查询"""
    normalized = sql.strip().upper()

    # 必须以 SELECT 或 SHOW 或 DESCRIBE/DESC/EXPLAIN 开头
    if not re.match(r'^(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b', normalized):
        raise PermissionError(
            f"❌ [DATABASE IRON LAW] 仅允许 SELECT/SHOW/DESCRIBE 查询。\n"
            f"   拒绝执行: {sql[:80]}..."
        )

    # 额外检查是否包含写操作关键词（防御 SELECT ... INTO, 子查询注入等）
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in normalized:
            raise PermissionError(
                f"❌ [DATABASE IRON LAW] 检测到禁止的关键词: {keyword}\n"
                f"   拒绝执行: {sql[:80]}..."
            )


def query(sql: str, params=None, as_dict=True):
    """
    执行只读 SQL 查询并返回结果。

    Args:
        sql: SELECT 查询语句
        params: 查询参数（防 SQL 注入）
        as_dict: True 返回 dict 列表，False 返回 tuple 列表

    Returns:
        查询结果列表
    """
    # ====== SAFETY CHECK ======
    _validate_query(sql)

    ssh_host = os.getenv('SSH_HOST')
    ssh_port = int(os.getenv('SSH_PORT', 22))
    ssh_user = os.getenv('SSH_USER')
    ssh_password = os.getenv('SSH_PASSWORD')

    db_host = os.getenv('DB_HOST')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')

    with SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        remote_bind_address=(db_host, db_port),
        local_bind_address=('127.0.0.1',),
    ) as tunnel:
        cursor_class = pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor
        conn = pymysql.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4',
            cursorclass=cursor_class,
            connect_timeout=10,
            read_timeout=30,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return results
        finally:
            conn.close()


def show_tables():
    """列出数据库中所有表"""
    return query("SHOW TABLES")


def describe_table(table_name: str):
    """查看表结构"""
    # 防注入：表名只允许字母数字下划线和连字符
    if not re.match(r'^[a-zA-Z0-9_\-]+$', table_name):
        raise ValueError(f"非法表名: {table_name}")
    return query(f"DESCRIBE `{table_name}`")


# ============================================================
# CLI 入口：python db_helper.py "SELECT * FROM users LIMIT 5"
# ============================================================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python db_helper.py \"SELECT ...\"")
        print("      python db_helper.py --tables")
        print("      python db_helper.py --describe <table_name>")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--tables':
        results = show_tables()
    elif arg == '--describe' and len(sys.argv) >= 3:
        results = describe_table(sys.argv[2])
    else:
        results = query(arg)

    # 输出 JSON（便于 Agent 解析）
    print(json.dumps(results, ensure_ascii=False, default=str, indent=2))
