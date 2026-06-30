import re
import requests

r = requests.get("https://console.open.onebound.cn/console/?go=login&do=login", timeout=15)
text = r.text
for m in re.finditer(r'name="([^"]+)"', text):
    print("name=", m.group(1))
for m in re.finditer(r"id=\"([^\"]+)\"", text):
    val = m.group(1)
    if any(k in val.lower() for k in ["user", "pass", "login", "account", "phone"]):
        print("id=", val)

session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://console.open.onebound.cn/console/?go=login&do=login",
        "origin": "https://console.open.onebound.cn",
    }
)
url = "https://console.open.onebound.cn/console/?go=login&do=login"
field_sets = [
    {"username": "test", "password": "test"},
    {"user_name": "test", "password": "test"},
    {"login_name": "test", "password": "test"},
    {"mobile": "test", "password": "test"},
    {"phone": "test", "password": "test"},
    {"account": "test", "password": "test"},
    {"user": "test", "pass": "test"},
]
for data in field_sets:
    resp = session.post(url, data=data, timeout=15)
    print(data, "->", resp.text[:200])
