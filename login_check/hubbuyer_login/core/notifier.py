# -*- coding: utf-8 -*-
"""WeCom notifier for the prod login check."""

from datetime import datetime

import requests

from config.settings import (
    API_CONFIG,
    ENABLE_ALARM_NOTIFIER,
    ENABLE_NORMAL_NOTIFIER,
    ENV_TYPE,
    REPORT_CONFIG,
    REQUEST_TIMEOUT_NOTIFIER,
    WEBHOOK_URL_ALARM,
    WEBHOOK_URL_NORMAL,
)


class Notifier:
    """Build and send login check notification messages."""

    @staticmethod
    def _login_url():
        base_url = API_CONFIG.get("BASE_URL", "").rstrip("/")
        login_path = API_CONFIG.get("ENDPOINTS", {}).get("login", "")
        return f"{base_url}{login_path}"

    @staticmethod
    def build_login_template(result, report_path=None):
        result = result or {}
        success = bool(result.get("success"))
        now = datetime.now()
        status_text = "通过" if success else "异常"
        title = "登录检查执行通知" if success else "登录检查告警通知"
        responsible_person = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未配置")
        alarm_user_ids = REPORT_CONFIG.get("ALARM_USER_IDS", [])
        status_code = result.get("status_code", "")
        message = str(result.get("message", ""))

        lines = [
            title,
            "",
            f"> 环境：{ENV_TYPE}",
            f"> 结果：{status_text}",
            f"> 检查时间：{now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 负责人：{responsible_person}",
            f"> 接口：{Notifier._login_url()}",
            f"> HTTP状态码：{status_code}",
            "",
            "检查项",
            f"- B2B登录接口校验：{status_text}",
            "",
            "结果说明",
            message or "无",
        ]

        if report_path:
            lines.extend(["", f"报告文件：{report_path}"])

        if not success:
            at_text = " ".join(f"<@{user_id}>" for user_id in alarm_user_ids)
            lines.extend(["", "异常详情", message or "未获取到异常说明"])
            if at_text:
                lines.extend(["", f"提醒：{at_text}"])

        lines.extend(["", "【报告自动生成】"])
        return "\n".join(lines)

    @staticmethod
    def send_login_report(result, report_path=None, force=False, skip=False):
        if skip:
            return "skipped: --no-notify"

        success = bool((result or {}).get("success"))
        if success:
            enabled = ENABLE_NORMAL_NOTIFIER
            webhook_url = WEBHOOK_URL_NORMAL
            disabled_reason = "normal notifier switch is off"
        else:
            enabled = ENABLE_ALARM_NOTIFIER
            webhook_url = WEBHOOK_URL_ALARM
            disabled_reason = "alarm notifier switch is off"

        if not force and not enabled:
            return f"skipped: {disabled_reason}"
        if not webhook_url:
            return "skipped: webhook url is empty"

        content = Notifier.build_login_template(result, report_path=report_path)
        response = requests.post(
            webhook_url,
            json={"msgtype": "markdown", "markdown": {"content": content}},
            timeout=REQUEST_TIMEOUT_NOTIFIER,
            proxies={"http": None, "https": None},
        )
        response.raise_for_status()
        return f"sent: {response.status_code}"
