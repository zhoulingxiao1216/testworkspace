"""
Controlled database helper for Agent 2.

Default mode is readonly and accepts SELECT statements only.
Mock write mode is intentionally gated by environment flags, table allowlists,
SQL markers, and a small SQL guard. This helper is for test/mock data setup,
not for production data maintenance or schema changes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ALLOWED_ENVIRONMENTS = {"test", "mock", "dev", "local", "qa", "staging"}
READONLY_START = ("select", "with", "explain")
MOCK_WRITE_START = ("insert", "update", "delete")
DANGEROUS_TOKENS = {
    "alter",
    "create",
    "drop",
    "truncate",
    "grant",
    "revoke",
    "replace",
    "merge",
    "call",
    "execute",
    "load",
    "outfile",
    "infile",
    "shutdown",
    "set global",
    "set session",
}


class GuardError(ValueError):
    """Raised when a SQL statement violates the agent DB policy."""


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def cfg_value(config: Dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key, config.get(key, default))


def normalize_sql(sql: str) -> str:
    collapsed = re.sub(r"\s+", " ", sql.strip())
    return collapsed


def sql_fingerprint(sql: str) -> str:
    return hashlib.sha256(normalize_sql(sql).encode("utf-8")).hexdigest()[:16]


def strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return normalize_sql(sql)


def assert_single_statement(sql: str) -> None:
    cleaned = strip_sql_comments(sql)
    if ";" in cleaned.rstrip(";"):
        raise GuardError("Multiple SQL statements are not allowed.")


def sql_start(sql: str) -> str:
    cleaned = strip_sql_comments(sql).lower().lstrip("(")
    return cleaned.split(" ", 1)[0] if cleaned else ""


def contains_dangerous_token(sql: str) -> Optional[str]:
    cleaned = strip_sql_comments(sql).lower()
    for token in DANGEROUS_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", cleaned):
            return token
    return None


def parse_target_tables(sql: str) -> List[str]:
    cleaned = strip_sql_comments(sql).lower()
    patterns = [
        r"\binsert\s+into\s+`?([a-zA-Z0-9_.]+)`?",
        r"\bupdate\s+`?([a-zA-Z0-9_.]+)`?",
        r"\bdelete\s+from\s+`?([a-zA-Z0-9_.]+)`?",
    ]
    tables: List[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, cleaned):
            tables.append(match.group(1).strip("`"))
    return tables


def has_where_clause(sql: str) -> bool:
    return bool(re.search(r"\bwhere\b", strip_sql_comments(sql).lower()))


def csv_set(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def assert_readonly_sql(sql: str) -> None:
    assert_single_statement(sql)
    start = sql_start(sql)
    if start not in READONLY_START:
        raise GuardError("Readonly mode allows SELECT/WITH/EXPLAIN only.")
    dangerous = contains_dangerous_token(sql)
    if dangerous:
        raise GuardError(f"Readonly SQL contains forbidden token: {dangerous}")


def assert_mock_write_sql(sql: str, config: Dict[str, str]) -> List[str]:
    assert_single_statement(sql)
    start = sql_start(sql)
    if start not in MOCK_WRITE_START:
        raise GuardError("Mock write mode allows INSERT/UPDATE/DELETE only.")

    dangerous = contains_dangerous_token(sql)
    if dangerous:
        raise GuardError(f"Mock write SQL contains forbidden token: {dangerous}")

    require_marker = cfg_value(config, "AGENT_DB_REQUIRE_MOCK_MARKER", "true").lower() != "false"
    if require_marker and "AGENT_MOCK_DATA" not in sql:
        raise GuardError("Mock write SQL must contain comment marker: /* AGENT_MOCK_DATA */")

    if start in {"update", "delete"} and not has_where_clause(sql):
        raise GuardError("UPDATE/DELETE mock writes require a WHERE clause.")

    tables = parse_target_tables(sql)
    if not tables:
        raise GuardError("Could not identify target table for mock write.")

    allowlist = csv_set(cfg_value(config, "AGENT_DB_MOCK_TABLE_ALLOWLIST"))
    if not allowlist:
        raise GuardError("AGENT_DB_MOCK_TABLE_ALLOWLIST must be set for mock writes.")

    short_tables = {table.split(".")[-1] for table in tables}
    not_allowed = sorted(table for table in short_tables if table not in allowlist)
    if not_allowed:
        raise GuardError(f"Mock write target table not in allowlist: {', '.join(not_allowed)}")

    return tables


def assert_mock_write_environment(config: Dict[str, str]) -> None:
    enabled = cfg_value(config, "AGENT_DB_ALLOW_MOCK_WRITE", "false").lower() == "true"
    if not enabled:
        raise GuardError("Mock write requires AGENT_DB_ALLOW_MOCK_WRITE=true.")

    env_name = cfg_value(config, "AGENT_DB_ENV", "").lower()
    if env_name not in ALLOWED_ENVIRONMENTS:
        raise GuardError(
            "Mock write requires AGENT_DB_ENV to be one of: "
            + ", ".join(sorted(ALLOWED_ENVIRONMENTS))
        )

    database = cfg_value(config, "AGENT_DB_NAME")
    pattern = cfg_value(config, "AGENT_DB_MOCK_DATABASE_PATTERN", r"(test|mock|dev|qa|staging)")
    if database and not re.search(pattern, database, re.I):
        confirmed = cfg_value(config, "AGENT_DB_ASSUME_NON_PROD", "false").lower() == "true"
        if not confirmed:
            raise GuardError(
                "Database name does not look non-production. Set AGENT_DB_ASSUME_NON_PROD=true "
                "only after human confirmation."
            )


def guard_sql(sql: str, mode: str, config: Dict[str, str]) -> List[str]:
    if mode == "readonly":
        assert_readonly_sql(sql)
        return []
    if mode == "mock_write":
        assert_mock_write_environment(config)
        return assert_mock_write_sql(sql, config)
    raise GuardError("Mode must be readonly or mock_write.")


def maybe_start_ssh_tunnel(config: Dict[str, str]):
    if cfg_value(config, "AGENT_DB_SSH_ENABLED", "false").lower() != "true":
        return None, cfg_value(config, "AGENT_DB_HOST", "127.0.0.1"), int(
            cfg_value(config, "AGENT_DB_PORT", "3306")
        )

    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError as exc:
        raise RuntimeError("sshtunnel is required for SSH DB connections.") from exc

    ssh_kwargs: Dict[str, Any] = {
        "ssh_address_or_host": (
            cfg_value(config, "AGENT_DB_SSH_HOST"),
            int(cfg_value(config, "AGENT_DB_SSH_PORT", "22")),
        ),
        "ssh_username": cfg_value(config, "AGENT_DB_SSH_USER"),
        "remote_bind_address": (
            cfg_value(config, "AGENT_DB_HOST", "127.0.0.1"),
            int(cfg_value(config, "AGENT_DB_PORT", "3306")),
        ),
        "local_bind_address": ("127.0.0.1", 0),
    }
    ssh_password = cfg_value(config, "AGENT_DB_SSH_PASSWORD")
    ssh_pkey = cfg_value(config, "AGENT_DB_SSH_PKEY")
    if ssh_password:
        ssh_kwargs["ssh_password"] = ssh_password
    if ssh_pkey:
        ssh_kwargs["ssh_pkey"] = ssh_pkey

    tunnel = SSHTunnelForwarder(**ssh_kwargs)
    tunnel.start()
    return tunnel, "127.0.0.1", tunnel.local_bind_port


def connect_mysql(config: Dict[str, str], host: str, port: int):
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("PyMySQL is required for MySQL DB connections.") from exc

    return pymysql.connect(
        host=host,
        port=port,
        user=cfg_value(config, "AGENT_DB_USER"),
        password=cfg_value(config, "AGENT_DB_PASSWORD"),
        database=cfg_value(config, "AGENT_DB_NAME"),
        charset=cfg_value(config, "AGENT_DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=int(cfg_value(config, "AGENT_DB_CONNECT_TIMEOUT", "10")),
    )


def audit_log(config: Dict[str, str], payload: Dict[str, Any]) -> None:
    audit_path = Path(
        cfg_value(
            config,
            "AGENT_DB_AUDIT_LOG",
            ".agent/memory/agent2-test-execution/db_mock_audit.jsonl",
        )
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        **payload,
    }
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def execute_sql(sql: str, mode: str, config: Dict[str, str], dry_run: bool) -> Dict[str, Any]:
    tables = guard_sql(sql, mode, config)
    fingerprint = sql_fingerprint(sql)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "mode": mode,
            "sql_hash": fingerprint,
            "tables": tables,
        }

    tunnel = None
    conn = None
    try:
        driver = cfg_value(config, "AGENT_DB_DRIVER", "mysql").lower()
        if driver != "mysql":
            raise RuntimeError("Only AGENT_DB_DRIVER=mysql is supported.")

        tunnel, host, port = maybe_start_ssh_tunnel(config)
        conn = connect_mysql(config, host, port)
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if mode == "readonly":
                rows = cursor.fetchall()
                conn.rollback()
                result = {
                    "ok": True,
                    "mode": mode,
                    "sql_hash": fingerprint,
                    "rowcount": cursor.rowcount,
                    "rows": rows,
                }
            else:
                conn.commit()
                result = {
                    "ok": True,
                    "mode": mode,
                    "sql_hash": fingerprint,
                    "rowcount": cursor.rowcount,
                    "tables": tables,
                }

        audit_log(
            config,
            {
                "event": "db_execute",
                "mode": mode,
                "env": cfg_value(config, "AGENT_DB_ENV"),
                "database": cfg_value(config, "AGENT_DB_NAME"),
                "sql_hash": fingerprint,
                "tables": tables,
                "rowcount": result.get("rowcount"),
                "dry_run": False,
            },
        )
        return result
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
        if tunnel:
            tunnel.stop()


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent controlled DB helper")
    parser.add_argument("--env-file", required=True, help="Path to project .env DB config")
    parser.add_argument("--mode", choices=["readonly", "mock_write"], default=None)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sql", help="SQL statement")
    group.add_argument("--sql-file", help="File containing a single SQL statement")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not execute")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    env_file = Path(args.env_file)
    config = load_env_file(env_file)
    sql = args.sql if args.sql is not None else Path(args.sql_file).read_text(encoding="utf-8")
    mode = args.mode or cfg_value(config, "AGENT_DB_MODE", "readonly")
    try:
        result = execute_sql(sql, mode, config, args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
