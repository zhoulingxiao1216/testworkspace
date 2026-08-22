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
from modules.sticker_8253_adjust import (
    TARGET_UID as STICKER_8253_UID,
    Sticker8253AdjustError,
    apply_external_id_overrides,
    adjust_8253_short_stickers,
    fetch_8253_short_sticker_rows,
    preview_to_dataframe_rows,
    result_to_dataframe_rows,
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


def resolve_sticker_order_id_from_upload() -> str:
    if uploaded is None:
        return ""
    try:
        rows, _ = parse_bulk_template(uploaded.getvalue())
    except Exception:
        return ""
    for row in rows:
        main_order_id = str(row.get("main_order_id", "")).strip()
        if main_order_id:
            return main_order_id
    return ""


def normalize_key_part(value) -> str:
    text = "" if value is None else str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


col_preview, col_run, col_sticker, _ = st.columns([3, 3, 3, 1])
preview_btn = col_preview.button("🔍 解析并预览", type="secondary", use_container_width=True)
run_btn = col_run.button("🚀 确认同步到后台", type="primary", use_container_width=True, disabled=uploaded is None)
sticker_order_id = optional_order_id.strip() or resolve_sticker_order_id_from_upload()
sticker_disabled = str(uid) != STICKER_8253_UID or not sticker_order_id
sticker_btn = col_sticker.button(
    "加载8253贴纸列表",
    type="secondary",
    use_container_width=True,
    disabled=sticker_disabled,
)
overwrite_manual_sticker = st.checkbox(
    "覆盖已手动使用过的8253贴纸",
    value=False,
    disabled=str(uid) != STICKER_8253_UID,
    help="默认跳过已有 json_url 的贴纸，避免覆盖业务人员已手动调整过的内容。",
)

if str(uid) == STICKER_8253_UID:
    if sticker_order_id:
        st.caption(f"8253贴纸主订单号：{sticker_order_id}")
    else:
        st.caption("填写主订单号，或上传含「注文番号」列的Excel后，可加载8253贴纸列表并勾选保存。")

if sticker_btn:
    try:
        with st.spinner("正在读取8253当前贴纸数据..."):
            sticker_rows = fetch_8253_short_sticker_rows(sticker_order_id)

        if not sticker_rows:
            st.warning("未找到该主订单号下 UID=8253 的商品。")
            st.stop()

        excel_sku_by_order_id = {}
        if uploaded is not None:
            try:
                excel_rows, _ = parse_bulk_template(uploaded.getvalue())
                excel_sku_by_order_id = {
                    str(row.get("order_id", "")).strip(): str(row.get("external_id", "")).strip()
                    for row in excel_rows
                    if str(row.get("order_id", "")).strip() and str(row.get("external_id", "")).strip()
                }
            except Exception as exc:
                st.warning(f"Excel SKU 读取失败，本次仅展示数据库SKU：{exc}")

        if excel_sku_by_order_id:
            sticker_rows = apply_external_id_overrides(
                sticker_rows,
                excel_sku_by_order_id,
                source="Excel",
            )

        st.session_state["sticker_8253_rows"] = sticker_rows
        st.session_state["sticker_8253_order_id"] = sticker_order_id
        st.session_state["sticker_8253_selected_keys"] = []
        st.session_state["sticker_8253_selection_revision"] = (
            st.session_state.get("sticker_8253_selection_revision", 0) + 1
        )
        st.rerun()
    except Sticker8253AdjustError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"8253贴纸列表读取失败：{exc}")

sticker_rows_state = []
if (
    str(uid) == STICKER_8253_UID
    and sticker_order_id
    and st.session_state.get("sticker_8253_order_id") == sticker_order_id
):
    sticker_rows_state = st.session_state.get("sticker_8253_rows", [])

if sticker_rows_state:
    st.markdown("---")
    st.subheader("8253贴纸22号保存")
    st.warning("先勾选要保存的商品，再点击保存勾选贴纸。检测到乱码SKU会阻断保存。")

    def sticker_row_key(row: dict) -> str:
        return str(row.get("order_id", "")).strip()

    sticker_saveable_keys = {
        sticker_row_key(row)
        for row in sticker_rows_state
        if row.get("status_label") != "阻断"
        and (overwrite_manual_sticker or not row.get("is_manual_saved"))
    }
    sticker_selected_keys = set(st.session_state.get("sticker_8253_selected_keys", [])) & sticker_saveable_keys

    sticker_select_col, sticker_clear_col, _ = st.columns([1, 1, 6])
    if sticker_select_col.button("全选可保存贴纸", use_container_width=True, disabled=not sticker_saveable_keys):
        st.session_state["sticker_8253_selected_keys"] = sorted(sticker_saveable_keys)
        st.session_state["sticker_8253_selection_revision"] = (
            st.session_state.get("sticker_8253_selection_revision", 0) + 1
        )
        st.rerun()
    if sticker_clear_col.button("取消贴纸全选", use_container_width=True, disabled=not sticker_rows_state):
        st.session_state["sticker_8253_selected_keys"] = []
        st.session_state["sticker_8253_selection_revision"] = (
            st.session_state.get("sticker_8253_selection_revision", 0) + 1
        )
        st.rerun()

    sticker_preview_df = pd.DataFrame(
        [
            {
                "选择": sticker_row_key(row) in sticker_selected_keys,
                **preview_row,
            }
            for row, preview_row in zip(
                sticker_rows_state,
                preview_to_dataframe_rows(sticker_rows_state),
            )
        ]
    )

    edited_sticker_df = st.data_editor(
        sticker_preview_df,
        use_container_width=True,
        hide_index=True,
        key=f"sticker_8253_preview_selection_{st.session_state.get('sticker_8253_selection_revision', 0)}",
        disabled=[
            "商品番号",
            "贵社SKU",
            "SKU来源",
            "当前config_id",
            "尺寸",
            "JSON",
            "当前状态",
            "说明",
            "最新贴纸时间",
        ],
        column_config={
            "选择": st.column_config.CheckboxColumn(
                "选择",
                help="只保存已勾选且状态允许保存的贴纸。",
            )
        },
    )

    selected_sticker_rows = []
    sticker_rows_by_order_id = {
        sticker_row_key(row): row
        for row in sticker_rows_state
    }
    if "选择" in edited_sticker_df:
        for _, edited_row in edited_sticker_df.iterrows():
            if not bool(edited_row.get("选择")):
                continue
            order_id = normalize_key_part(edited_row.get("商品番号", ""))
            row = sticker_rows_by_order_id.get(order_id)
            if row and order_id in sticker_saveable_keys:
                selected_sticker_rows.append(row)
    st.session_state["sticker_8253_selected_keys"] = sorted(
        sticker_row_key(row) for row in selected_sticker_rows
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("贴纸总数", len(sticker_rows_state))
    c2.metric("可保存", len(sticker_saveable_keys))
    c3.metric("已勾选", len(selected_sticker_rows))
    c4.metric("阻断/跳过", len(sticker_rows_state) - len(sticker_saveable_keys))

    save_selected_sticker_btn = st.button(
        "保存勾选贴纸为22号",
        type="primary",
        disabled=not selected_sticker_rows,
    )
    if save_selected_sticker_btn:
        try:
            with st.spinner("正在保存勾选的8253短贴纸..."):
                manual_selected_rows = [
                    row
                    for row in selected_sticker_rows
                    if row.get("is_manual_saved")
                ]
                if manual_selected_rows and not overwrite_manual_sticker:
                    st.warning("勾选的贴纸已有手动保存记录。请先勾选「覆盖已手动使用过的8253贴纸」后再保存。")
                    st.stop()
                sticker_result = adjust_8253_short_stickers(
                    sticker_order_id,
                    admin_sessid,
                    selected_sticker_rows,
                    overwrite_manual=overwrite_manual_sticker,
                )

            st.dataframe(
                pd.DataFrame(result_to_dataframe_rows(sticker_result["results"])),
                use_container_width=True,
                hide_index=True,
            )

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("本次勾选", sticker_result["total"])
            r2.metric("成功", sticker_result["success"])
            r3.metric("失败", sticker_result["failed"])
            r4.metric("跳过", sticker_result["skipped"])

            if sticker_result["failed"]:
                st.error(f"部分贴纸保存失败，日志：{sticker_result['log_path']}")
            elif sticker_result["success"] == 0:
                st.warning(
                    "本次没有保存任何贴纸。若要修复已有手动贴纸或乱码贴纸，"
                    "请勾选「覆盖已手动使用过的8253贴纸」后重试。"
                )
            else:
                st.success(f"勾选贴纸已处理完成，日志：{sticker_result['log_path']}")
        except Sticker8253AdjustError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"8253贴纸处理失败：{exc}")
        st.stop()

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
        meta["backend_sku_preview_status"] = "missing_order_id"
        return mark_backend_sku_unavailable(plan, "未填写主订单号，无法预览后台SKU"), meta

    token_info = ensure_token()
    if not token_info:
        meta["backend_sku_preview_status"] = "token_failed"
        return mark_backend_sku_unavailable(
            plan,
            "管理员Session过期或客户Token获取失败，无法预览后台SKU",
        ), meta

    from modules.sakura_client import fetch_order_items

    mapping, errors = fetch_preview_mapping(preview_order_ids, token_info, fetch_order_items)
    if errors:
        st.warning("拉取订单详情失败，无法预览部分后台 SKU：" + "；".join(errors))
        meta["backend_sku_preview_status"] = "partial_error"
        meta["backend_sku_preview_errors"] = errors
    else:
        meta["backend_sku_preview_status"] = "ok"
    meta["backend_sku_mapping_count"] = len(mapping)
    plan = attach_current_sku(plan, mapping, preview_attempted=True)
    return plan, meta


def mark_backend_sku_unavailable(plan_rows: List[dict], reason: str) -> List[dict]:
    marked_rows = []
    for row in plan_rows:
        item = dict(row)
        if item.get("action") == "update":
            item["current_sku"] = ""
            item["current_sku_status"] = "unavailable"
            item["reason"] = reason
        marked_rows.append(item)
    return marked_rows


def format_backend_sku(row: dict) -> str:
    current_sku = row.get("current_sku")
    if current_sku:
        return current_sku
    if row.get("current_sku_status") == "unavailable":
        return "未获取"
    return "—"


def plan_row_key(row: dict) -> str:
    return plan_row_key_from_values(row.get("row_no", ""), row.get("order_id", ""))


def plan_row_key_from_values(row_no, order_id) -> str:
    return f"{normalize_key_part(row_no)}|{normalize_key_part(order_id)}"


def reset_selected_update_rows(plan_rows: List[dict]) -> None:
    st.session_state["sku_sync_selected_keys"] = [
        plan_row_key(row)
        for row in plan_rows
        if row.get("action") == "update"
    ]
    st.session_state["sku_sync_selection_revision"] = (
        st.session_state.get("sku_sync_selection_revision", 0) + 1
    )


if preview_btn or run_btn:
    file_bytes = uploaded.getvalue()
    file_sig = (uploaded.name, len(file_bytes), str(uid), optional_order_id.strip())
    plan_stale = st.session_state.get("sku_sync_file_sig") != file_sig
    try:
        if preview_btn or plan_stale or not st.session_state.get("sku_sync_plan"):
            plan, meta = load_plan(file_bytes)
            st.session_state["sku_sync_plan"] = plan
            st.session_state["sku_sync_meta"] = meta
            st.session_state["sku_sync_filename"] = uploaded.name
            st.session_state["sku_sync_file_sig"] = file_sig
            reset_selected_update_rows(plan)
    except Exception as exc:
        st.error(f"Excel 解析失败：{exc}")
        st.stop()

plan = st.session_state.get("sku_sync_plan")
meta = st.session_state.get("sku_sync_meta")

if not plan:
    st.stop()

update_rows = [r for r in plan if r["action"] == "update"]
skip_rows = [r for r in plan if r["action"] == "skip"]
update_row_keys = {plan_row_key(row) for row in update_rows}
plan_by_key = {plan_row_key(row): row for row in plan}
all_plan_keys = set(plan_by_key)
sticker_preview_enabled = str(uid) == STICKER_8253_UID
sticker_preview_keys = {
    plan_row_key(row)
    for row in plan
    if str(row.get("external_id", "")).strip()
}
selection_scope_keys = sticker_preview_keys if sticker_preview_enabled else update_row_keys
selected_keys = set(st.session_state.get("sku_sync_selected_keys", [])) & selection_scope_keys
if "sku_sync_selected_keys" not in st.session_state:
    selected_keys = set(update_row_keys)
    st.session_state["sku_sync_selected_keys"] = sorted(selected_keys)

metrics_placeholder = st.empty()
backend_sku_preview_status = meta.get("backend_sku_preview_status")

if backend_sku_preview_status == "token_failed":
    st.error("后台当前SKU未获取：管理员 Session 过期或客户 Token 获取失败，请更新 PHPSESSID 后重新解析预览。")
elif backend_sku_preview_status == "missing_order_id":
    st.warning("后台当前SKU未获取：未填写主订单号，只能展示 Excel 中的目标 SKU。")
elif backend_sku_preview_status == "partial_error":
    st.warning("后台当前SKU部分获取失败，请优先核对失败订单后再同步。")

if sticker_preview_enabled:
    st.caption(
        "说明：**Excel贵社SKU** = 从上传文件读取的目标值；"
        "**后台当前SKU** = 从系统拉取的现有值（用于对比）。"
        "8253模式下，勾选行可用于保存贴纸字号；SKU同步仍只处理「动作=update」的行。"
    )
else:
    st.caption(
        "说明：**Excel贵社SKU** = 从上传文件读取的目标值；"
        "**后台当前SKU** = 填写主订单号后从系统拉取的现有值（用于对比）。"
        "勾选后只会同步「动作=update」的行。"
    )

preview_rows = [
    {
        "Excel行号": r.get("row_no"),
        "商品番号": r.get("order_id"),
        "Excel贵社SKU": r.get("external_id") or "—",
        "后台当前SKU": format_backend_sku(r),
        "动作": r.get("action"),
        "说明": r.get("reason"),
    }
    for r in plan
]

selected_update_rows = []
selected_preview_rows = []

if update_rows or sticker_preview_enabled:
    select_col, clear_col, _ = st.columns([1, 1, 6])
    select_label = "全选贴纸" if sticker_preview_enabled else "全选待更新"
    select_target_keys = sticker_preview_keys if sticker_preview_enabled else update_row_keys
    if select_col.button(select_label, use_container_width=True, disabled=not select_target_keys):
        st.session_state["sku_sync_selected_keys"] = sorted(select_target_keys)
        st.session_state["sku_sync_selection_revision"] = (
            st.session_state.get("sku_sync_selection_revision", 0) + 1
        )
        st.rerun()

    if clear_col.button("取消全选", use_container_width=True):
        st.session_state["sku_sync_selected_keys"] = []
        st.session_state["sku_sync_selection_revision"] = (
            st.session_state.get("sku_sync_selection_revision", 0) + 1
        )
        st.rerun()

    selection_col_name = "选择贴纸" if sticker_preview_enabled else "选择"
    preview_df = pd.DataFrame(
        [
            {
                selection_col_name: plan_row_key(r) in selected_keys,
                **preview_row,
            }
            for r, preview_row in zip(plan, preview_rows)
        ]
    )

    edited_preview_df = st.data_editor(
        preview_df,
        use_container_width=True,
        hide_index=True,
        key=f"sku_sync_preview_selection_{st.session_state.get('sku_sync_selection_revision', 0)}",
        disabled=["Excel行号", "商品番号", "Excel贵社SKU", "后台当前SKU", "动作", "说明"],
        column_config={
            selection_col_name: st.column_config.CheckboxColumn(
                selection_col_name,
                help="8253时用于选择要重新保存字号的贴纸；SKU同步仍只处理动作为update的行。"
                if sticker_preview_enabled
                else "只同步已勾选且动作为 update 的行。",
            )
        },
    )

    if selection_col_name in edited_preview_df:
        for _, edited_row in edited_preview_df.iterrows():
            if not bool(edited_row.get(selection_col_name)):
                continue
            row_key = plan_row_key_from_values(
                edited_row.get("Excel行号", ""),
                edited_row.get("商品番号", ""),
            )
            row = plan_by_key.get(row_key)
            if row:
                selected_preview_rows.append(row)
                if row.get("action") == "update":
                    selected_update_rows.append(row)
    selected_keys_to_store = [
        plan_row_key(row)
        for row in selected_preview_rows
        if plan_row_key(row) in all_plan_keys
    ]
    st.session_state["sku_sync_selected_keys"] = sorted(selected_keys_to_store)
else:
    st.info("当前所有行都是 skip / SKU已一致，没有可同步的待更新行。")
    st.session_state["sku_sync_selected_keys"] = []
    st.dataframe(
        pd.DataFrame(preview_rows),
        use_container_width=True,
        hide_index=True,
    )

unselected_update_count = len(update_rows) - len(selected_update_rows)

with metrics_placeholder.container():
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("解析行数", len(plan))
    m2.metric("待更新", len(update_rows))
    selected_metric_label = "已选贴纸" if sticker_preview_enabled else "已勾选"
    selected_metric_value = len(selected_preview_rows) if sticker_preview_enabled else len(selected_update_rows)
    m3.metric(selected_metric_label, selected_metric_value)
    m4.metric("跳过", len(skip_rows) + unselected_update_count)

if sticker_preview_enabled:
    save_preview_sticker_btn = st.button(
        "保存勾选贴纸为22号",
        type="secondary",
        disabled=not selected_preview_rows or not sticker_order_id,
        help="按当前表格勾选行重新保存8253短贴纸字号；不受SKU是否需要同步影响。",
    )
    if save_preview_sticker_btn:
        try:
            selected_sku_by_order_id = {
                str(row.get("order_id", "")).strip(): str(row.get("external_id", "")).strip()
                for row in selected_preview_rows
                if str(row.get("order_id", "")).strip() and str(row.get("external_id", "")).strip()
            }
            if not selected_sku_by_order_id:
                st.warning("没有可用于保存贴纸的已勾选SKU。")
                st.stop()

            with st.spinner("正在按勾选行读取8253贴纸并保存22号字号..."):
                sticker_rows = fetch_8253_short_sticker_rows(sticker_order_id)
                sticker_rows = apply_external_id_overrides(
                    sticker_rows,
                    selected_sku_by_order_id,
                    source="Excel预览",
                )
                selected_sticker_rows = [
                    row
                    for row in sticker_rows
                    if str(row.get("order_id", "")).strip() in selected_sku_by_order_id
                ]
                manual_selected_rows = [
                    row
                    for row in selected_sticker_rows
                    if row.get("is_manual_saved")
                ]
                if manual_selected_rows and not overwrite_manual_sticker:
                    st.warning("勾选的贴纸已有手动保存记录。请先勾选「覆盖已手动使用过的8253贴纸」后再保存。")
                    st.stop()
                sticker_result = adjust_8253_short_stickers(
                    sticker_order_id,
                    admin_sessid,
                    selected_sticker_rows,
                    overwrite_manual=overwrite_manual_sticker,
                )

            st.dataframe(
                pd.DataFrame(result_to_dataframe_rows(sticker_result["results"])),
                use_container_width=True,
                hide_index=True,
            )
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("本次勾选", sticker_result["total"])
            r2.metric("成功", sticker_result["success"])
            r3.metric("失败", sticker_result["failed"])
            r4.metric("跳过", sticker_result["skipped"])
            if sticker_result["failed"]:
                st.error(f"部分贴纸保存失败，日志：{sticker_result['log_path']}")
            elif sticker_result["success"] == 0:
                st.warning(
                    "本次没有保存任何贴纸。若要修复已有手动贴纸或乱码贴纸，"
                    "请勾选「覆盖已手动使用过的8253贴纸」后重试。"
                )
            else:
                st.success(f"勾选贴纸已处理完成，日志：{sticker_result['log_path']}")
        except Sticker8253AdjustError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"8253贴纸处理失败：{exc}")
        st.stop()

if preview_btn and not run_btn:
    if sticker_preview_enabled:
        st.info("预览完成。SKU已一致的行也可以勾选后点击「保存勾选贴纸为22号」。")
    else:
        st.info("预览完成。勾选要同步的行后点击「确认同步到后台」。")
    st.stop()

if not run_btn:
    st.stop()

if not update_rows:
    st.warning("没有需要更新的行。")
    st.stop()

if backend_sku_preview_status == "token_failed":
    st.error("后台当前SKU未获取成功，请先更新 PHPSESSID 并重新解析预览。")
    st.stop()

if not selected_update_rows:
    st.warning("没有勾选需要同步的 update 行。")
    st.stop()

token_info = ensure_token()
if not token_info:
    st.stop()

st.markdown("---")
st.subheader("执行结果")

progress = st.progress(0.0, text="准备同步…")
results = []
success_count = fail_count = 0

for idx, row in enumerate(selected_update_rows, start=1):
    progress.progress(idx / len(selected_update_rows), text=f"同步中 {idx}/{len(selected_update_rows)}…")
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
c3.metric("跳过", len(skip_rows) + unselected_update_count)

log_path = write_sync_log(
    {
        "filename": st.session_state.get("sku_sync_filename"),
        "uid": uid,
        "optional_order_id": optional_order_id.strip(),
        "meta": meta,
        "plan": plan,
        "selected_update_rows": [
            {"row_no": r.get("row_no"), "order_id": r.get("order_id")}
            for r in selected_update_rows
        ],
        "skipped_by_unselected": unselected_update_count,
        "results": results,
    }
)
st.success(f"同步完成。日志已保存：{log_path}")

if fail_count:
    st.error("部分行同步失败，请检查商品番号是否属于所选 UID，或 Token 是否有效。")
else:
    st.success("全部待更新行已成功同步，请到后台订单列表核对 SKU。")
