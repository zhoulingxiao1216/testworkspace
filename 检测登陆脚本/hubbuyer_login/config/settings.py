# -*- coding: utf-8 -*-
"""Prod-only settings for the standalone login check script."""

from config.data.login_data import ACCOUNTS_POOL
import config.api.prod as api_mod
import config.url.prod as url_mod


ENV_TYPE = "prod"

API_CONFIG = {
    "BASE_URL": api_mod.API_CONFIG.get("BASE_URL"),
    "url_B2B_pc": url_mod.B2B_PC_url,
    "url_B2B_h5": url_mod.B2B_H5_url,
    "url_D2C_pc": url_mod.D2C_PC_url,
    "url_AboutUs_pc": url_mod.url_AboutUs_pc,
    "url_AboutUs_h5": url_mod.url_AboutUs_h5,
    "url_ADMIN": getattr(url_mod, "ADMIN_url", "https://admin.hubbuyer.com/"),
    "ENDPOINTS": api_mod.API_CONFIG["ENDPOINTS"],
    "ACCOUNT_LIST": ACCOUNTS_POOL["prod"]["frontend"],
}

REQUEST_TIMEOUT_API = 25
REQUEST_TIMEOUT_NOTIFIER = 10

REPORT_CONFIG = {
    "RESPONSIBLE_PERSON": "周凌虓",
    "ALARM_USER_IDS": ["ZhouLingXiao"],
    "PROJECT_NAME": "Sakuradk2 自动化巡检系统",
    "SAVE_DIR": "reports",
}

# A群：全通关报告 Webhook 地址
ENABLE_NORMAL_NOTIFIER = False
WEBHOOK_URL_NORMAL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=74a91292-a1ac-49e1-b1df-7cea1f54588b"

# B群：故障报警 Webhook 地址
ENABLE_ALARM_NOTIFIER = False
WEBHOOK_URL_ALARM = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e28fa03c-3299-4ba7-bb51-e7de294a16d7"
