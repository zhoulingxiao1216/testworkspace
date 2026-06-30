"""Read-only access helpers for the formal PolarDB connection.

This module intentionally supports SELECT-like statements only. Do not add
write helpers here unless the database access policy changes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

import pymysql
import streamlit as st


_FORBIDDEN_SQL_RE = re.compile(
    r"\b("
    r"insert|update|delete|replace|merge|truncate|drop|alter|create|rename|"
    r"grant|revoke|lock|unlock|call|set|use|commit|rollback|start|begin|"
    r"load|handler|optimize|repair|analyze|outfile|dumpfile"
    r")\b|for\s+update\b",
    re.IGNORECASE,
)


def assert_select_only(sql: str) -> None:
    """Reject anything that is not a single SELECT query."""
    normalized = (sql or "").strip()
    if not normalized:
        raise ValueError("SQL 不能为空")

    normalized_no_semicolon = normalized.rstrip(";").strip()
    if ";" in normalized_no_semicolon:
        raise ValueError("只允许单条只读 SQL")

    first_word = normalized_no_semicolon.split(None, 1)[0].lower()
    if first_word != "select":
        raise ValueError("正式库只允许 SELECT")

    if _FORBIDDEN_SQL_RE.search(normalized_no_semicolon):
        raise ValueError("SQL 包含禁止的写入或变更关键字")


def get_formal_db_config() -> Dict[str, Any]:
    cfg = dict(st.secrets["database"]["formal"])
    return {
        "host": cfg["host"],
        "port": int(cfg["port"]),
        "database": cfg.get("database"),
        "user": cfg["user"],
        "password": cfg["password"],
    }


def get_readonly_connection() -> pymysql.connections.Connection:
    cfg = get_formal_db_config()
    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg.get("database"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=10,
        autocommit=True,
    )


def fetch_all(
    sql: str,
    params: Optional[Sequence[Any]] = None,
    *,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Run a read-only SQL query and return rows as dictionaries."""
    assert_select_only(sql)
    safe_limit = max(1, min(int(limit), 5000))
    with get_readonly_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            rows = cursor.fetchmany(safe_limit)
    return list(rows)
