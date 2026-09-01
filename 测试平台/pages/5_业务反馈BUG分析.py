"""Business feedback BUG intake and AI-assisted TAPD description."""

from __future__ import annotations

import base64
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from modules.ai_client import AIConfigError, is_ai_configured, run_ai_analysis
from modules.paste_feedback import paste_feedback
from utils import local_css

WORKSPACE_ROOT = Path(r"D:\test_workspace")
PROJECTS_ROOT = WORKSPACE_ROOT / "测试项目"
PROJECT_CODE_DIRS = {
    "樱花站": Path(r"D:\sakura"),
    "全球站": Path(r"D:\global\Global"),
}

st.set_page_config(page_title="业务反馈BUG分析", page_icon="🧩", layout="wide")
local_css()
st.title("🧩 业务反馈 BUG 分析")
st.caption("面向截图 + 一句话反馈的 BUG 记录，AI 自动整理 TAPD 缺陷描述。")


def _safe_filename(value: str, fallback: str = "bug") -> str:
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", value.strip())
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe[:80] or fallback


def _resolve_code_dir(project_name: str) -> Path:
    return PROJECT_CODE_DIRS.get(project_name, PROJECTS_ROOT / project_name)


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


for key, default in {
    "bug_saved_images": [],
    "bug_initial_analysis": "",
    "bug_generate_tapd_payload": {},
    "bug_generate_tapd_requested": False,
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

with right:
    st.subheader("2. TAPD 缺陷描述")

    if st.session_state.get("bug_generate_tapd_requested"):
        payload = st.session_state.get("bug_generate_tapd_payload") or {}
        pending_feedback_text = str(payload.get("feedback_text") or "")
        pending_image_paths = [Path(path) for path in payload.get("image_paths", [])]
        st.session_state["bug_generate_tapd_requested"] = False
        st.session_state["bug_generate_tapd_payload"] = {}
        try:
            with st.spinner("AI 正在整理 TAPD 缺陷描述..."):
                st.session_state["bug_initial_analysis"] = run_ai_analysis(
                    _bug_intake_prompt(pending_feedback_text),
                    image_paths=pending_image_paths,
                    use_vision_model=bool(pending_image_paths),
                )
        except AIConfigError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(f"AI 分析失败：{exc}")

    st.text_area("TAPD 缺陷描述（可编辑）", key="bug_initial_analysis", height=420)

    if st.button("AI生成TAPD缺陷描述", type="primary", use_container_width=True, disabled=not configured):
        image_paths = _save_current_images(project_name, clipboard_images, uploaded_files)
        if not feedback_text and not image_paths:
            st.error("请至少提供截图或业务原话。")
        else:
            st.session_state["bug_generate_tapd_payload"] = {
                "feedback_text": feedback_text,
                "image_paths": [str(path) for path in image_paths],
            }
            st.session_state["bug_generate_tapd_requested"] = True
            st.rerun()
