# -*- coding: utf-8 -*-
"""
7182 Open API 商品搜索接口压测入口。

目标接口:
    POST /open_api/v1/product/search

启动示例:
    $env:OPEN_API_ACCESS_TOKEN = "Bearer xxxxx"
    locust -f locustfile_open_api_search.py --headless -u 50 -r 5 -t 5m

可选环境变量:
    OPEN_API_BASE_URL=https://main-api.hubbuyer.com
    OPEN_API_ACCESS_TOKEN=Bearer xxxxx
    OPEN_API_ENABLE_DETAIL_FLOW=true
    OPEN_API_DETAIL_REQUESTS_PER_SEARCH=4
    OPEN_API_KEYWORD=裤子
    OPEN_API_KEYWORD_LANGUAGE=ja
    OPEN_API_PAGE=2
    OPEN_API_PAGE_SIZE=20
    OPEN_API_PRICE_MIN=10
    OPEN_API_PRICE_MAX=50
    OPEN_API_SHIP_TIME=24h
    OPEN_API_SORT=sales_desc
    OPEN_API_INCLUDE_DETAIL=false
    OPEN_API_CERTIFIED_FACTORY=false
    OPEN_API_ONE_PIECE_DROPSHIP=false
    OPEN_API_NEW_ARRIVAL_7D=false
    OPEN_API_SELECTION_1688=false
    OPEN_API_DETAIL_RESPONSE_LANGUAGE=ja
    OPEN_API_DETAIL_INCLUDE_SKU=true
    OPEN_API_DETAIL_INCLUDE_HTML_DETAIL=false
    OPEN_API_SEARCH_PAYLOAD={...}
"""
import json
import os
import random
import uuid

from locust import HttpUser, constant_throughput, task


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name, default):
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _json_path(data, path, default=None):
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _normalize_token(token):
    cleaned = str(token or "").strip()
    if not cleaned:
        return ""
    if cleaned.lower().startswith("bearer "):
        return cleaned
    return f"Bearer {cleaned}"


def _parse_keywords():
    raw_keywords = os.getenv("OPEN_API_KEYWORDS", "").strip()
    if raw_keywords:
        keywords = [item.strip() for item in raw_keywords.split(",") if item.strip()]
        if keywords:
            return keywords
    return [os.getenv("OPEN_API_KEYWORD", "裤子")]


def _build_payload():
    raw_payload = os.getenv("OPEN_API_SEARCH_PAYLOAD", "").strip()
    if raw_payload:
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OPEN_API_SEARCH_PAYLOAD 不是合法 JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("OPEN_API_SEARCH_PAYLOAD 必须是 JSON 对象")
        return payload

    return {
        "keyword": os.getenv("OPEN_API_KEYWORD", "裤子"),
        "keyword_language": os.getenv("OPEN_API_KEYWORD_LANGUAGE", "ja"),
        "page": _env_int("OPEN_API_PAGE", 2),
        "page_size": _env_int("OPEN_API_PAGE_SIZE", 20),
        "price_min": _env_int("OPEN_API_PRICE_MIN", 10),
        "price_max": _env_int("OPEN_API_PRICE_MAX", 50),
        "ship_time": os.getenv("OPEN_API_SHIP_TIME", "24h"),
        "include_detail": _env_bool("OPEN_API_INCLUDE_DETAIL", False),
        "certified_factory": _env_bool("OPEN_API_CERTIFIED_FACTORY", False),
        "one_piece_dropship": _env_bool("OPEN_API_ONE_PIECE_DROPSHIP", False),
        "new_arrival_7d": _env_bool("OPEN_API_NEW_ARRIVAL_7D", False),
        "selection_1688": _env_bool("OPEN_API_SELECTION_1688", False),
        "sort": os.getenv("OPEN_API_SORT", "sales_desc"),
    }


def _extract_offer_ids(body):
    data = body.get("data") or {}
    items = data.get("items") or []
    if not isinstance(items, list):
        return []
    return [
        str(item.get("offer_id")).strip()
        for item in items
        if isinstance(item, dict) and item.get("offer_id")
    ]


def _validate_search_structure(body):
    if not isinstance(body, dict):
        return "响应体不是 JSON 对象"

    data = body.get("data")
    if not isinstance(data, dict):
        return "缺少 data 对象"

    items = data.get("items")
    if not isinstance(items, list):
        return "缺少 data.items 列表"
    if not items:
        return "data.items 为空，无法联动详情接口"

    sample = items[0]
    if not isinstance(sample, dict):
        return "data.items[0] 不是对象"

    required_fields = ["offer_id", "title_ja", "image_url", "product_url"]
    missing = [field for field in required_fields if field not in sample]
    if missing:
        return f"搜索结果缺少关键字段: {', '.join(missing)}"
    return ""


def _validate_detail_structure(body, expected_offer_id):
    if not isinstance(body, dict):
        return "响应体不是 JSON 对象"

    data = body.get("data")
    if not isinstance(data, dict):
        return "缺少 data 对象"

    actual_offer_id = str(data.get("offer_id") or "").strip()
    if actual_offer_id != expected_offer_id:
        return f"详情接口返回 offer_id 不匹配: expected={expected_offer_id} actual={actual_offer_id}"

    required_fields = ["title_ja", "images", "price", "seller", "service_tags_ja"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return f"详情结果缺少关键字段: {', '.join(missing)}"

    if not isinstance(data.get("images"), list):
        return "data.images 不是数组"
    if not isinstance(data.get("service_tags_ja"), list):
        return "data.service_tags_ja 不是数组"

    include_sku = _env_bool("OPEN_API_DETAIL_INCLUDE_SKU", True)
    if include_sku and not isinstance(data.get("skus"), list):
        return "include_sku=true 时 data.skus 不是数组"

    return ""


class OpenApiSearchUser(HttpUser):
    wait_time = constant_throughput(_env_int("OPEN_API_TASKS_PER_USER_PER_SECOND", 1))
    host = os.getenv("OPEN_API_BASE_URL", "https://main-api.hubbuyer.com").rstrip("/")

    def on_start(self):
        token = _normalize_token(os.getenv("OPEN_API_ACCESS_TOKEN", ""))
        if not token:
            raise RuntimeError("缺少 OPEN_API_ACCESS_TOKEN，无法发起压测")

        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": token,
        }
        self.payload = _build_payload()
        self.keywords = _parse_keywords()
        self.enable_detail_flow = _env_bool("OPEN_API_ENABLE_DETAIL_FLOW", True)
        self.detail_requests_per_search = max(0, _env_int("OPEN_API_DETAIL_REQUESTS_PER_SEARCH", 4))
        self.detail_payload_template = {
            "response_language": os.getenv("OPEN_API_DETAIL_RESPONSE_LANGUAGE", "ja"),
            "include_sku": _env_bool("OPEN_API_DETAIL_INCLUDE_SKU", True),
            "include_html_detail": _env_bool("OPEN_API_DETAIL_INCLUDE_HTML_DETAIL", False),
        }

    def _request_detail(self, offer_id):
        detail_payload = dict(self.detail_payload_template)
        detail_payload["offer_id"] = offer_id
        detail_headers = dict(self.headers)
        detail_headers["X-Request-Id"] = f"locust-{uuid.uuid4().hex}"

        with self.client.post(
            "/open_api/v1/product/detail",
            json=detail_payload,
            headers=detail_headers,
            name="POST /open_api/v1/product/detail",
            catch_response=True,
        ) as detail_response:
            try:
                detail_body = detail_response.json()
            except ValueError:
                detail_response.failure(
                    f"响应不是合法 JSON，HTTP {detail_response.status_code}: {detail_response.text[:300]}"
                )
                return

            if detail_response.status_code != 200:
                detail_response.failure(f"HTTP {detail_response.status_code}: {detail_body}")
                return

            if detail_body.get("code") != 200:
                detail_response.failure(f"业务码异常: code={detail_body.get('code')} body={detail_body}")
                return

            structure_error = _validate_detail_structure(detail_body, offer_id)
            if structure_error:
                detail_response.failure(structure_error)
                return

            detail_response.success()

    @task
    def search_product(self):
        headers = dict(self.headers)
        headers["X-Request-Id"] = f"locust-{uuid.uuid4().hex}"
        payload = dict(self.payload)
        payload["keyword"] = random.choice(self.keywords)
        with self.client.post(
            "/open_api/v1/product/search",
            json=payload,
            headers=headers,
            name="POST /open_api/v1/product/search",
            catch_response=True,
        ) as response:
            try:
                body = response.json()
            except ValueError:
                response.failure(f"响应不是合法 JSON，HTTP {response.status_code}: {response.text[:300]}")
                return

            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {body}")
                return

            if body.get("code") != 200:
                response.failure(f"业务码异常: code={body.get('code')} body={body}")
                return

            structure_error = _validate_search_structure(body)
            if structure_error:
                response.failure(structure_error)
                return

            offer_ids = _extract_offer_ids(body)
            response.success()

        if self.enable_detail_flow:
            for _ in range(self.detail_requests_per_search):
                self._request_detail(random.choice(offer_ids))