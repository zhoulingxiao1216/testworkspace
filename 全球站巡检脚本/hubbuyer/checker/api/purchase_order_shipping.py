# -*- coding: utf-8 -*-
# checker/api/purchase_order_shipping.py
# 后台发货全链路：创建发货单 -> 配货 -> 装箱(5步) -> 待清算 -> 绑定运单 -> 确认发货
import json
import os
import re
import sys
import traceback

import requests

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import REQUEST_TIMEOUT_API, ENV_TYPE
from core.rules.assertion import AssertionTool
from core.path_manager import DATA_DIR, normalize_purchase_order_shipping_config
from checker.api.order_audit import _admin_login
try:
    from checker.api.order_audit import build_admin_auth_headers, admin_api_base_url
except ImportError:
    from config.settings import API_CONFIG as _API_CONFIG
    def admin_api_base_url():
        return (_API_CONFIG.get("BASE_URL") or "https://api.hubbuyer.com").rstrip("/")
    def build_admin_auth_headers(token, admin_site_origin=None, extra_headers=None):
        from config.settings import API_CONFIG as _C
        origin = (admin_site_origin or (_C.get("url_ADMIN") or "https://admin.hubbuyer.com/")).rstrip("/")
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "logintype": "admin",
            "origin": origin,
            "referer": origin + "/",
            "authorization": (token or "").replace("Bearer ", "").strip(),
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers
from checker.api.purchase_order_audit import _build_audit_headers
from checker.api.shipping_context_store import (
    load_shipping_context,
    save_shipping_context,
    allocate_waybill_counter,
    commit_waybill_counter,
)

CONFIG_FILE = "purchase_order_shipping.json"


def _load_config():
    path = os.path.join(DATA_DIR, CONFIG_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到发货链路配置 {CONFIG_FILE}")
    with open(path, "r", encoding="utf-8") as f:
        return normalize_purchase_order_shipping_config(json.load(f))


def _post(token, cfg_block, payload, all_rules, rule_key):
    """通用 POST + AssertionTool 断言，返回 {success, message, body, status_code}。"""
    url = (cfg_block.get("url") or "").strip()
    if not url:
        return {"success": False, "message": f"url 为空({rule_key})", "body": {}, "status_code": 0}
    headers = _build_audit_headers(token, cfg_block)
    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    rules = all_rules.get(rule_key) or all_rules.get("default") or {}
    check = AssertionTool.verify_api_common(resp, rules=rules)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return {
        "success": check["success"],
        "message": check.get("message", ""),
        "body": body,
        "status_code": resp.status_code,
    }


def _extract_from_body(body, *keys):
    """多路径提取，取第一个非空值。"""
    data = body.get("data") or {}
    for k in keys:
        v = data.get(k)
        if v:
            return v
        # also try top-level
        v = body.get(k)
        if v:
            return v
    return None


def _fetch_ku_stock_in_log_id(token, user_main_uuid, order_no, cfg, product_uuid=None):
    """通过 stockProductList 查询当前巡检入库记录，返回 ku_stock_in_log_id。
    优先用 product_uuid（item.uuid，D 格式）进行精确过滤。
    """
    # 优先用 stockProductList（需要 product_uuid = item.uuid 的 D 格式）
    stock_cfg = cfg.get("ku_stock_in_log_list_api") or {}
    if stock_cfg.get("enabled") and product_uuid:
        stock_url = (stock_cfg.get("url") or "").strip()
        if stock_url:
            try:
                headers = _build_audit_headers(token, stock_cfg)
                payload = {
                    "user_main_uuid": "",  # 必须为空，传 uuid 会导致 PHP 500
                    "user_name": "",
                    "order_detail_uuid": product_uuid,
                    "serial_number": "",
                    "order_no": "",
                }
                resp = requests.post(
                    stock_url, headers=headers, json=payload,
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
                        if log_id:
                            return int(log_id)
            except Exception:
                pass
    return None


def _query_latest_ship_order_no(token, user_main_uuid, cfg, all_rules):
    """createShipOrder 接口不返回单号，改从发货单列表中取最新一条。
    同时尝试从行数据中提取 ship_order_detail_id 并写入上下文缓存。
    """
    list_cfg = cfg.get("ship_order_list_api") or {}
    if not list_cfg.get("enabled"):
        return None
    payload = {
        "page": 1,
        "limit": 5,
        "user_main_uuid": user_main_uuid,
    }
    try:
        url = (list_cfg.get("url") or "").strip()
        if not url:
            return None
        headers = _build_audit_headers(token, list_cfg)
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_API,
            verify=False,
            proxies={"http": None, "https": None},
        )
        body = resp.json()
        data = body.get("data") or {}
        # 兼容 {data: {list: [...]}} 和 {data: [...]}
        rows = data.get("list") or data.get("data") or []
        if isinstance(data, list):
            rows = data
        if not rows:
            return None
        # 取第一条（最新）
        row = rows[0]
        no = row.get("ship_order_no") or row.get("no") or row.get("order_no")
        # 尝试从行中提取 detail_id（部分 list 接口把 details 内嵌在行数据里）
        detail_id = None
        for dkey in ("details", "ship_order_details", "detail_list", "detail"):
            sub = row.get(dkey)
            if sub and isinstance(sub, list) and sub[0]:
                detail_id = sub[0].get("id") or sub[0].get("ship_order_detail_id")
                break
        if detail_id:
            save_shipping_context({"ship_order_detail_id_from_list": detail_id})
        return no
    except Exception:
        return None


def _fetch_ship_order_detail_id(token, ship_order_no, cfg, all_rules, msgs):
    """创建发货单后查询明细列表，返回 ship_order_detail_id。
    优先使用 _query_latest_ship_order_no 写入上下文的缓存值，
    否则主动请求 ship_order_detail_list_api。
    """
    # 优先检查列表查询时已提取的 detail_id
    ctx_now = load_shipping_context()
    cached_detail_id = ctx_now.get("ship_order_detail_id_from_list")
    if cached_detail_id:
        msgs.append(f"明细查询:OK(detail_id={cached_detail_id}，来自列表缓存)")
        return cached_detail_id

    detail_cfg = cfg.get("ship_order_detail_list_api") or {}
    if not detail_cfg.get("enabled"):
        raise RuntimeError("ship_order_detail_list_api 未启用，无法获取 ship_order_detail_id")
    payload = {
        "ship_order_no": ship_order_no,
        "order_detail_uuid": "",
        "ku_box_name": "",
        "distribute_status": "",
        "type": "detail_list",
        "is_insert": 0,
    }
    # 直接发 HTTP 请求，不走 AssertionTool 断言（允许业务 code 不为 200 时灵活处理）
    url = (detail_cfg.get("url") or "").strip()
    if not url:
        raise RuntimeError("ship_order_detail_list_api url 为空")
    headers = _build_audit_headers(token, detail_cfg)
    try:
        resp = requests.post(
            url, headers=headers, json=payload,
            timeout=REQUEST_TIMEOUT_API, verify=False,
            proxies={"http": None, "https": None},
        )
        body = resp.json()
    except Exception as e:
        raise RuntimeError(f"发货单明细接口请求异常: {e}")

    def _parse_rows(b):
        data_field = b.get("data") or {}
        # goodsList 返回 {data: {data: [...]}}
        if isinstance(data_field, dict):
            inner = data_field.get("data") or data_field.get("list") or []
            if isinstance(inner, list) and inner:
                return inner
        if isinstance(data_field, list):
            return data_field
        return []

    rows = _parse_rows(body)
    if not rows:
        raise RuntimeError(
            f"发货单明细列表为空或接口错误，ship_order_no={ship_order_no}，"
            f"响应: code={body.get('code')} msg={body.get('message', body.get('msg', ''))}"
        )
    detail_id = rows[0].get("id") or rows[0].get("ship_order_detail_id")
    if not detail_id:
        raise RuntimeError(f"明细列表返回但无法解析 id 字段，行数据: {rows[0]}")
    msgs.append(f"明细查询:OK(detail_id={detail_id})")
    return detail_id


def run(task_config=None):
    msgs = []
    try:
        cfg = _load_config()
        allowed_envs = cfg.get("allowed_envs") or ["main", "prod", "test"]
        if ENV_TYPE not in allowed_envs:
            msg = f"发货链路:跳过(当前环境 {ENV_TYPE} 不在 {allowed_envs})"
            result = {"success": True, "message": msg, "status_code": 200, "actual": msg}
            print(json.dumps(result, ensure_ascii=False))
            return result

        all_rules = AssertionTool.get_rules_dynamically("purchase_order_shipping", root_path) or {}

        # ── 严格本轮数据校验 ──────────────────────────────────────────────────
        ctx = load_shipping_context()
        required_keys = ["order_no", "order_detail_id", "quantity", "user_main_uuid"]
        missing = [k for k in required_keys if not ctx.get(k)]
        if missing:
            raise RuntimeError(
                f"发货上下文缺失字段 {missing}，请先运行仓配(purchase_order_ops)并确保入库成功"
            )

        target_product_id = cfg.get("target_product_id", "")
        saved_product_id = str(ctx.get("product_id") or "")
        if target_product_id and saved_product_id and saved_product_id != target_product_id:
            raise RuntimeError(
                f"入库商品ID({saved_product_id})与目标商品({target_product_id})不匹配，"
                "请确认本轮巡检已使用正确的入库商品"
            )

        token = _admin_login()
        msgs.append("后台登录:OK")

        order_detail_id = ctx["order_detail_id"]
        ku_stock_in_log_id = ctx.get("ku_stock_in_log_id")
        quantity = int(ctx["quantity"])
        user_main_uuid = ctx["user_main_uuid"]
        order_no = ctx.get("order_no", "")

        # ── 尝试补查 ku_stock_in_log_id（入库接口不返回时，从日志列表接口取）──────
        if not ku_stock_in_log_id:
            product_uuid = ctx.get("product_uuid") or ""
            ku_stock_in_log_id = _fetch_ku_stock_in_log_id(token, user_main_uuid, order_no, cfg, product_uuid)
            if ku_stock_in_log_id:
                save_shipping_context({"ku_stock_in_log_id": ku_stock_in_log_id})
                msgs.append(f"入库日志查询:OK(ku_stock_in_log_id={ku_stock_in_log_id})")
            else:
                # 服务端允许 ku_stock_in_log_id=None，直接继续创建发货单
                msgs.append("入库日志查询:跳过(ku_stock_in_log_id不可用，服务端允许 null)")

        # ── Step 1: 创建发货单 ────────────────────────────────────────────────
        create_cfg = cfg.get("create_ship_order_api") or {}
        if not create_cfg.get("enabled"):
            raise RuntimeError("create_ship_order_api 未启用，发货链路无法启动")

        from datetime import datetime
        today_str = datetime.now().strftime("%m%d")
        create_payload = {
            "ku_stock_in_log_data": [{
                "order_detail_id": order_detail_id,
                "ku_stock_in_log_id": ku_stock_in_log_id,
                "quantity": quantity,
            }],
            "store_box_ids": None,
            "store_min_box_ids": None,
            "user_main_uuid": user_main_uuid,
            "logistics_config_id": cfg.get("logistics_config_id", 26),
            "delivery_address_id": cfg.get("delivery_address_id", 54),
            "importer_address_id": "",
            "tariff_account_id": "",
            "tariff_payment_type": cfg.get("tariff_payment_type", 1),
            "deport_remark": f"巡检测试创建发货单-{today_str}",
            "config_param": cfg.get("config_param", []),
        }
        r = _post(token, create_cfg, create_payload, all_rules, "create_ship_order_api")
        if not r["success"]:
            raise RuntimeError(f"创建发货单:FAIL({r['message']})")

        # 提取 ship_order_no
        ship_order_no = _extract_from_body(
            r["body"], "ship_order_no", "shipOrderNo", "order_no", "no"
        )
        if not ship_order_no:
            # 尝试从响应字符串中用正则找 WL- 前缀单号
            m = re.search(r"WL-[A-Z0-9]+-[0-9\-]+", json.dumps(r["body"], ensure_ascii=False))
            if m:
                ship_order_no = m.group(0)
        if not ship_order_no:
            # 接口仅返回 sign:True 不含单号，查询最新发货单列表来获取
            ship_order_no = _query_latest_ship_order_no(token, user_main_uuid, cfg, all_rules)
        if not ship_order_no:
            raise RuntimeError(f"创建发货单成功但无法提取 ship_order_no，响应: {r['body']}")

        save_shipping_context({"ship_order_no": ship_order_no})
        msgs.append(f"创建发货单:OK({ship_order_no})")

        # ── 查询发货单明细 → ship_order_detail_id ────────────────────────────
        ship_order_detail_id = _fetch_ship_order_detail_id(token, ship_order_no, cfg, all_rules, msgs)
        save_shipping_context({"ship_order_detail_id": ship_order_detail_id})

        # ── Step 2: 配货 ──────────────────────────────────────────────────────
        distribute_cfg = cfg.get("distribute_api") or {}
        if not distribute_cfg.get("enabled"):
            raise RuntimeError("distribute_api 未启用，无法继续")
        r = _post(token, distribute_cfg, {
            "ship_order_detail_id": ship_order_detail_id,
            "store_min_box_id": "",
            "store_box_id": "",
            "goods_qty": quantity,
            "ship_order_no": ship_order_no,
        }, all_rules, "distribute_api")
        if not r["success"]:
            raise RuntimeError(f"配货:FAIL({r['message']})")
        msgs.append("配货:OK")

        # ── Step 2.1: 配货完成 ────────────────────────────────────────────────
        dist_done_cfg = cfg.get("distribute_done_api") or {}
        if not dist_done_cfg.get("enabled"):
            raise RuntimeError("distribute_done_api 未启用，无法继续")
        r = _post(token, dist_done_cfg, {"ship_order_no": ship_order_no}, all_rules, "distribute_done_api")
        if not r["success"]:
            raise RuntimeError(f"配货完成:FAIL({r['message']})")
        msgs.append("配货完成:OK")

        # ── Step 3.1: 创建发货箱 ──────────────────────────────────────────────
        box_insert_cfg = cfg.get("box_insert_api") or {}
        if not box_insert_cfg.get("enabled"):
            raise RuntimeError("box_insert_api 未启用，无法继续")
        r = _post(token, box_insert_cfg, {"ship_order_no": ship_order_no}, all_rules, "box_insert_api")
        if not r["success"]:
            raise RuntimeError(f"创建发货箱:FAIL({r['message']})")

        box_id = _extract_from_body(r["body"], "id", "box_id", "boxId")
        if not box_id:
            # box_insert 返回 data.box_data.id
            box_id = ((r["body"].get("data") or {}).get("box_data") or {}).get("id")
        if not box_id:
            raise RuntimeError(f"创建发货箱成功但无法提取 box_id，响应: {r['body']}")
        box_id = int(box_id)
        save_shipping_context({"box_id": box_id})
        msgs.append(f"创建发货箱:OK(box_id={box_id})")

        box_spec = cfg.get("box_spec") or {"long": "12", "width": "12", "height": "12", "weight": "3"}

        # ── Step 3.2: 商品入箱 (is_done=0) ───────────────────────────────────
        box_done_cfg = cfg.get("box_done_api") or {}
        if not box_done_cfg.get("enabled"):
            raise RuntimeError("box_done_api 未启用，无法继续")
        r = _post(token, box_done_cfg, {
            "ship_order_detail_id": str(ship_order_detail_id),
            "store_min_box_id": "",
            "store_box_id": "",
            "box_info": [{
                "box_id": box_id,
                "long": "0.00", "width": "0.00", "height": "0.00", "weight": "0.00",
                "distribution_name": None, "pack_name": None,
                "quantity": str(quantity),
            }],
            "is_done": 0,
            "ship_order_no": ship_order_no,
        }, all_rules, "box_done_api")
        if not r["success"]:
            raise RuntimeError(f"商品入箱:FAIL({r['message']})")
        msgs.append("商品入箱:OK")

        # ── Step 3.3: 满箱确认 (is_done=200) ─────────────────────────────────
        r = _post(token, box_done_cfg, {
            "ship_order_detail_id": "",
            "store_min_box_id": "",
            "store_box_id": "",
            "box_info": [{
                "box_id": box_id,
                "long": box_spec.get("long", "12"),
                "width": box_spec.get("width", "12"),
                "height": box_spec.get("height", "12"),
                "weight": box_spec.get("weight", "3"),
                "distribution_name": None, "pack_name": None,
                "quantity": 0,
            }],
            "is_done": 200,
            "ship_order_no": ship_order_no,
        }, all_rules, "box_done_api")
        if not r["success"]:
            raise RuntimeError(f"满箱确认:FAIL({r['message']})")
        msgs.append("满箱确认:OK")

        # ── Step 3.4: 发货附加项（所有勾选项 quantity=1） ─────────────────────
        fjx_cfg = cfg.get("update_fjx_api") or {}
        if not fjx_cfg.get("enabled"):
            raise RuntimeError("update_fjx_api 未启用，无法继续")
        fjx_items = cfg.get("config_param") or [{"uuid": "JPT-FJX-047", "quantity": 0}]
        for fjx_item in fjx_items:
            fjx_uuid = fjx_item.get("uuid", "")
            fjx_payload = {
                "ship_order_no": ship_order_no,
                "type": "fjx",
                "config_param": {"uuid": fjx_uuid, "quantity": 1},
                "checked": 1,
                "uuid": fjx_uuid,
            }
            if fjx_item.get("fjx_spec_info"):
                fjx_payload["config_param"]["fjx_spec_info"] = fjx_item["fjx_spec_info"]
            r = _post(token, fjx_cfg, fjx_payload, all_rules, "update_fjx_api")
            if not r["success"]:
                raise RuntimeError(f"发货附加项:FAIL({fjx_uuid}|{r['message']})")
        msgs.append(f"发货附加项:OK({len(fjx_items)}项)")

        # ── Step 3.5: 装箱完成 ────────────────────────────────────────────────
        complete_cfg = cfg.get("complete_box_api") or {}
        if not complete_cfg.get("enabled"):
            raise RuntimeError("complete_box_api 未启用，无法继续")
        r = _post(token, complete_cfg, {"ship_order_no": ship_order_no}, all_rules, "complete_box_api")
        if not r["success"]:
            raise RuntimeError(f"装箱完成:FAIL({r['message']})")
        msgs.append("装箱完成:OK")

        # ── Step 4.1: 移动到待清算 ────────────────────────────────────────────
        settling_cfg = cfg.get("remove_settling_api") or {}
        if not settling_cfg.get("enabled"):
            raise RuntimeError("remove_settling_api 未启用，无法继续")
        r = _post(token, settling_cfg, {"ship_order_no": ship_order_no}, all_rules, "remove_settling_api")
        if not r["success"]:
            raise RuntimeError(f"移动待清算:FAIL({r['message']})")
        msgs.append("移动待清算:OK")

        # ── Step 4.2: 待清算扣款 ──────────────────────────────────────────────
        deduct_cfg = cfg.get("deduct_money_api") or {}
        if not deduct_cfg.get("enabled"):
            raise RuntimeError("deduct_money_api 未启用，无法继续")
        r = _post(token, deduct_cfg, {"ship_order_no": ship_order_no}, all_rules, "deduct_money_api")
        if not r["success"]:
            raise RuntimeError(f"待清算扣款:FAIL({r['message']})")
        msgs.append("待清算扣款:OK")

        # ── Step 5.1: 绑定运单号（当天全局唯一，冲突重试） ─────────────────────
        waybill_cfg = cfg.get("update_waybill_no_api") or {}
        if not waybill_cfg.get("enabled"):
            raise RuntimeError("update_waybill_no_api 未启用，无法继续")

        retry_limit = cfg.get("waybill_no_retry_limit", 5)
        base_counter, today = allocate_waybill_counter()
        waybill_bound = None
        for attempt in range(retry_limit):
            current_counter = base_counter + attempt
            waybill_no = f"{today}-{current_counter:03d}"
            r = _post(token, waybill_cfg, {
                "ship_order_box_ids": [box_id],
                "waybill_no": waybill_no,
            }, all_rules, "update_waybill_no_api")
            if r["success"]:
                commit_waybill_counter(today, current_counter)
                waybill_bound = waybill_no
                msgs.append(f"绑定运单号:OK({waybill_no})")
                break
            body_msg = str((r["body"].get("message") or "")).lower()
            if any(kw in body_msg for kw in ("重复", "duplicate", "exist", "已存在", "already")):
                continue  # 号码冲突，自动递增重试
            raise RuntimeError(f"绑定运单号:FAIL({r['message']})")
        else:
            raise RuntimeError(f"绑定运单号:FAIL(重试 {retry_limit} 次仍冲突，基础号={today}-{base_counter:03d})")

        # ── Step 5.2: 确认发货 ────────────────────────────────────────────────
        sure_cfg = cfg.get("sure_ship_api") or {}
        if not sure_cfg.get("enabled"):
            raise RuntimeError("sure_ship_api 未启用，无法继续")
        r = _post(token, sure_cfg, {"ship_order_no": ship_order_no}, all_rules, "sure_ship_api")
        if not r["success"]:
            raise RuntimeError(f"确认发货:FAIL({r['message']})")
        msgs.append(f"确认发货:OK({ship_order_no}|运单:{waybill_bound})")

        message = " | ".join(msgs)
        result = {
            "success": True,
            "message": message,
            "status_code": 200,
            "actual": f"发货链路: {message}",
        }

    except RuntimeError as e:
        fail_msg = str(e)
        # 把已有 msgs 追加失败消息（如果失败消息还没在里面）
        if fail_msg not in (msgs[-1] if msgs else ""):
            msgs.append(fail_msg)
        message = " | ".join(msgs)
        result = {
            "success": False,
            "message": message,
            "status_code": 500,
            "actual": fail_msg,
        }
    except Exception as e:
        result = {
            "success": False,
            "message": f"执行异常:{type(e).__name__}: {str(e)}",
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
