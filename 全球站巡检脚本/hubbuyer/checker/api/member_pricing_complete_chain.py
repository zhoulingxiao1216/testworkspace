# -*- coding: utf-8 -*-
# checker/api/member_pricing_complete_chain.py
# 价格体系专项巡检链路：只读校验附加项展示、价格来源、费用预览、快照与发货附加项。
import json
import os
import sys
import traceback

try:
    import requests
except ModuleNotFoundError:
    try:
        from pip._vendor import requests
    except ModuleNotFoundError:
        requests = None

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ModuleNotFoundError:
    try:
        from pip._vendor import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ModuleNotFoundError:
        urllib3 = None

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.data.cookie import CookieManager
from config.data.headers import get_base_headers, get_b2b_headers
from config.settings import API_CONFIG, ENV_TYPE, REQUEST_TIMEOUT_API, INSPECTION_SWITCHES
from config.data.login_data import ACCOUNTS_POOL
from core.path_manager import DATA_DIR, TOKEN_DIR
from core.rules.assertion import AssertionTool


CONFIG_FILE = "member_pricing_complete_chain.json"
DEFAULT_CHECK_PATH = "/api_b2b/cartQuoteStep1/getCheckFjxList"
DEFAULT_PREVIEW_PATH = "/api_b2b/cartQuoteStep1/getCheckFjxFeeTotal"
CHECKPOINT_TITLE = "价格体系专项巡检链路"
CHECKPOINT_EXPECTED = "价格体系专项巡检通过"
FEATURE_SWITCH_KEYS = {
    "cart_preview": "check_api_member_pricing_cart_preview",
    "snapshot": "check_api_member_pricing_snapshot",
    "service_pricing": "check_api_member_pricing_service_pricing",
    "ship_fjx": "check_api_member_pricing_ship_fjx",
}


def _is_feature_enabled(feature_name, fallback_enabled=True):
    switch_key = FEATURE_SWITCH_KEYS.get(feature_name)
    if switch_key and switch_key in INSPECTION_SWITCHES:
        return bool(INSPECTION_SWITCHES.get(switch_key)), True
    return bool(fallback_enabled), False


def emit_result(final_result):
    print(json.dumps(final_result, ensure_ascii=False), flush=True)
    return final_result


class InspectionRecorder:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.messages = []
        self.sub_results = {}

    def _add(self, status, name, message, actual=""):
        success = status == "PASS"
        if status == "PASS":
            self.passed += 1
        elif status == "SKIP":
            self.skipped += 1
            success = True
        else:
            self.failed += 1

        line = "%s:%s" % (name, status)
        if message:
            line += "(%s)" % message
        self.messages.append(line)
        self.sub_results[name] = {
            "success": success,
            "message": line,
            "status_code": 200 if success else 500,
            "expected": "PASS",
            "actual": actual or message,
        }

    def pass_(self, name, message=""):
        self._add("PASS", name, message)

    def fail(self, name, message="", actual=""):
        self._add("FAIL", name, message, actual)

    def skip(self, name, message=""):
        self._add("SKIP", name, message)

    def assert_(self, condition, name, fail_message="", actual=""):
        if condition:
            self.pass_(name)
        else:
            self.fail(name, fail_message, actual)

    def to_result(self, title):
        success = self.failed == 0 and self.passed > 0
        message = "%s: %s | Passed=%s Failed=%s Skipped=%s" % (
            title,
            "PASS" if success else "FAIL",
            self.passed,
            self.failed,
            self.skipped,
        )
        if self.messages:
            message += " || " + " | ".join(self.messages[:30])
            if len(self.messages) > 30:
                message += " | ...共%s项" % len(self.messages)
        return {
            "success": success,
            "message": message,
            "status_code": 200 if success else 500,
            "expected": CHECKPOINT_EXPECTED,
            "actual": "Passed=%s Failed=%s Skipped=%s" % (self.passed, self.failed, self.skipped),
            "sub_results": self.sub_results,
        }


def _load_json_file(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(task_config=None):
    task_config = task_config or {}
    configured = (task_config.get("data_file") or "").strip()
    path = configured if configured else os.path.join(DATA_DIR, CONFIG_FILE)
    default = {
        "defaults": {"language": "korean", "currency": "KRW", "nation": "Korea"},
        "cases": [
            {
                "name": "当前登录账号价格体系基础健康",
                "enabled": True,
                "login_account": "",
                "expected": {
                    "minCheckCount": 1,
                    "requireAnyAddon": True,
                    "requirePricingSourceOnPricedItems": False,
                },
            }
        ],
    }
    return _load_json_file(path, default)


def load_current_tokens():
    token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
    return _load_json_file(token_file, {})


def _clean_token(token):
    return (token or "").replace("Bearer ", "").strip()


def _string_ids(ids):
    return [str(item) for item in (ids or []) if item not in ("", None)]


def _extract_login_token(response):
    token = ""
    try:
        if getattr(response, "cookies", None):
            token = response.cookies.get("pro_auth_token") or ""
    except Exception:
        token = ""
    if token:
        return _clean_token(token)

    try:
        body = response.json()
    except Exception:
        return ""
    data = body.get("data") if isinstance(body, dict) else {}
    if isinstance(data, dict):
        return _clean_token(data.get("login_token") or data.get("token") or "")
    return ""


def _login_frontend_account(account):
    if requests is None:
        raise RuntimeError("缺少依赖 requests，请先安装 requirements.txt")
    base_url = (API_CONFIG.get("BASE_URL") or "").rstrip("/")
    login_path = API_CONFIG.get("ENDPOINTS", {}).get("login") or "/api/login/login"
    response = requests.post(
        base_url + login_path,
        headers=get_base_headers(base_url),
        json=account,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    check = AssertionTool.verify_api_common(response)
    if not check["success"]:
        raise RuntimeError("前台登录失败: %s" % check.get("message", "未知错误"))
    token = _extract_login_token(response)
    if not token:
        raise RuntimeError("前台登录成功但未返回 token")
    return token


def _resolve_login_account(case, target_mail):
    user = case.get("user") or {}
    if user.get("account") and user.get("password"):
        return {
            "email": user.get("account"),
            "password": user.get("password"),
            "code": user.get("code", ""),
            "type": user.get("type", "password"),
            "jump_url": user.get("jump_url", ""),
            "jump_site": user.get("jump_site", "B2B"),
        }

    accounts = API_CONFIG.get("ACCOUNT_LIST") or ACCOUNTS_POOL.get(ENV_TYPE, {}).get("frontend", [])
    if target_mail:
        for account in accounts:
            if (account.get("email") or account.get("mail") or "").strip() == target_mail:
                return account
    return accounts[0] if accounts else None


def _cookie_from_token(token):
    clean = _clean_token(token)
    if not clean:
        return ""
    return (
        "PHPSID=qokjm6u9opg4qoo68pn3q48g2d; "
        "PHPSESSID=qokjm6u9opg4qoo68pn3q48g2d; "
        "pro_auth_token=%s; server_login_token=%s; loginToken=%s; login_token=%s"
    ) % (clean, clean, clean, clean)


def resolve_user_credentials(case, task_config=None):
    task_config = task_config or {}
    tokens = load_current_tokens()
    target_mail = (
        case.get("login_account")
        or task_config.get("login_account")
        or case.get("user", {}).get("account")
        or ""
    ).strip()

    token = _clean_token(case.get("userLoginToken") or "")
    if not token and target_mail:
        token = _clean_token(tokens.get(target_mail) or tokens.get(target_mail.lower()) or "")
        if not token:
            for key, val in tokens.items():
                if key.strip() == target_mail:
                    target_mail = key
                    token = _clean_token(val)
                    break

    if not token and tokens:
        target_mail = list(tokens.keys())[0]
        token = _clean_token(tokens[target_mail])

    if not token:
        account = _resolve_login_account(case, target_mail)
        if account:
            target_mail = account.get("email") or account.get("mail") or target_mail
            token = _login_frontend_account(account)

    cookie = case.get("cookie") or ""
    if not cookie and target_mail:
        cookie = CookieManager.get_b2b_cookie(target_mail)
    if not cookie and token:
        cookie = _cookie_from_token(token)

    return target_mail, token, cookie


def _case_headers(config, case, token, cookie):
    base_url = (config.get("apiBaseUrl") or API_CONFIG.get("BASE_URL") or "").rstrip("/")
    defaults = config.get("defaults") or {}
    headers = get_b2b_headers(
        base_url,
        token,
        cookie,
        currency=case.get("currency") or defaults.get("currency") or "KRW",
        language=case.get("language") or defaults.get("language") or "korean",
        nation=case.get("nation") or defaults.get("nation") or "Korea",
    )
    headers.update({
        "origin": "https://fjx.hubbuyer.com",
        "Origin": "https://fjx.hubbuyer.com",
        "referer": "https://fjx.hubbuyer.com/",
        "adminlogintoken": "",
        "withcredentials": "true",
    })
    return headers


def request_json(base_url, path, headers, payload):
    if requests is None:
        raise RuntimeError("缺少依赖 requests，请先安装 requirements.txt")
    response = requests.post(
        base_url.rstrip("/") + path,
        json=payload or {},
        headers=headers,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    check = AssertionTool.verify_api_common(response)
    if not check["success"]:
        raise RuntimeError(check.get("message", "接口校验失败"))
    return response.json()


def _admin_login_lazy():
    from checker.api.order_audit import _admin_login
    return _admin_login()


def _build_admin_auth_headers_lazy(token):
    from checker.api.order_audit import build_admin_auth_headers
    return build_admin_auth_headers(token)


def response_data(payload):
    if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
        return payload.get("data")
    return payload if isinstance(payload, dict) else {}


def rows_from_list_data(payload):
    data = response_data(payload)
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("data", "list"):
        if isinstance(data.get(key), list):
            return data[key]
    return []


def item_uuid(item):
    if not isinstance(item, dict):
        return ""
    return str(
        item.get("uuid")
        or item.get("fjx_config_uuid")
        or item.get("check_config_uuid")
        or item.get("user_fjx_config_uuid")
        or item.get("source_uuid")
        or ""
    )


def fee_info_of(item):
    fee_info = item.get("fee_info") if isinstance(item, dict) else None
    if isinstance(fee_info, list):
        return fee_info[0] if fee_info and isinstance(fee_info[0], dict) else {}
    return fee_info if isinstance(fee_info, dict) else {}


def normalize_number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def price_of(item):
    if not isinstance(item, dict):
        return None
    fee_info = fee_info_of(item)
    for candidate in (
        item.get("user_price"),
        item.get("display_user_price"),
        item.get("price"),
        fee_info.get("user_price"),
        fee_info.get("talk_user_price"),
        fee_info.get("step_price"),
        fee_info.get("start_fee"),
    ):
        number = normalize_number(candidate)
        if number is not None:
            return number
    return None


def almost_equal(left, right, epsilon=0.01):
    a = normalize_number(left)
    b = normalize_number(right)
    return a is not None and b is not None and abs(a - b) <= epsilon


def flatten_check_fjx_list(payload):
    data = response_data(payload)
    if not isinstance(data, dict):
        data = {}
    checks = data.get("check_data") if isinstance(data.get("check_data"), list) else []
    fjx = []
    categories = data.get("fjx_data") if isinstance(data.get("fjx_data"), list) else []
    for category in categories:
        if not isinstance(category, dict):
            continue
        for item in category.get("fjx_config_data") or []:
            if isinstance(item, dict):
                fjx.append(item)
    user_fjx = data.get("user_fjx_data") if isinstance(data.get("user_fjx_data"), list) else []
    user_fjx = [item for item in user_fjx if isinstance(item, dict)]
    return {
        "checks": checks,
        "fjx": fjx,
        "userFjx": user_fjx,
        "all": (
            [{"kind": "check", "item": item} for item in checks]
            + [{"kind": "fjx", "item": item} for item in fjx]
            + [{"kind": "user_fjx", "item": item} for item in user_fjx]
        ),
        "raw": data,
    }


def find_by_key(flat, key):
    parts = str(key).split(":", 1)
    if len(parts) != 2:
        return None
    kind, uuid = parts
    for entry in flat.get("all") or []:
        if entry.get("kind") == kind and item_uuid(entry.get("item")) == str(uuid):
            return entry.get("item")
    return None


def _bucket(flat, kind):
    if kind == "check":
        return flat.get("checks") or []
    if kind == "fjx":
        return flat.get("fjx") or []
    return flat.get("userFjx") or []


def _assert_visible(flat, kind, uuid, should_be_visible, label, recorder):
    found = any(item_uuid(item) == str(uuid) for item in _bucket(flat, kind))
    recorder.assert_(
        found == should_be_visible,
        label,
        "%s:%s %s" % (kind, uuid, "未出现" if should_be_visible else "仍可见"),
    )


def run_check_fjx_assertions(flat, case, recorder):
    name = case.get("name") or "未命名用例"
    expected = case.get("expected") or {}

    min_check_count = expected.get("minCheckCount")
    if min_check_count is not None:
        recorder.assert_(
            len(flat.get("checks") or []) >= int(min_check_count),
            "%s-检品列表数量" % name,
            "check_data 数量不足，actual=%s" % len(flat.get("checks") or []),
        )

    if expected.get("requireAnyAddon"):
        addon_count = len(flat.get("fjx") or []) + len(flat.get("userFjx") or [])
        recorder.assert_(
            addon_count > 0,
            "%s-附加项至少存在一项" % name,
            "fjx_data/user_fjx_data 均为空",
        )

    for uuid in expected.get("visibleCheckUuids") or []:
        _assert_visible(flat, "check", uuid, True, "%s-check-%s可见" % (name, uuid), recorder)
    for uuid in expected.get("hiddenCheckUuids") or []:
        _assert_visible(flat, "check", uuid, False, "%s-check-%s隐藏" % (name, uuid), recorder)
    for uuid in expected.get("visibleFjxUuids") or []:
        _assert_visible(flat, "fjx", uuid, True, "%s-fjx-%s可见" % (name, uuid), recorder)
    for uuid in expected.get("hiddenFjxUuids") or []:
        _assert_visible(flat, "fjx", uuid, False, "%s-fjx-%s隐藏" % (name, uuid), recorder)
    for uuid in expected.get("visibleUserFjxUuids") or []:
        _assert_visible(flat, "user_fjx", uuid, True, "%s-user_fjx-%s可见" % (name, uuid), recorder)
    for uuid in expected.get("hiddenUserFjxUuids") or []:
        _assert_visible(flat, "user_fjx", uuid, False, "%s-user_fjx-%s隐藏" % (name, uuid), recorder)

    for key, source in (expected.get("pricingSources") or {}).items():
        item = find_by_key(flat, key)
        recorder.assert_(item is not None, "%s-%s存在" % (name, key), "目标项不存在")
        if item:
            recorder.assert_(
                str(item.get("pricing_source") or "") == str(source),
                "%s-%s价格来源" % (name, key),
                "actual=%s expected=%s" % (item.get("pricing_source"), source),
            )

    for key, expected_price in (expected.get("prices") or {}).items():
        item = find_by_key(flat, key)
        recorder.assert_(item is not None, "%s-%s存在用于价格校验" % (name, key), "目标项不存在")
        if item:
            recorder.assert_(
                almost_equal(price_of(item), expected_price),
                "%s-%s价格" % (name, key),
                "actual=%s expected=%s" % (price_of(item), expected_price),
            )

    forbidden_hits = []
    for entry in flat.get("all") or []:
        price = price_of(entry.get("item"))
        if price is None:
            continue
        for forbidden in expected.get("forbiddenPrices") or []:
            if almost_equal(price, forbidden):
                forbidden_hits.append("%s:%s=%s" % (entry.get("kind"), item_uuid(entry.get("item")), price))
    if expected.get("forbiddenPrices"):
        recorder.assert_(
            not forbidden_hits,
            "%s-旧价格不可见" % name,
            ",".join(forbidden_hits),
        )

    if expected.get("requirePricingSourceOnPricedItems"):
        missing = []
        for entry in flat.get("all") or []:
            item = entry.get("item")
            if price_of(item) is not None and not item.get("pricing_source"):
                missing.append("%s:%s" % (entry.get("kind"), item_uuid(item)))
        recorder.assert_(
            not missing,
            "%s-有价格项均带pricing_source" % name,
            ",".join(missing),
        )


def _cart_detail_ids_from_store(target_mail):
    id_file = os.path.join(DATA_DIR, "B2B_Addon_id.json")
    data = _load_json_file(id_file, {})
    rows = data.get(target_mail) or []
    ids = []
    for item in rows:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item.get("id")))
    return ids


def _first_uuid(items):
    for item in items or []:
        uid = item_uuid(item)
        if uid:
            return uid
    return ""


def run_cart_preview(config, case, headers, target_mail, recorder, flat=None):
    preview = case.get("cartPreview") or {}
    name = case.get("name") or "未命名用例"
    enabled, from_global = _is_feature_enabled("cart_preview", preview.get("enabled"))
    if not enabled:
        recorder.skip("%s-费用预览" % name, "统一开关关闭" if from_global else "未启用")
        return
    cart_ids = preview.get("cartDetailIds") or []
    if preview.get("useStoredCartDetailIds") and not cart_ids:
        cart_ids = _cart_detail_ids_from_store(target_mail)
    cart_ids = _string_ids(cart_ids)
    if not cart_ids:
        if from_global:
            recorder.fail("%s-费用预览" % name, "统一开关已开启但缺少 cartDetailIds")
        else:
            recorder.skip("%s-费用预览" % name, "缺少 cartDetailIds")
        return

    base_url = (config.get("apiBaseUrl") or API_CONFIG.get("BASE_URL") or "").rstrip("/")
    path = preview.get("path") or DEFAULT_PREVIEW_PATH
    check_uuids = list(preview.get("checkUuids") or [])
    if preview.get("checkUuid"):
        check_uuids = [preview.get("checkUuid")] + check_uuids
    fjx_uuids = list(preview.get("fjxUuids") or [])
    user_fjx_uuids = list(preview.get("userFjxUuids") or [])

    # 健康巡检模式下允许自动从 getCheckFjxList 结果里回填一组选择项，避免 40000 入参错误。
    if not check_uuids and not fjx_uuids and not user_fjx_uuids and isinstance(flat, dict):
        first_check = _first_uuid(flat.get("checks"))
        first_fjx = _first_uuid(flat.get("fjx"))
        first_user_fjx = _first_uuid(flat.get("userFjx"))
        # 仅回填一种类型，避免接口对组合参数校验失败。
        if first_check:
            check_uuids = [first_check]
        elif first_fjx:
            fjx_uuids = [first_fjx]
        elif first_user_fjx:
            user_fjx_uuids = [first_user_fjx]

    if not check_uuids and not fjx_uuids and not user_fjx_uuids:
        if from_global:
            recorder.fail("%s-费用预览" % name, "统一开关已开启但缺少 check/fjx/user_fjx 选择项")
        else:
            recorder.skip("%s-费用预览" % name, "缺少 check/fjx/user_fjx 选择项")
        return

    base_payload = {
        "cart_detail_ids": cart_ids,
        "check_uuid": check_uuids,
        "fjx_uuids": fjx_uuids,
        "user_fjx_uuids": user_fjx_uuids,
    }

    variants = [("default", base_payload)]
    # 部分环境对 check_uuid 仅接受字符串。
    if len(check_uuids) == 1:
        as_str = dict(base_payload)
        as_str["check_uuid"] = check_uuids[0]
        variants.append(("check_uuid_str", as_str))
    # 尝试按单一选择类型请求，规避组合校验导致的 40000。
    if check_uuids:
        variants.append(("check_only", {
            "cart_detail_ids": cart_ids,
            "check_uuid": [check_uuids[0]],
            "fjx_uuids": [],
            "user_fjx_uuids": [],
        }))
        variants.append(("check_only_str", {
            "cart_detail_ids": cart_ids,
            "check_uuid": check_uuids[0],
            "fjx_uuids": [],
            "user_fjx_uuids": [],
        }))
    if fjx_uuids:
        variants.append(("fjx_only", {
            "cart_detail_ids": cart_ids,
            "check_uuid": [],
            "fjx_uuids": [fjx_uuids[0]],
            "user_fjx_uuids": [],
        }))
    if user_fjx_uuids:
        variants.append(("user_fjx_only", {
            "cart_detail_ids": cart_ids,
            "check_uuid": [],
            "fjx_uuids": [],
            "user_fjx_uuids": [user_fjx_uuids[0]],
        }))

    seen = set()
    normalized_variants = []
    for label, payload in variants:
        key = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        normalized_variants.append((label, payload))

    # 兼容另一种常见命名：cart_detail_id_arr
    cart_key_variants = []
    for label, payload in normalized_variants:
        if "cart_detail_ids" in payload:
            alt = dict(payload)
            alt["cart_detail_id_arr"] = alt.pop("cart_detail_ids")
            cart_key_variants.append((label + "_cart_arr", alt))
    for label, payload in cart_key_variants:
        key = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        normalized_variants.append((label, payload))

    errors = []
    for label, payload in normalized_variants:
        try:
            response = request_json(base_url, path, headers, payload)
            recorder.pass_("%s-费用预览接口" % name, "命中策略:%s" % label)
            expected_total = preview.get("expectedTotal")
            if expected_total is not None:
                data = response_data(response)
                actual = data.get("total_check_fjx_fee") if isinstance(data, dict) else None
                recorder.assert_(
                    almost_equal(actual, expected_total),
                    "%s-费用预览合计" % name,
                    "actual=%s expected=%s" % (actual, expected_total),
                )
            return
        except Exception as e:
            errors.append("%s=%s" % (label, str(e)))

    recorder.fail(
        "%s-费用预览接口" % name,
        "所有策略失败",
        " | ".join(errors[:6]),
    )


def run_snapshot_checks(config, case, user_headers, target_mail, recorder):
    checks = case.get("snapshotChecks") or []
    name = case.get("name") or "未命名用例"
    enabled, from_global = _is_feature_enabled("snapshot", True)
    if not enabled:
        recorder.skip("%s-快照校验" % name, "统一开关关闭" if from_global else "未启用")
        return
    if not checks:
        if from_global:
            recorder.fail("%s-快照校验" % name, "统一开关已开启但未配置 snapshotChecks")
        else:
            recorder.skip("%s-快照校验" % name, "未配置")
        return

    base_url = (config.get("apiBaseUrl") or API_CONFIG.get("BASE_URL") or "").rstrip("/")
    admin_token = None
    for item in checks:
        label = "%s-%s" % (name, item.get("name") or item.get("path") or "快照")
        try:
            auth = item.get("auth") or "user"
            headers = user_headers
            if auth == "admin":
                if admin_token is None:
                    admin_token = _admin_login_lazy()
                headers = _build_admin_auth_headers_lazy(admin_token)
            path = item.get("path")
            body = dict(item.get("body") or {})
            if (path or "") == DEFAULT_CHECK_PATH and "cart_detail_id_arr" not in body:
                ids = item.get("cartDetailIds") or case.get("cartDetailIds") or []
                if item.get("useStoredCartDetailIds", case.get("useStoredCartDetailIds")):
                    ids = ids or _cart_detail_ids_from_store(target_mail)
                if ids:
                    body["cart_detail_id_arr"] = _string_ids(ids)
            response = request_json(base_url, path, headers, body)
            text = json.dumps(response, ensure_ascii=False)
            recorder.pass_("%s接口" % label)
            for expected in item.get("expectContains") or []:
                recorder.assert_(str(expected) in text, "%s包含%s" % (label, expected), "未找到关键字")
            for forbidden in item.get("expectNotContains") or []:
                recorder.assert_(str(forbidden) not in text, "%s不包含%s" % (label, forbidden), "出现禁用关键字")
        except Exception as e:
            recorder.fail(label, str(e), traceback.format_exc())





def run_service_pricing(config, case, recorder):
    probe = case.get("servicePricing") or {}
    name = case.get("name") or "未命名用例"
    enabled, from_global = _is_feature_enabled("service_pricing", probe.get("enabled"))
    if not enabled:
        recorder.skip("%s-国家服务价" % name, "统一开关关闭" if from_global else "未启用")
        return
    base_url = (config.get("apiBaseUrl") or API_CONFIG.get("BASE_URL") or "").rstrip("/")
    calls = []
    if probe.get("checkConfigUuid"):
        calls.append(("check", "/admin_b2b/serviceCountryConfig/checkList", {
            "country_code": case.get("countryCode"),
            "check_config_uuid": probe.get("checkConfigUuid"),
            "page": 1,
            "pageSize": 100,
        }))
    if probe.get("fjxConfigUuid"):
        calls.append(("fjx", "/admin_b2b/serviceCountryConfig/fjxList", {
            "country_code": case.get("countryCode"),
            "fjx_config_uuid": probe.get("fjxConfigUuid"),
            "page": 1,
            "pageSize": 100,
        }))
    if not calls:
        if from_global:
            recorder.fail("%s-国家服务价" % name, "统一开关已开启但未配置 config uuid")
        else:
            recorder.skip("%s-国家服务价" % name, "未配置 config uuid")
        return
    try:
        token = _admin_login_lazy()
        headers = _build_admin_auth_headers_lazy(token)
        for label, path, body in calls:
            response = request_json(base_url, path, headers, body)
            recorder.pass_("%s-%s国家服务价接口" % (name, label))
            if probe.get("expectNoBlankMemberLevel"):
                blank = [
                    str(row.get("id") or row.get("uuid") or "unknown")
                    for row in rows_from_list_data(response)
                    if not row.get("member_level_uuid")
                ]
                recorder.assert_(not blank, "%s-%s国家服务价无空会员等级" % (name, label), ",".join(blank))
    except Exception as e:
        recorder.fail("%s-国家服务价" % name, str(e), traceback.format_exc())


def run_ship_fjx_checks(config, case, recorder):
    checks = case.get("shipFjxChecks") or []
    name = case.get("name") or "未命名用例"
    enabled, from_global = _is_feature_enabled("ship_fjx", True)
    if not enabled:
        recorder.skip("%s-发货附加项" % name, "统一开关关闭" if from_global else "未启用")
        return
    if not checks:
        if from_global:
            recorder.fail("%s-发货附加项" % name, "统一开关已开启但未配置 shipFjxChecks")
        else:
            recorder.skip("%s-发货附加项" % name, "未配置")
        return
    base_url = (config.get("apiBaseUrl") or API_CONFIG.get("BASE_URL") or "").rstrip("/")
    try:
        token = _admin_login_lazy()
        headers = _build_admin_auth_headers_lazy(token)
        for check in checks:
            label = "%s-%s" % (name, check.get("name") or "发货附加项")
            path = check.get("path") or "/admin_b2b/shipOrderDetail/fjxList"
            response = request_json(base_url, path, headers, check.get("body") or {})
            data = response_data(response)
            fjx = data.get("fjx_data") if isinstance(data, dict) and isinstance(data.get("fjx_data"), list) else []
            user_fjx = data.get("user_fjx_data") if isinstance(data, dict) and isinstance(data.get("user_fjx_data"), list) else []
            recorder.pass_("%s接口" % label)
            if check.get("requireAnyShipAddon", True):
                recorder.assert_(len(fjx) + len(user_fjx) > 0, "%s至少存在一项" % label, "fjx_data/user_fjx_data 均为空")
            required_sources = set(str(x) for x in check.get("requiredPricingSources") or [])
            if required_sources:
                actual_sources = set(str(item.get("pricing_source") or "") for item in fjx + user_fjx if isinstance(item, dict))
                recorder.assert_(required_sources.issubset(actual_sources), "%s价格来源覆盖" % label, "actual=%s expected=%s" % (sorted(actual_sources), sorted(required_sources)))
    except Exception as e:
        recorder.fail("%s-发货附加项" % name, str(e), traceback.format_exc())


def run_case(config, case, task_config, recorder):
    name = case.get("name") or "未命名用例"
    if case.get("enabled") is False:
        recorder.skip(name, "用例关闭")
        return

    target_mail, token, cookie = resolve_user_credentials(case, task_config)
    if not token or not cookie:
        recorder.fail("%s-凭据" % name, "缺失 B2B token/cookie")
        return

    base_url = (config.get("apiBaseUrl") or API_CONFIG.get("BASE_URL") or "").rstrip("/")
    headers = _case_headers(config, case, token, cookie)
    flat = None
    try:
        payload = case.get("checkFjxListPayload")
        if payload is None:
            payload = {}
            ids = case.get("cartDetailIds") or []
            if case.get("useStoredCartDetailIds"):
                ids = ids or _cart_detail_ids_from_store(target_mail)
            if ids:
                payload["cart_detail_id_arr"] = _string_ids(ids)
        response = request_json(base_url, case.get("checkFjxListPath") or DEFAULT_CHECK_PATH, headers, payload)
        recorder.pass_("%s-附加项列表接口" % name)
        flat = flatten_check_fjx_list(response)
        run_check_fjx_assertions(flat, case, recorder)
    except Exception as e:
        recorder.fail("%s-附加项列表接口" % name, str(e), traceback.format_exc())

    run_snapshot_checks(config, case, headers, target_mail, recorder)
    run_service_pricing(config, case, recorder)
    run_ship_fjx_checks(config, case, recorder)


def run(task_config=None):
    task_config = task_config or {}
    recorder = InspectionRecorder()
    try:
        config = load_config(task_config)
        cases = config.get("cases") or []
        if not cases:
            recorder.fail("配置", "member_pricing_complete_chain.json 未配置 cases")
        for case in cases:
            if isinstance(case, dict):
                run_case(config, case, task_config, recorder)
    except Exception as e:
        recorder.fail("执行异常", "%s: %s" % (type(e).__name__, e), traceback.format_exc())
    return emit_result(recorder.to_result(CHECKPOINT_TITLE))


if __name__ == "__main__":
    cfg = {}
    if len(sys.argv) > 1:
        try:
            cfg = json.loads(sys.argv[1])
        except (TypeError, ValueError):
            cfg = {}
    run(cfg)
