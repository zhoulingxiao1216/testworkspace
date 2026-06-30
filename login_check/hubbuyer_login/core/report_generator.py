# -*- coding: utf-8 -*-
"""Report generator for the prod login check."""

import json
from datetime import datetime
from pathlib import Path

from config.settings import API_CONFIG, ENV_TYPE, REPORT_CONFIG, REQUEST_TIMEOUT_API


class LoginReportGenerator:
    """Generate and save the standalone login check report."""

    def __init__(self, result, accounts=None, check_time=None):
        self.result = result or {}
        self.accounts = accounts
        self.check_time = check_time or datetime.now()

    @staticmethod
    def _project_root():
        return Path(__file__).resolve().parents[1]

    @staticmethod
    def _login_url():
        base_url = API_CONFIG.get("BASE_URL", "").rstrip("/")
        login_path = API_CONFIG.get("ENDPOINTS", {}).get("login", "")
        return f"{base_url}{login_path}"

    @staticmethod
    def _mask_account(account):
        if not account:
            return ""
        if "@" not in account:
            return account
        name, domain = account.split("@", 1)
        if len(name) <= 2:
            masked_name = name[:1] + "*"
        else:
            masked_name = name[:2] + "***" + name[-1:]
        return f"{masked_name}@{domain}"

    def _configured_accounts(self):
        if self.accounts is not None:
            return self.accounts
        return API_CONFIG.get("ACCOUNT_LIST", [])

    def _status_text(self):
        return "通过" if bool(self.result.get("success")) else "异常"

    def _timestamp(self):
        return self.check_time.strftime("%Y%m%d_%H%M%S")

    def _check_time_text(self):
        return self.check_time.strftime("%Y-%m-%d %H:%M:%S")

    def _reports_dir(self):
        save_dir_name = REPORT_CONFIG.get("SAVE_DIR", "reports")
        reports_dir = self._project_root() / save_dir_name
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir

    def _account_rows(self):
        accounts = self._configured_accounts()
        if not accounts:
            return ["| 未配置 | - | 未执行 |"]

        message = str(self.result.get("message", ""))
        rows = []
        for account in accounts:
            email = account.get("email") or account.get("mail") or "unknown"
            site = account.get("jump_site") or "-"
            if f"{email}:OK" in message:
                status = "通过"
            elif f"{email}:ERR" in message or f"{email}:异常" in message:
                status = "异常"
            else:
                status = "未匹配"
            rows.append(f"| {self._mask_account(email)} | {site} | {status} |")
        return rows

    def generate_report(self):
        success = bool(self.result.get("success"))
        status_text = self._status_text()
        responsible_person = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未配置")
        project_name = REPORT_CONFIG.get("PROJECT_NAME", "全球站登录检查")
        status_code = self.result.get("status_code", "")
        message = str(self.result.get("message", ""))

        lines = [
            f"# {project_name} - 登录检查报告",
            "",
            "## 执行摘要",
            f"- 环境: {ENV_TYPE}",
            f"- 结果: {status_text}",
            f"- 检查时间: {self._check_time_text()}",
            f"- 负责人: {responsible_person}",
            "",
            "## 接口信息",
            f"- Base URL: {API_CONFIG.get('BASE_URL', '')}",
            f"- 登录接口: {self._login_url()}",
            f"- 请求超时: {REQUEST_TIMEOUT_API}s",
            "",
            "## 检查结果",
            "| 检查项 | 结果 | HTTP状态码 | 说明 |",
            "| --- | --- | --- | --- |",
            f"| B2B登录接口校验 | {status_text} | {status_code} | {message} |",
            "",
            "## 账号明细",
            "| 账号 | 站点 | 结果 |",
            "| --- | --- | --- |",
            *self._account_rows(),
        ]

        if not success:
            lines.extend(
                [
                    "",
                    "## 异常详情",
                    message or "未获取到异常说明",
                ]
            )

        lines.extend(["", "【报告自动生成】"])
        return "\n".join(lines)

    def generate_json_report(self):
        return {
            "环境": ENV_TYPE,
            "结果": self._status_text(),
            "检查时间": self._check_time_text(),
        }

    def save_report(self, report_content, filename=None):
        if filename is None:
            filename = f"登录检查报告_{self._timestamp()}.md"

        file_path = self._reports_dir() / filename
        file_path.write_text(report_content, encoding="utf-8")
        return str(file_path)

    def save_json_report(self, json_content, filename=None):
        if filename is None:
            filename = f"登录检查报告_{self._timestamp()}.json"

        file_path = self._reports_dir() / filename
        file_path.write_text(
            json.dumps(json_content, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(file_path)

    def save_reports(self):
        md_path = self.save_report(self.generate_report())
        json_path = self.save_json_report(self.generate_json_report())
        return {"md": md_path, "json": json_path}
