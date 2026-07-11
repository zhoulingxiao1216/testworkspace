"""Streamlit component wrapper for rich bug feedback paste input."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent.parent / "components" / "paste_feedback"
_paste_feedback = components.declare_component("paste_feedback", path=str(_COMPONENT_DIR))


def paste_feedback(*, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = default or {"text": "", "images": []}
    value = _paste_feedback(key=key, default=fallback)
    return value if isinstance(value, dict) else fallback
