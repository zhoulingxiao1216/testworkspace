import streamlit as st
import requests
import json
import time
import os
import re
import cv2
import numpy as np
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR

from modules.sakura_auth_ui import render_admin_session_manager

st.set_page_config(page_title="SKU智能比对", page_icon="🏷️", layout="wide")

st.title("🏷️ SKU 智能比对 (OCR)")

# ── 常量 ─────────────────────────────────────────────────────
BASE_URL = "https://www.sakuradk2.com"
CONFIG_PATH = Path(__file__).parent.parent / "sku_accounts.json"


def create_direct_session() -> requests.Session:
    """Use direct network access; the local Windows proxy can be stale or closed."""
    session = requests.Session()
    session.trust_env = False
    return session


def direct_get(url, **kwargs):
    with create_direct_session() as session:
        return session.get(url, **kwargs)


def direct_post(url, **kwargs):
    with create_direct_session() as session:
        return session.post(url, **kwargs)


# ── 加载配置 ─────────────────────────────────────────────────
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)

# ── 通过管理员 Session 获取客户 Token ────────────────────────
def get_user_token(admin_sessid: str, uid: str) -> dict:
    """
    模拟后台 '进入会员中心' 操作:
    访问 /user/userShow?uid=XXX&type=1，用管理员的 PHPSESSID 获取客户的 login_token。
    """
    s = create_direct_session()
    s.cookies.set("PHPSESSID", admin_sessid, domain="sakuradk2.com")

    try:
        r = s.get(
            f"{BASE_URL}/user/userShow",
            params={"uid": uid, "type": 1},
            timeout=15,
            allow_redirects=False,
        )
    except requests.exceptions.ProxyError as e:
        return {"success": False, "error": "PROXY_ERROR", "detail": str(e)}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": "NETWORK_ERROR", "detail": str(e)}
    
    # 检查是否被重定向到了 manager/login（说明 admin session 过期）
    location = r.headers.get("Location", "")
    if "/manager/login" in location:
        return {"success": False, "error": "ADMIN_SESSION_EXPIRED"}
    
    # userShow 成功时会 302 到 /web_view/user/home，并且 Set-Cookie 里会带上客户 token
    # requests.Session 会自动收集这些 cookie
    login_token = s.cookies.get("login_token", "")
    new_sessid = s.cookies.get("PHPSESSID", admin_sessid)
    user_id = s.cookies.get("login_user_id", uid)
    
    if not login_token:
        return {"success": False, "error": "NO_TOKEN_RETURNED"}
    
    return {
        "success": True,
        "token": login_token,
        "sessid": new_sessid,
        "user_id": user_id,
    }


# ── 网络请求函数 ─────────────────────────────────────────────
def fetch_order_detail(order_id, headers, cookies):
    url = f"{BASE_URL}/api_user/agent/orderDetail"
    r = direct_post(url, headers=headers, cookies=cookies, json={"orderId": order_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != 200:
        msg = data.get("message", "") or data.get("msg", "")
        raise Exception(f"订单数据拉取失败: {msg} (status={data.get('status')})")
    return data

def fetch_tag_info(item_id, headers, cookies, type_param, api_path):
    url = f"{BASE_URL}{api_path}"
    params = {"itemid": item_id, "type": type_param, "orgPage": 1, "cusPage": 1, "searchText": ""}
    r = direct_get(url, headers=headers, cookies=cookies, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ── 加载配置并构建 UI ────────────────────────────────────────
config = load_config()
admin_sessid = config.get("admin_session", {}).get("PHPSESSID", "")
accounts = config.get("accounts", [])

col1, col2 = st.columns([1, 2])

with col1:
    # ── 管理员 Session 状态 ──
    admin_sessid = render_admin_session_manager(config)
    if not admin_sessid:
        st.stop()

    # ── 账号选择 ──
    st.markdown("---")
    st.subheader("👤 选择客户账号")
    account_labels = [a["label"] for a in accounts]
    selected_label = st.selectbox("客户账号", account_labels)
    selected_account = next(a for a in accounts if a["label"] == selected_label)
    uid = selected_account["uid"]
    
    st.info(f"当前客户：**{selected_label}** (UID: {uid})")

    # ── 订单号 ──
    st.markdown("---")
    st.subheader("🔍 比对任务")
    order_id = st.text_input("输入订单号 (Order ID)", placeholder="例如: 816026043058")
    start_btn = st.button("🚀 开始拉取与比对", type="primary", use_container_width=True, disabled=not order_id)
    mock_btn = st.button("🧪 Mock 测试（22匹配 + 4不匹配）", use_container_width=True)

with col2:
    st.subheader("📊 比对结果看板")
    result_container = st.empty()
    progress_bar = st.progress(0, text="等待开始...")
    log_container = st.container()


# ── 执行逻辑 ─────────────────────────────────────────────────
if start_btn and order_id:
    api_path = selected_account["api_path"]
    type_param = selected_account["type_param"]
    
    # Step 0: 获取客户 Token
    progress_bar.progress(0.02, text="0/3 正在获取客户授权 Token...")
    
    # 缓存机制：避免每次都重新获取
    cache_key = f"user_token_{uid}"
    token_info = st.session_state.get(cache_key)
    
    if not token_info:
        token_result = get_user_token(admin_sessid, uid)
        
        if not token_result["success"]:
            if token_result["error"] == "ADMIN_SESSION_EXPIRED":
                st.error(
                    "🔴 **管理员 Session 已过期！**\n\n"
                    "请按以下步骤更新：\n"
                    "1. 在浏览器中重新登录 Sakura 后台管理系统\n"
                    "2. 从 Cookie 中复制新的 `PHPSESSID`\n"
                    "3. 点击左侧的「🔄 更新管理员 Session」按钮粘贴新值\n"
                )
            elif token_result["error"] == "PROXY_ERROR":
                st.error(
                    "🔴 **网络代理异常，无法获取客户 Token。**\n\n"
                    "程序已改为直连 Sakura，但当前运行进程仍返回代理错误。"
                    "请重启 Streamlit 后重试。\n\n"
                    f"错误详情：{token_result.get('detail', '')}"
                )
            elif token_result["error"] == "NETWORK_ERROR":
                st.error(
                    "🔴 **网络请求失败，无法获取客户 Token。**\n\n"
                    "请确认本机可以访问 Sakura 后台域名，并检查管理员 Session 是否仍有效。\n\n"
                    f"错误详情：{token_result.get('detail', '')}"
                )
            else:
                st.error(f"获取客户 Token 失败：{token_result['error']}\n\n可能是管理员 Session 已过期，请更新。")
            progress_bar.empty()
            st.stop()
        
        token_info = token_result
        st.session_state[cache_key] = token_info

    current_token = token_info["token"]
    current_sessid = token_info["sessid"]
    user_id = token_info.get("user_id", uid)

    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "authorization": current_token,
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }
    COOKIES = {
        "PHPSESSID": current_sessid,
        "login_token": current_token,
        "server_login_token": current_token,
        "login_user_id": user_id,
    }

    # Setup temp dir
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", f"temp_images_{order_id}")
    temp_dir = os.path.normpath(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        progress_bar.progress(0.05, text="1/3 正在拉取订单详情...")
        data = fetch_order_detail(order_id, HEADERS, COOKIES)
        products_data = data.get("data", {})
        products = products_data.get("lists", []) if isinstance(products_data, dict) else []

        if not products:
            # 可能是 token 过期，清除缓存让下次重新获取
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.error("未找到商品或订单数据为空！可能是客户 Token 已失效，请再试一次。如果仍然失败请更新管理员 Session。")
            progress_bar.empty()
            st.stop()

        total_products = len(products)
        mapping = []

        with log_container:
            st.info(f"成功获取订单详情，共包含 **{total_products}** 个商品。准备下载贴纸/吊牌...")

        for i, p in enumerate(products, 1):
            progress_bar.progress(0.05 + 0.45 * (i / total_products), text=f"2/3 正在下载图片 ({i}/{total_products})...")
            oid = p["order_id"]
            ext_sku = p.get("order_ExternalID", "")
            time.sleep(0.1)

            try:
                tag_resp = fetch_tag_info(oid, HEADERS, COOKIES, type_param, api_path)
                td = tag_resp.get("data", {})
                tags_list = td.get("tags", [])

                if tags_list:
                    pic_url = tags_list[0].get("pic_url", "")
                    img_path = os.path.join(temp_dir, f"{oid}_{ext_sku}.png")
                    r2 = direct_get(pic_url, timeout=15)
                    with open(img_path, "wb") as f:
                        f.write(r2.content)
                    mapping.append({"order_id": oid, "sku": ext_sku, "local_img": img_path})
                else:
                    mapping.append({"order_id": oid, "sku": ext_sku, "status": "NO_TAG"})
            except Exception as e:
                mapping.append({"order_id": oid, "sku": ext_sku, "status": f"ERROR: {e}"})

        # Start OCR Verification
        progress_bar.progress(0.5, text="3/3 开始 OCR 智能识别比对...")
        ocr = RapidOCR()

        mismatches = []
        matches = []
        errors = []

        for i, m in enumerate(mapping, 1):
            progress_bar.progress(0.5 + 0.5 * (i / total_products), text=f"3/3 OCR 比对中 ({i}/{total_products})...")
            oid = m.get("order_id", "?")
            expected_sku = m.get("sku", "")
            img_path = m.get("local_img", "")

            if not img_path or not os.path.exists(img_path):
                errors.append({"序号": i, "期望SKU": expected_sku, "异常原因": m.get("status", "no image")})
                continue

            try:
                img_array = np.fromfile(img_path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is None:
                    errors.append({"序号": i, "期望SKU": expected_sku, "异常原因": "图片加载失败"})
                    continue
                result, _ = ocr(img)
            except Exception as e:
                errors.append({"序号": i, "期望SKU": expected_sku, "异常原因": str(e)})
                continue

            if not result:
                errors.append({"序号": i, "期望SKU": expected_sku, "异常原因": "OCR 未识别到文字"})
                continue

            all_text = [item[1] for item in result]

            found_sku = ""
            for text in all_text:
                text_clean = text.strip()
                if re.match(r'^[a-z0-9]+-[a-z0-9]+-', text_clean, re.IGNORECASE):
                    found_sku = text_clean
                    break

            if not found_sku:
                for text in all_text:
                    text_clean = text.strip()
                    if any(text_clean.lower().startswith(p) for p in ['sbg-', 'bdo-', 'ar-', '7j-', 'fl-']):
                        found_sku = text_clean
                        break

            if not found_sku:
                errors.append({"序号": i, "期望SKU": expected_sku, "异常原因": f"未找到SKU格式文本: {all_text[:3]}"})
                continue

            if found_sku.lower() == expected_sku.lower():
                matches.append({"序号": i, "order_id": oid, "期望SKU": expected_sku, "OCR识别SKU": found_sku})
            else:
                mismatches.append({"序号": i, "期望SKU": expected_sku, "OCR识别SKU": found_sku, "OCR原始文本": str(all_text[:3])})

        progress_bar.progress(1.0, text="比对完成！")

        # Display Results
        with result_container:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("总计数量", total_products)
            m2.metric("✅ 匹配成功", len(matches))
            m3.metric("❌ 匹配失败", len(mismatches))
            m4.metric("⚠️ 获取/识别异常", len(errors))

        with log_container:
            if mismatches:
                st.error("以下商品 SKU 与贴纸/吊牌不匹配：")
                st.dataframe(mismatches, use_container_width=True, hide_index=True)
            if errors:
                st.warning("以下商品在下载或识别时出现异常：")
                st.dataframe(errors, use_container_width=True, hide_index=True)

            if len(matches) == total_products and total_products > 0:
                st.success("🎉 全部商品 SKU 核对通过，完美匹配！")
                
                # 随机抽取 5 个展示图片，供业务抽查
                import random
                sample_size = min(5, len(matches))
                samples = random.sample(matches, sample_size)
                
                st.markdown("---")
                st.markdown(f"🔎 **随机抽检 {sample_size} 项**（请肉眼核对图片上的 SKU 与系统 SKU 是否一致）")
                
                # 构建 order_id -> img_path 的映射
                img_map = {m["order_id"]: m.get("local_img", "") for m in mapping if m.get("local_img")}
                
                for s_item in samples:
                    oid = s_item["order_id"]
                    sku = s_item["期望SKU"]
                    img_path = img_map.get(oid, "")
                    
                    col_img, col_info = st.columns([2, 1])
                    with col_info:
                        st.markdown(f"**第 {s_item['序号']} 项**")
                        st.markdown(f"**系统 SKU:** `{sku}`")
                        st.markdown(f"**OCR 识别:** `{s_item.get('OCR识别SKU', '')}`")
                        if sku.lower() == s_item.get("OCR识别SKU", "").lower():
                            st.success("✅ 一致")
                        else:
                            st.error("❌ 不一致")
                    with col_img:
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, caption=f"{sku}", use_container_width=True)
                        else:
                            st.warning("图片未找到")
                    st.markdown("---")

    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 401:
            # Token 过期，清缓存
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.error(
                "🔴 **客户 Token 已过期！**\n\n"
                "请再次点击「开始拉取与比对」按钮重试。\n"
                "如果反复失败，请更新管理员 Session。"
            )
        else:
            st.error(f"执行过程中发生异常: {e}")
        progress_bar.empty()
    except Exception as e:
        st.error(f"执行过程中发生异常: {e}")
        progress_bar.empty()

# ── Mock 测试逻辑 ────────────────────────────────────────────
if mock_btn:
    import random
    mock_skus = [
        "FL-1687-F-BE", "FL-1687-F-IV", "FL-1687-F-BK", "FL-1686-L-BK",
        "FL-1686-M-BK", "FL-1686-L-IV", "FL-1686-M-IV", "FL-1685-L-BK",
        "FL-1685-M-BK", "FL-1685-L-BE", "FL-1685-M-BE", "FL-1684-F-BK",
        "FL-1684-F-GRE", "FL-1683-L-WHBK", "FL-1683-M-WHBK", "FL-1682-L-BK",
        "FL-1682-M-BK", "FL-1681-F-BK", "FL-1680-L-BK", "FL-1680-M-BK",
        "FL-1680-L-BE", "FL-1680-M-BE", "FL-1679-L-BE", "FL-1679-M-BE",
        "FL-1679-L-BK", "FL-1679-M-BK",
    ]
    total_products = 26
    mismatch_indices = random.sample(range(total_products), 4)
    
    matches = []
    mismatches = []
    
    for idx in range(total_products):
        progress_bar.progress((idx + 1) / total_products, text=f"Mock 比对中 ({idx+1}/{total_products})...")
        time.sleep(0.05)
        sku = mock_skus[idx]
        oid = 1330871 - idx
        
        if idx in mismatch_indices:
            # 模拟 OCR 识别错误：把最后一段改掉
            parts = sku.rsplit("-", 1)
            wrong_sku = parts[0] + "-XX" if len(parts) > 1 else sku + "-ERR"
            mismatches.append({
                "order_id": oid,
                "expected_sku": sku,
                "actual_sku": wrong_sku,
                "ocr_texts": str([wrong_sku, "FLEUR LABEL", "Made in China"])
            })
        else:
            matches.append({"order_id": oid, "expected_sku": sku, "actual_sku": sku})
    
    progress_bar.progress(1.0, text="Mock 比对完成！")
    
    with result_container:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("总计数量", total_products)
        m2.metric("✅ 匹配成功", len(matches))
        m3.metric("❌ 匹配失败", len(mismatches))
        m4.metric("⚠️ 获取/识别异常", 0)
    
    with log_container:
        if mismatches:
            st.error("以下商品 SKU 与贴纸/吊牌不匹配：")
            st.dataframe(mismatches, use_container_width=True)
        st.info(f"ℹ️ 以上为 Mock 数据，非真实比对结果。")
