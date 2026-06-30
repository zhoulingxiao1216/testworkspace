import re
import requests

r = requests.get("https://console.open.onebound.cn/console/?go=login&do=login", timeout=15)
text = r.text
print("status", r.status_code, "len", len(text))
for keyword in ["login", "password", "account", "do=", "ajax", "submit"]:
    idx = 0
    hits = 0
    while hits < 3:
        pos = text.lower().find(keyword.lower(), idx)
        if pos < 0:
            break
        snippet = text[max(0, pos - 80) : pos + 120].replace("\n", " ")
        print(f"[{keyword}] {snippet}")
        idx = pos + len(keyword)
        hits += 1

# try common login POST patterns without real creds
session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://console.open.onebound.cn/console/?go=login&do=login",
    }
)
tests = [
    ("POST form", "https://console.open.onebound.cn/console/?go=login&do=login", {"account": "test", "password": "test"}),
    ("POST user login", "https://console.open.onebound.cn/console/?go=user&do=login", {"account": "test", "password": "test"}),
    ("POST index login", "https://console.open.onebound.cn/console/?go=index&do=login", {"account": "test", "password": "test"}),
    ("POST login login", "https://console.open.onebound.cn/console/?go=login&do=submit", {"account": "test", "password": "test"}),
]
for name, url, data in tests:
    resp = session.post(url, data=data, timeout=15)
    body = resp.text.strip()
    print(name, "->", resp.status_code, "ctype", resp.headers.get("content-type", ""), "head", body[:120].replace("\n", " "))
    print(" set-cookie", resp.headers.get("set-cookie", "")[:120])
