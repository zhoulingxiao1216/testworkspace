"""Business feedback BUG intake and AI-assisted root-cause analysis."""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from modules.ai_client import AIConfigError, is_ai_configured, run_ai_analysis
from modules.paste_feedback import paste_feedback
from modules.readonly_db import assert_select_only, fetch_all
from utils import local_css

WORKSPACE_ROOT = Path(r"D:\test_workspace")
PROJECTS_ROOT = WORKSPACE_ROOT / "测试项目"
BUG_DOC_TITLE = "业务反馈 BUG 提交单"
PROJECT_CODE_DIRS = {
    "樱花站": Path(r"D:\sakura"),
    "全球站": Path(r"D:\global\Global"),
}
GLOBAL_CODE_KEYWORD_ROUTES = {
    "前台问题": "user-b2b-view",
    "介绍中心": "user-all-view",
    "PDA": "global-wms",
    "IM": "global-im",
    "后台问题": "admin-all-view",
}

st.set_page_config(page_title="业务反馈BUG分析", page_icon="🧩", layout="wide")
local_css()
st.title("🧩 业务反馈 BUG 分析")
st.caption("面向截图 + 一句话反馈的 BUG 记录、AI 初判、只读深度分析和提交单生成。")


def _safe_filename(value: str, fallback: str = "bug") -> str:
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", value.strip())
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe[:80] or fallback


def _state_key(prefix: str, project_name: str) -> str:
    return f"{prefix}_{_safe_filename(project_name, fallback='project')}"


def _resolve_code_dir(project_name: str) -> Path:
    return PROJECT_CODE_DIRS.get(project_name, PROJECTS_ROOT / project_name)


def _resolve_search_dirs(project_name: str, keywords: str) -> tuple[Path, list[Path], list[str]]:
    project_dir = _resolve_code_dir(project_name)
    if project_name != "全球站":
        return project_dir, [project_dir], []

    normalized_keywords = (keywords or "").lower()
    matched_routes = []
    search_dirs = []
    for keyword, relative_dir in GLOBAL_CODE_KEYWORD_ROUTES.items():
        if keyword.lower() not in normalized_keywords:
            continue
        route_dir = project_dir / relative_dir
        matched_routes.append(f"{keyword} -> {relative_dir}")
        search_dirs.append(route_dir)

    return project_dir, search_dirs or [project_dir], matched_routes


def _ensure_bug_dirs(project_name: str) -> tuple[Path, Path]:
    doc_dir = PROJECTS_ROOT / project_name / "测试文档"
    attachment_dir = doc_dir / "bug反馈附件"
    attachment_dir.mkdir(parents=True, exist_ok=True)
    return doc_dir, attachment_dir


def _save_uploads(project_name: str, uploaded_files: list[Any]) -> list[Path]:
    if not project_name or not uploaded_files:
        return []
    _, attachment_dir = _ensure_bug_dirs(project_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []
    for index, file in enumerate(uploaded_files, start=1):
        suffix = Path(file.name).suffix.lower() or ".png"
        target = attachment_dir / f"{ts}_{index:02d}_{_safe_filename(Path(file.name).stem)}{suffix}"
        target.write_bytes(file.getvalue())
        saved_paths.append(target)
    return saved_paths


def _save_clipboard_images(project_name: str, images: list[dict[str, str]]) -> list[Path]:
    if not project_name or not images:
        return []
    _, attachment_dir = _ensure_bug_dirs(project_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_paths = []
    for index, image in enumerate(images, start=1):
        data_url = str(image.get("data_url") or "")
        match = re.match(r"^data:image/(png|jpeg|jpg);base64,(.+)$", data_url, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        suffix = ".jpg" if match.group(1).lower() in {"jpeg", "jpg"} else ".png"
        name = _safe_filename(Path(str(image.get("name") or "clipboard")).stem)
        target = attachment_dir / f"{ts}_paste_{index:02d}_{name}{suffix}"
        target.write_bytes(base64.b64decode(match.group(2)))
        saved_paths.append(target)
    return saved_paths


def _save_current_images(project_name: str, clipboard_images: list[dict[str, str]], uploaded_files: list[Any]) -> list[Path]:
    if st.session_state.get("bug_saved_images"):
        return st.session_state["bug_saved_images"]
    saved = [*_save_clipboard_images(project_name, clipboard_images), *_save_uploads(project_name, uploaded_files)]
    st.session_state["bug_saved_images"] = saved
    return saved


def _run_git(project_dir: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return f"执行失败：{exc}"
    return (result.stdout or result.stderr or "无输出").strip()[:6000]


def _collect_code_context(project_name: str, keywords: str) -> dict[str, Any]:
    project_dir, search_dirs, matched_routes = _resolve_search_dirs(project_name, keywords)
    if not project_dir.exists():
        return {"project_dir": str(project_dir), "exists": False, "message": "项目代码目录不存在"}

    context: dict[str, Any] = {
        "project_dir": str(project_dir),
        "search_dirs": [str(path) for path in search_dirs],
        "matched_routes": matched_routes,
        "exists": True,
        "git_status": _run_git(project_dir, ["status", "--short"]),
        "git_latest_log": _run_git(project_dir, ["log", "-3", "--oneline", "--decorate"]),
        "matches": [],
    }
    terms = [x.strip() for x in re.split(r"[,，\n\s]+", keywords or "") if x.strip()]
    if not terms:
        return context

    suffixes = {".py", ".js", ".ts", ".tsx", ".vue", ".php", ".java", ".go", ".sql", ".md", ".yaml", ".yml", ".json"}
    skip_parts = {"node_modules", ".git", "__pycache__", "dist", "build", "vendor"}
    matches = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for path in search_dir.rglob("*"):
            if len(matches) >= 30:
                break
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if any(part in skip_parts for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            hit_terms = [term for term in terms if term.lower() in text.lower()]
            if not hit_terms:
                continue
            lines = []
            for line_no, line in enumerate(text.splitlines(), start=1):
                if any(term.lower() in line.lower() for term in hit_terms):
                    lines.append({"line": line_no, "text": line.strip()[:240]})
                if len(lines) >= 5:
                    break
            matches.append({"file": str(path.relative_to(project_dir)), "terms": hit_terms, "lines": lines})
        if len(matches) >= 30:
            break
    context["matches"] = matches
    return context


def _bug_intake_prompt(feedback_text: str) -> str:
    return f"""
你是测试平台的 TAPD 缺陷描述整理 Agent。
业务通常只提供截图和一句话，你需要把这些非结构化信息整理成 TAPD 缺陷详情里的标准描述。

业务原话：
{feedback_text or "业务未填写文字描述，请主要依据截图识别问题。"}

请只输出以下四段，不要输出其他标题、原因分析、风险评级、代码建议：

【BUG标题】
1. ...

【前提条件】
1. ...

【操作步骤&实际结果】
1. ...
2. ...

【预期结果】
1. ...

整理规则：
- 【BUG标题】用一句话概括问题，格式建议为“模块/页面 + 异常现象”，标题要短，适合直接作为 TAPD 缺陷标题。
- 【前提条件】写账号、系统、页面、订单号、报价单号、客户、环境、链接等已知前置条件。
- 【操作步骤&实际结果】按业务实际反馈整理操作路径和当前异常结果，可以合并写在同一步里。
- 【预期结果】写系统应该达到的正确表现。
- 如果截图或文字没有提供的信息，不要编造；用“需补充确认”表达。
- 语言要短，适合直接粘贴到 TAPD 缺陷详情。
- 不要使用 Markdown 的 ## 标题。
- 不要输出“初步疑似原因”“需要进一步检查”“严重级别”等分析内容。

参考格式：
【BUG标题】
1. 后台报价单/代购订单修改负责人下拉框缺少“请选择”选项

【前提条件】
1. 后台 b2b 系统，报价单和代购订单中修改负责人页面。

【操作步骤&实际结果】
1. 进入报价单/代购订单详情，点击修改负责人。
2. 下拉框缺少“请选择”选项，且与客户信息详情页展示不一致。

【预期结果】
1. 修改负责人下拉框应包含“请选择”选项，并与客户信息详情页保持一致。
""".strip()


def _deep_analysis_prompt(feedback_text: str, initial_analysis: str, code_context: dict[str, Any], db_summary: str) -> str:
    return f"""
你是测试平台的深度根因分析 Agent。当前任务只做问题检查，不做代码修复；数据库只允许查询。

业务反馈：
{feedback_text or "无业务文字描述"}

AI 初步分析：
{initial_analysis or "尚未生成"}

只读代码检查结果：
{json.dumps(code_context, ensure_ascii=False, indent=2)}

只读数据库检查结果：
{db_summary or "尚未执行数据库查询"}

请输出 Markdown，固定包含：
## 根因判断
## 证据链
## 可能涉及代码位置
## 数据库检查结论
## 风险评估
## 是否建议提交 BUG
## 待研发确认项

要求：明确区分已确认事实和推测；不要输出代码修复内容；不要建议执行写库 SQL。
""".strip()


def _build_bug_report(project_name: str, reporter: str, feedback_text: str, image_paths: list[Path], initial: str, deep: str, severity: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attachments = "\n".join(f"- `{path}`" for path in image_paths) or "- 无"
    return f"""# {BUG_DOC_TITLE}

## 基本信息

| 字段 | 内容 |
| --- | --- |
| 项目 | {project_name or "未选择"} |
| 反馈人 | {reporter or "未填写"} |
| 生成时间 | {now} |
| 严重级别 | {severity or "待确认"} |
| 分析方式 | 截图/业务原话 + TAPD 缺陷描述 + 只读深度分析 |

## 业务原始反馈

{feedback_text or "业务未填写文字描述，仅提供截图。"}

## 截图附件

{attachments}

## TAPD 缺陷描述

{initial or "未生成"}

## 深度分析结论

{deep or "未生成"}

## 提交约束

- 本单仅记录问题现象、证据链和疑似原因。
- 未做代码修复。
- 数据库检查仅允许只读查询。
- 敏感凭据、Token、Cookie、Webhook 不得写入本单。

## 变更记录

| 时间 | 说明 |
| --- | --- |
| {now} | 由测试平台生成业务反馈 BUG 提交单 |
"""


def _save_bug_report(project_name: str, markdown_text: str) -> Path:
    doc_dir, _ = _ensure_bug_dirs(project_name)
    target = doc_dir / f"BUG提交单_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
    target.write_text(markdown_text, encoding="utf-8")
    return target


for key, default in {
    "bug_saved_images": [],
    "bug_initial_analysis": "",
    "bug_code_contexts": {},
    "bug_db_result": "",
    "bug_deep_analysis": "",
    "bug_report_markdown": "",
    "bug_report_path": "",
}.items():
    st.session_state.setdefault(key, default)

configured, config_message = is_ai_configured()
if configured:
    st.success("AI 配置已检测到。")
else:
    st.warning(config_message)
    with st.expander("AI 配置示例", expanded=False):
        st.caption("Gemini 推荐配置")
        st.code(
            """
[ai]
api_key = "你的_Gemini_API_Key"
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
model = "你的 Gemini 文本模型"
vision_model = "你的 Gemini 图片理解模型"
timeout = 60
max_retries = 2
temperature = 0.2
api_type = "chat_completions"
trust_env = false
""".strip(),
            language="toml",
        )
        st.caption("OpenAI 官方接口配置")
        st.code(
            """
[ai]
api_key = "你的_OpenAI_API_Key"
base_url = "https://api.openai.com/v1"
model = "你的 OpenAI 文本模型"
vision_model = "你的 OpenAI 图片理解模型"
timeout = 60
max_retries = 2
temperature = 0.2
api_type = "responses"
trust_env = false
""".strip(),
            language="toml",
        )

left, right = st.columns([0.95, 1.35], gap="large")

with left:
    st.subheader("1. 业务反馈")
    project_name = st.selectbox("项目", options=list(PROJECT_CODE_DIRS.keys()), index=0)
    st.caption(f"代码只读检查目录：{_resolve_code_dir(project_name)}")
    reporter = st.text_input("反馈人", placeholder="例如：吴四佳")
    severity = st.selectbox("严重级别", ["待确认", "P0/Blocker", "P1/High", "P2/Medium", "P3/Low"], index=0)
    st.caption("业务原话")
    paste_value = paste_feedback(key="bug_feedback_paste", default={"text": "", "images": []})
    feedback_text = str(paste_value.get("text") or "")
    clipboard_images = paste_value.get("images") if isinstance(paste_value.get("images"), list) else []
    if clipboard_images:
        with st.expander(f"已粘贴 {len(clipboard_images)} 张截图，点击查看", expanded=False):
            cols = st.columns(min(3, len(clipboard_images)))
            for index, image in enumerate(clipboard_images):
                with cols[index % len(cols)]:
                    st.image(image["data_url"], caption=image.get("name", "image"), width=220)

    with st.expander("备用：从本地选择截图", expanded=False):
        uploaded_files = st.file_uploader(
            "选择截图文件",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

    if st.session_state["bug_saved_images"]:
        with st.expander(f"已保存 {len(st.session_state['bug_saved_images'])} 张截图，点击查看", expanded=False):
            cols = st.columns(min(3, len(st.session_state["bug_saved_images"])))
            for index, image_path in enumerate(st.session_state["bug_saved_images"]):
                with cols[index % len(cols)]:
                    st.image(str(image_path), caption=image_path.name, width=220)

    st.subheader("2. TAPD 缺陷描述")
    if st.button("AI生成TAPD缺陷描述", type="primary", use_container_width=True, disabled=not configured):
        image_paths = _save_current_images(project_name, clipboard_images, uploaded_files)
        if not feedback_text and not image_paths:
            st.error("请至少提供截图或业务原话。")
        else:
            try:
                with st.spinner("AI 正在整理 TAPD 缺陷描述..."):
                    st.session_state["bug_initial_analysis"] = run_ai_analysis(
                        _bug_intake_prompt(feedback_text),
                        image_paths=image_paths,
                        use_vision_model=bool(image_paths),
                    )
            except AIConfigError as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"AI 分析失败：{exc}")
    st.text_area("TAPD 缺陷描述（可编辑）", key="bug_initial_analysis", height=260)

with right:
    st.subheader("3. 只读深度分析")
    code_contexts = st.session_state.setdefault("bug_code_contexts", {})
    keyword_key = _state_key("bug_code_keywords", project_name)
    if keyword_key not in st.session_state:
        st.session_state[keyword_key] = "入金 重复 客户 余额 订单 审核"
    search_keywords = st.text_input("代码检索关键词", key=keyword_key)
    _, current_search_dirs, current_routes = _resolve_search_dirs(project_name, search_keywords)
    st.caption(f"当前项目：{project_name}；只读检索目录：{'、'.join(str(path) for path in current_search_dirs)}")
    if project_name == "全球站":
        st.caption("全球站关键词路由：前台问题→user-b2b-view；介绍中心→user-all-view；PDA→global-wms；IM→global-im；后台问题→admin-all-view")
        if current_routes:
            st.info(f"已命中优先检索范围：{'；'.join(current_routes)}")
    if st.button(f"只读检查{project_name}项目代码", use_container_width=True, key=_state_key("bug_code_search", project_name)):
        with st.spinner("正在只读检索项目代码..."):
            code_contexts[project_name] = _collect_code_context(project_name, search_keywords)
            st.session_state["bug_code_contexts"] = code_contexts
    current_code_context = code_contexts.get(project_name, {})
    if current_code_context:
        st.json(current_code_context, expanded=False)

    with st.expander("数据库只读查询", expanded=False):
        st.caption("仅允许单条 SELECT。禁止 INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE 等写入或变更语句。")
        sql_text = st.text_area("SQL", height=120, placeholder="select * from table_name where id = ... limit 20")
        limit = st.number_input("最多读取行数", min_value=1, max_value=5000, value=100, step=50)
        if st.button("执行只读查询", use_container_width=True):
            try:
                assert_select_only(sql_text)
                rows = fetch_all(sql_text, limit=int(limit))
                st.session_state["bug_db_result"] = json.dumps(rows, ensure_ascii=False, indent=2) if rows else "查询成功，无结果。"
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"查询被拒绝或执行失败：{exc}")
    if st.session_state["bug_db_result"]:
        st.text_area("数据库查询结果摘要", key="bug_db_result", height=160)

    if st.button("AI生成深度分析结论", type="primary", use_container_width=True, disabled=not configured):
        try:
            with st.spinner("AI 正在汇总代码和数据库证据..."):
                st.session_state["bug_deep_analysis"] = run_ai_analysis(
                    _deep_analysis_prompt(
                        feedback_text,
                        st.session_state["bug_initial_analysis"],
                        current_code_context,
                        st.session_state["bug_db_result"],
                    )
                )
        except AIConfigError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(f"深度分析失败：{exc}")
    st.text_area("深度分析结论（可编辑）", key="bug_deep_analysis", height=260)

    st.subheader("4. BUG 提交单")
    if st.button("生成BUG提交单", type="primary", use_container_width=True):
        image_paths = _save_current_images(project_name, clipboard_images, uploaded_files)
        markdown_text = _build_bug_report(
            project_name,
            reporter,
            feedback_text,
            image_paths,
            st.session_state["bug_initial_analysis"],
            st.session_state["bug_deep_analysis"],
            severity,
        )
        st.session_state["bug_report_markdown"] = markdown_text
        target = _save_bug_report(project_name, markdown_text)
        st.session_state["bug_report_path"] = str(target)
        st.success(f"BUG 提交单已生成：{target}")
    if st.session_state["bug_report_markdown"]:
        st.download_button(
            "下载BUG提交单",
            data=st.session_state["bug_report_markdown"].encode("utf-8"),
            file_name=Path(st.session_state["bug_report_path"] or "BUG提交单.md").name,
            mime="text/markdown",
            use_container_width=True,
        )
        st.markdown(st.session_state["bug_report_markdown"])
