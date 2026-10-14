# -*- coding: utf-8 -*-
import json
import urllib.request

from config.settings import ENABLE_WECHAT_NOTIFIER, REQUEST_TIMEOUT_NOTIFIER, WEBHOOK_URL


class Notifier:
    @staticmethod
    def _build_content(report_data):
        lines = []
        for item in report_data.values():
            message = str(item.get("message") or "").strip()
            if message:
                lines.append(message)
        return "\n".join(lines).strip()

    @staticmethod
    def send_wechat_report(report_data, is_all_pass):
        if not ENABLE_WECHAT_NOTIFIER or not WEBHOOK_URL or not report_data:
            return

        content = Notifier._build_content(report_data)
        if not content:
            return

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_NOTIFIER) as response:
                response.read()
        except Exception as e:
            print(f"微信推送失败: {type(e).__name__}: {e}")
