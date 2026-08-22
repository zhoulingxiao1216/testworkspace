"""8160 贴纸 SKU 定向修改工具逻辑。

该模块读取单个商品当前贴纸数据，并执行受控的单商品更新/贴纸重生成操作。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pymysql
from sshtunnel import SSHTunnelForwarder

from modules.readonly_db import fetch_all


TARGET_USER_ID = 8160
MAX_ITEM_COUNT = 50

DEFAULT_MAIN_ORDER_ID = "816026070791"
DEFAULT_UPLOAD_TYPE = "816026070792"
DEFAULT_ITEM_IDS_TEXT = "1379534\n1379533\n1379532\n1379531"
DEFAULT_MAPPING_TEXT = """FL-1806-L-BL => FL-1806-F-BL
FL-1806-M-BL => FL-1806-F-BL
FL-1806-L-WH => FL-1806-F-WH
FL-1806-M-WH => FL-1806-F-WH"""

SAKURA_DB_TOOL = Path(r"D:\sakura\tools\sakura-db\connect.py")
SAKURA_DB_PYTHON = Path(r"C:\Python314\python.exe")
SAKURA_DB_CONFIG = SAKURA_DB_TOOL.parent / "config.local.json"


class StickerSkuToolError(ValueError):
    """用户输入或预检查失败。"""


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.strip()
    if text.lower() == "nan":
        return ""
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def parse_item_ids(raw_text: str) -> List[str]:
    tokens = re.split(r"[\s,，;；]+", raw_text or "")
    item_ids: List[str] = []
    seen = set()

    for token in tokens:
        item_id = normalize_text(token)
        if not item_id:
            continue
        if not re.fullmatch(r"\d+", item_id):
            raise StickerSkuToolError(f"商品番号只能是数字：{item_id}")
        if item_id not in seen:
            item_ids.append(item_id)
            seen.add(item_id)

    if not item_ids:
        raise StickerSkuToolError("请至少填写一个商品番号。")
    if len(item_ids) > MAX_ITEM_COUNT:
        raise StickerSkuToolError(f"单次最多处理 {MAX_ITEM_COUNT} 个商品番号。")
    return item_ids


def parse_sku_mapping(raw_text: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}

    for line_no, raw_line in enumerate((raw_text or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if "=>" in line:
            old_sku, new_sku = line.split("=>", 1)
        elif "->" in line:
            old_sku, new_sku = line.split("->", 1)
        elif "→" in line:
            old_sku, new_sku = line.split("→", 1)
        else:
            parts = re.split(r"[\t,，]+", line)
            if len(parts) != 2:
                raise StickerSkuToolError(f"第 {line_no} 行替换关系格式不正确：{raw_line}")
            old_sku, new_sku = parts

        old_sku = normalize_text(old_sku)
        new_sku = normalize_text(new_sku)
        if not old_sku or not new_sku:
            raise StickerSkuToolError(f"第 {line_no} 行替换关系不能为空：{raw_line}")
        mapping[old_sku] = new_sku

    if not mapping:
        raise StickerSkuToolError("请填写至少一组 SKU 替换关系。")
    return mapping


def validate_basic_inputs(main_order_id: str, upload_type: str) -> tuple[str, str]:
    main_order_id = normalize_text(main_order_id)
    upload_type = normalize_text(upload_type)

    if not main_order_id:
        raise StickerSkuToolError("请填写主订单号。")
    if not upload_type:
        raise StickerSkuToolError("请填写上传批次 / type。")
    if not re.fullmatch(r"\d+", main_order_id):
        raise StickerSkuToolError("主订单号只能是数字。")
    if not re.fullmatch(r"\d+", upload_type):
        raise StickerSkuToolError("上传批次 / type 只能是数字。")
    return main_order_id, upload_type


def validate_main_order_id(main_order_id: str) -> str:
    main_order_id = normalize_text(main_order_id)
    if not main_order_id:
        raise StickerSkuToolError("请填写主订单号。")
    if not re.fullmatch(r"\d+", main_order_id):
        raise StickerSkuToolError("主订单号只能是数字。")
    return main_order_id


def _placeholders(values: Sequence[Any]) -> str:
    return ",".join(["%s"] * len(values))


def _render_sql(sql: str, params: Sequence[Any] | None = None) -> str:
    rendered = sql
    for param in params or ():
        rendered = rendered.replace("%s", sql_quote(param), 1)
    return rendered


def _parse_tsv_query_output(output: str) -> List[Dict[str, Any]]:
    lines = [line for line in (output or "").splitlines() if line.strip()]
    data_lines = [line for line in lines if not re.fullmatch(r"\(\d+ rows?\)", line.strip())]
    if not data_lines:
        return []

    columns = data_lines[0].split("\t")
    rows: List[Dict[str, Any]] = []
    for line in data_lines[1:]:
        values = line.split("\t")
        if len(values) < len(columns):
            values.extend([""] * (len(columns) - len(values)))
        rows.append(dict(zip(columns, values)))
    return rows


def _fetch_all_via_sakura_db_tool(sql: str, params: Sequence[Any] | None = None) -> List[Dict[str, Any]]:
    if not SAKURA_DB_TOOL.exists():
        raise FileNotFoundError(f"未找到只读查询工具：{SAKURA_DB_TOOL}")

    rendered_sql = _render_sql(sql, params)
    python_exe = str(SAKURA_DB_PYTHON) if SAKURA_DB_PYTHON.exists() else (shutil.which("python") or "python")
    completed = subprocess.run(
        [python_exe, str(SAKURA_DB_TOOL), "query", rendered_sql],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(detail or f"sakura-db 查询失败，退出码 {completed.returncode}")
    return _parse_tsv_query_output(completed.stdout)


def fetch_all_readonly(
    sql: str,
    params: Sequence[Any] | None = None,
    *,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """读取正式库数据。

    本地测试环境直连 PolarDB 经常超时；若存在 Sakura 只读 SSH 查询工具，
    优先使用该工具。该工具自身只允许 SELECT/SHOW/DESCRIBE/EXPLAIN 等只读 SQL。
    """

    if SAKURA_DB_TOOL.exists():
        return _fetch_all_via_sakura_db_tool(sql, params)
    return fetch_all(sql, params=params, limit=limit)


def _to_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_deleted_pub_row(row: Dict[str, Any]) -> bool:
    return _to_int(row.get("pub_delete_time"), 0) > 0


def fetch_target_rows(
    main_order_id: str,
    upload_type: str,
    item_ids: Sequence[str],
    sku_mapping: Dict[str, str],
) -> List[Dict[str, Any]]:
    """读取目标商品当前状态，并按 SKU 替换关系补充校验结果。"""

    if not item_ids:
        raise StickerSkuToolError("商品番号不能为空。")

    in_sql = _placeholders(item_ids)
    upload_type = normalize_text(upload_type)
    upload_type_filter = "          AND p2.type = %s\n" if upload_type else ""
    sql = f"""
SELECT
    od.orderid,
    od.order_id,
    od.uid,
    od.quote_order_id,
    od.order_ExternalID AS current_top_sku,
    q.order_ExternalID AS quote_top_sku,
    p.id AS pub_id,
    p.type AS upload_type,
    p.sku AS barcode_sku,
    p.jan_code,
    p.stickers_status,
    p.source_id,
    p.is_stickers,
    p.delete_time AS pub_delete_time,
    pn.pic_id,
    pn.config_title AS pic_title,
    pn.pic_url,
    FROM_UNIXTIME(pn.add_time) AS pic_add_time
FROM xierun.orderdetail od
LEFT JOIN xierun.quotedetail q
    ON q.order_id = od.quote_order_id
   AND q.uid = od.uid
LEFT JOIN `api-open`.pub_api_order_new p
    ON p.id = (
        SELECT p2.id
        FROM `api-open`.pub_api_order_new p2
        WHERE p2.user_order_id = od.order_id
          AND p2.uuid = od.uid
{upload_type_filter}          AND p2.source_id = 1
          AND p2.is_stickers = 1
        ORDER BY CASE WHEN p2.delete_time = 0 THEN 0 ELSE 1 END, p2.id DESC
        LIMIT 1
    )
LEFT JOIN xierun.pic_newspaper pn
    ON pn.pic_id = (
        SELECT MAX(pn2.pic_id)
        FROM xierun.pic_newspaper pn2
        WHERE pn2.item_id = od.order_id
          AND pn2.user_id = od.uid
    )
WHERE od.uid = %s
  AND od.orderid = %s
  AND od.order_id IN ({in_sql})
ORDER BY od.order_id
""".strip()

    params: List[Any] = []
    if upload_type:
        params.append(upload_type)
    params.extend([TARGET_USER_ID, main_order_id, *item_ids])
    db_rows = fetch_all_readonly(sql, params=params, limit=max(len(item_ids), 1) + 20)
    by_item_id = {normalize_text(row.get("order_id")): dict(row) for row in db_rows}

    rows: List[Dict[str, Any]] = []
    target_values = set(sku_mapping.values())

    for item_id in item_ids:
        row = by_item_id.get(item_id)
        if not row:
            rows.append(
                {
                    "order_id": item_id,
                    "current_top_sku": "",
                    "new_top_sku": "",
                    "status": "blocked",
                    "reason": "未找到商品，或商品不属于该主订单 / 8160 用户。",
                }
            )
            continue

        current_top_sku = normalize_text(row.get("current_top_sku"))
        new_top_sku = sku_mapping.get(current_top_sku, "")
        status = "ready"
        reasons: List[str] = []

        if _to_int(row.get("uid")) != TARGET_USER_ID:
            reasons.append("uid 不是 8160")
        if normalize_text(row.get("orderid")) != main_order_id:
            reasons.append("主订单号不匹配")
        if not row.get("pub_id"):
            reasons.append("未找到对应上传批次的 pub_api_order_new 记录")
        if row.get("pub_id") and _is_deleted_pub_row(row):
            reasons.append("最新贴纸上传记录已作废，需勾选恢复后才能更新")
        if upload_type and row.get("pub_id") and normalize_text(row.get("upload_type")) != upload_type:
            reasons.append("上传批次 / type 不匹配")
        if row.get("pub_id") and _to_int(row.get("source_id")) != 1:
            reasons.append("source_id 不是 1，非订单 Excel 导入记录")
        if row.get("pub_id") and _to_int(row.get("is_stickers")) != 1:
            reasons.append("该记录未勾选贴纸 is_stickers")

        if not new_top_sku:
            if current_top_sku in target_values:
                status = "already_target"
                new_top_sku = current_top_sku
                reasons.append("当前上方 SKU 已是目标值，不会纳入 UPDATE。")
            else:
                reasons.append("当前上方 SKU 未命中替换关系")

        if reasons and status != "already_target":
            status = "blocked"

        row.update(
            {
                "order_id": item_id,
                "current_top_sku": current_top_sku,
                "new_top_sku": new_top_sku,
                "status": status,
                "reason": "；".join(reasons) if reasons else "可更新",
            }
        )
        rows.append(row)

    return rows


def fetch_item_snapshot(main_order_id: str, item_id: str) -> Dict[str, Any]:
    """按单个商品番号读取当前上方 SKU、贴纸条码和最新上传批次。"""

    main_order_id = validate_main_order_id(main_order_id)
    item_ids = parse_item_ids(item_id)
    if len(item_ids) != 1:
        raise StickerSkuToolError("每次只允许处理一个商品番号，请只填写一个。")

    rows = fetch_target_rows(main_order_id, "", item_ids, {"__snapshot__": "__snapshot__"})
    row = rows[0] if rows else {"order_id": item_ids[0]}
    row = dict(row)
    if row.get("pub_id"):
        row["status"] = "snapshot"
        row["reason"] = "已读取当前 SKU 和贴纸条码。"
    return row


def fetch_manual_change_rows(
    main_order_id: str,
    item_id: str,
    new_top_sku: str,
    new_barcode_sku: str,
    allow_restore_deleted: bool = False,
) -> List[Dict[str, Any]]:
    """按用户手工输入的目标 SKU / 贴纸条码构建单商品预检查结果。"""

    row = fetch_item_snapshot(main_order_id, item_id)
    current_top_sku = normalize_text(row.get("current_top_sku"))
    current_barcode_sku = normalize_text(row.get("barcode_sku"))
    target_top_sku = normalize_text(new_top_sku)
    target_barcode_sku = normalize_text(new_barcode_sku)

    reasons: List[str] = []
    if not row.get("pub_id"):
        reasons.append("未找到对应商品或最新有效贴纸上传记录")
    if row.get("pub_id") and _is_deleted_pub_row(row) and not allow_restore_deleted:
        reasons.append("最新贴纸上传记录已作废，请勾选允许恢复后再更新")
    if row.get("pub_id") and _to_int(row.get("source_id")) != 1:
        reasons.append("source_id 不是 1，非订单 Excel 导入记录")
    if row.get("pub_id") and _to_int(row.get("is_stickers")) != 1:
        reasons.append("该记录未勾选贴纸 is_stickers")
    if not target_top_sku:
        reasons.append("修改后 SKU 不能为空")
    if not target_barcode_sku:
        reasons.append("修改后贴纸条码不能为空")

    if reasons:
        status = "blocked"
        reason = "；".join(reasons)
    elif _is_deleted_pub_row(row):
        status = "ready"
        reason = "可更新，将恢复已作废上传记录并重置贴纸状态"
    elif target_top_sku == current_top_sku and target_barcode_sku == current_barcode_sku:
        status = "already_target"
        reason = "修改后 SKU 和贴纸条码均与当前值一致，不会纳入 UPDATE。"
    else:
        status = "ready"
        reason = "可更新"

    row.update(
        {
            "new_top_sku": target_top_sku,
            "new_barcode_sku": target_barcode_sku,
            "status": status,
            "reason": reason,
        }
    )
    return [row]


def _load_sakura_db_config() -> Dict[str, Any]:
    if not SAKURA_DB_CONFIG.exists():
        raise FileNotFoundError(f"未找到数据库连接配置：{SAKURA_DB_CONFIG}")
    with SAKURA_DB_CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def _open_sakura_db_tunnel(cfg: Dict[str, Any]) -> SSHTunnelForwarder:
    ssh = cfg["ssh"]
    mysql = cfg["mysql"]
    tunnel = cfg["tunnel"]
    return SSHTunnelForwarder(
        (ssh["host"], int(ssh["port"])),
        ssh_username=ssh["username"],
        ssh_password=ssh["password"],
        remote_bind_address=(mysql["host"], int(mysql["port"])),
        local_bind_address=(tunnel["local_host"], int(tunnel["local_port"])),
    )


def _open_write_connection(cfg: Dict[str, Any], server: SSHTunnelForwarder) -> pymysql.connections.Connection:
    mysql = cfg["mysql"]
    return pymysql.connect(
        host=cfg["tunnel"]["local_host"],
        port=server.local_bind_port,
        user=mysql["username"],
        password=mysql["password"],
        database=mysql.get("database", "xierun"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
        read_timeout=30,
        write_timeout=30,
        autocommit=False,
    )


def execute_item_update(
    main_order_id: str,
    item_id: str,
    new_top_sku: str,
    new_barcode_sku: str,
    allow_restore_deleted: bool = False,
) -> Dict[str, Any]:
    """确认更新单个商品的贴纸 SKU / 贴纸条码。"""

    main_order_id = validate_main_order_id(main_order_id)
    item_ids = parse_item_ids(item_id)
    if len(item_ids) != 1:
        raise StickerSkuToolError("每次只允许处理一个商品番号，请只填写一个。")

    item_id = item_ids[0]
    target_top_sku = normalize_text(new_top_sku)
    target_barcode_sku = normalize_text(new_barcode_sku)
    if not target_top_sku:
        raise StickerSkuToolError("修改后 SKU 不能为空。")
    if not target_barcode_sku:
        raise StickerSkuToolError("修改后贴纸条码不能为空。")

    before = fetch_item_snapshot(main_order_id, item_id)
    if not before.get("pub_id"):
        raise StickerSkuToolError("未找到该商品最新有效贴纸上传记录，不能更新。")
    restore_deleted = _is_deleted_pub_row(before)
    if restore_deleted and not allow_restore_deleted:
        raise StickerSkuToolError("该商品最新贴纸上传记录已作废，请勾选允许恢复后再更新。")

    current_top_sku = normalize_text(before.get("current_top_sku"))
    current_barcode_sku = normalize_text(before.get("barcode_sku"))
    top_changed = target_top_sku != current_top_sku
    barcode_changed = target_barcode_sku != current_barcode_sku
    if not top_changed and not barcode_changed and not restore_deleted:
        raise StickerSkuToolError("修改后 SKU 和贴纸条码均与当前值一致，无需更新。")

    cfg = _load_sakura_db_config()
    affected = {
        "orderdetail": 0,
        "quotedetail": 0,
        "pub_api_order_new": 0,
    }

    with _open_sakura_db_tunnel(cfg) as server:
        conn = _open_write_connection(cfg, server)
        try:
            with conn.cursor() as cursor:
                if top_changed:
                    cursor.execute(
                        """
UPDATE xierun.orderdetail
SET order_ExternalID = %s
WHERE uid = %s
  AND orderid = %s
  AND order_id = %s
  AND order_ExternalID = %s
""".strip(),
                        (target_top_sku, TARGET_USER_ID, main_order_id, item_id, current_top_sku),
                    )
                    affected["orderdetail"] = cursor.rowcount
                    if cursor.rowcount != 1:
                        raise StickerSkuToolError("orderdetail 更新行数异常，已回滚。")

                    cursor.execute(
                        """
UPDATE xierun.quotedetail q
JOIN xierun.orderdetail od
    ON od.quote_order_id = q.order_id
   AND od.uid = q.uid
SET q.order_ExternalID = od.order_ExternalID
WHERE od.uid = %s
  AND od.orderid = %s
  AND od.order_id = %s
""".strip(),
                        (TARGET_USER_ID, main_order_id, item_id),
                    )
                    affected["quotedetail"] = cursor.rowcount

                if barcode_changed or restore_deleted:
                    set_parts = []
                    set_params: List[Any] = []
                    if barcode_changed:
                        set_parts.append("sku = %s")
                        set_params.append(target_barcode_sku)
                    if restore_deleted:
                        set_parts.append("delete_time = 0")
                        set_parts.append("stickers_status = 0")

                    delete_time_condition = "AND delete_time = %s" if restore_deleted else "AND delete_time = 0"
                    sku_condition = "AND sku = %s" if barcode_changed else ""
                    where_params: List[Any] = [before["pub_id"], TARGET_USER_ID, item_id]
                    if restore_deleted:
                        where_params.append(_to_int(before.get("pub_delete_time"), 0))
                    if barcode_changed:
                        where_params.append(current_barcode_sku)

                    cursor.execute(
                        f"""
UPDATE `api-open`.pub_api_order_new
SET {", ".join(set_parts)}
WHERE id = %s
  AND uuid = %s
  AND user_order_id = %s
  AND source_id = 1
  AND is_stickers = 1
  {delete_time_condition}
  {sku_condition}
""".strip(),
                        tuple(set_params + where_params),
                    )
                    affected["pub_api_order_new"] = cursor.rowcount
                    if cursor.rowcount != 1:
                        raise StickerSkuToolError("pub_api_order_new 更新行数异常，已回滚。")

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    after = fetch_item_snapshot(main_order_id, item_id)
    log_path = write_operation_log(
        {
            "action": "confirm_update",
            "main_order_id": main_order_id,
            "item_id": item_id,
            "target_top_sku": target_top_sku,
            "target_barcode_sku": target_barcode_sku,
            "allow_restore_deleted": allow_restore_deleted,
            "restore_deleted": restore_deleted,
            "affected": affected,
            "before": before,
            "after": after,
        }
    )
    return {"affected": affected, "before": before, "after": after, "log_path": str(log_path)}


def trigger_sticker_regenerate(
    main_order_id: str,
    item_id: str,
    allow_restore_deleted: bool = False,
) -> Dict[str, Any]:
    """重置单个商品贴纸生成状态。"""

    main_order_id = validate_main_order_id(main_order_id)
    item_ids = parse_item_ids(item_id)
    if len(item_ids) != 1:
        raise StickerSkuToolError("每次只允许处理一个商品番号，请只填写一个。")

    item_id = item_ids[0]
    before = fetch_item_snapshot(main_order_id, item_id)
    if not before.get("pub_id"):
        raise StickerSkuToolError("未找到该商品最新有效贴纸上传记录，不能重新生成。")
    restore_deleted = _is_deleted_pub_row(before)
    if restore_deleted and not allow_restore_deleted:
        raise StickerSkuToolError("该商品最新贴纸上传记录已作废，请勾选允许恢复后再重新生成。")

    cfg = _load_sakura_db_config()
    affected = 0
    with _open_sakura_db_tunnel(cfg) as server:
        conn = _open_write_connection(cfg, server)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
UPDATE `api-open`.pub_api_order_new
SET {"delete_time = 0, " if restore_deleted else ""}stickers_status = 0
WHERE id = %s
  AND uuid = %s
  AND user_order_id = %s
  AND source_id = 1
  AND is_stickers = 1
  {"AND delete_time = %s" if restore_deleted else "AND delete_time = 0"}
""".strip(),
                    (
                        before["pub_id"],
                        TARGET_USER_ID,
                        item_id,
                        *([_to_int(before.get("pub_delete_time"), 0)] if restore_deleted else []),
                    ),
                )
                affected = cursor.rowcount
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    after = fetch_item_snapshot(main_order_id, item_id)
    log_path = write_operation_log(
        {
            "action": "regenerate_sticker",
            "main_order_id": main_order_id,
            "item_id": item_id,
            "allow_restore_deleted": allow_restore_deleted,
            "restore_deleted": restore_deleted,
            "affected": affected,
            "before": before,
            "after": after,
        }
    )
    return {"affected": affected, "before": before, "after": after, "log_path": str(log_path)}


def sql_quote(value: Any) -> str:
    text = normalize_text(value)
    return "'" + text.replace("\\", "\\\\").replace("'", "''") + "'"


def write_operation_log(payload: Dict[str, Any], *, prefix: str = "sticker_regen") -> Path:
    base = Path(__file__).resolve().parent.parent / "sku_sync_logs"
    base.mkdir(exist_ok=True)
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = base / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path
