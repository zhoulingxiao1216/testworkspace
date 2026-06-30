"""
app.py
项目首页大屏，提供汇总报表、文件批量导入与进度视图。
"""
from __future__ import annotations

import streamlit as st
from datetime import datetime
from pathlib import Path
import pandas as pd

from db_manager import (
    init_db, upsert_case, get_tc_ids_by_source, 
    delete_cases_by_tc_ids, get_cases_by_source, delete_cases_by_source,
    reset_all_status
)
from md_parser import parse_md_text
from modules.frontend_dashboard import st_dashboard_grid
from utils import load_data, local_css, _build_excel_bytes, render_sidebar

st.set_page_config(page_title="HyperMember-TestConsole", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")
init_db()
local_css()

# Session State Keys
for key in ["active_file_filter", "confirm_delete_file", "orphan_tc_ids", "orphan_source", 
            "confirm_reset", "import_result", "last_upload_key", "current_upload_key", 
            "upload_records", "upload_filename"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "key" in key or "result" in key or "source" in key else (None if "records" in key or "delete" in key else ([] if "orphan" in key else False))

if "active_file_filter" not in st.session_state or not st.session_state.active_file_filter:
    st.session_state.active_file_filter = "__GLOBAL__"
if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

global_df = load_data()

# ── 全局共同侧边栏 ──────────────────────────────────────────
render_sidebar(global_df)

# ── 主页面：导入与历史看板 ──────────────────────────────────────────
if st.session_state.import_result:
    st.success(st.session_state.import_result)
    if st.button("前往 🧪 测试执行 →", type="primary"):
        st.session_state.import_result = ""
        st.session_state.active_file_filter = "__GLOBAL__"
        st.session_state.execution_status_filter = None
        st.switch_page("pages/1_🧪_测试执行.py")

col_upload, col_batch_mgmt = st.columns([1, 1])

with col_upload:
    uploaded = st.file_uploader(
        "选择 .md 文件",
        type=["md"],
        help="支持 #### TC-XXX 格式的 Markdown 文件，重复 TC 编号将更新已有记录",
    )

    if uploaded is not None:
        file_key = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.current_upload_key != file_key:
            st.session_state.import_result = ""
            with st.spinner(f"正在解析 {uploaded.name}…"):
                try:
                    text = uploaded.getvalue().decode("utf-8-sig")
                    records = parse_md_text(text)
                except Exception as exc:
                    st.error(f"文件读取失败：{exc}")
                    records = []
            st.session_state.upload_records = records
            st.session_state.upload_filename = uploaded.name
            st.session_state.current_upload_key = file_key

        records = st.session_state.upload_records
        filename = st.session_state.upload_filename

        if st.session_state.last_upload_key == file_key and records is None:
            st.info(f"`{filename}` 已成功导入。如需重导请改变文件。")
        elif records is not None:
            if not records:
                st.warning("未检测到符合格式的本用例，请核对文件格式。")
            else:
                st.info(f"解析到 **{len(records)}** 条用例，点击执行入库。")
                if st.button("🚀 开始解析并入库", type="primary", use_container_width=True):
                    n_ins = n_upd = n_fail = 0
                    prog = st.progress(0, text="写入中…")
                    for i, r in enumerate(records):
                        tc_id, r_copy = r.get("tc_id"), {k: v for k, v in r.items() if k != "tc_id"}
                        r_copy["sort_order"] = i
                        try:
                            _, action = upsert_case(tc_id=tc_id, source_file=filename, **r_copy)
                            if action == "inserted": n_ins += 1
                            else: n_upd += 1
                        except Exception as exc:
                            n_fail += 1
                            st.error(f"{tc_id} 写入失败：{exc}")
                        prog.progress((i + 1) / len(records), text=f"写入中… {i + 1}/{len(records)}")

                    st.session_state.import_result = f"成功导入 {n_ins + n_upd} 条用例 (新增 {n_ins}, 更新 {n_upd}, 失败 {n_fail})"

                    archive_dir = Path(__file__).parent / "测试用例导入记录"
                    archive_dir.mkdir(exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    (archive_dir / f"{Path(filename).stem}_{ts}{Path(filename).suffix}").write_bytes(uploaded.getvalue())

                    st.session_state.last_upload_key = file_key
                    st.session_state.upload_records = None

                    existing_tc_ids = get_tc_ids_by_source(filename)
                    new_tc_ids = {r.get("tc_id") for r in records if r.get("tc_id")}
                    orphans = existing_tc_ids - new_tc_ids
                    if orphans:
                        st.session_state.orphan_tc_ids, st.session_state.orphan_source = sorted(orphans), filename
                    else:
                        st.session_state.orphan_tc_ids, st.session_state.orphan_source = [], ""
                    
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")
    st.markdown("**🏷️ 其它辅助工具**")
    st.page_link("pages/2_sku_verify.py", label="🏷️ 进入 SKU 智能比对", use_container_width=True)
    if st.button("📦 进入 SKU 批量同步", use_container_width=True, key="goto_sku_bulk_sync"):
        st.switch_page("pages/4_sku_bulk_sync.py")
    st.page_link("pages/3_性能压测.py", label="🚦 进入性能压测配置", use_container_width=True)

with col_batch_mgmt:
    all_sources = sorted(global_df["source_file"].dropna().unique().tolist()) if not global_df.empty else []
    all_sources = [s for s in all_sources if s]
    if all_sources:
        st.markdown("**📂 批次管理**")
        sel_source = st.selectbox("选择批次", options=all_sources, label_visibility="collapsed")
        if sel_source:
            sf_df = global_df[global_df["source_file"] == sel_source]
            sf_total, sf_pass, sf_fail = len(sf_df), int((sf_df["status"]=="Pass").sum()), int((sf_df["status"]=="Fail").sum())
            st.caption(f"✅{sf_pass}  ❌{sf_fail}  ⏳{sf_total - sf_pass - sf_fail}  —  共 {sf_total} 条")

            if st.session_state.confirm_delete_file == sel_source:
                st.error(f"⚠️ 即将删除 **{sel_source}** 的全部 **{sf_total}** 条用例。删除前将自动归档。操作不可撤销。")
                c_cfm, c_cancel = st.columns(2)
                if c_cfm.button("✅ 确认删除", type="primary", use_container_width=True):
                    archive_rows = get_cases_by_source(sel_source)
                    if archive_rows:
                        a_dir = Path(__file__).parent / "测试用例归档"
                        a_dir.mkdir(exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        pd.DataFrame([dict(r) for r in archive_rows]).to_excel(str(a_dir / f"{Path(sel_source).stem}_归档_{ts}.xlsx"), index=False, sheet_name="归档数据")
                    n = delete_cases_by_source(sel_source)
                    st.session_state.confirm_delete_file = None
                    st.session_state.import_result = f"已删除 {sel_source} 的 {n} 条用例。"
                    st.cache_data.clear()
                    st.rerun()
                if c_cancel.button("取消", use_container_width=True):
                    st.session_state.confirm_delete_file = None
                    st.rerun()
            else:
                if st.button("🗑️ 删除此批次", use_container_width=True):
                    st.session_state.confirm_delete_file = sel_source
                    st.rerun()
    else:
        st.info("暂无已导入的批次数据")

# ── 孤儿用例提示 ────────────────────────────────────────────
if st.session_state.orphan_tc_ids:
    orphan_list, src = st.session_state.orphan_tc_ids, st.session_state.orphan_source
    st.warning(f"⚠️ 检测到 **{len(orphan_list)}** 条用例在新版 `{src}` 中已不存在：\n\n" + ", ".join(f"`{t}`" for t in orphan_list[:20]) + ("…" if len(orphan_list) > 20 else ""))
    c1, c2 = st.columns(2)
    if c1.button("🗑️ 同步删除废弃用例", type="primary", use_container_width=True):
        n_del = delete_cases_by_tc_ids(orphan_list)
        st.session_state.orphan_tc_ids, st.session_state.orphan_source = [], ""
        st.session_state.import_result += f"\n已同步清理 {n_del} 条废弃用例。"
        st.cache_data.clear()
        st.rerun()
    if c2.button("保留不删", use_container_width=True):
        st.session_state.orphan_tc_ids, st.session_state.orphan_source = [], ""
        st.rerun()

st.markdown("<br/>", unsafe_allow_html=True)
st.markdown('<div class="history-section-header"><h2><i class="fas fa-history"></i> 工作看板</h2></div>', unsafe_allow_html=True)

total = len(global_df)
pass_cnt = int((global_df["status"] == "Pass").sum()) if total else 0
fail_cnt = int((global_df["status"] == "Fail").sum()) if total else 0

total_stats = {"total": total, "pass": pass_cnt, "fail": fail_cnt, "pending": total - pass_cnt - fail_cnt}
files_data = []
if not global_df.empty:
    for f in global_df["source_file"].unique():
        if not f: continue
        sf_df = global_df[global_df["source_file"] == f]
        files_data.append({
            "filename": f, "timestamp": "", "total": len(sf_df),
            "pass": int((sf_df["status"] == "Pass").sum()),
            "fail": int((sf_df["status"] == "Fail").sum()),
            "pending": int((sf_df["status"].isin(["Untested", "Blocked"])).sum())
        })

selected_target = st_dashboard_grid(total_stats, files_data, key="home_dashboard")
if selected_target:
    st.session_state.active_file_filter = selected_target
    st.session_state.execution_status_filter = None
    st.switch_page("pages/1_🧪_测试执行.py")
