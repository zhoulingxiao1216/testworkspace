# -*- coding: utf-8 -*-
"""
全球站 B2B 链路压测 — Locust 主文件

默认模型更贴近“在线用户”：
    浏览商品 -> 部分用户加购 -> 少量用户提交自助报价单

启动示例:
    # Web UI 模式
    locust -f locustfile.py

    # 100 用户链路压测
    locust -f locustfile.py --headless -u 100 -r 10 -t 30m

    # 只跑下单链路
    locust -f locustfile.py --headless -u 50 -r 5 -t 10m --tags journey submit_order
"""
import copy
import json
import os
import random
import sys
import threading
import time

from locust import LoadTestShape, User, between, events, tag, task
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 路径初始化
# ==========================================
PERFORMANCE_ROOT = os.path.dirname(os.path.abspath(__file__))
if PERFORMANCE_ROOT not in sys.path:
    sys.path.insert(0, PERFORMANCE_ROOT)

# --- 从 config/ 加载所有配置（规则分离、账号分离、开关分离） ---
from config.settings import (
    ACCOUNT_PICK_STRATEGY,
    API_CONFIG,
    AUTH_BUYER_FIXED_COUNT,
    B2B_SITE_URL,
    BROWSE_STEPS_PER_JOURNEY,
    CART_LIST_RETRY_TIMES,
    CART_LIST_RETRY_WAIT,
    ENV_TYPE,
    FJX_SITE_URL,
    GUEST_TASK_WEIGHTS,
    GUEST_USER_WEIGHT,
    PAGE_VISIT_URLS,
    GUEST_PAGE_CHECKS,
    AUTH_PAGE_CHECKS,
    PAGE_TITLE_KEYWORD,
    STRESS_ENABLE_FULL_QUOTE_FLOW,
    STRESS_ENABLE_PAGE_CHECK,
    STRESS_ENABLE_QUOTE_DOWNLOAD,
    STRESS_QUOTE_DOWNLOAD_LANGUAGE,
    STRESS_ENABLE_TAOBAO_ADD_CART,
    STRESS_ENABLE_TAOBAO_DETAIL,
    STRESS_ENABLE_TAOBAO_KEYWORD,
    STRESS_LOGISTICS_CONFIG_ID,
    STRESS_QUOTE_TYPE,
    STRESS_REQUEST_TIMEOUT,
    STRESS_SWITCHES,
    STRESS_REAL_SPAWN_RATE,
    STRESS_RUN_TIME,
    STRESS_RUN_TIME_SECONDS,
    STRESS_USE_SPLIT_LOAD_SHAPE,
    STRESS_VIRTUAL_SPAWN_RATE,
    SUBMIT_ORDER_MAX_CART_ITEMS,
    TASK_WEIGHTS,
    TOKEN_COOKIE_NAME,
    USER_WAIT_MAX,
    USER_WAIT_MIN,
    VIRTUAL_USER_COUNT,
    CookieManager,
    TOKEN_DIR,
    get_base_headers,
    get_b2b_headers,
    get_b2b_img_search_headers,
)
from config.data.payloads import (
    ADD_CART_DATA,
    B2B_ADDON_DATA,
    IMG_SEARCH_DATA,
    KEYWORD_SEARCH_DATA,
    SUBMIT_ORDER_DATA,
)
from config.data.stress_accounts import STRESS_ACCOUNTS_POOL
from config.rules_loader import (
    extract_response_detail,
    get_assertion_rules,
    load_rules,
    verify_download_response,
    verify_response,
)


# ==========================================
# 基础工具
# ==========================================

def _get_base_url():
    return API_CONFIG.get("BASE_URL", "").rstrip("/")


def _get_endpoints():
    return API_CONFIG.get("ENDPOINTS", {})


def _get_accounts():
    accounts = STRESS_ACCOUNTS_POOL.get(ENV_TYPE, {}).get("frontend", [])
    selected_emails = [
        item.strip().lower()
        for item in os.getenv("STRESS_ACCOUNT_EMAILS", "").split(",")
        if item.strip()
    ]
    if not selected_emails:
        return accounts

    selected_set = set(selected_emails)
    return [
        account for account in accounts
        if (account.get("email") or account.get("mail", "")).strip().lower() in selected_set
    ]


def _clean_token(token):
    return (token or "").replace("Bearer ", "").strip()


def _build_b2b_cookie(token):
    clean_jwt = _clean_token(token)
    if not clean_jwt:
        return ""
    return (
        "PHPSESSID=qokjm6u9opg4qoo68pn3q48g2d; "
        f"{TOKEN_COOKIE_NAME}={clean_jwt}; "
        f"server_login_token={clean_jwt}; "
        f"loginToken={clean_jwt}; "
        f"login_token={clean_jwt}; "
        "Hm_lvt_6a2d0dadf560f4632634bc304b87a5dd=1768350161"
    )


def _get_b2b_cookie(email, token):
    # 优先使用本用户当前 token 组 Cookie，避免高并发时读到共享文件里的旧 token。
    cookie = _build_b2b_cookie(token)
    if cookie:
        return cookie
    return CookieManager.get_b2b_cookie(email)


def _absolute_url(base_url, endpoint):
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"{base_url}{endpoint}"


def _copy_payload(data):
    return copy.deepcopy(data) if data else {}


# ==========================================
# 账号与 Token 缓存
# ==========================================
_account_lock = threading.Lock()
_account_cursor = 0
_token_cache = {}


def _pick_account(accounts):
    global _account_cursor
    if not accounts:
        return {}

    if ACCOUNT_PICK_STRATEGY == "random":
        return random.choice(accounts)

    with _account_lock:
        account = accounts[_account_cursor % len(accounts)]
        _account_cursor += 1
        return account


def _load_tokens_from_disk():
    token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _get_token(email):
    global _token_cache
    if not _token_cache:
        _token_cache = _load_tokens_from_disk()
    token = _token_cache.get(email, "")
    if token:
        return token
    for key, value in _token_cache.items():
        if key.strip().lower() == email.strip().lower():
            return value
    return ""


def _set_token(email, token):
    global _token_cache
    if email and token:
        _token_cache[email] = token


# ==========================================
# Locust 事件上报
# ==========================================
_FAILURE_DETAIL_LOCK = threading.Lock()


def _truncate_response_body(body, max_len=500):
    if body is None:
        return ""
    if isinstance(body, dict):
        text = json.dumps(body, ensure_ascii=False)
    else:
        text = str(body)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_failure_exception(account, err, body=None, http_status=None):
    acct = (account or "未知").strip() or "未知"
    main_err = (err or "").strip()
    if http_status and not main_err:
        main_err = f"HTTP {http_status}"

    detail = extract_response_detail(body) if isinstance(body, dict) else ""
    parts = [f"[账号:{acct}]"]
    if main_err:
        parts.append(main_err)
    if detail and detail not in main_err:
        parts.append(f"详情:{detail}")
    return " ".join(parts)


def _append_failure_detail(record):
    path = os.getenv("STRESS_FAILURE_DETAIL_PATH", "").strip()
    if not path:
        return
    try:
        with _FAILURE_DETAIL_LOCK:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _reset_failure_detail_log():
    path = os.getenv("STRESS_FAILURE_DETAIL_PATH", "").strip()
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8"):
            pass
    except Exception:
        pass


def _fire_event(
    request_type,
    name,
    response_time,
    response_length,
    exception=None,
    account=None,
    response_body=None,
    http_status=None,
    url="",
):
    formatted_exception = exception
    if exception is not None:
        formatted_exception = _format_failure_exception(
            account,
            exception,
            response_body,
            http_status,
        )
        _append_failure_detail(
            {
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": request_type,
                "name": name,
                "account": (account or "未知").strip() or "未知",
                "error": formatted_exception,
                "url": url,
                "http_status": http_status,
                "response": _truncate_response_body(response_body),
            }
        )

    events.request.fire(
        request_type=request_type,
        name=name,
        response_time=response_time,
        response_length=response_length,
        exception=formatted_exception,
    )


# ==========================================
# 前台页面级检查（SPA 文档级：状态码 + 标题关键字断言）
# ==========================================
_PAGE_BROWSER_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    ),
}


def _perform_page_check(session, name, url, title_keyword="", extra_headers=None, account="虚拟访客"):
    """GET 前台页面，校验：1) HTTP 2xx/3xx；2) 命中标题关键字（防白屏/降级）。"""
    headers = dict(_PAGE_BROWSER_HEADERS)
    if extra_headers:
        headers.update(extra_headers)

    start = time.perf_counter()
    try:
        resp = session.get(
            url,
            headers=headers,
            timeout=STRESS_REQUEST_TIMEOUT,
            verify=False,
            proxies={"http": None, "https": None},
        )
        elapsed = (time.perf_counter() - start) * 1000
        length = len(resp.content)

        if not (200 <= resp.status_code < 400):
            _fire_event(
                "GET", name, elapsed, length,
                exception=f"HTTP {resp.status_code}",
                account=account,
                http_status=resp.status_code,
                url=url,
            )
            return False

        if title_keyword and title_keyword not in resp.text:
            _fire_event(
                "GET", name, elapsed, length,
                exception=f"标题缺失关键字，疑似白屏/降级（期望含『{title_keyword}』）",
                account=account,
                http_status=resp.status_code,
                url=url,
            )
            return False

        _fire_event("GET", name, elapsed, length)
        return True
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        _fire_event("GET", name, elapsed, 0, exception=str(e), account=account, url=url)
        return False


def _build_page_list(page_checks):
    """将 [{name, path}] 配置转为携带完整 URL 的页面清单。"""
    pages = []
    for item in page_checks or []:
        path = item.get("path", "")
        if not path:
            continue
        pages.append({"name": item.get("name") or path, "url": f"{B2B_SITE_URL}{path}"})
    return pages


# ==========================================
# 响应提取
# ==========================================
def _extract_cart_ids(response_json):
    """参考巡检 B2B_Addon.py：从 data.seller_data[].data[].id 提取购物车明细 ID。"""
    data = response_json.get("data", {}) if isinstance(response_json, dict) else {}
    seller_data = data.get("seller_data", [])

    if isinstance(seller_data, dict):
        seller_data = seller_data.get("data", []) if "data" in seller_data else [seller_data]
    if not isinstance(seller_data, list):
        seller_data = []

    ids = []
    for seller in seller_data:
        if not isinstance(seller, dict):
            continue
        items = seller.get("data", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(item.get("id"))
    return ids


def _extract_quote_no(response_json):
    if not isinstance(response_json, dict):
        return ""
    data = response_json.get("data", {})
    if isinstance(data, dict):
        return data.get("quote_no", "") or data.get("quoteNo", "") or data.get("order_no", "")
    return ""


def _normalize_cart_detail_ids(cart_ids):
    """统一购物车明细 ID：返回 (字符串列表, 整数列表)。"""
    str_ids = []
    int_ids = []
    for cart_id in cart_ids or []:
        if cart_id in (None, ""):
            continue
        str_ids.append(str(cart_id))
        try:
            int_ids.append(int(cart_id))
        except (TypeError, ValueError):
            int_ids.append(cart_id)
    return str_ids, int_ids


def _get_fjx_headers(token, cookie, currency="JPY", language="japanese", nation="Japan"):
    """FJX iframe 附加项接口：使用 userlogintoken + main-fjx origin。"""
    clean_token = _clean_token(token)
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "currency": currency,
        "language": language,
        "nation": nation,
        "origin": FJX_SITE_URL,
        "referer": f"{FJX_SITE_URL}/",
        "userlogintoken": clean_token,
        "Cookie": cookie,
    }


def _get_quote_step2_headers(token, cookie, currency="JPY", language="japanese", nation="Japan"):
    """Step2 / quote/create：B2B 主站 + authorization。"""
    headers = get_b2b_headers(B2B_SITE_URL, token, cookie, currency=currency, language=language, nation=nation)
    headers.update({
        "origin": B2B_SITE_URL,
        "referer": f"{B2B_SITE_URL}/",
        "logintype": "user",
        "rate": "24.75",
        "withcredentials": "true",
    })
    return headers


def _is_enabled_fjx_item(item):
    return isinstance(item, dict) and item.get("uuid") and item.get("status", 200) == 200


def _fjx_language_text(value):
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if isinstance(v, (str, int, float)))
    if isinstance(value, list):
        return " ".join(_fjx_language_text(item) for item in value)
    return str(value or "")


def _fjx_item_search_text(group, item):
    fields = [
        group.get("name_language"),
        item.get("name_language"),
        item.get("tip_language"),
        item.get("before_language"),
        item.get("after_language"),
    ]
    return " ".join(_fjx_language_text(field) for field in fields).lower()


def _pick_first_fjx_uuid(groups, keyword_groups):
    for keywords in keyword_groups:
        for group in groups:
            for item in group.get("fjx_config_data", []):
                if not _is_enabled_fjx_item(item):
                    continue
                text = _fjx_item_search_text(group, item)
                if all(keyword.lower() in text for keyword in keywords):
                    return item["uuid"]
    return None


def _parse_runtime_fjx_selection(body):
    """从 getCheckFjxList 响应解析检品/附加项 UUID（参考巡检 B2B_Addon.py）。"""
    data = body.get("data", {}) if isinstance(body, dict) else {}
    check_items = [item for item in data.get("check_data", []) if _is_enabled_fjx_item(item)]
    if not check_items:
        return "", [], []

    groups = data.get("fjx_data", [])
    selected_fjx = []
    preferred_uuid_rules = [
        [["贴纸"], ["sticker"]],
        [["fba"], ["opp", "四角"], ["4-fold"]],
    ]
    for keyword_groups in preferred_uuid_rules:
        uuid = _pick_first_fjx_uuid(groups, keyword_groups)
        if uuid and uuid not in selected_fjx:
            selected_fjx.append(uuid)

    if not selected_fjx:
        for group in groups:
            for item in group.get("fjx_config_data", []):
                if _is_enabled_fjx_item(item) and not item.get("is_design"):
                    selected_fjx.append(item["uuid"])
                    break
            if selected_fjx:
                break

    return check_items[0]["uuid"], selected_fjx, []


def _iter_dicts(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from _iter_dicts(value)
    elif isinstance(data, list):
        for value in data:
            yield from _iter_dicts(value)


# ==========================================
# 搜索/详情/加购：商品 ID 与列表提取
# ==========================================
_SEARCH_ITEM_ID_KEYS = {
    "1688": ("offerId", "offer_id", "item_id"),
    "taobao": ("item_id", "itemId", "ItemID", "num_iid", "numIid", "id", "offer_id"),
}
_SEARCH_LIST_KEYS = ("data", "items", "list", "records", "result")


def _get_search_item_id(item, source):
    if not isinstance(item, dict):
        return ""
    for key in _SEARCH_ITEM_ID_KEYS.get(source, ("item_id",)):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _extract_search_items(response_json, source):
    """从关键词搜索响应中提取商品列表（1688 用 offerId，淘宝兼容多字段）。"""
    if not isinstance(response_json, dict):
        return []

    data = response_json.get("data", {})
    inner = data.get("data", {}) if isinstance(data, dict) else {}
    if isinstance(inner, dict):
        for list_key in _SEARCH_LIST_KEYS:
            items = inner.get(list_key)
            if not isinstance(items, list) or not items:
                continue
            result = []
            seen = set()
            for item in items:
                item_id = _get_search_item_id(item, source)
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                result.append(item)
            if result:
                return result

    # 兜底：深度遍历（兼容非标准嵌套）
    item_keys = _SEARCH_ITEM_ID_KEYS.get(source, ("item_id",))
    seen = set()
    items = []
    for item in _iter_dicts(response_json):
        item_id = _get_search_item_id(item, source)
        if not item_id or item_id in seen:
            continue
        if not any(key in item for key in item_keys):
            continue
        seen.add(item_id)
        items.append(item)
    return items


def _get_item_url(source, item_id):
    if source == "taobao":
        return f"https://item.taobao.com/item.htm?id={item_id}"
    return f"https://detail.1688.com/offer/{item_id}.html"


def _get_detail_endpoint(source):
    if source == "taobao":
        return "/api_tb/product/detail"
    return "/api_ali/product/detail"


def _enabled_keyword_sources():
    sources = ["1688"]
    if STRESS_ENABLE_TAOBAO_KEYWORD:
        sources.append("taobao")
    return sources


def _resolve_search_source(source=None):
    enabled = _enabled_keyword_sources()
    if source in enabled:
        return source
    if source == "taobao" and "1688" in enabled:
        return "1688"
    return random.choice(enabled)


def _enabled_add_cart_sources():
    sources = ["1688"]
    if STRESS_ENABLE_TAOBAO_ADD_CART:
        sources.append("taobao")
    return sources


def _enabled_dynamic_add_cart_sources():
    sources = ["1688"]
    if (
        STRESS_ENABLE_TAOBAO_ADD_CART
        and STRESS_ENABLE_TAOBAO_KEYWORD
        and STRESS_ENABLE_TAOBAO_DETAIL
    ):
        sources.append("taobao")
    return sources


def _to_int(value, default=0):
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _build_add_cart_payload_from_detail(source, item_id, detail_body):
    inner = detail_body.get("data", {}).get("data", {}) if isinstance(detail_body, dict) else {}
    if not isinstance(inner, dict):
        return {}

    product_index_uuid = str(inner.get("product_index_uuid") or inner.get("uuid") or "")
    sku_list = inner.get("productSkuInfos") or inner.get("skuInfos") or []
    if not product_index_uuid or not isinstance(sku_list, list):
        return {}

    min_order_quantity = _to_int(
        inner.get("minOrderQuantity") or inner.get("min_order_quantity"),
        1,
    )
    quantity = max(1, min_order_quantity)

    for sku in sku_list:
        if not isinstance(sku, dict):
            continue
        sku_id = sku.get("skuId") or sku.get("sku_id")
        spec_id = sku.get("specId") or sku.get("spec_id")
        amount_on_sale = sku.get("amountOnSale")
        if amount_on_sale is not None and _to_int(amount_on_sale, 0) <= 0:
            continue
        if not sku_id or not spec_id:
            continue
        # 1688：后端 add1688 在 DetailService::getBuyPriceSkuInfo 强依赖 sku.price；
        # 部分商品仅有 consignPrice/fenxiaoPriceInfo，缺 price 会触发 code=500。
        if source == "1688" and sku.get("price") in (None, ""):
            continue
        return {
            "product_index_uuid": product_index_uuid,
            "item_id": str(item_id),
            "platform": "pc",
            "goods_info": [
                {
                    "spec_id": str(spec_id),
                    "sku_id": sku_id,
                    "quantity": quantity,
                }
            ],
            "_item_url": _get_item_url(source, item_id),
        }
    return {}


# ==========================================
# 启动日志
# ==========================================
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    _reset_failure_detail_log()
    accounts = _get_accounts()
    print("")
    print(f"{'=' * 60}")
    print(f"压测环境: {ENV_TYPE.upper()}")
    print(f"   API域名:  {_get_base_url()}")
    print(f"   B2B站点:  {B2B_SITE_URL}")
    print(f"   FJX站点:  {FJX_SITE_URL}")
    print(f"   Token名:  {TOKEN_COOKIE_NAME}")
    print(f"   完整报价链路: {'开启' if STRESS_ENABLE_FULL_QUOTE_FLOW else '关闭（简化 quote/create）'}")
    print(f"   淘宝关键词搜索: {'开启' if STRESS_ENABLE_TAOBAO_KEYWORD else '关闭'}")
    print(f"   淘宝详情页接口: {'开启' if STRESS_ENABLE_TAOBAO_DETAIL else '关闭'}")
    print(f"   淘宝商品加购: {'开启' if STRESS_ENABLE_TAOBAO_ADD_CART else '关闭'}")
    print(f"   报价单下载检查: {'开启(下单后下载)' if STRESS_ENABLE_QUOTE_DOWNLOAD else '关闭'}")
    print(f"   账号数:   {len(accounts)}（{ACCOUNT_PICK_STRATEGY} 分配）")
    print(f"   用户模型: 真实账号用户固定 {AUTH_BUYER_FIXED_COUNT} 个，虚拟用户 {VIRTUAL_USER_COUNT} 个")
    if STRESS_USE_SPLIT_LOAD_SHAPE:
        print(f"   加载策略: 真实账号 {STRESS_REAL_SPAWN_RATE}/s → 虚拟用户 {STRESS_VIRTUAL_SPAWN_RATE}/s")
        print(f"   压测时长: {STRESS_RUN_TIME} ({STRESS_RUN_TIME_SECONDS}s)")
    print(f"   链路权重: 浏览={TASK_WEIGHTS.get('browse_only', 0)}, "
          f"浏览+加购={TASK_WEIGHTS.get('browse_add_cart', 0)}, "
          f"浏览+加购+下单={TASK_WEIGHTS.get('browse_add_cart_submit_order', 0)}")
    print(f"{'=' * 60}")
    print("")


# ==========================================
# Locust User：B2B 在线用户链路
# ==========================================
class RealUserBase(User):
    """
    真实账号用户行为基类（abstract，不会被 Locust 直接实例化）。

    包含登录、浏览（图搜/关键词）、加购、购物车、提交报价单、会员页面访问等全部
    业务方法与 run_* 行为单元。各入口脚本（接口/UI/全部）通过子类挂载所需 @task。
    """
    abstract = True
    wait_time = between(USER_WAIT_MIN, USER_WAIT_MAX)
    host = _get_base_url()

    def on_start(self):
        self.ready = False
        self.session = requests.Session()
        self.session.trust_env = False

        self.accounts = _get_accounts()
        if not self.accounts:
            print("⚠️  无可用压测账号，请在 config/data/stress_accounts.py 中配置")
            return

        self.account = _pick_account(self.accounts)
        self.email = self.account.get("email") or self.account.get("mail", "unknown")
        self.base_url = _get_base_url()
        self.endpoints = _get_endpoints()
        self.last_cart_ids = []
        self.member_pages = _build_page_list(AUTH_PAGE_CHECKS)

        self.token = _get_token(self.email)
        if not self.token:
            self._do_login("登录 [预热]")

        self.ready = bool(self.token)

    def _account_label(self):
        return getattr(self, "email", "") or "未知"

    # ------------------------------------------
    # 通用请求
    # ------------------------------------------
    def _post_json(self, name, url, headers, payload, rules=None):
        start = time.perf_counter()
        try:
            resp = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=STRESS_REQUEST_TIMEOUT,
                verify=False,
                proxies={"http": None, "https": None},
            )
            elapsed = (time.perf_counter() - start) * 1000
            response_length = len(resp.content)

            try:
                body = resp.json()
            except Exception as e:
                _fire_event(
                    "POST", name, elapsed, response_length,
                    exception=f"JSON解析失败: {e}",
                    account=self._account_label(),
                    http_status=resp.status_code,
                    url=url,
                )
                return False, {}, resp

            ok, err = verify_response(body, rules or {})
            if resp.status_code == 200 and ok:
                _fire_event("POST", name, elapsed, response_length)
                return True, body, resp

            _fire_event(
                "POST",
                name,
                elapsed,
                response_length,
                exception=err or f"HTTP {resp.status_code}",
                account=self._account_label(),
                response_body=body,
                http_status=resp.status_code,
                url=url,
            )
            return False, body, resp
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            _fire_event(
                "POST", name, elapsed, 0,
                exception=str(e),
                account=self._account_label(),
                url=url,
            )
            return False, {}, None

    def _post_form(self, name, url, headers, form_data, rules=None):
        start = time.perf_counter()
        try:
            resp = self.session.post(
                url,
                headers=headers,
                data=form_data,
                timeout=STRESS_REQUEST_TIMEOUT,
                verify=False,
                proxies={"http": None, "https": None},
            )
            elapsed = (time.perf_counter() - start) * 1000
            response_length = len(resp.content)

            try:
                body = resp.json()
            except Exception as e:
                _fire_event(
                    "POST", name, elapsed, response_length,
                    exception=f"JSON解析失败: {e}",
                    account=self._account_label(),
                    http_status=resp.status_code,
                    url=url,
                )
                return False, {}, resp

            ok, err = verify_response(body, rules or {})
            if resp.status_code == 200 and ok:
                _fire_event("POST", name, elapsed, response_length)
                return True, body, resp

            _fire_event(
                "POST",
                name,
                elapsed,
                response_length,
                exception=err or f"HTTP {resp.status_code}",
                account=self._account_label(),
                response_body=body,
                http_status=resp.status_code,
                url=url,
            )
            return False, body, resp
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            _fire_event(
                "POST", name, elapsed, 0,
                exception=str(e),
                account=self._account_label(),
                url=url,
            )
            return False, {}, None

    def _get_download(self, name, url, headers, rules=None, params=None):
        start = time.perf_counter()
        try:
            resp = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=STRESS_REQUEST_TIMEOUT,
                verify=False,
                proxies={"http": None, "https": None},
            )
            elapsed = (time.perf_counter() - start) * 1000
            response_length = len(resp.content)

            ok, err = verify_download_response(resp, rules or {})
            if ok:
                _fire_event("GET", name, elapsed, response_length)
                return True, resp

            _fire_event(
                "GET", name, elapsed, response_length,
                exception=err or f"HTTP {resp.status_code}",
                account=self._account_label(),
                http_status=resp.status_code,
                url=url,
            )
            return False, resp
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            _fire_event(
                "GET", name, elapsed, 0,
                exception=str(e),
                account=self._account_label(),
                url=url,
            )
            return False, None

    def _auth_context(self):
        token = _get_token(self.email) or getattr(self, "token", "")
        cookie = _get_b2b_cookie(self.email, token)
        if not token or not cookie:
            _fire_event(
                "AUTH", "B2B凭据", 0, 0,
                exception="缺少Token/Cookie",
                account=self._account_label(),
            )
            return "", ""
        return token, cookie

    def _do_login(self, name="登录"):
        url = f"{self.base_url}{self.endpoints.get('login', '')}"
        headers = get_base_headers(self.base_url)
        rules = get_assertion_rules("login")

        start = time.perf_counter()
        try:
            resp = self.session.post(
                url,
                headers=headers,
                json=self.account,
                timeout=STRESS_REQUEST_TIMEOUT,
                verify=False,
                proxies={"http": None, "https": None},
            )
            elapsed = (time.perf_counter() - start) * 1000
            response_length = len(resp.content)

            try:
                body = resp.json()
            except Exception as e:
                self.token = ""
                _fire_event(
                    "POST", name, elapsed, response_length,
                    exception=f"JSON解析失败: {e}",
                    account=self._account_label(),
                    http_status=resp.status_code,
                    url=url,
                )
                return False

            token = self._extract_token(resp, body)
            ok, err = verify_response(body, rules)
            if resp.status_code == 200 and (ok or (body.get("code") == 200 and token)):
                self.token = token or ""
                if token:
                    _set_token(self.email, token)
                _fire_event("POST", name, elapsed, response_length)
                return bool(token)

            self.token = ""
            _fire_event(
                "POST", name, elapsed, response_length,
                exception=err or f"HTTP {resp.status_code}",
                account=self._account_label(),
                response_body=body,
                http_status=resp.status_code,
                url=url,
            )
            return False
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            self.token = ""
            _fire_event(
                "POST", name, elapsed, 0,
                exception=str(e),
                account=self._account_label(),
                url=url,
            )
            return False

    def _extract_token(self, resp, body=None):
        cookie_name = TOKEN_COOKIE_NAME
        token = None
        if resp.cookies:
            token = resp.cookies.get(cookie_name)
        if not token:
            sc = resp.headers.get("Set-Cookie", "")
            cookie_prefix = f"{cookie_name}="
            if cookie_prefix in sc:
                start = sc.find(cookie_prefix) + len(cookie_prefix)
                end = sc.find(";", start)
                token = sc[start:end if end != -1 else len(sc)].strip()
        if not token and isinstance(body, dict):
            data = body.get("data", {})
            if isinstance(data, dict):
                token = data.get("token") or data.get("login_token")
        return token

    # ------------------------------------------
    # 业务步骤
    # ------------------------------------------
    def _request_img_search(self):
        token, cookie = self._auth_context()
        if not token:
            return False

        url = f"{self.base_url}/api_ali/product/keyword"
        b2b_config = IMG_SEARCH_DATA.get("B2B", {})
        payload = _copy_payload(b2b_config.get("params", {}))
        image_urls = b2b_config.get("image_urls", [])
        if image_urls:
            payload["image_url"] = random.choice(image_urls)

        headers = get_b2b_img_search_headers(self.base_url, token, cookie)
        headers["origin"] = B2B_SITE_URL
        headers["referer"] = B2B_SITE_URL

        ok, _, _ = self._post_json("图搜浏览", url, headers, payload, get_assertion_rules("img_search"))
        return ok

    def _request_keyword_search(self, source=None, return_body=False):
        token, cookie = self._auth_context()
        if not token:
            return (False, {}) if return_body else False

        source = _resolve_search_source(source)
        task_key = f"B2B_{source}_keyword"
        name = f"关键词浏览_{source}"
        endpoint_key = "keyword_search_B2B_1688" if source == "1688" else "keyword_search_B2B_taobao"
        url = _absolute_url(self.base_url, self.endpoints.get(endpoint_key, ""))
        payload = _copy_payload(KEYWORD_SEARCH_DATA.get(task_key, {}))

        all_kw = load_rules("keyword_search")
        headers_cfg = all_kw.get(task_key, {}).get("headers_config", {})
        headers = get_b2b_img_search_headers(
            self.base_url,
            token,
            cookie,
            currency=headers_cfg.get("currency", "KRW"),
            language=headers_cfg.get("language", "korean"),
            nation=headers_cfg.get("nation", "Korea"),
            rate=headers_cfg.get("rate", "220.68"),
            logintype=headers_cfg.get("logintype", "user"),
        )
        headers["origin"] = B2B_SITE_URL
        headers["referer"] = B2B_SITE_URL

        ok, body, _ = self._post_json(name, url, headers, payload, get_assertion_rules("keyword_search", task_key))
        return (ok, body) if return_body else ok

    def _browse_products(self):
        enabled_steps = []
        if STRESS_SWITCHES.get("stress_img_search"):
            enabled_steps.append(self._request_img_search)
        if STRESS_SWITCHES.get("stress_keyword_search"):
            enabled_steps.append(self._request_keyword_search)

        if not enabled_steps:
            _fire_event(
                "BROWSE", "浏览商品", 0, 0,
                exception="未开启图搜或关键词搜索",
                account=self._account_label(),
            )
            return False

        all_ok = True
        for _ in range(max(1, BROWSE_STEPS_PER_JOURNEY)):
            step = random.choice(enabled_steps)
            all_ok = step() and all_ok
        return all_ok

    def _request_add_cart(self):
        if not STRESS_SWITCHES.get("stress_add_cart"):
            return False

        token, cookie = self._auth_context()
        if not token:
            return False

        any_ok = False
        use_dynamic = os.getenv("STRESS_DYNAMIC_ADD_CART", "true").strip().lower() not in {"0", "false", "no", "off"}
        if use_dynamic:
            sources = _enabled_dynamic_add_cart_sources()
            random.shuffle(sources)
            for candidate_source in sources:
                payload = self._build_dynamic_add_cart_payload(candidate_source)
                if payload:
                    any_ok = self._post_add_cart(candidate_source, payload) or any_ok

        if not any_ok:
            source = random.choice(_enabled_add_cart_sources())
            payload = self._build_static_add_cart_payload(source)
            if payload:
                any_ok = self._post_add_cart(source, payload)

        if not any_ok:
            _fire_event(
                "POST", "商品加购", 0, 0,
                exception="missing add cart payload",
                account=self._account_label(),
            )
        return any_ok

    def _post_add_cart(self, source, payload):
        """执行单次加购 POST，并上报 Locust 事件。"""
        if source == "taobao" and not STRESS_ENABLE_TAOBAO_ADD_CART:
            return False

        token, cookie = self._auth_context()
        if not token:
            return False

        task_key = f"B2B_{source}"
        name = f"商品加购_{source}"
        endpoint_key = "add_cart_B2B_1688" if source == "1688" else "add_cart_B2B_taobao"
        url = _absolute_url(self.base_url, self.endpoints.get(endpoint_key, ""))

        payload_to_send = _copy_payload(payload)
        item_url = payload_to_send.pop("_item_url", "")
        item_id = str(payload_to_send.get("item_id", payload_to_send.get("ItemID", "")))
        headers = get_b2b_headers(B2B_SITE_URL, token, cookie, item_id=item_id, item_url=item_url)
        headers["origin"] = B2B_SITE_URL

        ok, _, _ = self._post_json(name, url, headers, payload_to_send, get_assertion_rules("add_cart", task_key))
        return ok

    def _build_static_add_cart_payload(self, source):
        task_key = f"B2B_{source}"
        task_data = ADD_CART_DATA.get(task_key, {})
        if isinstance(task_data, list) and task_data:
            return _copy_payload(random.choice(task_data))
        elif isinstance(task_data, dict):
            return _copy_payload(task_data)
        return {}

    def _build_dynamic_add_cart_payload(self, source):
        ok, search_body = self._request_keyword_search(source=source, return_body=True)
        if not ok:
            return {}

        items = _extract_search_items(search_body, source)
        random.shuffle(items)
        for item in items[:10]:
            item_id = _get_search_item_id(item, source)
            if not item_id:
                continue
            ok, detail_body = self._request_product_detail(source, item_id)
            if not ok:
                continue
            payload = _build_add_cart_payload_from_detail(source, item_id, detail_body)
            if payload:
                return payload
        return {}

    def _request_product_detail(self, source, item_id):
        if source == "taobao" and not STRESS_ENABLE_TAOBAO_DETAIL:
            return False, {}

        token, cookie = self._auth_context()
        if not token:
            return False, {}

        url = _absolute_url(self.base_url, _get_detail_endpoint(source))
        payload = {
            "item_id": str(item_id),
            "site": "B2B",
            "cache": "0",
            "repurchase_rate": "0",
        }
        headers = get_b2b_img_search_headers(self.base_url, token, cookie)
        headers["origin"] = B2B_SITE_URL
        if source == "taobao":
            headers["referer"] = f"{B2B_SITE_URL}/web_view/Taobao/details/?item_id={item_id}&key=&Lang=1&fg=0&sl=32&hot_desc=null&imageUrl=1"
            headers["currpath"] = "/Taobao/details/"
        else:
            headers["referer"] = f"{B2B_SITE_URL}/web_view/Alibaba/details/?item_id={item_id}&key=&Lang=1&fg=0&sl=32&hot_desc=null&imageUrl=1"
            headers["currpath"] = "/Alibaba/details/"

        ok, body, _ = self._post_json(f"商品详情_{source}", url, headers, payload, {})
        return ok, body

    def _request_cart_list(self, name="购物车列表"):
        token, cookie = self._auth_context()
        if not token:
            return []

        endpoint = self.endpoints.get("B2B_Addon_shoppinglist", "")
        if not endpoint:
            _fire_event(
                "POST", name, 0, 0,
                exception="未配置 B2B_Addon_shoppinglist endpoint",
                account=self._account_label(),
            )
            return []

        url = _absolute_url(self.base_url, endpoint)
        payload = _copy_payload(B2B_ADDON_DATA.get("B2B_Addon_shoppinglist", {}))
        headers = get_b2b_headers(self.base_url, token, cookie)
        headers["origin"] = B2B_SITE_URL
        headers["referer"] = f"{B2B_SITE_URL}/web_view/user/shopping/b2b_carts/"
        headers["currpath"] = "/user/shopping/b2b_carts/"

        ok, body, _ = self._post_json(name, url, headers, payload, {})
        if not ok:
            return []
        return _extract_cart_ids(body)

    def _resolve_added_cart_ids(self, before_ids):
        before_set = set(before_ids or [])
        latest_ids = []

        for index in range(max(1, CART_LIST_RETRY_TIMES)):
            latest_ids = self._request_cart_list("购物车列表 [加购后]")
            new_ids = [cart_id for cart_id in latest_ids if cart_id not in before_set]
            if new_ids:
                return new_ids[:SUBMIT_ORDER_MAX_CART_ITEMS]
            if index < CART_LIST_RETRY_TIMES - 1:
                time.sleep(CART_LIST_RETRY_WAIT)

        # 如果同账号并发导致无法区分新增项，退回到最新列表的前 N 个，避免链路断掉。
        return latest_ids[:SUBMIT_ORDER_MAX_CART_ITEMS]

    def _request_get_check_fjx_list(self):
        token, cookie = self._auth_context()
        if not token:
            return "", [], []

        endpoint = self.endpoints.get("B2B_Addon_CheckFjxList", "/api_b2b/cartQuoteStep1/getCheckFjxList")
        url = _absolute_url(self.base_url, endpoint)
        headers = _get_fjx_headers(token, cookie)
        ok, body, _ = self._post_json("附加项列表", url, headers, {}, {})
        if not ok:
            return "", [], []
        return _parse_runtime_fjx_selection(body)

    def _request_update_check_fjx(self, cart_ids, check_uuid, fjx_uuids, user_fjx_uuids=None):
        token, cookie = self._auth_context()
        if not token or not cart_ids or not check_uuid:
            return False

        endpoint = self.endpoints.get("B2B_Addon_Servicefjx", "/api_b2b/cartQuoteStep1/updateCheckFjx")
        url = _absolute_url(self.base_url, endpoint)
        payload = {
            "cart_detail_id_arr": cart_ids,
            "check_config_uuid": check_uuid,
            "fjx_config_uuid_arr": fjx_uuids or [],
            "user_fjx_config_uuid_arr": user_fjx_uuids or [],
        }
        headers = _get_fjx_headers(token, cookie)
        ok, _, _ = self._post_json("保存附加项", url, headers, payload, {})
        return ok

    def _request_get_check_fjx_fee_total(self, cart_ids, check_uuid, fjx_uuids, user_fjx_uuids=None):
        token, cookie = self._auth_context()
        if not token or not cart_ids or not check_uuid:
            return False

        endpoint = self.endpoints.get(
            "B2B_Addon_getCheckFjxFeeTotal",
            "/api_b2b/cartQuoteStep1/getCheckFjxFeeTotal",
        )
        url = _absolute_url(self.base_url, endpoint)
        payload = {
            "cart_detail_ids": cart_ids,
            "check_uuid": [check_uuid],
            "fjx_uuids": fjx_uuids or [],
            "user_fjx_uuids": user_fjx_uuids or [],
        }
        headers = _get_fjx_headers(token, cookie)
        ok, _, _ = self._post_json("附加项费用合计", url, headers, payload, {})
        return ok

    def _request_quote_step1_cart_detail_list(self, cart_ids):
        token, cookie = self._auth_context()
        if not token or not cart_ids:
            return False

        endpoint = self.endpoints.get(
            "B2B_Quote_step1_cartDetailList",
            "/api_b2b/cartQuoteStep1/cartDetailList",
        )
        url = _absolute_url(self.base_url, endpoint)
        payload = {"cart_detail_ids": cart_ids}
        headers = _get_fjx_headers(token, cookie)
        ok, _, _ = self._post_json("报价Step1明细", url, headers, payload, {})
        return ok

    def _request_quote_step2_cart_detail_list(self, cart_ids):
        token, cookie = self._auth_context()
        if not token or not cart_ids:
            return False

        endpoint = self.endpoints.get(
            "B2B_Quote_step2_cartDetailList",
            "/api_b2b/cartQuoteStep2/cartDetailList",
        )
        url = _absolute_url(self.base_url, endpoint)
        headers = _get_quote_step2_headers(token, cookie)
        headers["content-type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        form_data = {"cart_detail_ids": ",".join(cart_ids)}
        ok, _, _ = self._post_form("报价Step2明细", url, headers, form_data, {})
        return ok

    def _request_quote_step2_cart_detail_list_total_fee(self, cart_ids):
        token, cookie = self._auth_context()
        if not token or not cart_ids:
            return False

        endpoint = self.endpoints.get(
            "B2B_Quote_step2_cartDetailListTotalFee",
            "/api_b2b/cartQuoteStep2/cartDetailListTotalFee",
        )
        url = _absolute_url(self.base_url, endpoint)
        headers = _get_quote_step2_headers(token, cookie)
        headers["content-type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        form_data = {"cart_detail_ids": ",".join(cart_ids)}
        ok, _, _ = self._post_form("报价Step2费用合计", url, headers, form_data, {})
        return ok

    def _run_full_quote_flow(self, cart_ids):
        if not STRESS_SWITCHES.get("stress_full_quote_flow", STRESS_ENABLE_FULL_QUOTE_FLOW):
            return True

        str_ids, _ = _normalize_cart_detail_ids(cart_ids)
        if not str_ids:
            _fire_event(
                "POST", "完整报价链路", 0, 0,
                exception="无购物车明细ID",
                account=self._account_label(),
            )
            return False

        check_uuid, fjx_uuids, user_fjx_uuids = self._request_get_check_fjx_list()
        if not check_uuid:
            _fire_event(
                "POST", "完整报价链路", 0, 0,
                exception="未获取到可用检品UUID",
                account=self._account_label(),
            )
            return False

        steps = [
            ("保存附加项", lambda: self._request_update_check_fjx(str_ids, check_uuid, fjx_uuids, user_fjx_uuids)),
            ("附加项费用合计", lambda: self._request_get_check_fjx_fee_total(str_ids, check_uuid, fjx_uuids, user_fjx_uuids)),
            ("报价Step1明细", lambda: self._request_quote_step1_cart_detail_list(str_ids)),
            ("报价Step2明细", lambda: self._request_quote_step2_cart_detail_list(str_ids)),
            ("报价Step2费用合计", lambda: self._request_quote_step2_cart_detail_list_total_fee(str_ids)),
        ]
        for step_name, step_fn in steps:
            if not step_fn():
                _fire_event(
                    "POST", "完整报价链路", 0, 0,
                    exception=f"{step_name}失败",
                    account=self._account_label(),
                )
                return False
        return True

    def _request_submit_order(self, cart_ids, use_full_quote_flow=None):
        if not STRESS_SWITCHES.get("stress_submit_order"):
            return False

        token, cookie = self._auth_context()
        if not token:
            return False

        _, int_ids = _normalize_cart_detail_ids(cart_ids)
        if not int_ids:
            _fire_event(
                "POST", "提交报价单", 0, 0,
                exception="无购物车ID",
                account=self._account_label(),
            )
            return False

        use_full = (
            STRESS_ENABLE_FULL_QUOTE_FLOW
            if use_full_quote_flow is None
            else use_full_quote_flow
        )

        submit_url = _absolute_url(self.base_url, self.endpoints.get("submit_order_B2B", ""))
        b2b_submit_config = SUBMIT_ORDER_DATA.get("B2B_submit", {})
        if use_full:
            quote_type = STRESS_QUOTE_TYPE
            logistics_config_id = STRESS_LOGISTICS_CONFIG_ID
        else:
            quote_type = b2b_submit_config.get("quote_type", b2b_submit_config.get("quoteType", 1))
            logistics_config_id = b2b_submit_config.get(
                "logistics_config_id",
                b2b_submit_config.get("ExpressID", 27),
            )

        payload = {
            "quote_type": quote_type,
            "logistics_config_id": logistics_config_id,
            "cart_detail_id_arr": int_ids[:SUBMIT_ORDER_MAX_CART_ITEMS],
        }

        headers = _get_quote_step2_headers(token, cookie)
        headers["content-type"] = "application/json"

        ok, body, _ = self._post_json("提交报价单", submit_url, headers, payload, get_assertion_rules("submit_order"))
        quote_no = ""
        if ok:
            quote_no = _extract_quote_no(body)
            if quote_no:
                _fire_event("BUSINESS", "报价单号提取", 0, len(str(quote_no)))
        return ok, quote_no

    def _request_down_quote(self, quote_no, language=None):
        if not STRESS_SWITCHES.get("stress_quote_download", STRESS_ENABLE_QUOTE_DOWNLOAD):
            return False

        if not quote_no:
            return False

        token, cookie = self._auth_context()
        if not token:
            return False

        endpoint = self.endpoints.get("B2B_quote_downQuote", "/api_b2b/quotedetail/downQuote")
        url = _absolute_url(self.base_url, endpoint)
        params = {
            "quote_no": quote_no,
            "token": _clean_token(token),
            "language": language or STRESS_QUOTE_DOWNLOAD_LANGUAGE,
        }

        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "origin": B2B_SITE_URL,
            "referer": f"{B2B_SITE_URL}/",
            "Cookie": cookie,
        }

        rules = get_assertion_rules("down_quote")
        ok, _ = self._get_download("下载报价单", url, headers, rules=rules, params=params)
        return ok

    def _visit_member_page(self, name, url):
        """携带登录态 Cookie 访问需登录的前台页面（SPA 文档级检查）。"""
        token, cookie = self._auth_context()
        if not token or not cookie:
            return False
        extra_headers = {
            "Cookie": cookie,
            "referer": f"{B2B_SITE_URL}/",
        }
        return _perform_page_check(
            self.session, name, url, PAGE_TITLE_KEYWORD, extra_headers, account=self._account_label()
        )

    # ------------------------------------------
    # 行为单元（run_*）：由各入口脚本子类包装为 @task
    # ------------------------------------------
    def run_login_refresh(self):
        if not self.ready or not STRESS_SWITCHES.get("stress_login"):
            return
        self._do_login("登录刷新")

    def run_browse_only(self):
        if not self.ready or not STRESS_SWITCHES.get("stress_browse_only", True):
            return
        self._browse_products()

    def run_browse_add_cart(self):
        if not self.ready or not STRESS_SWITCHES.get("stress_browse_add_cart", True):
            return
        self._browse_products()
        if self._request_add_cart():
            self.last_cart_ids = self._request_cart_list("购物车列表 [加购确认]")

    def run_browse_add_cart_submit_order(self):
        if not self.ready or not STRESS_SWITCHES.get("stress_browse_add_cart_submit_order", True):
            return

        before_ids = self._request_cart_list("购物车列表 [下单前]")
        self._browse_products()
        if not self._request_add_cart():
            return

        cart_ids = self._resolve_added_cart_ids(before_ids)
        self.last_cart_ids = cart_ids
        if not self._run_full_quote_flow(cart_ids):
            return
        ok, quote_no = self._request_submit_order(cart_ids)
        if ok and quote_no:
            self._request_down_quote(quote_no)

    def run_member_page_visit(self):
        if not self.ready or not STRESS_ENABLE_PAGE_CHECK or not self.member_pages:
            return
        page = random.choice(self.member_pages)
        self._visit_member_page(page["name"], page["url"])


# ==========================================
# Locust User 基类：无账号虚拟用户（abstract）
# ==========================================
class GuestUserBase(User):
    """
    虚拟访客行为基类（abstract，不会被 Locust 直接实例化）。
    - 访问 B2B 前台页面（UI 检查）
    - 调用关键词搜索接口（接口检查）
    - 不参与加购、购物车、下单
    """
    abstract = True
    wait_time = between(USER_WAIT_MIN, USER_WAIT_MAX)
    host = B2B_SITE_URL

    def on_start(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.base_url = _get_base_url()
        self.endpoints = _get_endpoints()
        self.guest_pages = _build_page_list(GUEST_PAGE_CHECKS) or [
            {"name": "页面_B2B首页", "url": f"{B2B_SITE_URL}/"}
        ]

    def _get_page(self, name, url):
        # 兼容旧调用：免登录页面 GET + 标题关键字断言
        return _perform_page_check(self.session, name, url, PAGE_TITLE_KEYWORD)

    def _guest_keyword_search(self):
        source = _resolve_search_source()
        task_key = f"B2B_{source}_keyword"
        endpoint_key = "keyword_search_B2B_1688" if source == "1688" else "keyword_search_B2B_taobao"
        url = _absolute_url(self.base_url, self.endpoints.get(endpoint_key, ""))
        payload = _copy_payload(KEYWORD_SEARCH_DATA.get(task_key, {}))

        all_kw = load_rules("keyword_search")
        headers_cfg = all_kw.get(task_key, {}).get("headers_config", {})
        headers = get_b2b_img_search_headers(
            self.base_url,
            token="",
            cookie_str="",
            currency=headers_cfg.get("currency", "KRW"),
            language=headers_cfg.get("language", "korean"),
            nation=headers_cfg.get("nation", "Korea"),
            rate=headers_cfg.get("rate", "220.68"),
            logintype=headers_cfg.get("logintype", "user"),
        )
        headers["origin"] = B2B_SITE_URL
        headers["referer"] = B2B_SITE_URL
        headers.pop("Cookie", None)

        name = f"虚拟用户关键词查询_{source}"
        start = time.perf_counter()
        try:
            resp = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=STRESS_REQUEST_TIMEOUT,
                verify=False,
                proxies={"http": None, "https": None},
            )
            elapsed = (time.perf_counter() - start) * 1000
            response_length = len(resp.content)
            try:
                body = resp.json()
                ok, err = verify_response(body, get_assertion_rules("keyword_search", task_key))
            except Exception as e:
                body = None
                ok, err = False, f"JSON解析失败: {e}"

            if resp.status_code == 200 and ok:
                _fire_event("POST", name, elapsed, response_length)
            else:
                _fire_event(
                    "POST", name, elapsed, response_length,
                    exception=err or f"HTTP {resp.status_code}",
                    account="虚拟访客",
                    response_body=body if isinstance(body, dict) else None,
                    http_status=resp.status_code,
                    url=url,
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            _fire_event(
                "POST", name, elapsed, 0,
                exception=str(e),
                account="虚拟访客",
                url=url,
            )

    def run_page_visit(self):
        if not STRESS_ENABLE_PAGE_CHECK:
            return
        page = random.choice(self.guest_pages)
        _perform_page_check(self.session, page["name"], page["url"], PAGE_TITLE_KEYWORD)

    def run_keyword_search(self):
        self._guest_keyword_search()


# ==========================================
# LoadShape 工厂：按真实/虚拟用户分层加载
# ==========================================
def make_split_load_shape(real_user_cls=None, guest_user_cls=None):
    """
    生成测试平台分层加载模型（供各入口脚本复用）：
    1. 先按 STRESS_REAL_SPAWN_RATE 加载真实账号用户（若传入 real_user_cls）
    2. 再按 STRESS_VIRTUAL_SPAWN_RATE 加载虚拟访客用户（若传入 guest_user_cls）
    3. 到达 STRESS_RUN_TIME 后结束

    仅 UI 套或仅接口套可只传其中一类用户类。
    """

    class _SplitUserLoadShape(LoadTestShape):
        def tick(self):
            run_time = self.get_run_time()
            real_users = max(0, AUTH_BUYER_FIXED_COUNT) if real_user_cls else 0
            virtual_users = max(0, VIRTUAL_USER_COUNT) if guest_user_cls else 0
            total_users = real_users + virtual_users

            if total_users <= 0:
                return None
            if run_time >= STRESS_RUN_TIME_SECONDS:
                return None

            current_users = 0
            if self.runner is not None:
                current_users = self.runner.user_count

            if real_users > 0 and current_users < real_users:
                return (real_users, STRESS_REAL_SPAWN_RATE, [real_user_cls])

            if virtual_users > 0 and current_users < total_users:
                return (total_users, STRESS_VIRTUAL_SPAWN_RATE, [guest_user_cls])

            active_classes = [cls for cls in (real_user_cls, guest_user_cls) if cls]
            return (
                total_users,
                max(STRESS_REAL_SPAWN_RATE, STRESS_VIRTUAL_SPAWN_RATE),
                active_classes,
            )

    return _SplitUserLoadShape
