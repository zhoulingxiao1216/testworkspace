"""8160 贴纸 SKU 修改工具。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

import pandas as pd
import streamlit as st

from modules.sakura_auth_ui import render_admin_session_manager
from modules.sakura_client import load_sku_config
from modules.sticker_sku_regen import (
    DEFAULT_MAIN_ORDER_ID,
    TARGET_USER_ID,
    StickerSkuToolError,
    execute_item_update,
    fetch_item_snapshot,
    fetch_manual_change_rows,
    trigger_sticker_regenerate,
    validate_main_order_id,
)


PAGE_STATE_KEY = "sticker_sku_regen_state"
SNAPSHOT_STATE_KEY = "sticker_sku_regen_snapshot"
TARGET_TOP_SKU_KEY = "sticker_target_top_sku"
TARGET_BARCODE_SKU_KEY = "sticker_target_barcode_sku"
DEFAULT_ITEM_ID = "1379534"


st.set_page_config(page_title="8160贴纸SKU修改工具", page_icon="🏷️", layout="wide")
st.title("🏷️ 8160贴纸SKU修改工具")
st.caption("按商品番号定向修改 8160 订单贴纸上方 SKU，并生成重置贴纸状态的 SQL。")


def status_label(status: str) -> str:
    return {
        "ready": "可更新",
        "blocked": "阻断",
        "already_target": "已是目标",
        "snapshot": "已读取",
    }.get(status, status or "")


def is_deleted_upload(row: Dict[str, Any]) -> bool:
    try:
        return int(row.get("pub_delete_time") or 0) > 0
    except (TypeError, ValueError):
        return False


def upload_record_label(row: Dict[str, Any]) -> str:
    if not row.get("pub_id"):
        return "未找到"
    return "已作废" if is_deleted_upload(row) else "有效"


def rows_to_dataframe(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "商品番号": row.get("order_id", ""),
                "当前上方SKU": row.get("current_top_sku", "") or "—",
                "目标上方SKU": row.get("new_top_sku", "") or "—",
                "当前贴纸条码": row.get("barcode_sku", "") or "—",
                "目标贴纸条码": row.get("new_barcode_sku", "") or "—",
                "上传批次": row.get("upload_type", "") or "—",
                "pub_id": row.get("pub_id", "") or "—",
                "上传记录": upload_record_label(row),
                "贴纸状态": row.get("stickers_status", "") if row.get("stickers_status") is not None else "—",
                "当前贴纸标题": row.get("pic_title", "") or "—",
                "最新贴纸时间": row.get("pic_add_time", "") or "—",
                "检查结果": status_label(row.get("status", "")),
                "说明": row.get("reason", "") or "—",
            }
            for row in rows
        ]
    )


def parse_form_inputs() -> tuple[str, str, str, str]:
    main_order_id = validate_main_order_id(main_order_input)
    return main_order_id, item_id_input, target_top_sku_input, target_barcode_sku_input


def load_current_snapshot() -> Dict[str, Any]:
    main_order_id = validate_main_order_id(main_order_input)
    row = fetch_item_snapshot(main_order_id, item_id_input)
    st.session_state[SNAPSHOT_STATE_KEY] = row
    st.session_state[TARGET_TOP_SKU_KEY] = row.get("current_top_sku", "") or ""
    st.session_state[TARGET_BARCODE_SKU_KEY] = row.get("barcode_sku", "") or ""
    st.session_state[PAGE_STATE_KEY] = {
        "main_order_id": main_order_id,
        "upload_type": str(row.get("upload_type", "") or ""),
        "item_ids": [str(row.get("order_id", item_id_input))],
        "rows": [row],
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return row


def run_precheck() -> Dict[str, Any]:
    main_order_id, item_id, new_top_sku, new_barcode_sku = parse_form_inputs()
    rows = fetch_manual_change_rows(
        main_order_id,
        item_id,
        new_top_sku,
        new_barcode_sku,
        allow_restore_deleted=allow_restore_deleted_input,
    )
    resolved_upload_type = ""
    for row in rows:
        if row.get("upload_type"):
            resolved_upload_type = str(row["upload_type"])
            break
    state = {
        "main_order_id": main_order_id,
        "upload_type": resolved_upload_type,
        "item_ids": [str(rows[0].get("order_id", item_id))] if rows else [item_id],
        "target_top_sku": new_top_sku,
        "target_barcode_sku": new_barcode_sku,
        "rows": rows,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    st.session_state[PAGE_STATE_KEY] = state
    return state


config = load_sku_config()

with st.sidebar:
    admin_sessid = render_admin_session_manager(config, title="⚙️ 连接配置")
    if not admin_sessid:
        st.stop()

    st.markdown("---")
    st.subheader("工具约束")
    st.info(f"固定用户：{TARGET_USER_ID}\n\n当前版本会直接执行受控更新，请先确认读取当前数据。")

st.info(
    "该工具支持修改贴纸上方显示的 SKU 和贴纸下方条码数字，并重置 "
    "`pub_api_order_new.stickers_status` 等待任务重新生成。"
)

left, right = st.columns([1, 1])

with left:
    main_order_input = st.text_input("主订单号", value=DEFAULT_MAIN_ORDER_ID)
    st.caption("上传批次 / type 将按商品番号优先识别最新有效贴纸上传记录。")
    item_col, confirm_col = st.columns([3, 1], vertical_alignment="bottom")
    item_id_input = item_col.text_input(
        "商品番号",
        value=DEFAULT_ITEM_ID,
        help="每次只允许填写一个商品番号。",
    )
    confirm_clicked = confirm_col.button("确认读取", use_container_width=True)
    allow_restore_deleted_input = st.checkbox(
        "允许恢复已作废上传记录",
        help="仅恢复当前商品对应的 pub_api_order_new 单条记录，并重置贴纸状态。",
    )

if confirm_clicked:
    try:
        with st.spinner("正在读取当前 SKU 和贴纸条码..."):
            load_current_snapshot()
        st.rerun()
    except StickerSkuToolError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"读取失败：{exc}")

with right:
    snapshot = st.session_state.get(SNAPSHOT_STATE_KEY, {})
    current_col1, current_col2 = st.columns(2)
    current_col1.text_input("当前 SKU", value=snapshot.get("current_top_sku", ""), disabled=True)
    current_col2.text_input("当前贴纸条码", value=snapshot.get("barcode_sku", ""), disabled=True)
    if snapshot and is_deleted_upload(snapshot):
        st.warning("当前读取到的是已作废上传记录；勾选允许恢复后，才可更新或重新生成。")

    target_col1, target_col2 = st.columns(2)
    target_top_sku_input = target_col1.text_input(
        "修改后 SKU",
        key=TARGET_TOP_SKU_KEY,
        placeholder="确认读取后自动带出，可修改",
    )
    target_barcode_sku_input = target_col2.text_input(
        "修改后贴纸条码",
        key=TARGET_BARCODE_SKU_KEY,
        placeholder="确认读取后自动带出，可修改",
    )

btn_update, btn_regenerate, _btn_spacer = st.columns([1, 1, 4])
update_clicked = btn_update.button("确认更新", type="primary", use_container_width=True)
regenerate_clicked = btn_regenerate.button("重新生成贴纸", use_container_width=True)

if update_clicked:
    try:
        with st.spinner("正在确认并更新当前商品..."):
            state = run_precheck()
            rows = state.get("rows", [])
            if not rows or rows[0].get("status") != "ready":
                reason = rows[0].get("reason", "当前输入未通过校验。") if rows else "当前输入未通过校验。"
                raise StickerSkuToolError(reason)
            result = execute_item_update(
                state["main_order_id"],
                state["item_ids"][0],
                state.get("target_top_sku", ""),
                state.get("target_barcode_sku", ""),
                allow_restore_deleted=allow_restore_deleted_input,
            )
            st.session_state[SNAPSHOT_STATE_KEY] = result["after"]
            st.session_state[PAGE_STATE_KEY] = {
                "main_order_id": state["main_order_id"],
                "upload_type": str(result["after"].get("upload_type", "") or ""),
                "item_ids": [str(result["after"].get("order_id", state["item_ids"][0]))],
                "rows": [result["after"]],
                "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_action_result": result,
            }
        st.success(f"更新完成，日志已保存：{result['log_path']}")
    except StickerSkuToolError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"更新失败：{exc}")

if regenerate_clicked:
    try:
        main_order_id = validate_main_order_id(main_order_input)
        with st.spinner("正在重置贴纸生成状态..."):
            result = trigger_sticker_regenerate(
                main_order_id,
                item_id_input,
                allow_restore_deleted=allow_restore_deleted_input,
            )
            st.session_state[SNAPSHOT_STATE_KEY] = result["after"]
            st.session_state[PAGE_STATE_KEY] = {
                "main_order_id": main_order_id,
                "upload_type": str(result["after"].get("upload_type", "") or ""),
                "item_ids": [str(result["after"].get("order_id", item_id_input))],
                "rows": [result["after"]],
                "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_action_result": result,
            }
        st.success(f"已重置贴纸生成状态，日志已保存：{result['log_path']}")
    except StickerSkuToolError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"重新生成贴纸失败：{exc}")

state = st.session_state.get(PAGE_STATE_KEY)
if not state:
    st.stop()

rows = state.get("rows", [])
ready_count = sum(1 for row in rows if row.get("status") == "ready")
blocked_count = sum(1 for row in rows if row.get("status") == "blocked")
already_count = sum(1 for row in rows if row.get("status") == "already_target")

st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
m1.metric("商品数", len(rows))
m2.metric("可更新", ready_count)
m3.metric("阻断", blocked_count)
m4.metric("已是目标", already_count)

if state.get("checked_at"):
    st.caption(f"最近预检查：{state['checked_at']}")

preview_df = rows_to_dataframe(rows)
st.dataframe(preview_df, use_container_width=True, hide_index=True)

if blocked_count:
    st.error("存在阻断项，请修正主订单号、商品番号、修改后 SKU 或修改后贴纸条码后重新预检查。")
elif ready_count:
    st.success("校验通过，可以点击确认更新。")
else:
    st.info("已读取当前数据，修改右侧目标值后可确认更新。")

last_action_result = state.get("last_action_result")
if last_action_result:
    st.markdown("### 最近操作")
    st.json(
        {
            "affected": last_action_result.get("affected"),
            "log_path": last_action_result.get("log_path"),
        }
    )
