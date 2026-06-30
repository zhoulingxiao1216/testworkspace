#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TC-SEC-XSS-001：报价导出 Excel 公式注入验证

流程：
  1. updateSkuNumberData 写入 custom_sku 公式 payload
  2. quote/create 创建报价单
  3. （可选）校验已下载的 xlsx

用法：
  set HUBBUYER_TOKEN=eyJ...
  python xss001_quote_formula_test.py --cart-detail-id 48949 --payload "=HYPERLINK(...)"

  # 批量跑用例要求的 3 类前缀 + 正常对照
  python xss001_quote_formula_test.py --cart-detail-id 48949 --all-payloads

  # 校验浏览器导出的 Excel
  python xss001_quote_formula_test.py --check-xlsx D:\\Downloads\\quote.xlsx
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

API_BASE = os.getenv("HUBBUYER_API_BASE", "https://main-api.hubbuyer.com")
B2B_ORIGIN = os.getenv("HUBBUYER_B2B_ORIGIN", "https://main-b2b.hubbuyer.com")
TIMEOUT = 30
PROXIES = {"http": None, "https": None}

PAYLOADS = [
    ("hyperlink", '=HYPERLINK("http://evil.example.com","click")'),
    ("plus_cmd", "+cmd|' /C calc'!A0"),
    ("at_sum", "@SUM(1+1)"),
    ("normal", "NORMAL-SKU-20260617"),
]


def build_headers(token: str) -> dict:
    clean = token.replace("Bearer ", "").strip()
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": clean,
        "content-type": "application/json",
        "currency": "USD",
        "language": "korean",
        "logintype": "user",
        "nation": "Korea",
        "origin": B2B_ORIGIN,
        "referer": f"{B2B_ORIGIN}/",
        "rate": "0.16",
        "withcredentials": "true",
        "user-agent": "TC-SEC-XSS-001/1.0",
    }


def post_json(session: requests.Session, path: str, payload: dict) -> dict:
    url = f"{API_BASE}{path}"
    resp = session.post(url, json=payload, timeout=TIMEOUT, verify=False, proxies=PROXIES)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:500]}
    if resp.status_code != 200:
        raise RuntimeError(f"{path} HTTP {resp.status_code}: {body}")
    code = body.get("code")
    if code not in (0, 200, "0", "200"):
        raise RuntimeError(f"{path} business error code={code}: {body}")
    return body


def update_custom_sku(session: requests.Session, cart_detail_id: int, sku: str) -> dict:
    payload = {
        "cart_detail_id": cart_detail_id,
        "custom_sku": {"sku": sku},
        "amazon_sku": {
            "sku": "",
            "url": "",
            "asin": "",
            "fnsku": "",
            "child_id": "",
        },
        "self_sku": [],
    }
    return post_json(session, "/api_b2b/cartQuoteStep1/updateSkuNumberData", payload)


def create_quote(
    session: requests.Session,
    cart_detail_ids: list[int],
    quote_type: int,
    logistics_config_id: int,
) -> str:
    payload = {
        "quote_type": quote_type,
        "logistics_config_id": logistics_config_id,
        "cart_detail_id_arr": cart_detail_ids,
    }
    body = post_json(session, "/api_b2b/quote/create", payload)
    data = body.get("data") or {}
    quote_no = data.get("quote_no") or data.get("quoteNo") or data.get("order_no") or ""
    if not quote_no:
        raise RuntimeError(f"quote/create 未返回 quote_no: {body}")
    return quote_no


def check_xlsx(path: Path, expected_values: list[str] | None = None) -> list[dict]:
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("请先安装 openpyxl: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(path, data_only=False)
    findings: list[dict] = []
    targets = set(expected_values or [])
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=1, values_only=False):
            for cell in row:
                val = cell.value
                if val is None:
                    continue
                text = str(val)
                if targets and text not in targets:
                    continue
                if not targets and not text.startswith(("=", "+", "@", "-")):
                    continue
                findings.append(
                    {
                        "sheet": ws.title,
                        "cell": cell.coordinate,
                        "value": text,
                        "data_type": cell.data_type,
                        "is_string": cell.data_type == "s",
                        "pass": cell.data_type == "s",
                    }
                )
    return findings


def run_one(
    token: str,
    cart_detail_id: int,
    payload_name: str,
    payload: str,
    quote_type: int,
    logistics_config_id: int,
) -> dict:
    session = requests.Session()
    session.headers.update(build_headers(token))

    print(f"\n=== [{payload_name}] custom_sku = {payload!r} ===")
    sku_resp = update_custom_sku(session, cart_detail_id, payload)
    print(f"updateSkuNumberData OK: {json.dumps(sku_resp, ensure_ascii=False)[:200]}")

    quote_no = create_quote(session, [cart_detail_id], quote_type, logistics_config_id)
    print(f"quote/create OK: quote_no={quote_no}")
    print("下一步：在 B2B/管理端对该报价单点击「导出 Excel」，再执行 --check-xlsx 校验。")
    return {
        "payload_name": payload_name,
        "payload": payload,
        "cart_detail_id": cart_detail_id,
        "quote_no": quote_no,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="TC-SEC-XSS-001 报价公式注入 API 造数")
    parser.add_argument("--token", default=os.getenv("HUBBUYER_TOKEN", ""), help="B2B authorization JWT")
    parser.add_argument("--cart-detail-id", type=int, default=48949)
    parser.add_argument("--quote-type", type=int, default=1)
    parser.add_argument("--logistics-config-id", type=int, default=26)
    parser.add_argument("--payload", help="单个 custom_sku payload")
    parser.add_argument("--all-payloads", action="store_true", help="依次跑 hyperlink/plus_cmd/at_sum/normal")
    parser.add_argument("--check-xlsx", type=Path, help="校验已导出的 xlsx 是否全部为文本类型")
    args = parser.parse_args()

    if args.check_xlsx:
        if not args.check_xlsx.exists():
            print(f"文件不存在: {args.check_xlsx}", file=sys.stderr)
            return 1
        findings = check_xlsx(args.check_xlsx)
        if not findings:
            print("未找到以 = + @ - 开头的单元格；请确认文件或扩大搜索范围。")
            return 1
        failed = [f for f in findings if not f["pass"]]
        for item in findings:
            status = "PASS" if item["pass"] else "FAIL"
            print(
                f"{status} {item['sheet']}!{item['cell']} "
                f"type={item['data_type']} value={item['value']!r}"
            )
        print(f"\n汇总: {len(findings) - len(failed)}/{len(findings)} 单元格为文本类型")
        return 1 if failed else 0

    if not args.token:
        print("请设置 HUBBUYER_TOKEN 或 --token", file=sys.stderr)
        return 1

    results = []
    if args.all_payloads:
        for name, payload in PAYLOADS:
            try:
                results.append(
                    run_one(
                        args.token,
                        args.cart_detail_id,
                        name,
                        payload,
                        args.quote_type,
                        args.logistics_config_id,
                    )
                )
            except Exception as exc:
                print(f"FAIL [{name}]: {exc}", file=sys.stderr)
                return 1
    elif args.payload:
        results.append(
            run_one(
                args.token,
                args.cart_detail_id,
                "custom",
                args.payload,
                args.quote_type,
                args.logistics_config_id,
            )
        )
    else:
        parser.print_help()
        return 1

    out = Path(__file__).with_name(
        f"xss001_quote_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
