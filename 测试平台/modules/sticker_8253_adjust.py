"""8253 short-sticker adjustment helpers for the SKU bulk sync page."""

from __future__ import annotations

import base64
import json
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

import requests
from PIL import Image, ImageDraw, ImageFont

from modules.sakura_client import BASE_URL, create_direct_session
from modules.sticker_sku_regen import fetch_all_readonly, normalize_text, write_operation_log


TARGET_UID = "8253"
SHORT_TAG_CONFIG_ID = -15582
CANVAS_WIDTH = 300
CANVAS_HEIGHT = 82
IMAGE_SCALE = 2
FONT_SIZE = 22
MIN_SCALE = 0.4
MAX_TEXT_WIDTH = CANVAS_WIDTH - 20
INVALID_TEXT_MARKERS = ("\ufffd", "�")


class Sticker8253AdjustError(ValueError):
    """Raised when the 8253 sticker adjustment cannot continue safely."""


def validate_main_order_id(main_order_id: str) -> str:
    main_order_id = normalize_text(main_order_id)
    if not main_order_id:
        raise Sticker8253AdjustError("请填写主订单号。")
    if not re.fullmatch(r"\d+", main_order_id):
        raise Sticker8253AdjustError("主订单号只能是数字。")
    return main_order_id


def fetch_8253_short_sticker_rows(main_order_id: str) -> List[Dict[str, Any]]:
    """Fetch current order sticker rows for uid 8253."""

    main_order_id = validate_main_order_id(main_order_id)
    sql = """
SELECT
    od.orderid,
    od.order_id,
    od.uid,
    od.order_ExternalID AS external_id,
    pn.pic_id,
    pn.config_id,
    pn.config_title,
    pn.width,
    pn.height,
    pn.pic_url,
    pn.json_url,
    pn.base64_url,
    FROM_UNIXTIME(pn.add_time) AS pic_add_time,
    FROM_UNIXTIME(pn.up_time) AS pic_up_time
FROM xierun.orderdetail od
LEFT JOIN xierun.pic_newspaper pn
    ON pn.pic_id = (
        SELECT MAX(pn2.pic_id)
        FROM xierun.pic_newspaper pn2
        WHERE pn2.item_id = od.order_id
          AND pn2.user_id = od.uid
          AND pn2.pic_type = 1
    )
WHERE od.uid = %s
  AND od.orderid = %s
ORDER BY od.order_id
""".strip()

    rows = fetch_all_readonly(sql, params=[TARGET_UID, main_order_id], limit=500)
    return [_classify_row(dict(row)) for row in rows]


def has_invalid_sticker_text(value: Any) -> bool:
    text = normalize_text(value)
    return any(marker in text for marker in INVALID_TEXT_MARKERS)


def apply_external_id_overrides(
    rows: Sequence[Dict[str, Any]],
    sku_by_order_id: Dict[str, str],
    *,
    source: str,
) -> List[Dict[str, Any]]:
    adjusted_rows: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        order_id = normalize_text(item.get("order_id"))
        override = normalize_text(sku_by_order_id.get(order_id))
        if override:
            item["db_external_id"] = item.get("external_id", "")
            item["external_id"] = override
            item["external_id_source"] = source
        adjusted_rows.append(_classify_row(item))
    return adjusted_rows


def adjust_8253_short_stickers(
    main_order_id: str,
    admin_sessid: str,
    rows: Sequence[Dict[str, Any]] | None = None,
    *,
    overwrite_manual: bool = False,
) -> Dict[str, Any]:
    """Save 22pt short-sticker images through the existing Sakura edit endpoint."""

    main_order_id = validate_main_order_id(main_order_id)
    if not admin_sessid:
        raise Sticker8253AdjustError("后台 PHPSESSID 不能为空。")

    source_rows = list(rows) if rows is not None else fetch_8253_short_sticker_rows(main_order_id)
    results: List[Dict[str, Any]] = []
    success = failed = skipped = 0

    for row in source_rows:
        item_id = normalize_text(row.get("order_id"))
        external_id = normalize_text(row.get("external_id"))
        is_manual = bool(row.get("is_manual_saved"))

        if not item_id:
            skipped += 1
            results.append(_result_row(row, "skipped", "missing_item_id"))
            continue
        if not external_id:
            failed += 1
            results.append(_result_row(row, "failed", "empty_external_id"))
            continue
        if has_invalid_sticker_text(external_id):
            failed += 1
            results.append(_result_row(row, "failed", "invalid_external_id_encoding"))
            continue
        if is_manual and not overwrite_manual:
            skipped += 1
            results.append(_result_row(row, "skipped", "manual_json_url"))
            continue

        try:
            payload = build_short_sticker_payload(row)
            response = save_short_sticker(item_id, admin_sessid, payload)
            if response.get("success"):
                success += 1
                results.append(_result_row(row, "success", "saved", response=response.get("body")))
            else:
                failed += 1
                results.append(
                    _result_row(
                        row,
                        "failed",
                        response.get("detail") or response.get("error") or "api_error",
                        response=response.get("body"),
                    )
                )
        except Exception as exc:
            failed += 1
            results.append(_result_row(row, "failed", str(exc)))

        time.sleep(0.05)

    log_path = write_operation_log(
        {
            "action": "adjust_8253_short_stickers",
            "main_order_id": main_order_id,
            "uid": TARGET_UID,
            "overwrite_manual": overwrite_manual,
            "summary": {
                "total": len(source_rows),
                "success": success,
                "failed": failed,
                "skipped": skipped,
            },
            "results": results,
        },
        prefix="sticker_8253_adjust",
    )

    return {
        "main_order_id": main_order_id,
        "uid": TARGET_UID,
        "overwrite_manual": overwrite_manual,
        "total": len(source_rows),
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "results": results,
        "log_path": str(log_path),
    }


def build_short_sticker_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    text = normalize_text(row.get("external_id"))
    if has_invalid_sticker_text(text):
        raise Sticker8253AdjustError(f"SKU含乱码，禁止保存：{text}")
    pic_id = int(row.get("pic_id") or 0)
    image_data_url, metrics = render_short_sticker_png(text)
    fabric_json = build_fabric_json(text, metrics)

    return {
        "type": 1,
        "config_id": SHORT_TAG_CONFIG_ID,
        "pic_id": pic_id,
        "data": json.dumps(fabric_json, ensure_ascii=False, separators=(",", ":")),
        "base64": image_data_url,
        "saveTemplate": "true",
        "saveTag": "true",
        "title": text,
    }


def save_short_sticker(item_id: str, admin_sessid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    session = create_direct_session()
    session.cookies.set("PHPSESSID", admin_sessid, domain="sakuradk2.com")
    url = f"{BASE_URL}/api/Pic_Newspaper/updateOrderTag"
    params = {"itemid": item_id, "type": 1}
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/x-www-form-urlencoded",
        "origin": BASE_URL,
        "referer": f"{BASE_URL}/vue/tagDesign/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }

    try:
        resp = session.post(url, params=params, headers=headers, data=payload, timeout=30)
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": "NETWORK_ERROR", "detail": str(exc)}
    except ValueError:
        return {"success": False, "error": "INVALID_JSON", "detail": resp.text[:200]}

    status = body.get("status")
    if status in (1, "1", 200, "200"):
        return {"success": True, "body": body}

    return {
        "success": False,
        "error": "API_ERROR",
        "detail": body.get("msg") or body.get("message") or str(body),
        "body": body,
    }


def render_short_sticker_png(text: str) -> tuple[str, Dict[str, float]]:
    width = CANVAS_WIDTH * IMAGE_SCALE
    height = CANVAS_HEIGHT * IMAGE_SCALE
    max_width = MAX_TEXT_WIDTH * IMAGE_SCALE
    font_size = FONT_SIZE * IMAGE_SCALE
    font = _load_font(font_size)

    measure_image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(measure_image)
    bbox = draw.textbbox((0, 0), text, font=font)
    raw_text_width = max(1, bbox[2] - bbox[0])
    raw_text_height = max(1, bbox[3] - bbox[1])
    scale = min(1.0, max_width / raw_text_width)
    scale = max(MIN_SCALE, scale)

    effective_font_size = max(8, int(round(font_size * scale)))
    effective_font = _load_font(effective_font_size)
    bbox = draw.textbbox((0, 0), text, font=effective_font)
    text_width = max(1, bbox[2] - bbox[0])
    text_height = max(1, bbox[3] - bbox[1])
    x = int(round((width - text_width) / 2 - bbox[0]))
    y = int(round((height - text_height) / 2 - bbox[1]))

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((x, y), text, fill=(0, 0, 0), font=effective_font)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    metrics = {
        "raw_text_width": raw_text_width / IMAGE_SCALE,
        "raw_text_height": raw_text_height / IMAGE_SCALE,
        "scale": scale,
    }
    return data_url, metrics


def build_fabric_json(text: str, metrics: Dict[str, float]) -> Dict[str, Any]:
    raw_width = float(metrics["raw_text_width"])
    raw_height = float(metrics["raw_text_height"])
    scale = float(metrics["scale"])
    left = (CANVAS_WIDTH - raw_width * scale) / 2
    top = (CANVAS_HEIGHT - raw_height * scale) / 2

    return {
        "version": "5.3.0",
        "objects": [
            {
                "type": "i-text",
                "version": "5.3.0",
                "originX": "left",
                "originY": "top",
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(raw_width, 2),
                "height": round(raw_height, 2),
                "fill": "rgb(0,0,0)",
                "stroke": None,
                "strokeWidth": 1,
                "strokeDashArray": None,
                "strokeLineCap": "butt",
                "strokeDashOffset": 0,
                "strokeLineJoin": "miter",
                "strokeUniform": False,
                "strokeMiterLimit": 4,
                "scaleX": round(scale, 4),
                "scaleY": round(scale, 4),
                "angle": 0,
                "flipX": False,
                "flipY": False,
                "opacity": 1,
                "shadow": "",
                "visible": True,
                "backgroundColor": "",
                "fillRule": "nonzero",
                "paintFirst": "fill",
                "globalCompositeOperation": "source-over",
                "skewX": 0,
                "skewY": 0,
                "fontFamily": "arial",
                "fontWeight": "normal",
                "fontSize": str(FONT_SIZE),
                "text": text,
                "underline": False,
                "overline": False,
                "linethrough": False,
                "textAlign": "left",
                "fontStyle": "normal",
                "lineHeight": 1.16,
                "textBackgroundColor": "",
                "charSpacing": 0,
                "styles": [],
                "direction": "ltr",
                "path": None,
                "pathStartOffset": 0,
                "pathSide": "left",
                "pathAlign": "baseline",
                "id": f"short-sku-{int(time.time() * 1000)}",
            }
        ],
        "background": "#ffffff",
    }


def preview_to_dataframe_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "商品番号": row.get("order_id", ""),
            "贵社SKU": row.get("external_id", "") or "-",
            "SKU来源": row.get("external_id_source", "DB"),
            "当前config_id": row.get("config_id", "") or "-",
            "尺寸": f"{row.get('width') or '-'} x {row.get('height') or '-'}",
            "JSON": "有" if row.get("json_url") else "空",
            "当前状态": row.get("status_label", ""),
            "说明": row.get("reason", ""),
            "最新贴纸时间": row.get("pic_add_time", "") or "-",
        }
        for row in rows
    ]


def result_to_dataframe_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    status_map = {"success": "成功", "failed": "失败", "skipped": "跳过"}
    reason_map = {
        "saved": "已保存",
        "manual_json_url": "已有手动保存贴纸，未勾选覆盖，已跳过",
        "empty_external_id": "贵社SKU为空，无法保存",
        "invalid_external_id_encoding": "SKU含乱码，已阻断",
        "missing_item_id": "商品番号为空，已跳过",
    }
    return [
        {
            "商品番号": row.get("order_id", ""),
            "贵社SKU": row.get("external_id", "") or "-",
            "状态": status_map.get(row.get("status"), row.get("status", "")),
            "说明": reason_map.get(row.get("reason"), row.get("reason", "") or "-"),
        }
        for row in rows
    ]


def _classify_row(row: Dict[str, Any]) -> Dict[str, Any]:
    external_id = normalize_text(row.get("external_id"))
    has_json = bool(normalize_text(row.get("json_url")))
    has_invalid_text = has_invalid_sticker_text(external_id)
    if not external_id:
        status_label = "阻断"
        reason = "贵社SKU为空，无法生成短贴纸文本"
    elif has_invalid_text:
        status_label = "阻断"
        reason = "SKU含乱码，禁止保存；请用Excel中的正确SKU覆盖"
    elif has_json:
        status_label = "已手动保存"
        reason = "默认跳过，勾选覆盖后才会重新保存"
    else:
        status_label = "待处理"
        reason = "可按22号短贴纸重新保存"

    row["external_id"] = external_id
    row["external_id_source"] = row.get("external_id_source") or "DB"
    row["has_invalid_text"] = has_invalid_text
    row["is_manual_saved"] = has_json
    row["status_label"] = status_label
    row["reason"] = reason
    return row


def _result_row(
    row: Dict[str, Any],
    status: str,
    reason: str,
    *,
    response: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "order_id": normalize_text(row.get("order_id")),
        "external_id": normalize_text(row.get("external_id")),
        "pic_id": row.get("pic_id"),
        "config_id": row.get("config_id"),
        "status": status,
        "reason": reason,
        "response": response or {},
    }


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for font_path in font_paths:
        path = Path(font_path)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()
