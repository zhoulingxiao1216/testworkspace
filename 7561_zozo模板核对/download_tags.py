#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests, json, sys, time, os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")

AUTH_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczpcL1wvc2FrdXJhZGsyLmNvbSIsImlhdCI6MTc3NzM3MDMxNSwiZGF0YSI6eyJpZCI6NzU2MSwibmFtZSI6Ilx1Nzk1ZVx1OGMzN1x1MzAwMFx1NTA2NVx1NWZkNyIsIm1haWwiOiJrYW1peWFAN2pld2VscnkuanAifSwic2NvcGVzIjoicm9sZV9hY2Nlc3MiLCJleHAiOjE3Nzg2NjYzMTV9.0P27wGTtuZVBI6P0ZKQqOssYNK0DFlex6z7nANXRAIY"
BASE_URL = "https://www.sakuradk2.com"
ORDER_ID = "7561260428241"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "authorization": AUTH_TOKEN,
    "content-type": "application/json",
    "currpath": "/user/agent/order_detail/",
    "origin": BASE_URL,
    "platform": "PC",
    "referer": f"{BASE_URL}/web_view/user/agent/order_detail/?orderId={ORDER_ID}",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
}
COOKIES = {
    "PHPSESSID": "mhod39q9jgm15ut12troeahdgc",
    "login_token": AUTH_TOKEN,
    "server_login_token": AUTH_TOKEN,
    "login_user_id": "7561"
}

OUT_DIR = r"d:\test_workspace\tag_images_0428"
os.makedirs(OUT_DIR, exist_ok=True)

def fetch_order_detail():
    url = f"{BASE_URL}/api_user/agent/orderDetail"
    r = requests.post(url, headers=HEADERS, cookies=COOKIES, json={"orderId": ORDER_ID}, timeout=30)
    r.raise_for_status()
    # Check if we get auth error
    data = r.json()
    if data.get("status") == 401:
        print(f"Auth Error: {data}")
        sys.exit(1)
    return data

def fetch_tag_info(item_id):
    url = f"{BASE_URL}/api_user/Pic_Brand/getOrderBrandTag"
    params = {"itemid": item_id, "type": 1, "orgPage": 1, "cusPage": 1, "searchText": ""}
    r = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def main():
    print("拉取订单详情...")
    data = fetch_order_detail()
    products = data.get("data", {}).get("lists", [])
    if not products:
        print("未找到商品或订单数据异常：", data)
        sys.exit(1)
    print(f"共 {len(products)} 个商品\n")

    mapping = []
    for i, p in enumerate(products, 1):
        oid = p["order_id"]
        ext_sku = p.get("order_ExternalID", "")

        if i > 1:
            time.sleep(0.2)
        
        try:
            tag_resp = fetch_tag_info(oid)
            td = tag_resp.get("data", {})
            tags_list = td.get("tags", [])
            
            if tags_list:
                tag = tags_list[0]
                pic_url = tag.get("pic_url", "")
                config_title = tag.get("config_title", "")
                
                img_path = os.path.join(OUT_DIR, f"{oid}_{ext_sku}.png")
                r2 = requests.get(pic_url, timeout=15)
                with open(img_path, "wb") as f:
                    f.write(r2.content)
                
                mapping.append({
                    "index": i,
                    "order_id": oid,
                    "sku": ext_sku,
                    "config_title": config_title,
                    "pic_url": pic_url,
                    "local_img": img_path,
                    "img_size": len(r2.content),
                })
            else:
                mapping.append({"index": i, "order_id": oid, "sku": ext_sku, "status": "NO_TAG"})
        except Exception as e:
            mapping.append({"index": i, "order_id": oid, "sku": ext_sku, "status": f"ERROR: {e}"})
        
        if i % 20 == 0:
            print(f"  进度: {i}/{len(products)}")

    # 保存映射
    with open(r"d:\test_workspace\tag_mapping_0428.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    ok_count = len([m for m in mapping if m.get("local_img")])
    print(f"\n完成! 已下载 {ok_count}/{len(products)} 张吊牌图片")
    print(f"映射表: tag_mapping_0428.json")
    print(f"图片目录: {OUT_DIR}")

if __name__ == "__main__":
    main()
