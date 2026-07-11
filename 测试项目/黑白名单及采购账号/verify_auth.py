# -*- coding: utf-8 -*-
import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test_login(account, password, desc, ip):
    url = "https://test-api.hubbuyer.com/admin/login/login"
    
    payload = json.dumps({
      "account": account,
      "password": password
    })
    headers = {
      'accept': 'application/json, text/plain, */*',
      'accept-language': 'zh-CN,zh;q=0.9',
      'content-type': 'application/json',
      'logintype': 'admin',
      'origin': 'https://test-admin.hubbuyer.com',
      'priority': 'u=1, i',
      'referer': 'https://test-admin.hubbuyer.com/',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'x-forwarded-for': ip,
      'x-real-ip': ip
    }

    print(f"\n=======================")
    print(f"Testing [{desc}] - Account: {account} | Spoofing IP: {ip}")
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        status_code = response.status_code
        try:
            data = response.json()
            code = data.get("code")
            message = data.get("message")
        except:
            code = "N/A"
            message = response.text
            
        print(f"HTTP Status: {status_code} | Code: {code}")
        print(f"Server Message: {message}")
        if status_code == 200 and code == 200:
            print("=> 🟢 SUCCESS: Block bypassed / Whitelisted.")
        elif status_code == 200 and code == 40003:
            print("=> 🔴 INTERCEPTED: IP was blocked as unauthorized.")
        else:
            print("=> 🟡 OTHER Response")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    current_ip = "13.158.73.139"  # The provided IP
    # 1. 验证普通账号 (Should be INTERCEPTED if IP is missing from whitelist)
    test_login("test-khjl", "123456", "普通后台账号", current_ip)
    
    # 2. 验证拥有豁免权的授权账号 (Should be SUCCESS due to is_trusted=1)
    test_login("test-0420", "123456", "已鉴权管理员账号", current_ip)
