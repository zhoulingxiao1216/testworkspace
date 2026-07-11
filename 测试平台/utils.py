"""
utils.py
公共模块：提供页面全局共享的数据加载、UI注入、树层级计算等服务。
"""
from __future__ import annotations

import io
from pathlib import Path
from datetime import datetime
from textwrap import dedent
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

from db_manager import get_all_cases, reset_all_status
from modules.detail_view import _STATUS_CN

_STATUS_FILTER_LABELS = {
    "Pass": "已通过",
    "Fail": "已失败",
    "Untested": "未执行",
    "Blocked": "阻塞",
}

# ── TC-ID 前缀 → 端 / 模块组 映射 ─────────────────────────────────────────
_PREFIX_MAP: dict[str, tuple[str, str]] = {
    "MG":       ("管理端", "会员等级基础库 [TC-MG]"),
    "PR":       ("管理端", "全球会员定价 [TC-PR]"),
    "SV":       ("管理端", "全球服务定价 [TC-SV]"),
    "CD":       ("管理端", "大客专属定价 [TC-CD]"),
    "FI":       ("管理端", "入金审核 [TC-FI]"),
    "CL-INTRO": ("客户端", "介绍中心 - 服务/费用 [TC-CL-INTRO]"),
    "CL-CART":  ("客户端", "购物车 [TC-CL-CART]"),
    "CL-PAY":   ("客户端", "会员支付 [TC-CL-PAY]"),
    "CL-SN":    ("客户端", "番号管理 [TC-CL-SN]"),
    "CL-BLOCK": ("客户端", "下单页 - 会员准入拦截 [TC-CL-BLOCK]"),
    "CL-LIFE":  ("客户端", "会员生命周期 [TC-CL-LIFE]"),
    "SE":       ("客户端", "全局安全性 [TC-SE]"),
    "IM-AUTH":  ("全球站", "模块一：准入与登录态 [TC-IM-AUTH]"),
    "IM-CHAT":  ("全球站", "模块二：分配、命名、等级与群权限 [TC-IM-CHAT]"),
    "IM-NOTIFY":("全球站", "模块三：消息提醒与未读状态 [TC-IM-NOTIFY]"),
    "IM-UI":    ("全球站", "模块四：嵌入式抽屉展示与UI兼容性 [TC-IM-UI]"),
}

def _resolve_hierarchy(tc_id: str) -> tuple[str, str]:
    """从 TC-ID 推导 (side, module_group)。返回 ('未分类', '未分类') 作为兜底。"""
    parts = tc_id.split("-")
    if len(parts) >= 2:
        inner = parts[1:]
        for length in range(min(3, len(inner)), 0, -1):
            candidate = "-".join(inner[:length])
            if candidate[-1].isdigit():
                continue
            if candidate in _PREFIX_MAP:
                side, group = _PREFIX_MAP[candidate]
                return side, group
        
        fallback_candidate = inner[0]
        if not fallback_candidate.isdigit():
            return "未分类", f"模块 [{fallback_candidate}]"
            
    return "未分类", "未分类"

# ── 数据加载（带异常保护） ────────────────────────────────────────────────
@st.cache_data(ttl=0, show_spinner=False)
def load_data() -> pd.DataFrame:
    cols = [
        "id", "tc_id", "module", "title", "priority", "steps",
        "expected", "status", "actual_result", "bug_link", "actual_amount",
        "test_point", "source_file",
    ]
    try:
        rows = get_all_cases()
        return pd.DataFrame([dict(r) for r in rows], columns=cols)
    except Exception as exc:  # noqa: BLE001
        st.error(f"数据库读取失败：{exc}")
        return pd.DataFrame(columns=cols)

# ── Excel 导出 ────────────────────────────────────────────────────────────
_EXPORT_COLS = {
    "id":            "用例ID",
    "module":        "模块",
    "title":         "标题",
    "priority":      "优先级",
    "status":        "执行状态",
    "actual_result": "实际报错",
    "bug_link":      "Bug链接",
    "actual_amount": "实际金额(元)",
}

def _build_excel_bytes(df: pd.DataFrame) -> bytes:
    export_df = (
        df[list(_EXPORT_COLS.keys())]
        .rename(columns=_EXPORT_COLS)
        .copy()
    )
    export_df["执行状态"] = (
        export_df["执行状态"].map(_STATUS_CN).fillna(export_df["执行状态"])
    )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="执行报告")
        ws = writer.sheets["执行报告"]
        for col_cells in ws.columns:
            max_len = max(
                len(str(cell.value)) if cell.value else 0
                for cell in col_cells
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 60)
    return buf.getvalue()

# ── 赛博深色主题 CSS ──────────────────────────────────────────────────────
_CSS_PATH = Path(__file__).parent / "assets" / "style.css"

def local_css() -> None:
    """读取外部 CSS 文件并注入页面，强制覆盖 Streamlit 所有默认 UI。"""
    css_text = _CSS_PATH.read_text(encoding="utf-8")
    
    st.markdown(
        '<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />',
        unsafe_allow_html=True
    )
    st.markdown(f"<style>\n{css_text}\n</style>", unsafe_allow_html=True)

def render_sidebar(df: pd.DataFrame) -> None:
    """渲染统计与操作侧边栏（动态支持全局/专项）"""
    with st.sidebar:
        st.markdown("<h3 style='margin-top: 0; margin-bottom: 2rem;'><i class='fas fa-home' style='color:#10b981; margin-right: 0.5rem;'></i>测试工作台</h3>", unsafe_allow_html=True)
        total       = len(df)
        pass_cnt    = int((df["status"] == "Pass").sum()) if total else 0
        fail_cnt    = int((df["status"] == "Fail").sum()) if total else 0
        untested_cnt = int((df["status"] == "Untested").sum()) if total else 0
        blocked_cnt  = int((df["status"] == "Blocked").sum()) if total else 0
        executed    = int((df["status"] != "Untested").sum()) if total else 0
        overall_pct = executed / total if total else 0.0

        active_filter = st.session_state.get("active_file_filter", "__GLOBAL__")
        is_global = (active_filter == "__GLOBAL__")
        view_title = "全局视图" if is_global else "专项视图"
        active_status = st.session_state.get("execution_status_filter")

        def _first_id(status: str | None) -> int | None:
            target_df = df if status is None else df[df["status"] == status]
            if target_df.empty:
                return None
            return int(target_df.iloc[0]["id"])

        def _status_href(status: str | None) -> str:
            target_id = _first_id(status) or _first_id(None)
            params = {"status": status or "All"}
            if not is_global:
                params["source"] = active_filter
            if target_id is not None:
                params["tc"] = str(target_id)
            return f"/测试执行?{urlencode(params)}"

        def _stat_card(
            status: str | None,
            value: int,
            label: str,
            icon_class: str,
            extra_card_class: str = "",
        ) -> str:
            is_active = status is not None and active_status == status
            active_cls = " stat-active" if is_active else ""
            disabled_cls = " stat-disabled" if value == 0 else ""
            href = _status_href(status)
            return (
                f'<a class="stat-link{disabled_cls}" href="{href}" target="_self" aria-label="筛选{label}用例">'
                f'<div class="stat-box stat-filter-card status-{status or "All"}{active_cls}{extra_card_class}">'
                f'<div class="stat-icon {icon_class}"><i class="fas {icon_class}"></i></div>'
                f'<div class="stat-info">'
                f'<span class="stat-value">{value}</span>'
                f'<span class="stat-label">{label}</span>'
                f'</div>'
                f'</div>'
                f'</a>'
            )

        stats_html = "".join([
            _stat_card(None, total, "用例总数", "fa-layer-group total"),
            _stat_card("Pass", pass_cnt, "已通过", "fa-check-circle passed"),
            _stat_card("Fail", fail_cnt, "已失败", "fa-times-circle failed"),
            _stat_card("Untested", untested_cnt, "未执行", "fa-clock pending"),
            _stat_card("Blocked", blocked_cnt, "阻塞", "fa-ban blocked", " status-blocked"),
        ])

        st.markdown(dedent(f"""
        <div class="panel-title" style="margin-top: 1rem;"><i class="fas fa-chart-pie"></i> {view_title}</div>
        {stats_html}
        <div class="progress-section">
            <div class="progress-header">
                <span>整体进度</span>
                <span>{overall_pct * 100:.1f}%</span>
            </div>
            <div class="progress-bar-bg" title="通过: {pass_cnt}, 失败: {fail_cnt}, 未执行: {untested_cnt}, 阻塞: {blocked_cnt}">
                <div class="progress-bar-fill success" style="width: {pass_cnt / total * 100 if total else 0}%;"></div>
                <div class="progress-bar-fill danger" style="width: {fail_cnt / total * 100 if total else 0}%;"></div>
                <div class="progress-bar-fill pending" style="width: {(untested_cnt + blocked_cnt) / total * 100 if total else 0}%;"></div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)

        # ── 快速跳转按钮 ──────────────────────────────────────────
        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
        col_jmp_untested, col_jmp_blocked = st.columns(2)
        with col_jmp_untested:
            if st.button(f"⏳ 未执行 ({untested_cnt})", disabled=(untested_cnt == 0),
                         use_container_width=True, key="sidebar_jump_untested"):
                first_match = df[df["status"] == "Untested"].iloc[0]
                st.session_state.execution_status_filter = "Untested"
                st.session_state.selected_case_id = int(first_match["id"])
                st.query_params["status"] = "Untested"
                if not is_global:
                    st.query_params["source"] = active_filter
                st.query_params["tc"] = str(int(first_match["id"]))
                try:
                    st.switch_page("pages/1_🧪_测试执行.py")
                except Exception:
                    st.rerun()
        with col_jmp_blocked:
            if st.button(f"🚫 阻塞 ({blocked_cnt})", disabled=(blocked_cnt == 0),
                         use_container_width=True, key="sidebar_jump_blocked"):
                first_match = df[df["status"] == "Blocked"].iloc[0]
                st.session_state.execution_status_filter = "Blocked"
                st.session_state.selected_case_id = int(first_match["id"])
                st.query_params["status"] = "Blocked"
                if not is_global:
                    st.query_params["source"] = active_filter
                st.query_params["tc"] = str(int(first_match["id"]))
                try:
                    st.switch_page("pages/1_🧪_测试执行.py")
                except Exception:
                    st.rerun()

        if active_status in _STATUS_FILTER_LABELS:
            st.caption(f"当前筛选：{_STATUS_FILTER_LABELS[active_status]}")
            if st.button("显示全部用例", use_container_width=True, key="sidebar_clear_status_filter"):
                st.session_state.execution_status_filter = None
                first_id = _first_id(None)
                st.query_params["status"] = "All"
                if not is_global:
                    st.query_params["source"] = active_filter
                if first_id is not None:
                    st.session_state.selected_case_id = first_id
                    st.query_params["tc"] = str(first_id)
                st.rerun()

        st.divider()
        st.subheader("⚙️ 操作")

        if total > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            btn_label = "📥 导出全局报告" if is_global else "📥 导出专项报告"
            file_prefix = "global_report" if is_global else f"special_{active_filter.split('.')[0]}"
            
            st.download_button(
                label=btn_label,
                data=_build_excel_bytes(df),
                file_name=f"{file_prefix}_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.button("📥 导出报告", disabled=True, use_container_width=True)

        st.write("")

        if not st.session_state.get("confirm_reset", False):
            if st.button("🗑️ 重置所有结果", use_container_width=True, help="将所有用例状态恢复为「未执行」，操作不可撤销"):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("⚠️ 此操作将清空全部记录，确认继续？")
            c_y, c_n = st.columns(2)
            if c_y.button("确认重置", type="primary", use_container_width=True):
                reset_all_status()
                st.session_state.confirm_reset = False
                st.cache_data.clear()
                st.rerun()
            if c_n.button("取消", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()
