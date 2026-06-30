"""
测试执行页：展示树状测试用例，提供分栏操作与细节记录。
"""
import pandas as pd
import streamlit as st
from collections import OrderedDict

import modules.detail_view as detail
from modules.frontend_tree import st_execution_tree
from utils import load_data, local_css, _resolve_hierarchy, render_sidebar

# 必须先执行这句来保证样式和多页面独立渲染
st.set_page_config(page_title="执行面板", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
local_css()

# Session State 初始化
if "selected_case_id" not in st.session_state: st.session_state.selected_case_id = None
if "tree_last_selected" not in st.session_state: st.session_state.tree_last_selected = None
if "active_file_filter" not in st.session_state: st.session_state.active_file_filter = "__GLOBAL__"
if "expanded_sides"   not in st.session_state: st.session_state.expanded_sides   = set()
if "expanded_mgroups" not in st.session_state: st.session_state.expanded_mgroups = set()
if "expanded_tpoints" not in st.session_state: st.session_state.expanded_tpoints = set()
if "execution_status_filter" not in st.session_state: st.session_state.execution_status_filter = None

STATUS_FILTER_LABELS = {
    "Pass": "已通过",
    "Fail": "已失败",
    "Untested": "未执行",
    "Blocked": "阻塞",
}

# ── 返回首页按钮 ────────────────────────────────────────────────────────────
if st.button("⬅️ 返回项目首页", use_container_width=False):
    st.session_state.execution_status_filter = None
    st.switch_page("app.py")

# ── 数据过滤 ────────────────────────────────────────────────────────────────
global_df = load_data()

query_source = st.query_params.get("source")
if query_source == "__GLOBAL__":
    st.session_state.active_file_filter = "__GLOBAL__"
elif query_source:
    available_sources = set(global_df["source_file"].dropna().astype(str).tolist())
    if query_source in available_sources:
        st.session_state.active_file_filter = query_source

query_status = st.query_params.get("status")
if query_status == "All":
    st.session_state.execution_status_filter = None
elif query_status in STATUS_FILTER_LABELS:
    st.session_state.execution_status_filter = query_status
elif st.session_state.execution_status_filter not in STATUS_FILTER_LABELS:
    st.session_state.execution_status_filter = None

if st.session_state.active_file_filter != "__GLOBAL__":
    st.info(f"🎯 **专项工作台**：当前仅监控由 `{st.session_state.active_file_filter}` 导入产生的独立用例集。")
    if st.button("⬅️ 退出专项范围（返回首页）", type="primary"):
        st.session_state.active_file_filter = "__GLOBAL__"
        st.session_state.execution_status_filter = None
        st.switch_page("app.py")
    scoped_df = global_df[global_df["source_file"] == st.session_state.active_file_filter].copy()
else:
    scoped_df = global_df.copy()

# ── 渲染动态侧边栏 ──────────────────────────────────────────
render_sidebar(scoped_df)

status_filter = st.session_state.get("execution_status_filter")
if status_filter in STATUS_FILTER_LABELS:
    df = scoped_df[scoped_df["status"] == status_filter].copy()
else:
    df = scoped_df.copy()

total = len(df)
if total == 0:
    if status_filter in STATUS_FILTER_LABELS:
        st.warning(f"当前视角下暂无「{STATUS_FILTER_LABELS[status_filter]}」用例。")
        if st.button("显示全部用例", type="primary"):
            st.session_state.execution_status_filter = None
            st.query_params["status"] = "All"
            st.rerun()
    else:
        st.warning("当前视角下暂无用例数据，请重置过滤条件或前往「项目首页」导入文件。")
    st.stop()

# ── 为每条用例计算层级字段 ──────────────────────────────────────────────
def _add_hierarchy(row):
    tc_id = row.get("tc_id") or ""
    side, mgroup = _resolve_hierarchy(tc_id)
    return pd.Series({"side": side, "module_group": mgroup})

hierarchy_cols = df.apply(_add_hierarchy, axis=1)
df = pd.concat([df, hierarchy_cols], axis=1)
df["test_point"] = df["test_point"].fillna("").replace("", "其他")

# ── 确保 selected_case_id 有效与 URL 状态同步 ────────────────────────────────
valid_ids = set(df["id"].tolist())

# 从 URL 中恢复状态
query_tc = st.query_params.get("tc")
if query_tc and query_tc.isdigit() and int(query_tc) in valid_ids:
    if st.session_state.selected_case_id != int(query_tc):
        st.session_state.selected_case_id = int(query_tc)

if st.session_state.selected_case_id not in valid_ids:
    st.session_state.selected_case_id = int(df.iloc[0]["id"])
    first = df.iloc[0]
    st.session_state.expanded_sides.add(first["side"])
    st.session_state.expanded_mgroups.add(first["module_group"])
    st.session_state.expanded_tpoints.add((first["module_group"], first["test_point"]))

# 反向同步最新选中的 ID 到 URL
st.query_params["tc"] = str(st.session_state.selected_case_id)

# ── 构建有序树结构 ──────────────────────────────────────────────────────
tree = OrderedDict()
for _, r in df.iterrows():
    s, mg, tp = r["side"], r["module_group"], r["test_point"]
    tree.setdefault(s, OrderedDict()).setdefault(mg, OrderedDict()).setdefault(tp, []).append(r)

col_nav, col_work = st.columns([2, 3], gap="small")

with col_nav:
    status_badge = ""
    if status_filter in STATUS_FILTER_LABELS:
        status_badge = (
            f'<span style="margin-left:0.5rem;padding:0.15rem 0.45rem;'
            f'border:1px solid var(--border);border-radius:999px;'
            f'color:var(--text-secondary);font-size:0.75rem;">'
            f'{STATUS_FILTER_LABELS[status_filter]}</span>'
        )
    st.markdown(
        f'<div class="panel-title" style="margin: 0 4px 1rem 4px;">'
        f'<i class="fas fa-folder-tree"></i> 用例结构{status_badge}'
        f'<span style="color:var(--text-secondary);font-size:0.85rem;margin-left:auto;">'
        f'{total} 条</span></div>',
        unsafe_allow_html=True,
    )

    tree_json = []
    visual_order_ids = []  # 缓存前端视觉上显示的绝对顺序
    for side_name, mgroups in tree.items():
        side_cases = df[df["side"] == side_name]
        s_pass, s_total = int((side_cases["status"] == "Pass").sum()), len(side_cases)
        s_pct = int(s_pass / s_total * 100) if s_total else 0
        
        side_node = {"type": "side", "title": side_name, "pct": s_pct, "children": []}
        
        for mg_name, tpoints in mgroups.items():
            mg_node = {"type": "mg", "title": mg_name, "children": []}
            for tp_name, cases_list in tpoints.items():
                tp_node = {"type": "tp", "title": tp_name, "children": []}
                for row in cases_list:
                    c_id, c_status = int(row["id"]), row["status"]
                    tc_label = row.get("tc_id") or f"#{c_id}"
                    c_title = str(row["title"] or "")
                    tp_node["children"].append({
                        "type": "case", "id": c_id, "label": tc_label,
                        "title": c_title, "status": c_status
                    })
                    visual_order_ids.append(c_id)
                mg_node["children"].append(tp_node)
            side_node["children"].append(mg_node)
        tree_json.append(side_node)

    selected = st_execution_tree(tree_json, selected_id=st.session_state.selected_case_id, key="exec_tree")

    if selected is not None and selected != st.session_state.tree_last_selected:
        st.session_state.tree_last_selected = selected
        if selected != st.session_state.selected_case_id:
            st.session_state.selected_case_id = selected
            st.query_params["tc"] = str(selected)
            st.rerun()

with col_work:
    case_row = df[df["id"] == st.session_state.selected_case_id]
    if case_row.empty:
        st.info("请在左侧选择一个测试用例。")
        st.stop()
    case = case_row.iloc[0]
    detail.render_detail_panel(case, visual_order_ids)
