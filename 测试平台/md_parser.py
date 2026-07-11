"""
md_parser.py
Markdown 用例解析层：读取 .md 文件，提取测试用例并批量写入数据库。

同时支持两种 Markdown 格式：

格式A（列表）：
    #### TC-001 用例标题
    - **模块**：会员注册
    - **优先级**：P0
    - **操作步骤**：
      1. 步骤一
    - **预期结果**：预期描述

格式B（表格）：
    #### TC-CL-LIFE-007 用例标题
    | 字段 | 内容 |
    |:--|:--|
    | **测试点** | 并发更新... |
    | **优先级** | High |
    | **前置条件** | 账号已登录 |
    | **操作步骤** | 1. 步骤一 <br> 2. 步骤二 |
    | **预期结果** | 期望行为 |
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from db_manager import init_db, insert_case

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 正则模式
# ---------------------------------------------------------------------------

# 匹配 ## 或 ### 测试点标题（支持二级或三级标题）
_RE_H3 = re.compile(r"^(?:#{2}|#{3})\s+(.+)$", re.MULTILINE)

# 匹配用例块起始行：#### TC-001 标题文字
# TC 编号支持数字、字母、连字符，如 TC-001、TC-REG-001、TC-001A
_RE_HEADER = re.compile(
    r"^#{4}\s+(TC-[\w-]+)\s+(.+)$",
    re.MULTILINE,
)

# ── 列表格式字段（严格要求以 "- **字段**" 开头，不匹配表格行） ──────────
_RE_MODULE = re.compile(
    r"^-\s*\*\*模块\*\*[：:]\s*(.+?)(?:\s*\n|$)", re.MULTILINE
)
_RE_PRIORITY = re.compile(
    r"^-\s*\*\*优先级\*\*[：:]\s*(P[012])(?:\s*\n|$)", re.MULTILINE
)
# 多行字段：操作步骤（截止到"预期结果"行或下一个 #### 块）
_RE_STEPS = re.compile(
    r"^-\s*\*\*操作步骤\*\*[：:]?\s*([\s\S]+?)(?=\n-\s*\*\*预期结果\*\*|\n####|\Z)",
    re.MULTILINE,
)
# 多行字段：预期结果（截止到下一个 #### 块或文件末尾）
_RE_EXPECTED = re.compile(
    r"^-\s*\*\*预期结果\*\*[：:]?\s*([\s\S]+?)(?=\n####|\Z)",
    re.MULTILINE,
)

# ── 表格格式字段 ─────────────────────────────────────────────────────────
# 匹配表格数据行：| **字段名** | 内容 |
_RE_TABLE_ROW = re.compile(
    r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|",
    re.MULTILINE,
)

# 优先级标准化映射（支持中/英文及 P0/P1/P2 直接输入）
_PRIORITY_MAP: dict[str, str] = {
    "p0": "P0", "critical": "P0", "high": "P0", "高": "P0",
    "p1": "P1", "medium": "P1", "中": "P1",
    "p2": "P2", "low": "P2",  "低": "P2",
}


# ---------------------------------------------------------------------------
# 私有辅助函数
# ---------------------------------------------------------------------------

def _split_into_blocks(text: str) -> list[tuple[str, str, str, str]]:
    """
    按 #### TC- 切分文档，返回 [(case_id, title, block_text, test_point), ...] 列表。
    block_text 包含从该用例标题行到下一个用例标题行之间的全部文本。
    test_point 是该用例前最近的 ### 标题。
    """
    # 先收集所有 ### 标题位置
    h3_list = [(m.start(), m.group(1).strip()) for m in _RE_H3.finditer(text)]

    matches = list(_RE_HEADER.finditer(text))
    if not matches:
        return []

    blocks: list[tuple[str, str, str, str]] = []
    for idx, match in enumerate(matches):
        case_id = match.group(1)         # TC-001
        title = match.group(2).strip()   # 用例标题
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        # 找到该 TC 块前最近的 ### 标题作为 test_point
        test_point = ""
        for h3_pos, h3_name in reversed(h3_list):
            if h3_pos < start:
                test_point = h3_name
                break
        blocks.append((case_id, title, block, test_point))

    return blocks


def _clean_field(raw: str) -> str:
    """去除字段值首尾空白及多余的空行。"""
    lines = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines)


def _extract_table_fields(block: str) -> dict[str, str]:
    """
    从 Markdown 表格式用例块中提取所有「| **字段** | 值 |」键值对。
    自动处理 <br> 换行标记和残余 Markdown 加粗标记。
    """
    fields: dict[str, str] = {}
    for m in _RE_TABLE_ROW.finditer(block):
        key = m.group(1).strip()
        val = m.group(2).strip()
        val = re.sub(r"\s*<br\s*/?>\s*", "\n", val, flags=re.IGNORECASE)
        val = re.sub(r"\*\*(.+?)\*\*", r"\1", val)
        if key and val and val not in ("|", "内容", "---", ":--", "--"):
            fields[key] = val
    return fields


def _normalize_priority(raw: str) -> str | None:
    """将任意格式优先级字符串标准化为 P0/P1/P2，无法识别时返回 None。"""
    return _PRIORITY_MAP.get(raw.strip().lower())


def _module_from_tc_id(tc_id: str) -> str:
    """
    从 TC 编号中推断模块前缀，用于表格格式无 模块 字段时的兜底。
    例：TC-CL-LIFE-007 → CL-LIFE，TC-REG-001 → REG，TC-001 → TC-001
    """
    parts = tc_id.split("-")       # ['TC', 'CL', 'LIFE', '007']
    if len(parts) <= 2:
        return tc_id
    tail = parts[-1]
    inner = parts[1:-1] if tail.isdigit() else parts[1:]
    return "-".join(inner) if inner else tc_id


def _parse_block(case_id: str, title: str, block: str) -> dict | None:
    """
    从单个用例块中提取结构化字段。
    优先尝试「- **字段**：值」列表格式，其次尝试「| **字段** | 值 |」表格格式。

    Args:
        case_id : 用例编号，如 TC-CL-LIFE-007
        title   : 从标题行提取的标题文字
        block   : 该用例完整 Markdown 文本块

    Returns:
        包含 upsert_case / insert_case 所需字段的字典；缺失必要字段时返回 None。
    """
    # ── 列表格式匹配 ──────────────────────────────────────────────────────
    module_m   = _RE_MODULE.search(block)
    priority_m = _RE_PRIORITY.search(block)
    steps_m    = _RE_STEPS.search(block)
    expected_m = _RE_EXPECTED.search(block)

    # ── 若列表格式字段不完整，尝试表格格式 ──────────────────────────────
    table: dict[str, str] = {}
    if not module_m or not priority_m:
        table = _extract_table_fields(block)

    # ── 解析 module ───────────────────────────────────────────────────────
    if module_m:
        module = module_m.group(1).strip()
    elif "模块" in table:
        module = table["模块"]
    elif "测试点" in table:          # 表格格式 B 使用「测试点」而非「模块」
        module = table["测试点"]
    elif table:
        # 表格格式：从 TC-ID 推断模块前缀（如 TC-CL-LIFE-007 → CL-LIFE）
        module = _module_from_tc_id(case_id)
    else:
        logger.warning("  [SKIP] %s 缺少「模块」字段且无表格内容", case_id)
        return None

    # ── 解析 priority ─────────────────────────────────────────────────────
    if priority_m:
        priority = priority_m.group(1).strip()          # 已是 P0/P1/P2
    elif "优先级" in table:
        priority = _normalize_priority(table["优先级"])
    else:
        priority = None

    # 兜底：从标题 【High·xxx】 或 [P0] 提取
    if not priority:
        hm = re.search(r"[【\[](P[012]|[Hh]igh|[Mm]edium|[Ll]ow)[·\s·\]]", title)
        if hm:
            priority = _normalize_priority(hm.group(1))

    if not priority:
        logger.warning("  [SKIP] %s 无法识别优先级（原始值：%r）",
                       case_id, table.get("优先级", ""))
        return None

    # ── 解析 steps ────────────────────────────────────────────────────────
    if steps_m:
        steps = _clean_field(steps_m.group(1))
    elif "操作步骤" in table:
        pre = table.get("前置条件", "").strip()
        raw = table["操作步骤"]
        steps = (f"【前置条件】\n{pre}\n\n【操作步骤】\n{raw}" if pre else raw)
        steps = _clean_field(steps)
    else:
        steps = None

    # ── 解析 expected ─────────────────────────────────────────────────────
    if expected_m:
        expected = _clean_field(expected_m.group(1))
    elif "预期结果" in table:
        expected = _clean_field(table["预期结果"])
    else:
        expected = None

    # 从表格中提取备用的测试点（针对没有写 ## 标题的用例）
    extracted_tp = ""
    if "测试点" in table:
        # 取中英文冒号或空格前面的部分，作为简短测试点，例如 "1.1 未登录拦截：xxxxx" -> "1.1 未登录拦截"
        tp_raw = table["测试点"].split("：")[0].split(":")[0].strip()
        extracted_tp = tp_raw

    return {
        "module":   module,
        "title":    f"[{case_id}] {title}",
        "priority": priority,
        "steps":    steps,
        "expected": expected,
        "extracted_tp": extracted_tp,
    }


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def parse_md_text(text: str) -> list[dict]:
    """
    解析 Markdown 字符串中的测试用例，返回结构化字典列表（不写数据库）。

    每条字典包含键：tc_id, module, title, priority, steps, expected。
    解析失败（缺少必填字段）的用例会被自动跳过并记录警告日志。

    Args:
        text : Markdown 文档的完整字符串内容

    Returns:
        解析成功的用例字典列表
    """
    # 去除 UTF-8 BOM，防止文件首行无法被 ^ 匹配
    text = text.lstrip("\ufeff")

    # 诊断：打印所有 #### 开头的行，帮助排查格式不匹配问题
    h4_lines = [ln for ln in text.splitlines() if ln.startswith("####")]
    if h4_lines:
        logger.info("parse_md_text: 文件中共 %d 行以 #### 开头", len(h4_lines))
        for ln in h4_lines[:5]:
            logger.info("  示例行：%r", ln)
    else:
        logger.warning("parse_md_text: 文件中未发现任何 #### 开头的行")

    blocks = _split_into_blocks(text)
    records = []
    for case_id, title, block, test_point in blocks:
        record = _parse_block(case_id, title, block)
        if record:
            record["tc_id"] = case_id
            record["test_point"] = test_point or record.pop("extracted_tp", "")
            # Ensure no unexpected keys leak out that might break **kwargs to upsert_case
            if "extracted_tp" in record:
                del record["extracted_tp"] 
            records.append(record)
    logger.info("parse_md_text: 共解析出 %d 条用例", len(records))
    return records


def parse_and_import(md_path: str) -> int:
    """
    读取指定 Markdown 文件，解析所有 TC- 用例并批量写入数据库。

    Args:
        md_path : Markdown 文件的路径（字符串或 Path 均可）

    Returns:
        成功导入的用例数量
    """
    path = Path(md_path)

    if not path.exists():
        logger.error("文件不存在：%s", md_path)
        sys.exit(1)
    if path.suffix.lower() != ".md":
        logger.error("需要 .md 文件，实际传入：%s", path.suffix)
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    logger.info("已读取文件：%s（%d 字节）", path.name, len(text.encode("utf-8")))

    blocks = _split_into_blocks(text)
    logger.info("检测到 %d 个 TC- 用例块，开始解析导入...", len(blocks))
    logger.info("=" * 50)

    init_db()  # 幂等：表已存在时跳过创建

    success = 0
    skipped = 0

    for case_id, title, block, test_point in blocks:
        logger.info("  解析中：%s  %s", case_id, title)
        record = _parse_block(case_id, title, block)
        if record is None:
            skipped += 1
            continue
        try:
            # 去除不需要直接入库的扩展字段，并组合出入库所需的终极字段
            extracted_tp = record.pop("extracted_tp", "")
            final_tp = test_point or extracted_tp
            record["test_point"] = final_tp
            record["tc_id"] = case_id
            
            new_id = insert_case(**record)
            logger.info("  [OK] 写入成功，数据库 id=%d", new_id)
            success += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("  [ERR] %s 写入异常：%s", case_id, exc)
            skipped += 1

    logger.info("=" * 50)
    logger.info("导入完成：成功导入 %d 条用例，跳过 %d 条", success, skipped)
    return success


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python parser.py <path/to/testcases.md>")
        sys.exit(1)
    parse_and_import(sys.argv[1])
