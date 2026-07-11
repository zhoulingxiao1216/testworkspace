"""Sakura 管理员 Session 维护 UI。"""

from __future__ import annotations

import base64
from typing import Optional

import streamlit as st

from modules.sakura_client import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    fetch_admin_captcha,
    login_admin_with_captcha,
    save_sku_config,
)

_CAPTCHA_STATE_KEY = "sakura_admin_captcha_payload"
_LOGIN_VISIBLE_KEY = "sakura_admin_login_visible"
_MANUAL_VISIBLE_KEY = "sakura_admin_manual_visible"


def _decode_data_image(data_url: str) -> Optional[bytes]:
    if not data_url or "," not in data_url:
        return None
    try:
        _, encoded = data_url.split(",", 1)
        return base64.b64decode(encoded)
    except (ValueError, base64.binascii.Error):
        return None



def _clear_token_cache() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("user_token_"):
            del st.session_state[key]



def _clear_login_state() -> None:
    st.session_state.pop(_CAPTCHA_STATE_KEY, None)
    st.session_state.pop("sakura_admin_captcha_input", None)



def _save_session(config: dict, sessid: str) -> None:
    config.setdefault("admin_session", {})["PHPSESSID"] = sessid
    save_sku_config(config)
    _clear_token_cache()
    _clear_login_state()
    st.session_state.pop(_LOGIN_VISIBLE_KEY, None)
    st.session_state.pop(_MANUAL_VISIBLE_KEY, None)



def render_admin_session_manager(config: dict, *, title: str = "⚙️ 配置") -> str:
    admin_sessid = config.get("admin_session", {}).get("PHPSESSID", "")

    st.subheader(title)
    if admin_sessid:
        st.success("✅ 管理员 Session 已配置")
        action_col1, action_col2 = st.columns(2)
        if action_col1.button("🔄 自动重新获取", use_container_width=True):
            st.session_state[_LOGIN_VISIBLE_KEY] = True
        if action_col2.button("✍️ 手动更新", use_container_width=True):
            st.session_state[_MANUAL_VISIBLE_KEY] = True
    else:
        st.error("⚠️ 管理员 Session 未配置")
        st.session_state.setdefault(_LOGIN_VISIBLE_KEY, True)

    login_open = st.session_state.get(_LOGIN_VISIBLE_KEY, False)
    with st.expander("🤖 验证码登录获取 PHPSESSID", expanded=login_open):
        st.caption("平台会请求后台验证码图片，由使用者人工识别后点击确认，成功后自动写入当前配置。")

        refresh_col, submit_col = st.columns([1, 1])
        if refresh_col.button("获取/刷新验证码", use_container_width=True, key="sakura_admin_refresh_captcha"):
            result = fetch_admin_captcha()
            if result.get("success"):
                st.session_state[_CAPTCHA_STATE_KEY] = result
                st.session_state[_LOGIN_VISIBLE_KEY] = True
                st.session_state.pop("sakura_admin_captcha_input", None)
                st.rerun()
            else:
                st.error(f"获取验证码失败：{result.get('error')} {result.get('detail', '')}")

        captcha_payload = st.session_state.get(_CAPTCHA_STATE_KEY)
        if captcha_payload:
            image_bytes = _decode_data_image(captcha_payload.get("captcha", ""))
            if image_bytes:
                st.image(image_bytes, caption="请识别图片验证码后输入", use_container_width=False)
            else:
                st.warning("验证码图片解码失败，请刷新验证码。")

            st.text_input("验证码", key="sakura_admin_captcha_input", max_chars=8)
            if submit_col.button("确认获取 PHPSESSID", type="primary", use_container_width=True):
                captcha_code = st.session_state.get("sakura_admin_captcha_input", "").strip()
                if not captcha_code:
                    st.error("请先输入验证码。")
                else:
                    result = login_admin_with_captcha(
                        username=DEFAULT_ADMIN_USERNAME,
                        password=DEFAULT_ADMIN_PASSWORD,
                        captcha_code=captcha_code,
                        rand=captcha_payload.get("rand", ""),
                        captcha_sessid=captcha_payload.get("captcha_sessid", ""),
                    )
                    if result.get("success"):
                        _save_session(config, result["sessid"])
                        st.success("管理员 Session 已更新，页面即将刷新。")
                        st.rerun()
                    else:
                        detail = result.get("detail", "")
                        if result.get("error") == "INVALID_CAPTCHA":
                            st.error(f"验证码错误：{detail or '请重新识别后再试。'}")
                            refreshed = fetch_admin_captcha()
                            if refreshed.get("success"):
                                st.session_state[_CAPTCHA_STATE_KEY] = refreshed
                                st.session_state.pop("sakura_admin_captcha_input", None)
                                st.rerun()
                        elif result.get("error") == "INVALID_CREDENTIALS":
                            st.error(f"账号或密码错误：{detail}")
                        else:
                            st.error(f"登录失败：{result.get('error')} {detail}")
        else:
            st.info("先点击“获取/刷新验证码”，再由使用者手工识别验证码。")

    manual_open = st.session_state.get(_MANUAL_VISIBLE_KEY, not admin_sessid)
    with st.expander("✍️ 手动粘贴 PHPSESSID", expanded=manual_open):
        if not admin_sessid:
            st.markdown(
                """
1. 在浏览器中登录 Sakura 后台管理系统
2. 打开开发者工具，进入 Cookies
3. 复制 PHPSESSID
4. 粘贴到下方并保存
                """
            )
        new_sessid = st.text_input("PHPSESSID", type="password", key="sakura_admin_manual_sessid")
        if st.button("保存 PHPSESSID", use_container_width=True, key="sakura_admin_manual_save"):
            if new_sessid.strip():
                _save_session(config, new_sessid.strip())
                st.success("管理员 Session 已保存，页面即将刷新。")
                st.rerun()
            else:
                st.error("请先粘贴 PHPSESSID。")

    return config.get("admin_session", {}).get("PHPSESSID", "")
