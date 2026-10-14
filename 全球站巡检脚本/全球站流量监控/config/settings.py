# -*- coding: utf-8 -*-
import json
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_LOCAL_FILE = os.path.join(PROJECT_ROOT, "config", "secrets.local.json")


def _load_local_secrets():
    if not os.path.exists(SECRETS_LOCAL_FILE):
        return {}
    try:
        with open(SECRETS_LOCAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


ENV_TYPE = os.getenv("ENV_TYPE", "prod")

INSPECTION_SWITCHES = {
    "check_open1688_traffic": _env_bool("CHECK_OPEN1688_TRAFFIC", True),
}

INSPECTION_INTERVAL = int(os.getenv("INSPECTION_INTERVAL", "0"))
SCRIPT_RUNNER_TIMEOUT = int(os.getenv("SCRIPT_RUNNER_TIMEOUT", "180"))
REQUEST_TIMEOUT_NOTIFIER = int(os.getenv("REQUEST_TIMEOUT_NOTIFIER", "10"))

NODE_BIN = os.getenv("NODE_BIN", "node")
LOCAL_SECRETS = _load_local_secrets()

REPORT_CONFIG = {
    "PROJECT_NAME": "1688 开放平台应用流量监控",
    "RESPONSIBLE_PERSON": os.getenv("RESPONSIBLE_PERSON", "周凌虓"),
    "SAVE_DIR": "logs",
}

# 不在代码中保存 Webhook；宝塔计划任务里通过环境变量传入。
ENABLE_WECHAT_NOTIFIER = _env_bool(
    "MONITOR_NOTIFY_ENABLED",
    bool(LOCAL_SECRETS.get("monitor_notify_enabled", False)),
)
WEBHOOK_URL = os.getenv("MONITOR_WEBHOOK_URL") or LOCAL_SECRETS.get("monitor_webhook_url", "")
