# -*- coding: utf-8 -*-
"""
7182 Open API functional smoke test.

This script is for interface/acceptance testing, not performance testing.
Secrets are read from environment variables or CLI arguments and are never
written to the result file.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests


DEFAULT_BASE_URL = "https://main-api.hubbuyer.com"
DEFAULT_CLIENT_KEY = "hubbuyer-JPN62"
DEFAULT_KEYWORD = "クリスマス"
RESULT_DIR = Path(__file__).resolve().parent / "接口执行结果"


def _mask(value):
    if not value:
        return ""
    value = str(value)
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def _now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _absolute_url(base_url, path):
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _json_path(data, path, default=None):
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _extract_access_token(body):
    if not isinstance(body, dict):
        return ""
    data = body.get("data", {})
    candidates = [
        body.get("access_token"),
        body.get("token"),
        data.get("access_token") if isinstance(data, dict) else "",
        data.get("token") if isinstance(data, dict) else "",
    ]
    return next((str(item).strip() for item in candidates if item), "")


def _extract_offer_ids(body):
    items = _json_path(body, "data.items", [])
    if not isinstance(items, list):
        return []
    return [
        str(item.get("offer_id")).strip()
        for item in items
        if isinstance(item, dict) and item.get("offer_id")
    ]


def _code(body):
    if not isinstance(body, dict):
        return None
    return body.get("code", body.get("status"))


class SmokeRunner:
    def __init__(self, args):
        self.args = args
        self.session = requests.Session()
        self.session.trust_env = False
        self.results = []

    def post_json(
        self,
        case_id,
        path,
        payload,
        token="",
        expected_http=None,
        expected_code=None,
        expected_status_or_code=None,
    ):
        url = _absolute_url(self.args.base_url, path)
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Request-Id": f"codex-{uuid.uuid4().hex}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token.replace('Bearer ', '').strip()}"

        started = time.perf_counter()
        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.args.timeout,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            try:
                body = response.json()
            except Exception as exc:
                body = {}
                self.record(case_id, path, False, elapsed_ms, response.status_code, None, f"JSON parse failed: {exc}")
                return False, body

            checks = []
            if expected_http is not None:
                checks.append((response.status_code == expected_http, f"HTTP expected {expected_http}, got {response.status_code}"))
            if expected_code is not None:
                checks.append((_code(body) == expected_code, f"code expected {expected_code}, got {_code(body)}"))
            if expected_status_or_code is not None:
                allowed = expected_status_or_code
                if not isinstance(allowed, (list, tuple, set)):
                    allowed = [allowed]
                allowed = set(allowed)
                actual_code = _code(body)
                checks.append((
                    response.status_code in allowed or actual_code in allowed,
                    f"HTTP/code expected one of {sorted(allowed)}, got HTTP {response.status_code}, code {actual_code}",
                ))

            failed = [message for ok, message in checks if not ok]
            ok = not failed
            self.record(
                case_id,
                path,
                ok,
                elapsed_ms,
                response.status_code,
                _code(body),
                "; ".join(failed),
                trace_id=_json_path(body, "data.trace_id") or body.get("trace_id"),
            )
            return ok, body
        except requests.RequestException as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self.record(case_id, path, False, elapsed_ms, None, None, str(exc))
            return False, {}

    def post_form(self, case_id, path, payload, expected_http=None, expected_code=None):
        url = _absolute_url(self.args.base_url, path)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Request-Id": f"codex-{uuid.uuid4().hex}",
        }

        started = time.perf_counter()
        try:
            response = self.session.post(
                url,
                headers=headers,
                data=payload,
                timeout=self.args.timeout,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            try:
                body = response.json()
            except Exception as exc:
                body = {}
                self.record(case_id, path, False, elapsed_ms, response.status_code, None, f"JSON parse failed: {exc}")
                return False, body

            checks = []
            if expected_http is not None:
                checks.append((response.status_code == expected_http, f"HTTP expected {expected_http}, got {response.status_code}"))
            if expected_code is not None:
                checks.append((_code(body) == expected_code, f"code expected {expected_code}, got {_code(body)}"))

            failed = [message for ok, message in checks if not ok]
            ok = not failed
            self.record(
                case_id,
                path,
                ok,
                elapsed_ms,
                response.status_code,
                _code(body),
                "; ".join(failed),
                trace_id=_json_path(body, "data.trace_id") or body.get("trace_id"),
            )
            return ok, body
        except requests.RequestException as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self.record(case_id, path, False, elapsed_ms, None, None, str(exc))
            return False, {}

    def record(self, case_id, path, passed, elapsed_ms, http_status, business_code, error="", trace_id=""):
        self.results.append({
            "case_id": case_id,
            "path": path,
            "passed": passed,
            "elapsed_ms": elapsed_ms,
            "http_status": http_status,
            "business_code": business_code,
            "trace_id": trace_id or "",
            "error": error or "",
        })

    def get_token(self):
        if self.args.access_token:
            self.results.append({
                "case_id": "TC-AUTH-000",
                "path": "/open_api/v1/auth/token",
                "passed": True,
                "elapsed_ms": 0,
                "http_status": None,
                "business_code": None,
                "trace_id": "",
                "error": "Using OPEN_API_ACCESS_TOKEN, token request skipped.",
            })
            return self.args.access_token.replace("Bearer ", "").strip()

        if not self.args.client_secret:
            self.results.append({
                "case_id": "TC-AUTH-000",
                "path": "/open_api/v1/auth/token",
                "passed": False,
                "elapsed_ms": 0,
                "http_status": None,
                "business_code": None,
                "trace_id": "",
                "error": "Missing OPEN_API_CLIENT_SECRET or OPEN_API_ACCESS_TOKEN.",
            })
            return ""

        token_payload = {
            "client_key": self.args.client_key,
            "client_secret": self.args.client_secret,
        }
        if self.args.auth_body_type == "json":
            ok, body = self.post_json(
                "TC-AUTH-001",
                "/open_api/v1/auth/token",
                token_payload,
                expected_http=200,
                expected_code=200,
            )
        else:
            ok, body = self.post_form(
                "TC-AUTH-001",
                "/open_api/v1/auth/token",
                token_payload,
                expected_http=200,
                expected_code=200,
            )
        token = _extract_access_token(body)
        if ok and token:
            return token
        self.results[-1]["passed"] = False
        if ok:
            self.results[-1]["error"] = "Token response did not include access_token."
        return ""

    def run_positive_cases(self):
        token = self.get_token()
        if not token:
            return

        search_payload = {
            "keyword": self.args.keyword,
            "keyword_language": "ja",
            "response_language": "ja",
            "page": 1,
            "page_size": self.args.page_size,
            "include_detail": False,
        }
        ok, search_body = self.post_json(
            "TC-SRCH-001",
            "/open_api/v1/product/search",
            search_payload,
            token=token,
            expected_http=200,
            expected_code=200,
        )

        offer_ids = _extract_offer_ids(search_body)
        if ok and not offer_ids:
            self.results[-1]["passed"] = False
            self.results[-1]["error"] = "Search response did not include data.items[].offer_id."

        offer_id = self.args.offer_id or (offer_ids[0] if offer_ids else "")
        if not offer_id:
            self.record(
                "TC-DET-001",
                "/open_api/v1/product/detail",
                False,
                0,
                None,
                None,
                "No offer_id available from search and OPEN_API_OFFER_ID was not provided.",
            )
            return

        detail_payload = {
            "offer_id": offer_id,
            "response_language": "ja",
            "include_sku": True,
            "include_html_detail": False,
        }
        ok, detail_body = self.post_json(
            "TC-DET-001",
            "/open_api/v1/product/detail",
            detail_payload,
            token=token,
            expected_http=200,
            expected_code=200,
        )
        detail_offer_id = str(_json_path(detail_body, "data.offer_id", "")).strip()
        if ok and detail_offer_id and detail_offer_id != str(offer_id):
            self.results[-1]["passed"] = False
            self.results[-1]["error"] = f"Detail offer_id mismatch: expected {offer_id}, got {detail_offer_id}."

    def run_negative_cases(self):
        self.post_json(
            "TC-AUTH-005",
            "/open_api/v1/product/search",
            {
                "keyword": self.args.keyword,
                "keyword_language": "ja",
                "response_language": "ja",
                "page": 1,
                "page_size": 20,
            },
            expected_status_or_code=401,
        )
        self.post_json(
            "TC-SRCH-003",
            "/open_api/v1/product/search",
            {
                "keyword": "",
                "keyword_language": "ja",
                "response_language": "ja",
                "page": 1,
                "page_size": 20,
            },
            token=self.args.access_token.replace("Bearer ", "").strip() if self.args.access_token else "",
            expected_status_or_code=400 if self.args.access_token else 401,
        )

    def save(self):
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = RESULT_DIR / f"7182_open_api_smoke_{stamp}.json"
        summary = {
            "generated_at": _now(),
            "base_url": self.args.base_url,
            "client_key": self.args.client_key,
            "client_secret": _mask(self.args.client_secret),
            "access_token": _mask(self.args.access_token),
            "keyword": self.args.keyword,
            "offer_id": self.args.offer_id,
            "results": self.results,
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for item in self.results if item["passed"]),
                "failed": sum(1 for item in self.results if not item["passed"]),
            },
        }
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return path, summary


def parse_args():
    parser = argparse.ArgumentParser(description="7182 Open API functional smoke test")
    parser.add_argument("--base-url", default=os.getenv("OPEN_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--client-key", default=os.getenv("OPEN_API_CLIENT_KEY", DEFAULT_CLIENT_KEY))
    parser.add_argument("--client-secret", default=os.getenv("OPEN_API_CLIENT_SECRET", ""))
    parser.add_argument("--access-token", default=os.getenv("OPEN_API_ACCESS_TOKEN", ""))
    parser.add_argument("--keyword", default=os.getenv("OPEN_API_KEYWORD", DEFAULT_KEYWORD))
    parser.add_argument("--offer-id", default=os.getenv("OPEN_API_OFFER_ID", ""))
    parser.add_argument("--page-size", type=int, default=int(os.getenv("OPEN_API_PAGE_SIZE", "20")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("OPEN_API_TIMEOUT", "30")))
    parser.add_argument(
        "--auth-body-type",
        choices=["form", "json"],
        default=os.getenv("OPEN_API_AUTH_BODY_TYPE", "form").strip().lower(),
        help="Token request body type. Developer curl sample uses form.",
    )
    parser.add_argument("--negative-only", action="store_true")
    parser.add_argument("--skip-negative", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    runner = SmokeRunner(args)

    if args.negative_only:
        runner.run_negative_cases()
    else:
        runner.run_positive_cases()
        if not args.skip_negative:
            runner.run_negative_cases()

    path, summary = runner.save()
    print(f"Result file: {path}")
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))

    failed = summary["summary"]["failed"]
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
