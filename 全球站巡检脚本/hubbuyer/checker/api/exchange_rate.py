# -*- coding: utf-8 -*-
# checker/api/exchange_rate.py
# 当日汇率检测：校验后台 USD / JPY 两项汇率是否已更新且有效
import json
import sys
import os
import requests
from datetime import datetime

# --- 初始化根路径 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import REQUEST_TIMEOUT_API, ENV_TYPE, API_CONFIG
from config.data.login_data import ACCOUNTS_POOL

# ── 常量配置 ────────────────────────────────────────────────────────
ADMIN_BASE_URL  = (API_CONFIG.get("BASE_URL") or "https://api.hubbuyer.com").rstrip("/")
ADMIN_WEB_URL   = (API_CONFIG.get("url_ADMIN") or "https://admin.hubbuyer.com/").rstrip("/")
LOGIN_PATH      = "/admin/login/login"
RATE_LIST_PATH  = "/admin/exRateConfig/list"
TARGET_CURRENCIES = ["USD", "JPY"]   # 需检测的货币

# 从配置文件动态读取当前环境的后台账号
_admin_cfg     = ACCOUNTS_POOL.get(ENV_TYPE, {}).get("admin", {})
ADMIN_ACCOUNT  = _admin_cfg.get("account", "")
ADMIN_PASSWORD = _admin_cfg.get("password", "")

BASE_HEADERS = {
    "content-type":   "application/json",
    "logintype":      "admin",
    "origin":         ADMIN_WEB_URL,
    "accept":         "application/json, text/plain, */*",
}

# ── 工具函数 ──────────────────────────────────────────────

def _admin_login():
    """后台登录，返回 login_token 字符串；失败时抛出异常"""
    url = ADMIN_BASE_URL + LOGIN_PATH
    resp = requests.post(
        url,
        headers=BASE_HEADERS,
        json={"account": ADMIN_ACCOUNT, "password": ADMIN_PASSWORD},
        timeout=REQUEST_TIMEOUT_API,
        proxies={"http": None, "https": None}
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 200:
        raise RuntimeError(f"后台登录失败: code={body.get('code')} msg={body.get('message')}")
    token = body.get("data", {}).get("login_token")
    if not token:
        raise RuntimeError("后台登录成功但未返回 login_token")
    return token


def _fetch_rates(token):
    """请求汇率列表，返回 ex_rate_config_data 数组"""
    url = ADMIN_BASE_URL + RATE_LIST_PATH
    headers = {**BASE_HEADERS, "authorization": token}
    resp = requests.post(
        url,
        headers=headers,
        json={"currency": "", "page": 1, "limit": 30},
        timeout=REQUEST_TIMEOUT_API,
        proxies={"http": None, "https": None}
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 200:
        raise RuntimeError(f"汇率接口返回异常: code={body.get('code')} msg={body.get('message')}")
    return body.get("data", {}).get("ex_rate_config_data", [])


# ── 主检测函数 ────────────────────────────────────────────

def run_exchange_rate_check(task_config=None):
    today = datetime.now().strftime("%Y-%m-%d")
    pass_items, fail_items = [], []

    try:
        # Step 1: 后台登录
        token = _admin_login()

        # Step 2: 获取汇率列表
        rate_list = _fetch_rates(token)

        # 构建 currency -> record 映射
        rate_map = {item.get("currency", "").upper(): item for item in rate_list}

        # Step 3: 逐项校验
        for currency in TARGET_CURRENCIES:
            record = rate_map.get(currency)
            if not record:
                fail_items.append(f"{currency}:未返回数据")
                continue

            bank_rate  = record.get("bank_rate")   # 第三方银行原始汇率
            rate       = record.get("rate")         # 全球站给客户的计算汇率
            updated_at = record.get("updated_at", "")

            bank_str = str(bank_rate) if bank_rate is not None else "N/A"
            rate_str = str(rate) if rate is not None else "N/A"
            label    = f"{currency}(银行:{bank_str} 全球站:{rate_str})"

            # ── 通过条件：银行汇率不为空且今日已更新 ──
            if bank_rate is None or str(bank_rate).strip() == "" or float(bank_rate) <= 0:
                fail_items.append(f"{label}:银行汇率未获取")
            elif updated_at != today:
                fail_items.append(f"{label}:更新日期不是今天({updated_at})")
            else:
                pass_items.append(label)

    except Exception as e:
        result = {
            "success": False,
            "message": f"执行异常: {type(e).__name__}: {str(e)}",
            "status_code": 500
        }
        print(json.dumps(result, ensure_ascii=False))
        return result

    # ── 汇总输出 ──
    all_ok = len(fail_items) == 0 and len(pass_items) == len(TARGET_CURRENCIES)
    parts = pass_items + fail_items
    message = " | ".join(parts) if parts else "无返回数据"

    result = {
        "success": all_ok,
        "message": message,
        "status_code": 200
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


run = run_exchange_rate_check


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
            run_exchange_rate_check(task_config=task_config)
            sys.exit(0)
        except (json.JSONDecodeError, ValueError):
            pass
    run_exchange_rate_check()
