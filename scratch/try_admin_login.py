#!/usr/bin/env python3
"""
简单脚本：向后台登录接口发送 JSON 请求并打印响应。
用法：修改 `ACCOUNT` 与 `PASSWORD`，或通过命令行传入：
    python try_admin_login.py admin 123333
"""
import sys
import json
import requests

DEFAULT_ACCOUNT = "admin"
DEFAULT_PASSWORD = "123333"

def main():
    account = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ACCOUNT
    password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PASSWORD
    url = "https://hlc-admin.hubbuyer.com/admin/login/login"
    payload = {"account": account, "password": password}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    print(f"POST {url} -> payload={payload}")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        print("status:", r.status_code)
        try:
            print(json.dumps(r.json(), ensure_ascii=False, indent=2))
        except Exception:
            print(r.text)
    except Exception as e:
        print("request failed:", e)

if __name__ == '__main__':
    main()
