"""
db_manager.py
数据库操作层：负责 test_mission.db 的初始化与数据写入。
"""

from __future__ import annotations

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "test_mission.db")


def get_connection() -> sqlite3.Connection:
    """返回数据库连接，启用 WAL 模式提升并发写入安全性。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    初始化数据库，创建 test_cases 表（若已存在则跳过），
    并执行幂等迁移以补充 tc_id 字段。

    字段说明：
        id            - 自增主键
        module        - 所属模块（如：会员注册、积分结算）
        title         - 用例标题
        priority      - 优先级（P0 / P1 / P2）
        steps         - 测试步骤（Markdown 原文）
        expected      - 预期结果
        status        - 执行状态（Untested / Pass / Fail / Blocked）
        actual_result - 实际结果描述
        bug_link      - 关联 Bug 链接
        actual_amount - 实际金额（财务类用例专用，单位：元）
        tc_id         - 用例唯一编号（如 TC-001），用于防重复导入
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS test_cases (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        module        TEXT    NOT NULL,
        title         TEXT    NOT NULL,
        priority      TEXT    NOT NULL CHECK(priority IN ('P0', 'P1', 'P2')),
        steps         TEXT,
        expected      TEXT,
        status        TEXT    NOT NULL DEFAULT 'Untested'
                              CHECK(status IN ('Untested', 'Pass', 'Fail', 'Blocked')),
        actual_result TEXT,
        bug_link      TEXT,
        actual_amount REAL
    );
    """
    with get_connection() as conn:
        conn.execute(ddl)
        # 幂等迁移：为旧数据库补充 tc_id 列
        try:
            conn.execute("ALTER TABLE test_cases ADD COLUMN tc_id TEXT")
        except sqlite3.OperationalError:
            pass  # 列已存在，跳过
        # 幂等迁移：补充 sort_order 列（用于保持文档原始顺序）
        try:
            conn.execute("ALTER TABLE test_cases ADD COLUMN sort_order INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        # 幂等迁移：补充 test_point 列（测试点分组，对应 ### 标题）
        try:
            conn.execute("ALTER TABLE test_cases ADD COLUMN test_point TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        # 幂等迁移：补充 source_file 列（测试来源文件）
        try:
            conn.execute("ALTER TABLE test_cases ADD COLUMN source_file TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uix_tc_id ON test_cases(tc_id)"
        )
    print(f"[init_db] 数据库已就绪：{DB_PATH}")


def insert_case(
    module: str,
    title: str,
    priority: str,
    steps: Optional[str] = None,
    expected: Optional[str] = None,
    status: str = "Untested",
    actual_result: Optional[str] = None,
    bug_link: Optional[str] = None,
    actual_amount: Optional[float] = None,
    source_file: str = "",
) -> int:
    """
    插入单条测试用例，返回新记录的 id。

    Args:
        module        : 所属模块名称
        title         : 用例标题
        priority      : 优先级，必须为 'P0' / 'P1' / 'P2'
        steps         : 测试步骤（可选）
        expected      : 预期结果（可选）
        status        : 执行状态，默认 'Untested'
        actual_result : 实际结果（可选）
        bug_link      : Bug 链接（可选）
        actual_amount : 实际金额，财务类用例使用（可选）
        source_file   : 来源md文件名称（可选）

    Returns:
        新插入记录的自增 id
    """
    sql = """
    INSERT INTO test_cases
        (module, title, priority, steps, expected,
         status, actual_result, bug_link, actual_amount, source_file)
    VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        module, title, priority, steps, expected,
        status, actual_result, bug_link, actual_amount, source_file,
    )
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        new_id = cursor.lastrowid
    print(f"[insert_case] 已插入用例 id={new_id}：{title}")
    return new_id


def get_all_cases() -> list[sqlite3.Row]:
    """
    返回 test_cases 表中所有记录，按 module、priority、id 排序。

    Returns:
        sqlite3.Row 对象列表，可通过列名下标访问字段。
    """
    sql = """
    SELECT id, module, title, priority, steps, expected,
           status, actual_result, bug_link, actual_amount, tc_id, test_point, source_file
    FROM   test_cases
    ORDER  BY sort_order, id
    """
    with get_connection() as conn:
        return conn.execute(sql).fetchall()


def update_case_status(
    case_id: int,
    status: str,
    actual_result: Optional[str] = None,
    bug_link: Optional[str] = None,
) -> None:
    """
    更新指定用例的执行状态与实际结果。

    Args:
        case_id       : 用例主键 id
        status        : 新状态，必须为 Pass / Fail / Blocked / Untested
        actual_result : 实际报错描述（仅 Fail 时建议填写）
        bug_link      : Bug 连接（仅 Fail 时建议填写）
    """
    sql = """
    UPDATE test_cases
    SET    status = ?, actual_result = ?, bug_link = ?
    WHERE  id = ?
    """
    with get_connection() as conn:
        conn.execute(sql, (status, actual_result, bug_link, case_id))
    print(f"[update_case_status] id={case_id} → status={status}")


def reset_all_status() -> int:
    """
    将所有用例的 status 重置为 'Untested'，同时清空 actual_result。

    Returns:
        受影响的行数
    """
    sql = "UPDATE test_cases SET status = 'Untested', actual_result = NULL"
    with get_connection() as conn:
        cursor = conn.execute(sql)
        count = cursor.rowcount
    print(f"[reset_all_status] 已重置 {count} 条记录")
    return count


def upsert_case(
    tc_id: str,
    module: str,
    title: str,
    priority: str,
    steps: Optional[str] = None,
    expected: Optional[str] = None,
    sort_order: int = 0,
    test_point: str = "",
    source_file: str = "",
) -> tuple[int, str]:
    """
    按 tc_id 执行 Upsert：TC 编号已存在则更新字段，否则插入新记录。
    执行状态（status / actual_result）在 Update 时不会被覆盖，保留已有结果。

    Args:
        tc_id    : 唯一用例编号，如 TC-001
        module   : 所属模块
        title    : 用例标题
        priority : 优先级
        steps    : 操作步骤（可选）
        expected : 预期结果（可选）

    Returns:
        (record_id, action)，action 为 'inserted' 或 'updated'
    """
    if not tc_id:
        raise ValueError("严重错误：tc_id 缺失！拒绝执行幂等更新操作以防数据无限重复。")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM test_cases WHERE tc_id = ?", (tc_id,)
        ).fetchone()

        if row:
            conn.execute(
                """UPDATE test_cases
                   SET module = ?, title = ?, priority = ?, steps = ?, expected = ?,
                       sort_order = ?, test_point = ?, source_file = ?
                   WHERE tc_id = ?""",
                (module, title, priority, steps, expected, sort_order, test_point, source_file, tc_id),
            )
            record_id = row["id"]
            action = "updated"
        else:
            cursor = conn.execute(
                """INSERT INTO test_cases
                       (tc_id, module, title, priority, steps, expected, sort_order, test_point, source_file)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tc_id, module, title, priority, steps, expected, sort_order, test_point, source_file),
            )
            record_id = cursor.lastrowid
            action = "inserted"

    print(f"[upsert_case] {action} {tc_id} (id={record_id})")
    return record_id, action


def get_cases_by_source(source_file: str) -> list[sqlite3.Row]:
    """返回指定 source_file 关联的所有用例（用于删除前存档）。"""
    sql = """
    SELECT id, tc_id, module, title, priority, steps, expected,
           status, actual_result, bug_link, actual_amount, test_point, source_file
    FROM   test_cases
    WHERE  source_file = ?
    ORDER  BY sort_order, id
    """
    with get_connection() as conn:
        return conn.execute(sql, (source_file,)).fetchall()


def delete_cases_by_source(source_file: str) -> int:
    """按 source_file 物理删除整批用例，返回删除条数。"""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM test_cases WHERE source_file = ?", (source_file,)
        )
        count = cursor.rowcount
    print(f"[delete_cases_by_source] 已删除 {count} 条来自 '{source_file}' 的用例")
    return count


def get_tc_ids_by_source(source_file: str) -> set[str]:
    """返回某个 source_file 下所有已有的 tc_id 集合（用于差异对比）。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT tc_id FROM test_cases WHERE source_file = ? AND tc_id IS NOT NULL",
            (source_file,),
        ).fetchall()
    return {r["tc_id"] for r in rows}


def delete_cases_by_tc_ids(tc_ids: list[str]) -> int:
    """按 tc_id 列表批量删除指定用例，返回删除条数。"""
    if not tc_ids:
        return 0
    placeholders = ", ".join("?" for _ in tc_ids)
    with get_connection() as conn:
        cursor = conn.execute(
            f"DELETE FROM test_cases WHERE tc_id IN ({placeholders})",
            list(tc_ids),
        )
        count = cursor.rowcount
    print(f"[delete_cases_by_tc_ids] 已删除 {count} 条废弃用例")
    return count


if __name__ == "__main__":
    # 直接运行本脚本时执行初始化，并写入一条示例数据用于验证
    init_db()
    insert_case(
        module="会员积分结算",
        title="验证消费满100元积分翻倍规则正确触发",
        priority="P0",
        steps="1. 登录会员账号\n2. 完成满100元订单支付\n3. 查看积分明细",
        expected="积分明细显示本次获得积分 = 消费金额 × 2",
        actual_amount=128.50,
    )
