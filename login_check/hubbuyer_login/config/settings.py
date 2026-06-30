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
    "PROJECT_NAME": "Hubbuyer",
    "SAVE_DIR": "reports",
}

# A群：全通关报告 Webhook 地址
ENABLE_NORMAL_NOTIFIER = True
WEBHOOK_URL_NORMAL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0e2cf7e5-c0be-403f-91d3-b98d66238f40"

# B群：故障报警 Webhook 地址
ENABLE_ALARM_NOTIFIER = True
WEBHOOK_URL_ALARM = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=ffc99f50-ae48-4abc-9c87-e5318772494c"
