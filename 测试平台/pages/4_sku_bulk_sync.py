"""批量上传模板 → 后台 SKU 同步工具。"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

import pandas as pd
import streamlit as st

from modules.sakura_auth_ui import render_admin_session_manager
from modules.sakura_client import (
    get_user_token,
    load_sku_config,
    save_external_id,
)
from modules.sku_sync import (
    attach_current_sku,
    build_sync_plan,
    fetch_preview_mapping,
    parse_bulk_template,
    resolve_preview_order_ids,
    write_sync_log,
)

st.set_page_config(page_title="SKU 批量同步工具", page_icon="📦", layout="wide")
st.title("📦 SKU 批量同步工具")
st.caption("读取贴纸/吊牌批量上传 Excel 中的「贵社SKU」，按「商品番号」更新后台 order_ExternalID。")

config = load_sku_config()
admin_sessid = config.get("admin_session", {}).get("PHPSESSID", "")
accounts = config.get("accounts", [])
MANUAL_UID_LABEL = "手动填写客户 UID"

with st.sidebar:
    admin_sessid = render_admin_session_manager(config, title="⚙️ 连接配置")
    if not admin_sessid:
        st.stop()

    st.markdown("---")
    st.subheader("👤 客户账号")
    labels = [MANUAL_UID_LABEL] + [a["label"] for a in accounts]
    selected_label = st.selectbox("订单所属客户", labels)

    if selected_label == MANUAL_UID_LABEL:
        manual_input = st.text_input(
            "客户 UID",
            placeholder="例如 8113",
            help="填写后点击「确认」才会生效，避免误填 UID 直接同步",
            key="sku_sync_manual_uid_input",
        ).strip()
        _, confirm_col = st.columns([3, 1])
        with confirm_col:
            confirm_uid_btn = st.button("确认", use_container_width=True, key="sku_sync_confirm_uid")

        if confirm_uid_btn:
            if not manual_input:
                st.error("请先填写客户 UID。")
            elif not manual_input.isdigit():
                st.error("UID 应为纯数字。")
            else:
                prev_uid = st.session_state.get("sku_sync_confirmed_uid", "")
                if prev_uid != manual_input:
                    for key in list(st.session_state.keys()):
                        if key.startswith("user_token_"):
                            del st.session_state[key]
                    for key in ("sku_sync_plan", "sku_sync_meta", "sku_sync_filename"):
                        st.session_state.pop(key, None)
                st.session_state["sku_sync_confirmed_uid"] = manual_input
                st.rerun()

        uid = st.session_state.get("sku_sync_confirmed_uid", "")
        if not uid:
            st.warning("请填写客户 UID 并点击「确认」。")
        elif manual_input and manual_input != uid:
            st.info(f"当前生效 UID: **{uid}**")
            st.caption(f"输入框为 **{manual_input}**，与当前生效 UID 不一致，修改后请再次点击「确认」。")
        else:
            st.success(f"已确认 UID: **{uid}**")
    else:
        selected_account = next(a for a in accounts if a["label"] == selected_label)
        uid = selected_account["uid"]
        st.session_state.pop("sku_sync_confirmed_uid", None)
        st.info(f"UID: **{uid}**")

    if accounts:
        st.caption("常用客户可在 sku_accounts.json 中预设；临时客户请选「手动填写客户 UID」。")

    st.warning(
        "同步只会更新**该 UID 名下**的商品番号。"
        "Excel 里每一行都会用这个客户的身份调用 API，"
        "选错客户会导致「产品不存在」或改错账号的数据。"
    )

if not uid or not str(uid).strip().isdigit():
    st.warning("请先在侧边栏选择或填写有效的客户 UID。")
    st.stop()

uploaded = st.file_uploader(
    "上传贴纸/吊牌批量 Excel（.xlsx）",
    type=["xlsx"],
    help="表头需含「商品番号」「贵社SKU」；支持备注行 + 表头 + 数据（3 行起即可）。",
)

optional_order_id = st.text_input(
    "可选：主订单号（用于预览当前 SKU）",
    placeholder="留空则自动读取 Excel「注文番号」列",
    help="填写后可覆盖 Excel 中的注文番号；预览需与侧边栏 UID 一致。",
)

col_preview, col_run, _ = st.columns([3, 3, 4])
preview_btn = col_preview.button("🔍 解析并预览", type="secondary", use_container_width=True)
run_btn = col_run.button("🚀 确认同步到后台", type="primary", use_container_width=True, disabled=uploaded is None)

if uploaded is None:
    st.info("请先上传 Excel 文件。")
    st.stop()


def ensure_token() -> Optional[dict]:
    cache_key = f"user_token_{uid}"
    token_info = st.session_state.get(cache_key)
    if token_info:
        return token_info

    result = get_user_token(admin_sessid, uid)
    if not result.get("success"):
        if result.get("error") == "ADMIN_SESSION_EXPIRED":
            st.error("管理员 Session 已过期，请在侧边栏更新 PHPSESSID。")
        else:
            st.error(f"获取客户 Token 失败：{result.get('error')} {result.get('detail', '')}")
        return None

    st.session_state[cache_key] = result
    return result


def load_plan(file_bytes: bytes) -> Tuple[List[dict], dict]:
    rows, meta = parse_bulk_template(file_bytes)
    plan = build_sync_plan(rows)

    preview_order_ids = resolve_preview_order_ids(optional_order_id, rows)
    if not preview_order_ids:
        return attach_current_sku(plan, {}, preview_attempted=False), meta

    token_info = ensure_token()
    if not token_info:
        return plan, meta

    from modules.sakura_client import fetch_order_items

    mapping, errors = fetch_preview_mapping(preview_order_ids, token_info, fetch_order_items)
    if errors:
        st.warning("拉取订单详情失败，无法预览部分后台 SKU：" + "；".join(errors))
    plan = attach_current_sku(plan, mapping, preview_attempted=True)
    return plan, meta


if preview_btn or run_btn:
    file_bytes = uploaded.getvalue()
    try:
        plan, meta = load_plan(file_bytes)
    except Exception as exc:
        st.error(f"Excel 解析失败：{exc}")
        st.stop()

    st.session_state["sku_sync_plan"] = plan
    st.session_state["sku_sync_meta"] = meta
    st.session_state["sku_sync_filename"] = uploaded.name

plan = st.session_state.get("sku_sync_plan")
meta = st.session_state.get("sku_sync_meta")

if not plan:
    st.stop()

update_rows = [r for r in plan if r["action"] == "update"]
skip_rows = [r for r in plan if r["action"] == "skip"]

m1, m2, m3 = st.columns(3)
m1.metric("解析行数", len(plan))
m2.metric("待更新", len(update_rows))
m3.metric("跳过", len(skip_rows))

st.caption(
    "说明：**Excel贵社SKU** = 从上传文件读取的目标值；"
    "**后台当前SKU** = 填写主订单号后从系统拉取的现有值（用于对比）。"
)

preview_df = pd.DataFrame(
    [
        {
            "Excel行号": r.get("row_no"),
            "商品番号": r.get("order_id"),
            "Excel贵社SKU": r.get("external_id") or "—",
            "后台当前SKU": r.get("current_sku") or "—",
            "动作": r.get("action"),
            "说明": r.get("reason"),
        }
        for r in plan
    ]
)
st.dataframe(preview_df, use_container_width=True, hide_index=True)

if preview_btn and not run_btn:
    st.info("预览完成。确认无误后点击「确认同步到后台」。")
    st.stop()

if not run_btn:
    st.stop()

if not update_rows:
    st.warning("没有需要更新的行。")
    st.stop()

token_info = ensure_token()
if not token_info:
    st.stop()

st.markdown("---")
st.subheader("执行结果")

progress = st.progress(0.0, text="准备同步…")
results = []
success_count = fail_count = 0

for idx, row in enumerate(update_rows, start=1):
    progress.progress(idx / len(update_rows), text=f"同步中 {idx}/{len(update_rows)}…")
    resp = save_external_id(row["order_id"], row["external_id"], token_info, item_type=1)
    if resp.get("success"):
        success_count += 1
        status = "success"
        detail = "已更新"
    else:
        fail_count += 1
        status = "failed"
        detail = resp.get("detail") or resp.get("error") or "未知错误"

    results.append(
        {
            "row_no": row.get("row_no"),
            "order_id": row["order_id"],
            "external_id": row["external_id"],
            "previous_sku": row.get("current_sku", ""),
            "status": status,
            "detail": detail,
        }
    )
    time.sleep(0.05)

progress.progress(1.0, text="同步完成")

result_df = pd.DataFrame(
    [
        {
            "Excel行号": r.get("row_no"),
            "商品番号": r.get("order_id"),
            "Excel贵社SKU": r.get("external_id") or "—",
            "后台当前SKU": r.get("previous_sku") or "—",
            "状态": "成功" if r.get("status") == "success" else "失败",
            "说明": r.get("detail") or "—",
        }
        for r in results
    ]
)
st.dataframe(result_df, use_container_width=True, hide_index=True)

c1, c2, c3 = st.columns(3)
c1.metric("成功", success_count)
c2.metric("失败", fail_count)
c3.metric("跳过", len(skip_rows))

log_path = write_sync_log(
    {
        "filename": st.session_state.get("sku_sync_filename"),
        "uid": uid,
        "optional_order_id": optional_order_id.strip(),
        "meta": meta,
        "plan": plan,
        "results": results,
    }
)
st.success(f"同步完成。日志已保存：{log_path}")

if fail_count:
    st.error("部分行同步失败，请检查商品番号是否属于所选 UID，或 Token 是否有效。")
else:
    st.success("全部待更新行已成功同步，请到后台订单列表核对 SKU。")
