# -*- coding: utf-8 -*-
# checker/api/onebound_daily_stats.py
# 万邦控制台：拉取指定日期 API 调用次数统计（巡检默认取前一日）
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

import requests

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import REQUEST_TIMEOUT_API

DATA_FILE = os.path.join(root_path, "config", "data", "onebound_daily_stats.json")
DEFAULT_HEADERS = {
    "accept": "*/*",
    "origin": "https://console.open.onebound.cn",
    "referer": "https://console.open.onebound.cn/console/?go=api_log_use&do=browse&",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
}


class CaptchaRecognitionError(RuntimeError):
    """Raised when a Onebound captcha cannot be fetched or recognized."""


def _fetch_captcha(session, base_url, timeout):
    url = f"{base_url.rstrip('/')}/index.php?go=front&do=authcode"
    resp = session.get(
        url,
        params={"_": int(time.time() * 1000)},
        headers={
            **DEFAULT_HEADERS,
            "referer": f"{base_url.rstrip('/')}/?go=login&do=login",
        },
        timeout=timeout,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    content_type = str(resp.headers.get("content-type") or "").lower()
    image_bytes = resp.content or b""
    if not image_bytes or not content_type.startswith("image/"):
        raise CaptchaRecognitionError("Onebound captcha image response is invalid")
    return image_bytes


def _recognize_captcha(image_bytes, ocr=None):
    if ocr is None:
        try:
            import ddddocr
        except ImportError as exc:
            raise CaptchaRecognitionError(
                "Onebound captcha OCR dependency is unavailable; install ddddocr"
            ) from exc
        ocr = ddddocr.DdddOcr(show_ad=False)

    ocr.set_ranges("0123456789")
    value = str(ocr.classification(image_bytes) or "").strip()
    if not re.fullmatch(r"\d{4}", value):
        raise CaptchaRecognitionError("Onebound captcha OCR did not return four digits")
    return value


def _load_config():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_session(cfg, timeout, ocr=None):
    login_cfg = cfg.get("login") or {}
    username = str(login_cfg.get("username") or "").strip()
    password = str(login_cfg.get("password") or "").strip()
    base_url = cfg.get("console_base_url", "https://console.open.onebound.cn/console/").rstrip("/")

    if username and password:
        session = requests.Session()
        session.trust_env = False
        login_url = f"{base_url}/?go=front&do=login"
        try:
            max_attempts = int(login_cfg.get("captcha_max_attempts", 3))
        except (TypeError, ValueError):
            max_attempts = 3
        if max_attempts <= 0:
            max_attempts = 3

        last_recognition_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                image_bytes = _fetch_captcha(session, base_url, timeout)
                authcode = _recognize_captcha(image_bytes, ocr=ocr)
            except CaptchaRecognitionError as exc:
                last_recognition_error = exc
                if attempt == max_attempts:
                    category = (
                        "captcha acquisition"
                        if "image response" in str(exc)
                        else "OCR"
                    )
                    raise RuntimeError(
                        f"Onebound captcha {category} failed after {max_attempts} attempts"
                    ) from exc
                continue

            resp = session.post(
                login_url,
                data={
                    "username": username,
                    "password": password,
                    "authcode": authcode,
                },
                headers={
                    **DEFAULT_HEADERS,
                    "referer": f"{base_url}/?go=login&do=login",
                    "content-type": "application/x-www-form-urlencoded",
                },
                timeout=timeout,
                proxies={"http": None, "https": None},
            )
            resp.raise_for_status()
            body = resp.text.strip()
            if not body.startswith("{"):
                raise RuntimeError("Onebound login returned a non-JSON response")
            payload = resp.json()
            status = payload.get("status")
            if status not in (0, "0", False, None):
                return session

            error = str(
                (payload.get("data") or {}).get("error")
                or payload.get("error_msg")
                or "unknown error"
            )
            error_lower = error.lower()
            is_captcha_error = (
                "验证码" in error
                or "图形码" in error
                or "captcha" in error_lower
                or "authcode" in error_lower
            )
            if not is_captcha_error:
                raise RuntimeError(f"Onebound login failed: {error}")
            if attempt == max_attempts:
                raise RuntimeError(
                    f"Onebound captcha rejected after {max_attempts} attempts"
                )

        raise RuntimeError(
            f"Onebound captcha OCR failed after {max_attempts} attempts: "
            f"{type(last_recognition_error).__name__}"
        )

    cookies = cfg.get("cookies") or {}
    if not cookies.get("PHPSESSID"):
        raise RuntimeError(
            "请在 config/data/onebound_daily_stats.json 配置 login.username/password，"
            "或手动填写 cookies.PHPSESSID"
        )
    session = requests.Session()
    session.trust_env = False
    session.cookies.update(cookies)
    return session


def _apply_api_key_cookie(session, cfg):
    api_key = cfg.get("api_key_cookie") or (cfg.get("cookies") or {}).get("api_key")
    if api_key:
        session.cookies.set("api_key", api_key, domain=".onebound.cn")


def _select_map(field_meta):
    from_type = (field_meta or {}).get("FromType") or []
    if len(from_type) >= 2 and isinstance(from_type[1], dict):
        return from_type[1]
    return {}


def _fetch_browse_page(base_url, session, headers, page, page_size, timeout):
    url = f"{base_url.rstrip('/')}/?go=api_log_use&do=browse"
    resp = session.post(
        url,
        params={"page": page, "size": page_size},
        headers=headers,
        timeout=timeout,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    body = resp.text.strip()
    if not body.startswith("{"):
        raise RuntimeError(f"万邦控制台返回非 JSON，可能 Cookie 已失效: {body[:120]}")
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("万邦控制台响应格式异常")
    return data


def _resolve_stats_date(cfg):
    """巡检脚本通常早上 8 点执行，默认统计前一日完整数据。"""
    offset_days = int(cfg.get("stats_date_offset_days", -1))
    return (datetime.now() + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def _collect_date_rows(base_url, session, headers, page_size, max_pages, timeout, target_date):
    matched_rows = []
    field_meta = {}

    for page in range(1, max_pages + 1):
        data = _fetch_browse_page(base_url, session, headers, page, page_size, timeout)
        field_meta = data.get("TI") or field_meta
        rows = data.get("dataArray") or []
        if not rows:
            break

        hit_older_than_target = False
        for row in rows:
            log_date = str(row.get("log_date") or "")
            if log_date == target_date:
                matched_rows.append(row)
            elif log_date and log_date < target_date:
                hit_older_than_target = True
        if hit_older_than_target:
            break

    return target_date, matched_rows, field_meta


def _aggregate_rows(date_rows, field_meta):
    key_map = _select_map(field_meta.get("api_key_id"))
    type_map = _select_map(field_meta.get("api_type_id"))
    name_map = _select_map(field_meta.get("api_name_id"))

    grouped = defaultdict(lambda: {"use_real": 0, "use_all": 0, "use_cache": 0})
    total = {"use_real": 0, "use_all": 0, "use_cache": 0}

    for row in date_rows:
        api_key = key_map.get(str(row.get("api_key_id")), row.get("api_key_id"))
        api_type = type_map.get(str(row.get("api_type_id")), row.get("api_type_id"))
        api_name = name_map.get(str(row.get("api_name_id")), row.get("api_name_id"))
        label = f"{api_key}/{api_type}/{api_name}"

        use_real = int(row.get("use_real") or 0)
        use_all = int(row.get("use_all") or 0)
        use_cache = int(row.get("use_cache") or 0)

        grouped[label]["use_real"] += use_real
        grouped[label]["use_all"] += use_all
        grouped[label]["use_cache"] += use_cache

        total["use_real"] += use_real
        total["use_all"] += use_all
        total["use_cache"] += use_cache

    return grouped, total


def _format_message(stats_date, grouped, total):
    if not grouped:
        return f"{stats_date} 暂无调用记录"

    summary = (
        f"{stats_date} 合计 实际:{total['use_real']} 总计:{total['use_all']} 缓存:{total['use_cache']}"
    )
    details = []
    for label in sorted(grouped.keys()):
        item = grouped[label]
        details.append(
            f"{label} 实际:{item['use_real']} 总计:{item['use_all']} 缓存:{item['use_cache']}"
        )
    return summary + " | " + " | ".join(details)


def run_onebound_daily_stats_check(task_config=None):
    try:
        cfg = _load_config()
        base_url = cfg.get("console_base_url", "https://console.open.onebound.cn/console/")
        page_size = int(cfg.get("page_size", 100))
        max_pages = int(cfg.get("max_pages", 10))
        timeout = int(cfg.get("request_timeout", REQUEST_TIMEOUT_API))

        session = _build_session(cfg, timeout)
        _apply_api_key_cookie(session, cfg)

        stats_date = _resolve_stats_date(cfg)
        stats_date, date_rows, field_meta = _collect_date_rows(
            base_url, session, DEFAULT_HEADERS, page_size, max_pages, timeout, stats_date
        )
        grouped, total = _aggregate_rows(date_rows, field_meta)
        message = _format_message(stats_date, grouped, total)

        result = {
            "success": True,
            "message": message,
            "status_code": 200,
            "expected": f"成功拉取万邦 {stats_date} 调用统计",
            "actual": message,
            "stats": {
                "date": stats_date,
                "total": total,
                "details": dict(grouped),
            },
        }
    except Exception as e:
        result = {
            "success": False,
            "message": f"万邦调用统计失败: {type(e).__name__}: {e}",
            "status_code": 500,
            "expected": "成功拉取万邦前日调用统计",
            "actual": str(e),
        }

    print(json.dumps(result, ensure_ascii=False))
    return result


run = run_onebound_daily_stats_check


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
            run_onebound_daily_stats_check(task_config=task_config)
            sys.exit(0)
        except (json.JSONDecodeError, ValueError):
            pass
    run_onebound_daily_stats_check()
