import html as _html
import streamlit as st
from db_manager import update_case_status

STATUS_ICON    = {"Untested": "⬜", "Pass": "✅", "Fail": "❌", "Blocked": "🚫"}
PRIORITY_BADGE = {"P0": "🔴 P0", "P1": "🟡 P1", "P2": "🟢 P2"}
_STATUS_CN     = {"Untested": "未执行", "Pass": "通过", "Fail": "失败", "Blocked": "阻塞"}

def _commit_and_refresh() -> None:
    """DB 写入后清除数据缓存并强制重渲染。"""
    st.cache_data.clear()
    st.rerun()

def _step_html(text: str) -> str:
    """将纯文本步骤转义为 HTML 安全字符串，保留换行。"""
    return _html.escape(text or "").replace("\n", "<br>")

def _priority_badge_html(priority: str) -> str:
    """返回带颜色 CSS 类的优先级 HTML 徽标。"""
    _MAP = {
        "P0": '<span class="pri-p0">🔴 P0</span>',
        "P1": '<span class="pri-p1">🟡 P1</span>',
        "P2": '<span class="pri-p2">🟢 P2</span>',
    }
    return _MAP.get(priority, _html.escape(priority))

@st.dialog("📝 记录缺陷详情")
def fail_dialog(case_id: int, tc_label: str, next_id):
    st.markdown(f"您正在将 **{tc_label}** 标记为 <b style='color:var(--danger)'>失败</b>，请补充缺陷详情：", unsafe_allow_html=True)
    actual_result = st.text_area("🔴 实际报错快照", placeholder="必填：发生了什么错误？...", height=120)
    bug_link = st.text_input("🔗 缺陷单号 / 截图链接", placeholder="选填：如 Jira / TAPD 链接...")
    
    if st.button("🚀 提报缺陷并置为失败", type="primary"):
        if not actual_result.strip():
            st.error("请填写实际报错细节，以便研发定位！")
            return
        update_case_status(case_id, "Fail", actual_result.strip(), bug_link.strip())
        st.toast(f"❌ {tc_label} 已落库为失败", icon="❌")
        if next_id:
            st.session_state.selected_case_id = next_id
            st.query_params["tc"] = str(next_id)
        _commit_and_refresh()

def render_detail_panel(case, all_ids: list = None) -> None:
    """渲染右侧的测试用例执行详情及动作按钮面板。"""
    case_id    = int(case["id"])
    tc_label   = case.get("tc_id") or f"#{case_id}"
    status     = case["status"]
    priority   = case["priority"]
    title_text = str(case["title"] or "")
    steps      = str(case["steps"] or "")
    expected   = str(case["expected"] or "")
    actual_res = str(case.get("actual_result") or "").strip()
    bug_link   = str(case.get("bug_link") or "").strip()
    icon       = STATUS_ICON.get(status, "⬜")
    status_cn  = _STATUS_CN.get(status, status)
    sel_module = case["module_group"]
    sel_tp     = case["test_point"]

    # 面包屑导航
    st.markdown(
        f'<div style="font-size:0.70rem;color:#8B949E;padding:4px 0 8px;'
        f'font-family:JetBrains Mono,monospace;">'
        f'{_html.escape(case["side"])} › '
        f'{_html.escape(sel_module)} › '
        f'{_html.escape(sel_tp)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 用例详情区块 ────────────────────────────────────────────────────
    st.markdown('<div class="tc-header">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="tc-id">{_html.escape(str(tc_label))}</div>'
        f'<div class="tc-title" style="font-size: 1.25rem; font-weight: 600; margin: 0.5rem 0;">{_html.escape(title_text)}</div>'
        f'<div class="tc-meta">{_priority_badge_html(priority)}'
        f'<span class="badge" style="margin-left:8px; background:rgba(16,185,129,0.1); color:var(--success); border:1px solid rgba(16,185,129,0.2);">'
        f'{icon} {status_cn}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True) # 闭合 tc-header
    # ── 状态与导航操作区（统一集中的紧凑型工具栏） ──────────────────
    st.markdown('<div style="margin-top: 0.5rem;"></div>', unsafe_allow_html=True)
    # 用比例扩宽“未执行”按钮防止挤压折行，中间插入占位空白列，把翻页按钮顶到右侧
    btn_pass, btn_fail, btn_untest, _, btn_prev, btn_next = st.columns([1.4, 1.4, 1.8, 3.4, 2.0, 2.0], gap="small", vertical_alignment="center")

    # helper for finding next case id
    all_ids = all_ids or []
    try:
        current_idx = all_ids.index(case_id)
    except ValueError:
        current_idx = 0
    next_id = all_ids[current_idx + 1] if current_idx + 1 < len(all_ids) else None
    prev_id = all_ids[current_idx - 1] if current_idx - 1 >= 0 else None

    with btn_pass:
        if st.button("✅ 通过", key=f"btn_pass_{case_id}", use_container_width=True):
            update_case_status(case_id, "Pass")
            st.toast(f"✅ {tc_label} 已通过", icon="✅")
            if next_id:
                st.session_state.selected_case_id = next_id
                st.query_params["tc"] = str(next_id)
            _commit_and_refresh()
    with btn_fail:
        if st.button("❌ 失败", key=f"btn_fail_{case_id}", use_container_width=True):
            fail_dialog(case_id, tc_label, next_id)
    with btn_untest:
        if st.button("🚫 阻塞", key=f"btn_block_{case_id}", use_container_width=True):
            update_case_status(case_id, "Blocked")
            st.toast(f"🚫 {tc_label} 已标记为阻塞", icon="🚫")
            if next_id:
                st.session_state.selected_case_id = next_id
                st.query_params["tc"] = str(next_id)
            _commit_and_refresh()

    with btn_prev:
        if st.button("⬅️ 上一条 (Prev)", key=f"btn_prev_{case_id}", disabled=(prev_id is None), use_container_width=True):
            st.session_state.selected_case_id = prev_id
            st.query_params["tc"] = str(prev_id)
            st.rerun()
    with btn_next:
        if st.button("下一条 (Next) ➡️", key=f"btn_next_{case_id}", disabled=(next_id is None), use_container_width=True):
            st.session_state.selected_case_id = next_id
            st.query_params["tc"] = str(next_id)
            st.rerun()

    st.markdown('<div class="tc-section">', unsafe_allow_html=True)
    if steps or expected:
        with st.container(height=350, border=False):
            c_s, c_e = st.columns(2)
            with c_s:
                if steps:
                    st.markdown("<h3><i class='fas fa-shoe-prints'></i> 操作步骤</h3>", unsafe_allow_html=True)
                    st.markdown(f'<div class="tc-content">{_step_html(steps)}</div>', unsafe_allow_html=True)
            with c_e:
                if expected:
                    st.markdown("<h3><i class='fas fa-bullseye'></i> 预期结果</h3>", unsafe_allow_html=True)
                    st.markdown(f'<div class="tc-content">{_step_html(expected)}</div>', unsafe_allow_html=True)
    
    # ── 缺陷复盘展示区 ────────────────────────────────────────────────────
    if actual_res or bug_link:
        st.markdown("<hr style='margin: 1.5rem 0 1rem 0; border-color: rgba(239, 68, 68, 0.2);'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:var(--danger); margin-bottom: 0.8rem;'><i class='fas fa-bug'></i> 缺陷复盘记录</h3>", unsafe_allow_html=True)
        
        fail_html = '<div style="background: rgba(239, 68, 68, 0.05); border: 1px dashed rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 1.2rem; line-height: 1.6;">'
        
        if actual_res:
            fail_html += (
                f"<div style='margin-bottom: 0.8rem;'>"
                f"<strong style='color: var(--danger); font-size: 0.95rem;'>🔴 报错详情：</strong><br>"
                f"<div style='color: #f8fafc; font-family: var(--font-mono); white-space: pre-wrap; margin-top: 0.4rem; padding: 0.8rem; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 0.9rem;'>{_step_html(actual_res)}</div>"
                f"</div>"
            )
            
        if bug_link:
            display_link = (
                f"<a href='{bug_link}' target='_blank' style='color: var(--brand); text-decoration: none; font-weight: 600;'>{_html.escape(bug_link)} ↗</a>" 
                if bug_link.startswith("http") else _html.escape(bug_link)
            )
            fail_html += (
                f"<div>"
                f"<strong style='color: var(--text-secondary); font-size: 0.95rem;'>🔗 追踪链接：</strong> {display_link}"
                f"</div>"
            )
            
        fail_html += '</div>'
        st.markdown(fail_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

