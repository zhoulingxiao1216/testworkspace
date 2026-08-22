"""AI client helpers for bug feedback analysis."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

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
    cfg.setdefault("max_retries", 2)
    cfg.setdefault("api_type", "responses")
    cfg.setdefault("vision_model", cfg["model"])
    cfg.setdefault("trust_env", False)
    return cfg


def is_ai_configured() -> tuple[bool, str]:
    try:
        get_ai_config()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return True, "AI 配置可用"


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _base_host(cfg: dict[str, Any]) -> str:
    parsed = urlparse(str(cfg.get("base_url") or ""))
    return parsed.netloc or str(cfg.get("base_url") or "AI 接口")


def _redact_error_text(text: str, cfg: dict[str, Any]) -> str:
    api_key = str(cfg.get("api_key") or "")
    if api_key:
        text = text.replace(api_key, "***")
    return re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer ***", text)


def _error_chain(exc: Exception, cfg: dict[str, Any]) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current and id(current) not in seen and len(parts) < 3:
        seen.add(id(current))
        message = str(current).strip()
        if message:
            parts.append(f"{current.__class__.__name__}: {message}")
        current = current.__cause__ or current.__context__
    return _redact_error_text("；".join(parts) or exc.__class__.__name__, cfg)


def _format_ai_error(exc: Exception, cfg: dict[str, Any]) -> str:
    name = exc.__class__.__name__
    host = _base_host(cfg)
    detail = _error_chain(exc, cfg)
    trust_env = str(_as_bool(cfg.get("trust_env"), False)).lower()

    if name == "APIConnectionError":
        return (
            f"AI 接口连接失败：无法连接到 {host}。"
            f"请确认本机网络、DNS、证书或代理是否可用；当前 trust_env={trust_env}。"
            f"底层错误：{detail}"
        )
    if name == "APITimeoutError":
        return (
            f"AI 接口请求超时：{host} 在 {cfg.get('timeout')} 秒内未返回。"
            "可适当调大 [ai].timeout，或减少一次上传的截图数量/大小。"
            f"底层错误：{detail}"
        )
    if name in {"AuthenticationError", "PermissionDeniedError"}:
        return f"AI 鉴权失败：请检查 [ai].api_key 是否有效、是否有当前模型权限。底层错误：{detail}"
    if name == "NotFoundError":
        return f"AI 模型或接口不存在：请检查 [ai].base_url、model、vision_model。底层错误：{detail}"
    if name == "RateLimitError":
        return f"AI 接口限流或额度不足：请稍后重试或检查账号额度。底层错误：{detail}"
    if name == "BadRequestError":
        return (
            "AI 请求被接口拒绝：请检查模型是否支持当前文本/图片输入，"
            "以及 api_type 是否与服务商兼容。"
            f"底层错误：{detail}"
        )
    if name == "APIStatusError":
        status = getattr(getattr(exc, "response", None), "status_code", "未知")
        return f"AI 接口返回异常状态 HTTP {status}：{detail}"
    return f"AI 调用失败：{detail}"


def _get_openai_client(cfg: dict[str, Any]):
    try:
        from openai import OpenAI
        import httpx
    except ImportError as exc:
        raise AIConfigError("缺少 openai/httpx 依赖，请先执行：pip install openai") from exc

    timeout = float(cfg.get("timeout", 60))
    http_client = httpx.Client(timeout=timeout, trust_env=_as_bool(cfg.get("trust_env"), False))
    return OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg.get("base_url"),
        timeout=timeout,
        max_retries=int(cfg.get("max_retries", 2)),
        http_client=http_client,
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
    paths = list(image_paths or [])
    model = cfg.get("vision_model") if use_vision_model and paths else cfg["model"]
    api_type = str(cfg.get("api_type", "responses")).lower()
    client = None

    try:
        client = _get_openai_client(cfg)
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
    except AIConfigError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AIConfigError(_format_ai_error(exc, cfg)) from exc
    finally:
        if client is not None:
            close = getattr(client, "close", None)
            if callable(close):
                close()
