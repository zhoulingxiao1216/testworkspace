# -*- coding: utf-8 -*-
"""
全球站压测 — 主配置文件
参照巡检系统 (hubbuyer/config/settings.py) 格式，集中管理所有压测参数
"""
import os
import sys


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name, default, minimum=None):
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    try:
        parsed = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _env_float(name, default, minimum=None):
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _parse_duration_seconds(value, default_seconds):
    raw = str(value or "").strip().lower()
    if not raw:
        return default_seconds
    try:
        if raw.endswith("ms"):
            return max(1, int(float(raw[:-2]) / 1000))
        if raw.endswith("s"):
            return max(1, int(float(raw[:-1])))
        if raw.endswith("m"):
            return max(1, int(float(raw[:-1]) * 60))
        if raw.endswith("h"):
            return max(1, int(float(raw[:-1]) * 3600))
        return max(1, int(float(raw)))
    except (TypeError, ValueError):
        return default_seconds


# ==========================================
# 0. 路径初始化：桥接巡检系统基础设施
#    策略：临时将 hubbuyer 置于 sys.path 最前，加载其 settings 后恢复
#    避免 Performance/config 与 hubbuyer/config 的模块名冲突
# ==========================================
PERFORMANCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUBBUYER_ROOT = os.path.abspath(os.path.join(PERFORMANCE_ROOT, "..", "..", "全球站巡检脚本", "hubbuyer"))

# --- 临时切换 sys.path，让 hubbuyer 优先解析 config.* ---
_saved_path = sys.path.copy()
# 移除 Performance 目录（防止解析到 Performance/config）
sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(PERFORMANCE_ROOT)]
# 确保 hubbuyer 在最前
if HUBBUYER_ROOT not in sys.path:
    sys.path.insert(0, HUBBUYER_ROOT)

# 清除已缓存的 config 模块（如果有）
_cached_config_keys = [k for k in sys.modules if k == "config" or k.startswith("config.")]
_cached_config_modules = {k: sys.modules.pop(k) for k in _cached_config_keys}

# 加载 hubbuyer 的 settings + 底层工具模块
import config.settings as _hubbuyer_settings
import config.data.headers as _hubbuyer_headers
import config.data.cookie as _hubbuyer_cookie
import core.path_manager as _hubbuyer_path_manager

_hubbuyer_API_CONFIG = _hubbuyer_settings.API_CONFIG
_hubbuyer_ENV_TYPE = _hubbuyer_settings.ENV_TYPE

# --- 恢复 sys.path 和模块缓存 ---
# 移除 hubbuyer 加载的 config.* 缓存（保留 core.* 不影响）
for k in list(sys.modules.keys()):
    if k == "config" or k.startswith("config."):
        del sys.modules[k]
# 恢复之前缓存的 Performance/config 模块
sys.modules.update(_cached_config_modules)
# 恢复路径，保留 hubbuyer（供运行时使用）
sys.path = _saved_path
if HUBBUYER_ROOT not in sys.path:
    sys.path.insert(0, HUBBUYER_ROOT)

# ==========================================
# 巡检系统工具 — 重导出（避免外部直接 import hubbuyer/config.*）
# ==========================================
# 请求头构建
get_base_headers = _hubbuyer_headers.get_base_headers
get_auth_headers = _hubbuyer_headers.get_auth_headers
get_b2b_headers = _hubbuyer_headers.get_b2b_headers
get_b2b_img_search_headers = _hubbuyer_headers.get_b2b_img_search_headers
# Cookie 管理
CookieManager = _hubbuyer_cookie.CookieManager
# 路径管理
TOKEN_DIR = _hubbuyer_path_manager.TOKEN_DIR
DATA_DIR_HUBBUYER = _hubbuyer_path_manager.DATA_DIR

# ==========================================
# 1. 压测环境开关（独立于巡检系统）
# ==========================================
# 设为 None 时跟随巡检系统 ENV_TYPE；设为 "prod" / "test" 则独立控制
_raw_env_override = os.getenv("STRESS_ENV") or os.getenv("STRESS_ENV_OVERRIDE")
STRESS_ENV_OVERRIDE = _raw_env_override.strip().lower() if _raw_env_override else None

ENV_TYPE = STRESS_ENV_OVERRIDE if STRESS_ENV_OVERRIDE else _hubbuyer_ENV_TYPE
if ENV_TYPE not in {"prod", "main", "test"}:
    ENV_TYPE = "prod"

# ==========================================
# 1.1 环境域名映射
# ==========================================
_ENV_DOMAINS = {
    "prod": {
        "api":  "https://api.hubbuyer.com",
        "b2b":  "https://b2b.hubbuyer.com",
        "fjx":  "https://fjx.hubbuyer.com",
    },
    "main": {
        "api":  "https://main-api.hubbuyer.com",
        "b2b":  "https://main-b2b.hubbuyer.com",
        "fjx":  "https://main-fjx.hubbuyer.com",
    },
    "test": {
        "api":  "https://test-api.hubbuyer.com",
        "b2b":  "https://test-b2b.hubbuyer.com",
        "fjx":  "https://test-fjx.hubbuyer.com",
    },
}

# 当前环境的 B2B / FJX 站点 URL（用于 origin/referer）
B2B_SITE_URL = _ENV_DOMAINS.get(ENV_TYPE, _ENV_DOMAINS["prod"])["b2b"]
FJX_SITE_URL = _ENV_DOMAINS.get(ENV_TYPE, _ENV_DOMAINS["prod"])["fjx"]

# 当前环境的 Token Cookie 名称（main 与 prod 一致沿用 pro_auth_token）
TOKEN_COOKIE_NAME = "pro_auth_token" if ENV_TYPE in {"prod", "main"} else "test_auth_token"

# ==========================================
# 1.2 Test 环境 API 配置（当巡检系统 test 配置不完整时兜底）
# ==========================================
_STRESS_TEST_API = {
    "BASE_URL": "https://test-api.hubbuyer.com",
    "ENDPOINTS": _hubbuyer_API_CONFIG.get("ENDPOINTS", {}),  # 路径与 prod 一致
}

# ==========================================
# 2. 压测接口开关（True = 参与压测）
# ==========================================
STRESS_ENABLE_ADD_CART = _env_bool("STRESS_ENABLE_ADD_CART", True)
STRESS_ENABLE_SUBMIT_ORDER = _env_bool("STRESS_ENABLE_SUBMIT_ORDER", True)
# 完整报价链路：附加项 Step1/Step2 后再 quote/create（默认开启；可 STRESS_ENABLE_FULL_QUOTE_FLOW=false 回退简化下单）
STRESS_ENABLE_FULL_QUOTE_FLOW = _env_bool(
    "STRESS_ENABLE_FULL_QUOTE_FLOW",
    STRESS_ENABLE_SUBMIT_ORDER,
)
# 淘宝链路开关（默认关闭，避免 taobao 40000 等不稳定接口干扰压测）
STRESS_ENABLE_TAOBAO_KEYWORD = _env_bool("STRESS_ENABLE_TAOBAO_KEYWORD", False)
STRESS_ENABLE_TAOBAO_DETAIL = _env_bool("STRESS_ENABLE_TAOBAO_DETAIL", False)
STRESS_ENABLE_TAOBAO_ADD_CART = _env_bool("STRESS_ENABLE_TAOBAO_ADD_CART", False)
# 报价单下载检查点（下单成功后用当轮 quote_no 下载；默认随提交报价单开关）
STRESS_ENABLE_QUOTE_DOWNLOAD = _env_bool(
    "STRESS_ENABLE_QUOTE_DOWNLOAD",
    STRESS_ENABLE_SUBMIT_ORDER,
)
STRESS_QUOTE_DOWNLOAD_LANGUAGE = os.getenv("STRESS_QUOTE_DOWNLOAD_LANGUAGE", "english").strip() or "english"

STRESS_SWITCHES = {
    "stress_login":          True,     # 登录接口
    "stress_img_search":     True,     # 图搜接口
    "stress_keyword_search": True,     # 关键词搜索接口（1688 始终参与；淘宝见 STRESS_ENABLE_TAOBAO_KEYWORD）
    "stress_taobao_keyword": STRESS_ENABLE_TAOBAO_KEYWORD,
    "stress_taobao_detail": STRESS_ENABLE_TAOBAO_DETAIL,
    "stress_taobao_add_cart": STRESS_ENABLE_TAOBAO_ADD_CART,
    "stress_add_cart":       STRESS_ENABLE_ADD_CART,        # 加购接口
    "stress_submit_order":   STRESS_ENABLE_SUBMIT_ORDER,    # 提交报价单接口
    "stress_full_quote_flow": STRESS_ENABLE_FULL_QUOTE_FLOW,  # 附加项 + Step1/Step2 完整报价链路
    "stress_browse_only":    True,     # 仅浏览商品链路
    "stress_browse_add_cart": STRESS_ENABLE_ADD_CART,       # 浏览 + 加购链路
    "stress_browse_add_cart_submit_order": STRESS_ENABLE_SUBMIT_ORDER,  # 浏览 + 加购 + 提交报价单链路
    "stress_quote_download": STRESS_ENABLE_QUOTE_DOWNLOAD,  # 下单成功后下载当轮报价单
}

# ==========================================
# 3. Locust 任务权重（数值越大，该接口被调用的概率越高）
# ==========================================
TASK_WEIGHTS = {
    # 新链路模型：默认模拟“多数用户浏览、部分用户加购、少量用户下单”
    "login_refresh":  1,    # 登录刷新：低频维持 Token
    "browse_only":    6,    # 仅浏览商品：高频在线行为
    "browse_add_cart": 3,   # 浏览后加购：中频写入行为
    "browse_add_cart_submit_order": 1,  # 浏览后加购并提交报价单：低频重操作
    "member_page_visit": 2,  # 访问需登录的前台页面（购物车/附加项/订单提交）

    # 兼容旧配置键，供自定义脚本或历史命令引用
    "login":          1,
    "img_search":     3,
    "keyword_search": 3,
    "add_cart":       2,
    "submit_order":   1,
}

# ==========================================
# 4. 请求超时配置（秒）
# ==========================================
STRESS_REQUEST_TIMEOUT = 45         # 单次请求超时（比巡检更宽松）
STRESS_CONNECT_TIMEOUT = 10        # 连接超时

# ==========================================
# 5. Locust 用户行为配置
# ==========================================
USER_WAIT_MIN = 0.5    # 请求间最小等待（秒）
USER_WAIT_MAX = 2.0    # 请求间最大等待（秒）

# ==========================================
# 5.1 链路压测参数
# ==========================================
ACCOUNT_PICK_STRATEGY = os.getenv("STRESS_ACCOUNT_PICK_STRATEGY", "round_robin")  # round_robin / random
BROWSE_STEPS_PER_JOURNEY = _env_int("STRESS_BROWSE_STEPS", 2, minimum=1)          # 每个链路任务内执行几次浏览请求
SUBMIT_ORDER_MAX_CART_ITEMS = _env_int("STRESS_SUBMIT_ORDER_MAX_CART_ITEMS", 1, minimum=1)  # 每次提交报价单最多提交几个购物车明细ID
# 完整报价链路 quote/create 默认参数（与 main 环境浏览器抓包一致）
STRESS_QUOTE_TYPE = _env_int("STRESS_QUOTE_TYPE", 2, minimum=1)
STRESS_LOGISTICS_CONFIG_ID = _env_int("STRESS_LOGISTICS_CONFIG_ID", 28, minimum=1)
CART_LIST_RETRY_TIMES = 3              # 加购后查询购物车列表重试次数
CART_LIST_RETRY_WAIT = 0.3             # 加购后查询购物车列表重试间隔（秒）

# ==========================================
# 5.2 用户模型分配
# ==========================================
# 固定少量真实账号用户执行登录/加购/下单链路，其余用户走 Guest 轻量浏览模型。
AUTH_BUYER_FIXED_COUNT = _env_int("STRESS_REAL_USERS", 5, minimum=0)
VIRTUAL_USER_COUNT = _env_int("STRESS_VIRTUAL_USERS", 0, minimum=0)
GUEST_USER_WEIGHT = _env_int("STRESS_GUEST_WEIGHT", 100, minimum=1)
STRESS_REAL_SPAWN_RATE = _env_float("STRESS_REAL_SPAWN_RATE", 1.0, minimum=0.1)
STRESS_VIRTUAL_SPAWN_RATE = _env_float("STRESS_VIRTUAL_SPAWN_RATE", 10.0, minimum=0.1)
STRESS_RUN_TIME = os.getenv("STRESS_RUN_TIME", "10m")
STRESS_RUN_TIME_SECONDS = _parse_duration_seconds(STRESS_RUN_TIME, 600)
STRESS_USE_SPLIT_LOAD_SHAPE = _env_bool("STRESS_USE_SPLIT_LOAD_SHAPE", False)

GUEST_TASK_WEIGHTS = {
    "page_visit": 2,
    "keyword_search": 3,
}

# ==========================================
# 5.3 前台页面级检查项（SPA 文档级）
# ==========================================
# 站点为 SPA：各路由 GET 均返回同一 index.html 外壳，标题统一。
# 因此页面级检查靠 URL 名称区分、靠标题关键字断言防白屏/降级。
# path 仅写相对路径，域名由当前环境 B2B_SITE_URL 拼接（test/main/prod 通用）。
STRESS_ENABLE_PAGE_CHECK = _env_bool("STRESS_ENABLE_PAGE_CHECK", True)

# 页面标题关键字断言（命中视为外壳正常；缺失视为白屏/降级）
PAGE_TITLE_KEYWORD = os.getenv("STRESS_PAGE_TITLE_KEYWORD", "Hubbuyer | B2B Sourcing Platform").strip()

# 免登录前台页面（虚拟访客 Guest 用户访问）
GUEST_PAGE_CHECKS = [
    {"name": "页面_B2B首页",        "path": "/"},
    {"name": "页面_关键词搜索结果", "path": "/Alibaba/list?key=%E6%89%8B%E6%9C%BA%E5%A3%B3"},
]

# 需登录前台页面（真实账号用户携带 token/cookie 访问）
AUTH_PAGE_CHECKS = [
    {"name": "页面_购物车",         "path": "/user/cart/index"},
    {"name": "页面_购物车附加项",   "path": "/user/cart/additionalServices"},
    {"name": "页面_订单提交确认",   "path": "/user/cart/orderConfirm"},
]

# 兼容旧用法：Guest 页面 URL 列表（由免登录页面清单生成）
PAGE_VISIT_URLS = [f"{B2B_SITE_URL}{item['path']}" for item in GUEST_PAGE_CHECKS if item.get("path")]
PAGE_VISIT_URLS = [url for url in PAGE_VISIT_URLS if url]

# ==========================================
# 6. 通知控制：压测模式下强制关闭所有通知
# ==========================================
ENABLE_STRESS_NOTIFICATION = False

# ==========================================
# 7. 报告输出配置
# ==========================================
REPORT_DIR = os.path.join(PERFORMANCE_ROOT, "reports")
RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ==========================================
# 8. 拼装 API_CONFIG（环境感知）
# ==========================================
# 当使用 test 环境且巡检系统 test 配置的 BASE_URL 为空时，使用压测自有的 test 配置
_raw_base_url = _hubbuyer_API_CONFIG.get("BASE_URL", "")
if ENV_TYPE == "test" and not _raw_base_url:
    API_CONFIG = _STRESS_TEST_API.copy()
else:
    API_CONFIG = {
        "BASE_URL": _ENV_DOMAINS.get(ENV_TYPE, _ENV_DOMAINS["prod"])["api"],
        "ENDPOINTS": _hubbuyer_API_CONFIG.get("ENDPOINTS", {}),
    }

# 报价 Step1/Step2 补充端点（巡检配置未收录的路径）
_QUOTE_FLOW_ENDPOINTS = {
    "B2B_Addon_getCheckFjxFeeTotal": "/api_b2b/cartQuoteStep1/getCheckFjxFeeTotal",
    "B2B_Quote_step1_cartDetailList": "/api_b2b/cartQuoteStep1/cartDetailList",
    "B2B_Quote_step2_cartDetailList": "/api_b2b/cartQuoteStep2/cartDetailList",
    "B2B_Quote_step2_cartDetailListTotalFee": "/api_b2b/cartQuoteStep2/cartDetailListTotalFee",
    "B2B_quote_downQuote": "/api_b2b/quotedetail/downQuote",
}
API_CONFIG.setdefault("ENDPOINTS", {}).update(_QUOTE_FLOW_ENDPOINTS)
