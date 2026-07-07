# -*- coding: utf-8 -*-
# checker/api/purchase_order_ops.py
# 后台代购订单操作：一键采购 / 一键到货 / 一键正品 / 入库（按店铺抽样）
import json
import os
import sys
import traceback
import requests

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import REQUEST_TIMEOUT_API, API_CONFIG, ENV_TYPE
from core.rules.assertion import AssertionTool
from core.path_manager import DATA_DIR
from checker.api.order_audit import _admin_login
try:
    from checker.api.order_audit import admin_api_base_url
except ImportError:
    def admin_api_base_url():
        return (API_CONFIG.get("BASE_URL") or "https://api.hubbuyer.com").rstrip("/")
from checker.api.purchase_order_audit import _resolve_order_no, _build_audit_headers
from checker.api.quote_order_store import resolve_target_mail
from core.path_manager import normalize_purchase_order_ops_config

TARGET_CONFIG_FILE = "purchase_order_ops.json"


def _load_target_config():
    path = os.path.join(DATA_DIR, TARGET_CONFIG_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到 {TARGET_CONFIG_FILE}")
    with open(path, "r", encoding="utf-8") as f:
        return normalize_purchase_order_ops_config(json.load(f))


def _is_idempotent_success(body, step_cfg):
    """已执行过的操作视为冒烟通过（如：商品行已采购）"""
    if not isinstance(body, dict):
        return False
    code = body.get("code")
    message = str(body.get("message") or "")
    allowed_codes = step_cfg.get("idempotent_codes") or []
    keywords = step_cfg.get("idempotent_message_contains") or []
    if code in allowed_codes and any(k in message for k in keywords):
        return True
    return False


WAREHOUSE_PRICE_KEYS = (
    "change_price",
    "purchase_price",
    "purchase_unit_price",
    "real_purchase_price",
    "seller_purchase_price",
)


def _get_warehouse_price(item):
    """入库金额计算依赖采购价字段，普通 price 不足以保证 putInStock 成功"""
    if not isinstance(item, dict):
        return None
    for key in WAREHOUSE_PRICE_KEYS:
        val = item.get(key)
        if val is None or str(val).strip() == "":
            continue
        try:
            if float(val) >= 0:
                return val
        except (TypeError, ValueError):
            continue
    return None


def _detail_ready_for_warehouse(item):
    return _get_warehouse_price(item) is not None


def _detail_has_price(item):
    return _detail_ready_for_warehouse(item)


def _pending_store_qty(detail_item):
    """待入库数 = 正品数 - 已入库数"""
    try:
        genuine = int(float(detail_item.get("genuine_qty") or 0))
        stored = int(float(detail_item.get("store_qty") or 0))
    except (TypeError, ValueError):
        return 0
    return max(genuine - stored, 0)


def _resolve_warehouse_seller(token, order_no, target_cfg, seller_ctx):
    """入库前刷新明细，优先返回存在可入库明细的店铺"""
    sellers = _fetch_order_sellers(token, order_no, target_cfg.get("detail_api"))
    step_cfg = dict((target_cfg.get("steps") or {}).get("warehouse_in") or {})
    prefer_open_id = (seller_ctx.get("seller_open_id") or "").strip()
    candidates = _collect_warehouse_candidates(
        sellers, step_cfg, target_cfg, prefer_open_id=prefer_open_id
    )
    if candidates:
        seller, _, _ = candidates[0]
        seller_ctx["seller_open_id"] = seller.get("seller_open_id")
        seller_ctx["seller_name"] = seller.get("seller_name") or seller.get("seller_open_id")
        return seller, sellers

    pending_without_price = _find_pending_without_purchase_price(sellers)
    if pending_without_price:
        ids = ",".join(pending_without_price[:5])
        raise RuntimeError(
            f"待入库明细缺少采购价(change_price/purchase_price)，ids={ids}；"
            "一键链路可能未回填采购单价，无法自动入库"
        )
    return sellers[0], sellers


def _refresh_sample_seller(token, order_no, target_cfg, seller_ctx):
    seller, _ = _resolve_warehouse_seller(token, order_no, target_cfg, seller_ctx)
    return seller


def _ku_shelves_id(step_cfg, target_cfg):
    ku_shelves_ku_id = step_cfg.get("ku_shelves_ku_id")
    if ku_shelves_ku_id is None:
        ku_shelves_ku_id = target_cfg.get("default_ku_shelves_ku_id", 35)
    return ku_shelves_ku_id


def _build_warehouse_payload_for_line(seller, item, step_cfg, target_cfg):
    user_main_uuid = (seller.get("user_main_uuid") or "").strip()
    if not user_main_uuid:
        return None
    pending = _pending_store_qty(item)
    if pending <= 0 or not _detail_ready_for_warehouse(item):
        return None
    return {
        "store_min_box_ids": None,
        "ku_stock_in_log_data": [{
            "order_detail_id": item["id"],
            "quantity": str(pending),
        }],
        "ku_shelves_ku_id": _ku_shelves_id(step_cfg, target_cfg),
        "store_box_ids": None,
        "user_main_uuid": user_main_uuid,
    }


def _fetch_ku_log_id_from_stock_list(token, product_uuid):
    """入库成功后立即查 stockProductList，返回 ku_stock_in_log_id。
    必须在 createShipOrder 之前调用，否则空发货单会锁定库存记录导致查不到。
    """
    if not product_uuid:
        return None
    try:
        url = f"{admin_api_base_url()}/admin_b2b/KuStockLog/stockProductList"
        headers = _build_audit_headers(token, {})
        payload = {
            "user_main_uuid": "",  # 必须为空，传 uuid 会导致 PHP 500
            "user_name": "",
            "order_detail_uuid": product_uuid,
            "serial_number": "",
            "order_no": "",
        }
        resp = requests.post(
            url, headers=headers, json=payload,
            timeout=REQUEST_TIMEOUT_API, verify=False,
            proxies={"http": None, "https": None},
        )
        body = resp.json()
        if body.get("code") == 200:
            data = body.get("data") or {}
            rows = (
                data.get("all_stock_data")
                or data.get("list")
                or data.get("data")
                or []
            )
            if isinstance(data, list):
                rows = data
            if rows:
                log_id = rows[0].get("id") or rows[0].get("ku_stock_in_log_id")
                return int(log_id) if log_id else None
    except Exception:
        pass
    return None


def _collect_warehouse_candidates(sellers, step_cfg, target_cfg, prefer_open_id=None):
    ordered = []
    prefer_open_id = (prefer_open_id or "").strip()
    if prefer_open_id:
        ordered.extend([
            s for s in sellers
            if str(s.get("seller_open_id") or "").strip() == prefer_open_id
        ])
    ordered.extend([s for s in sellers if s not in ordered])

    candidates = []
    for seller in ordered:
        for item in seller.get("detail_data") or []:
            payload = _build_warehouse_payload_for_line(seller, item, step_cfg, target_cfg)
            if payload:
                candidates.append((seller, payload, item))
    return candidates


def _find_pending_without_purchase_price(sellers):
    ids = []
    for seller in sellers:
        for item in seller.get("detail_data") or []:
            if not isinstance(item, dict) or item.get("id") is None:
                continue
            if _pending_store_qty(item) > 0 and not _detail_ready_for_warehouse(item):
                ids.append(str(item["id"]))
    return ids


def _build_warehouse_payload(seller, step_cfg, target_cfg):
    user_main_uuid = (seller.get("user_main_uuid") or "").strip()
    if not user_main_uuid:
        raise RuntimeError("订单明细缺少 user_main_uuid，无法入库")

    line_mode = (step_cfg.get("line_mode") or "first_pending_line").strip()
    stock_lines = []
    missing_price_ids = []
    for item in seller.get("detail_data") or []:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        pending = _pending_store_qty(item)
        if pending <= 0:
            continue
        if not _detail_ready_for_warehouse(item):
            missing_price_ids.append(str(item["id"]))
            continue
        stock_lines.append({
            "order_detail_id": item["id"],
            "quantity": str(pending),
        })
        if line_mode in ("first_pending_line", "first_pending_priced_line"):
            break

    if not stock_lines:
        if missing_price_ids:
            raise RuntimeError(
                f"待入库明细缺少采购价(change_price/purchase_price)，ids={','.join(missing_price_ids)}"
            )
        return None

    return {
        "store_min_box_ids": None,
        "ku_stock_in_log_data": stock_lines,
        "ku_shelves_ku_id": _ku_shelves_id(step_cfg, target_cfg),
        "store_box_ids": None,
        "user_main_uuid": user_main_uuid,
    }


def _post_warehouse_payload(token, url, step_cfg, payload, all_rules, rule_key):
    headers = _build_audit_headers(token, step_cfg)
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    check = AssertionTool.verify_api_common(response, rules=all_rules.get(rule_key, {}))
    try:
        body = response.json()
    except Exception:
        body = {}
    return response, check, body


def _execute_warehouse_in_step(
    token, order_no, sellers, seller_ctx, step_cfg, rule_key, all_rules, target_cfg
):
    if not step_cfg or not step_cfg.get("enabled"):
        return {"success": True, "skipped": True, "message": f"{step_cfg.get('desc', '入库')}:跳过(未启用)"}

    url = (step_cfg.get("url") or "").strip()
    if not url:
        return {"success": False, "message": "入库:FAIL(url 为空)"}

    desc = step_cfg.get("desc") or "入库"
    skip_without_price = target_cfg.get("warehouse_in_skip_without_purchase_price", True)
    prefer_open_id = (seller_ctx.get("seller_open_id") or "").strip()
    candidates = _collect_warehouse_candidates(
        sellers, step_cfg, target_cfg, prefer_open_id=prefer_open_id
    )

    if not candidates:
        missing_price_ids = _find_pending_without_purchase_price(sellers)
        incomplete = []
        for seller in sellers:
            for item in (seller.get("detail_data") or []):
                if isinstance(item, dict) and item.get("is_store_incomplete") in (1, "1", True):
                    incomplete.append(str(item.get("id")))
        if incomplete and not missing_price_ids:
            return {
                "success": False,
                "message": f"{desc}:FAIL(待入库=0但明细仍标记未完成|ids={','.join(incomplete[:5])})",
            }
        if missing_price_ids:
            msg = (
                f"{desc}:SKIP(待入库明细缺少采购价change_price/purchase_price|"
                f"ids={','.join(missing_price_ids[:5])})"
            )
            return {"success": bool(skip_without_price), "message": msg}
        # 即使已全部入库，也尝试从明细数据中构建发货上下文（下一轮发货模块使用）
        try:
            _fallback_item = None
            for _s in sellers:
                for _it in (_s.get("detail_data") or []):
                    if isinstance(_it, dict) and _it.get("id") is not None:
                        _fallback_item = _it
                        _fallback_seller = _s
                        break
                if _fallback_item:
                    break
            if _fallback_item:
                _fallback_uuid = _fallback_item.get("user_main_uuid") or (
                    _fallback_seller.get("user_main_uuid") or ""
                )
                _ctx = _build_shipping_ctx(
                    order_no,
                    {
                        "ku_stock_in_log_data": [{"order_detail_id": _fallback_item["id"], "quantity": 0}],
                        "user_main_uuid": _fallback_uuid,
                    },
                    _fallback_item,
                    {},
                )
                return {"success": True, "message": f"{desc}:OK(已全部入库|待入库=0)", "_shipping_ctx": _ctx}
        except Exception:
            pass
        return {"success": True, "message": f"{desc}:OK(已全部入库|待入库=0)"}

    last_fail = ""
    for seller, payload, item in candidates:
        seller_name = seller.get("seller_name") or seller.get("seller_open_id") or "未知店铺"
        line_desc = ",".join(
            f"{row['order_detail_id']}x{row['quantity']}"
            for row in payload["ku_stock_in_log_data"]
        )
        _, check, body = _post_warehouse_payload(
            token, url, step_cfg, payload, all_rules, rule_key
        )
        if check["success"]:
            price_key = _get_warehouse_price(item)
            # 入库成功后立即查 stockProductList，拿到 ku_stock_in_log_id
            # 必须在 createShipOrder 之前调用，否则空发货单会锁定记录
            product_uuid = item.get("uuid") or ""
            ku_log_id = _fetch_ku_log_id_from_stock_list(token, product_uuid)
            shipping_ctx = _build_shipping_ctx(order_no, payload, item, body)
            if ku_log_id:
                shipping_ctx["ku_stock_in_log_id"] = ku_log_id
            return {
                "success": True,
                "message": (
                    f"{desc}:OK({seller_name}|{line_desc}|库位={payload['ku_shelves_ku_id']}|"
                    f"采购价={price_key})"
                ),
                "_shipping_ctx": shipping_ctx,
            }
        if _is_idempotent_success(body, step_cfg):
            api_msg = body.get("message") or "已入库"
            shipping_ctx = _build_shipping_ctx(order_no, payload, item, body)
            return {
                "success": True,
                "message": f"{desc}:OK(已执行|{seller_name}|{api_msg})",
                "_shipping_ctx": shipping_ctx,
            }

        detail = check.get("message", "未知错误")
        if body.get("message"):
            detail = f"{detail} | api_msg={body.get('message')}"
        if "bcmul" in str(body.get("message") or "").lower():
            detail += " | 提示:库位配置异常(如B-1-001/id=35)，可改用B-2-003/id=69"
            last_fail = detail
            continue
        return {"success": False, "message": f"{desc}:FAIL({detail})"}

    return {"success": False, "message": f"{desc}:FAIL({last_fail or '所有候选明细入库失败'})"}


def _build_shipping_ctx(order_no, payload, item, body):
    """从入库成功结果中提取发货上下文字段。"""
    log_data = (payload.get("ku_stock_in_log_data") or [{}])[0]
    ctx = {
        "order_no": order_no,
        "order_detail_id": log_data.get("order_detail_id"),
        "quantity": int(float(log_data.get("quantity") or 0)),
        "user_main_uuid": payload.get("user_main_uuid", ""),
    }
    try:
        data = body.get("data") or {}
        ku_log_id = (
            data.get("id") or data.get("ku_stock_in_log_id")
            or data.get("log_id") or data.get("stockInLogId")
        )
        if ku_log_id:
            ctx["ku_stock_in_log_id"] = int(ku_log_id)
    except Exception:
        pass
    try:
        pid = (
            item.get("product_no") or item.get("goods_no")
            or item.get("product_id") or item.get("goods_id") or ""
        )
        if pid:
            ctx["product_id"] = str(pid)
    except Exception:
        pass
    # uuid 字段是 D 格式的产品UUID，stockProductList 的 order_detail_uuid 参数需要它
    try:
        product_uuid = item.get("uuid") or ""
        if product_uuid:
            ctx["product_uuid"] = str(product_uuid)
        goods_uuid = item.get("goods_uuid") or ""
        if goods_uuid:
            ctx["goods_uuid"] = str(goods_uuid)
    except Exception:
        pass
    return ctx


def _execute_post_step(token, order_no, seller_ctx, step_cfg, rule_key, all_rules):
    if not step_cfg or not step_cfg.get("enabled"):
        return {"success": True, "skipped": True, "message": f"{step_cfg.get('desc', '步骤')}:跳过(未启用)"}

    url = (step_cfg.get("url") or "").strip()
    if not url:
        return {"success": False, "message": f"{step_cfg.get('desc', '步骤')}:FAIL(url 为空)"}

    headers = _build_audit_headers(token, step_cfg)
    payload = dict(step_cfg.get("json") or {})
    payload["order_no"] = order_no
    payload["seller_open_id"] = seller_ctx["seller_open_id"]
    payload["order_detail_ids"] = seller_ctx["order_detail_ids"]

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    check = AssertionTool.verify_api_common(response, rules=all_rules.get(rule_key, {}))
    desc = step_cfg.get("desc") or step_cfg.get("key") or "步骤"

    if check["success"]:
        return {"success": True, "message": f"{desc}:OK({seller_ctx['seller_name']}|ids={seller_ctx['order_detail_ids']})"}

    try:
        body = response.json()
    except Exception:
        body = {}

    if _is_idempotent_success(body, step_cfg):
        api_msg = body.get("message") or "已执行"
        return {
            "success": True,
            "message": f"{desc}:OK(已执行|{seller_ctx['seller_name']}|{api_msg})",
        }

    detail = check.get("message", "未知错误")
    if body.get("message"):
        detail = f"{detail} | api_msg={body.get('message')}"
    return {"success": False, "message": f"{desc}:FAIL({detail})"}


def _fetch_order_sellers(token, order_no, detail_cfg):
    if not detail_cfg or not detail_cfg.get("enabled"):
        raise RuntimeError("订单明细接口未启用，无法解析 seller_open_id / order_detail_ids")

    url = (detail_cfg.get("url") or "").strip()
    if not url:
        raise RuntimeError("订单明细接口 url 为空")

    headers = _build_audit_headers(token, detail_cfg)
    payload = dict(detail_cfg.get("json") or {})
    payload["order_no"] = order_no

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 200:
        raise RuntimeError(f"订单明细获取失败: code={body.get('code')} msg={body.get('message')}")

    sellers = (body.get("data") or {}).get("order_seller_data") or []
    if not sellers:
        raise RuntimeError("订单明细为空，无可用店铺")
    return sellers


def _extract_detail_ids(seller):
    ids = []
    for item in seller.get("detail_data") or []:
        if isinstance(item, dict) and item.get("id") is not None:
            ids.append(str(item["id"]))
    return ",".join(ids)


def _pick_sample_seller(sellers, target_cfg):
    mode = (target_cfg.get("sample_mode") or "first_seller").strip()
    if mode == "first_by_platform":
        preferred = target_cfg.get("prefer_platforms") or ["1688", "tb"]
        for platform in preferred:
            for seller in sellers:
                if str(seller.get("product_platform") or "").lower() == platform.lower():
                    detail_ids = _extract_detail_ids(seller)
                    if detail_ids:
                        return seller, detail_ids
        raise RuntimeError("未找到符合 prefer_platforms 的店铺明细")

    index = int(target_cfg.get("sample_seller_index") or 0)
    if index < 0 or index >= len(sellers):
        raise RuntimeError(f"sample_seller_index={index} 超出店铺数量 {len(sellers)}")
    seller = sellers[index]
    detail_ids = _extract_detail_ids(seller)
    if not detail_ids:
        raise RuntimeError(f"店铺[{seller.get('seller_name', index)}]无可用 order_detail_ids")
    return seller, detail_ids


def run(task_config=None):
    msgs = []
    try:
        target_cfg = _load_target_config()
        allowed_envs = target_cfg.get("allowed_envs") or ["main", "prod", "test"]
        if ENV_TYPE not in allowed_envs:
            message = f"后台代购订单操作:跳过(当前环境 {ENV_TYPE} 不在 {allowed_envs})"
            result = {
                "success": True,
                "message": message,
                "status_code": 200,
                "actual": message,
            }
            print(json.dumps(result, ensure_ascii=False))
            return result

        all_rules = AssertionTool.get_rules_dynamically("purchase_order_ops", root_path) or {}
        target_mail = resolve_target_mail()
        orderid_file = os.path.join(DATA_DIR, "payment_orderid.json")

        order_no = _resolve_order_no(target_cfg, orderid_file, target_mail)
        msgs.append(f"代购订单号获取:OK({order_no})")

        token = _admin_login()
        msgs.append("后台登录:OK")

        sellers = _fetch_order_sellers(token, order_no, target_cfg.get("detail_api"))
        seller, detail_ids = _pick_sample_seller(sellers, target_cfg)
        seller_ctx = {
            "seller_open_id": seller.get("seller_open_id"),
            "seller_name": seller.get("seller_name") or seller.get("seller_open_id"),
            "product_platform": seller.get("product_platform") or "",
            "order_detail_ids": detail_ids,
        }
        msgs.append(
            f"抽样店铺:OK({seller_ctx['seller_name']}|{seller_ctx['product_platform']}|ids={detail_ids}|共{len(sellers)}店)"
        )

        step_defs = [
            ("one_click_purchase", "one_click_purchase_api", "一键采购"),
            ("one_click_arrival", "one_click_arrival_api", "一键到货"),
            ("one_click_genuine", "one_click_genuine_api", "一键正品"),
            ("warehouse_in", "warehouse_in_api", "入库"),
        ]
        for step_key, rule_key, default_desc in step_defs:
            step_cfg = dict(target_cfg.get("steps", {}).get(step_key) or {})
            step_cfg.setdefault("desc", default_desc)
            if step_key == "warehouse_in":
                sellers = _fetch_order_sellers(token, order_no, target_cfg.get("detail_api"))
                step_result = _execute_warehouse_in_step(
                    token, order_no, sellers, seller_ctx, step_cfg, rule_key, all_rules, target_cfg
                )
            else:
                step_result = _execute_post_step(
                    token, order_no, seller_ctx, step_cfg, rule_key, all_rules
                )
            if step_result.get("skipped"):
                msgs.append(step_result["message"])
                continue
            msgs.append(step_result["message"])

            # 入库成功后保存发货上下文（供 purchase_order_shipping 消费）
            if step_key == "warehouse_in" and step_result.get("success"):
                _ctx = step_result.pop("_shipping_ctx", None)
                if _ctx:
                    try:
                        from checker.api.shipping_context_store import save_shipping_context
                        save_shipping_context(_ctx)
                    except Exception:
                        pass

            if not step_result["success"]:
                break

        all_ok = all(
            ":OK" in msg or ":跳过" in msg or ":SKIP" in msg for msg in msgs
        )
        message = " | ".join(msgs)
        result = {
            "success": all_ok,
            "message": message,
            "status_code": 200 if all_ok else 500,
            "actual": f"后台代购订单操作: {message}",
        }
    except Exception as e:
        message = f"执行异常:{type(e).__name__}: {str(e)}"
        result = {
            "success": False,
            "message": message,
            "status_code": 500,
            "actual": traceback.format_exc(),
        }

    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
            run(task_config=task_config)
            sys.exit(0)
        except (json.JSONDecodeError, ValueError):
            pass
    run()
