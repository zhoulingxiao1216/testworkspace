"""批量上传模板解析与 SKU 同步逻辑。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Sakura insert_new 完整模板：跳过 3 行后 item[4]=商品番号 item[13]=贵社SKU
PHP_FALLBACK_SKIP_ROWS = 3
PHP_FALLBACK_ORDER_COL = 4
PHP_FALLBACK_SKU_COL = 13

ORDER_ID_ALIASES = ("商品番号",)
SKU_ALIASES = ("贵社sku", "貴社sku")
ORDER_ID_EXCLUDE = ("注文番号", "订单号", "注文", "orderid", "orderno")


def _normalize_header(value: Any) -> str:
    text = str(value or "").replace(" ", "").replace("\u3000", "").strip()
    return text


def _normalize_header_lower(value: Any) -> str:
    return _normalize_header(value).lower()


def _normalize_cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def _column_letter(index: int) -> str:
    index += 1
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def find_order_column_index(header_row: List[Any]) -> Optional[int]:
    for idx, cell in enumerate(header_row):
        header = _normalize_header(cell)
        if not header:
            continue
        if "商品番号" not in header:
            continue
        excluded = False
        for bad in ORDER_ID_EXCLUDE:
            if bad in header and "商品番号" not in header.replace(bad, ""):
                excluded = True
                break
        if not excluded:
            return idx
    return None


def find_sku_column_index(header_row: List[Any]) -> Optional[int]:
    """
    识别贵社SKU列。
    优先「贵社SKU / 貴社SKU」，避免误匹配商品属性列 sku 或贴纸模板列 SKU。
    """
    best_idx: Optional[int] = None
    best_score = 0

    for idx, cell in enumerate(header_row):
        header_raw = _normalize_header(cell)
        header = _normalize_header_lower(cell)
        if not header:
            continue

        score = 0
        if header in ("贵社sku", "貴社sku"):
            score = 100
        elif header.endswith("贵社sku") or header.endswith("貴社sku"):
            score = 90
        elif "贵社sku" in header or "貴社sku" in header:
            score = 80
        elif header_raw.upper() == "SKU":
            # 右侧红色「SKU」列（贴纸内容），不是贵社SKU
            score = 10
        elif header == "sku":
            # 商品属性列（颜色/型号），绝不是贵社SKU
            score = 0
        else:
            continue

        if score > best_score:
            best_score = score
            best_idx = idx

    if best_score >= 80:
        return best_idx
    return None


def find_main_order_column_index(header_row: List[Any]) -> Optional[int]:
    """识别主订单号列（注文番号）。"""
    for idx, cell in enumerate(header_row):
        header = _normalize_header(cell)
        if not header:
            continue
        if header in ("注文番号", "主订单号", "订单号"):
            return idx
        if "注文番号" in header and "商品" not in header:
            return idx
    return None


def find_header_row(df: pd.DataFrame) -> Optional[Tuple[int, int, int, Optional[int]]]:
    for idx in range(len(df)):
        row = df.iloc[idx].tolist()
        col_order = find_order_column_index(row)
        col_sku = find_sku_column_index(row)
        if col_order is not None and col_sku is not None:
            col_main = find_main_order_column_index(row)
            return idx, col_order, col_sku, col_main
    return None


def _parse_with_columns(
    df: pd.DataFrame,
    header_row_idx: int,
    col_order: int,
    col_sku: int,
    *,
    source: str,
    col_main_order: Optional[int] = None,
) -> Tuple[List[dict], dict]:
    data = df.iloc[header_row_idx + 1 :]
    rows: List[dict] = []
    for excel_row_no, (_, record) in enumerate(data.iterrows(), start=header_row_idx + 2):
        order_id = _normalize_cell(record.iloc[col_order] if col_order < len(record) else "")
        external_id = _normalize_cell(record.iloc[col_sku] if col_sku < len(record) else "")
        main_order_id = ""
        if col_main_order is not None and col_main_order < len(record):
            main_order_id = _normalize_cell(record.iloc[col_main_order])
        if not order_id:
            continue
        rows.append(
            {
                "order_id": order_id,
                "external_id": external_id,
                "main_order_id": main_order_id,
                "row_no": excel_row_no,
            }
        )

    header = df.iloc[header_row_idx].tolist()
    meta = {
        "source": source,
        "header_row_idx": header_row_idx,
        "col_order": col_order,
        "col_sku": col_sku,
        "col_main_order": col_main_order,
        "col_order_letter": _column_letter(col_order),
        "col_sku_letter": _column_letter(col_sku),
        "col_main_order_letter": _column_letter(col_main_order) if col_main_order is not None else "",
        "header_order": _normalize_cell(header[col_order] if col_order < len(header) else ""),
        "header_sku": _normalize_cell(header[col_sku] if col_sku < len(header) else ""),
        "header_main_order": (
            _normalize_cell(header[col_main_order])
            if col_main_order is not None and col_main_order < len(header)
            else ""
        ),
        "header": [str(h) for h in header],
        "parsed_count": len(rows),
        "total_rows": len(df),
    }
    return rows, meta


def parse_bulk_template(file_bytes: bytes) -> Tuple[List[dict], dict]:
    df = pd.read_excel(BytesIO(file_bytes), header=None, engine="openpyxl")
    if df.empty:
        raise ValueError("Excel 为空，请确认文件内容")

    found = find_header_row(df)
    if found:
        header_row_idx, col_order, col_sku, col_main = found
        rows, meta = _parse_with_columns(
            df,
            header_row_idx,
            col_order,
            col_sku,
            source="header_scan",
            col_main_order=col_main,
        )
        if rows:
            return rows, meta

    if len(df.columns) > PHP_FALLBACK_SKU_COL and len(df) > PHP_FALLBACK_SKIP_ROWS:
        rows, meta = _parse_with_columns(
            df,
            PHP_FALLBACK_SKIP_ROWS,
            PHP_FALLBACK_ORDER_COL,
            PHP_FALLBACK_SKU_COL,
            source="php_fallback",
            col_main_order=3 if len(df.columns) > 3 else None,
        )
        if rows:
            return rows, meta

    preview = []
    for i in range(min(8, len(df))):
        preview.append([_normalize_cell(x) for x in df.iloc[i].tolist()[:16]])

    raise ValueError(
        "无法识别贴纸/吊牌批量模板。"
        f"共 {len(df)} 行、{len(df.columns)} 列。"
        "请确认表头含「商品番号」和「贵社SKU/貴社SKU」，且至少有一行商品数据。"
        f" 前几行预览：{preview}"
    )


def build_sync_plan(parsed_rows: List[dict]) -> List[dict]:
    plan: List[dict] = []
    for row in parsed_rows:
        new_sku = row["external_id"]
        if not new_sku:
            plan.append(
                {
                    **row,
                    "current_sku": "",
                    "action": "skip",
                    "reason": "Excel 贵社SKU 为空",
                }
            )
            continue
        plan.append(
            {
                **row,
                "current_sku": "",
                "action": "update",
                "reason": "待同步",
            }
        )
    return plan


def attach_current_sku(
    plan: List[dict],
    order_items: Dict[str, str],
    *,
    preview_attempted: bool = True,
) -> List[dict]:
    enriched: List[dict] = []
    for row in plan:
        item = dict(row)
        if item.get("action") != "update":
            enriched.append(item)
            continue

        order_id = _normalize_cell(item.get("order_id", ""))
        current = order_items.get(order_id, "")
        if not current:
            for key, value in order_items.items():
                if _normalize_cell(key) == order_id:
                    current = value
                    break

        item["current_sku"] = current
        if not current:
            if not preview_attempted:
                item["reason"] = "待同步（未找到主订单号，无法预览后台SKU）"
            else:
                item["reason"] = "待同步（未在主订单中匹配到该商品番号）"
        elif current == item["external_id"]:
            item["action"] = "skip"
            item["reason"] = "SKU 已一致"
        else:
            item["reason"] = "待同步"
        enriched.append(item)
    return enriched


def resolve_preview_order_ids(manual_order_id: str, parsed_rows: List[dict]) -> List[str]:
    """合并手动填写与 Excel 注文番号列，得到待拉取的主订单号列表。"""
    order_ids: List[str] = []
    seen = set()

    manual = _normalize_cell(manual_order_id)
    if manual:
        order_ids.append(manual)
        seen.add(manual)

    for row in parsed_rows:
        main_order_id = _normalize_cell(row.get("main_order_id", ""))
        if main_order_id and main_order_id not in seen:
            order_ids.append(main_order_id)
            seen.add(main_order_id)

    return order_ids


def fetch_preview_mapping(
    main_order_ids: List[str],
    token_info: dict,
    fetch_order_items,
) -> Tuple[Dict[str, str], List[str]]:
    combined: Dict[str, str] = {}
    errors: List[str] = []
    for main_order_id in main_order_ids:
        resp = fetch_order_items(main_order_id, token_info)
        if not resp.get("success"):
            errors.append(f"{main_order_id}: {resp.get('error', '未知错误')}")
            continue
        combined.update(extract_order_items(resp["data"]))
    return combined, errors


def extract_order_items(api_payload: dict) -> Dict[str, str]:
    data = api_payload.get("data", {})
    products = data.get("lists", []) if isinstance(data, dict) else []
    mapping: Dict[str, str] = {}
    for product in products:
        oid = _normalize_cell(product.get("order_id", ""))
        if oid:
            mapping[oid] = str(product.get("order_ExternalID") or "").strip()
    return mapping


def write_sync_log(
    payload: dict,
    *,
    log_dir: Optional[Path] = None,
) -> Path:
    base = log_dir or Path(__file__).resolve().parent.parent / "sku_sync_logs"
    base.mkdir(exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    path = base / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
