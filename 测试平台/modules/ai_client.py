"""AI client helpers for bug feedback analysis."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Iterable

import streamlit as st


class AIConfigError(RuntimeError):
    """Raised when AI configuration is missing or incomplete."""


def get_ai_config() -> dict[str, Any]:
    if "ai" not in st.secrets:
        raise AIConfigError("未配置 [ai]，请先在 .streamlit/secrets.toml 中配置 AI 参数。")

    cfg = dict(st.secrets["ai"])
    missing = [key for key in ("api_key", "model") if not cfg.get(key)]
    if missing:
        raise AIConfigError(f"AI 配置缺失：{', '.join(missing)}")

    cfg.setdefault("base_url", "https://api.openai.com/v1")
    cfg.setdefault("timeout", 60)
    cfg.setdefault("api_type", "responses")
    cfg.setdefault("vision_model", cfg["model"])
    return cfg


def is_ai_configured() -> tuple[bool, str]:
    try:
        get_ai_config()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return True, "AI 配置可用"


def _get_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIConfigError("缺少 openai 依赖，请先执行：pip install openai") from exc

    cfg = get_ai_config()
    return OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        timeout=float(cfg.get("timeout", 60)),
    )


def _image_to_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def run_ai_analysis(
    prompt: str,
    *,
    image_paths: Iterable[str | Path] | None = None,
    use_vision_model: bool = False,
) -> str:
    cfg = get_ai_config()
    client = _get_openai_client()
    paths = list(image_paths or [])
    model = cfg.get("vision_model") if use_vision_model and paths else cfg["model"]
    api_type = str(cfg.get("api_type", "responses")).lower()

    if api_type == "chat_completions":
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for path in paths:
            content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(path)}})
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=float(cfg.get("temperature", 0.2)),
        )
        return response.choices[0].message.content or ""

    content = [{"type": "input_text", "text": prompt}]
    for path in paths:
        content.append({"type": "input_image", "image_url": _image_to_data_url(path)})
    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": content}],
        temperature=float(cfg.get("temperature", 0.2)),
    )
    return response.output_text
