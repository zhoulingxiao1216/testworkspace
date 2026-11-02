# -*- coding: utf-8 -*-
# 报价单/代购订单号读写（提交→报价单审核→支付→代购订单审核）
import json
import os
from datetime import datetime
from uuid import uuid4

from core.path_manager import DATA_DIR, TOKEN_DIR
from config.settings import ENV_TYPE

SUBMIT_RECORD_FILE = "submit_order_record.json"


def current_round_binding():
    run_id = os.environ.get("HUBBUYER_RUN_ID", "").strip()
    return {"run_id": run_id, "env_type": ENV_TYPE} if run_id else {}


def _matches_round(info):
    binding = current_round_binding()
    return bool(binding) and all(info.get(key) == value for key, value in binding.items())


def convert_quote_to_order_no(quote_no):
    """付款后 B2B-BJ → B2B-DD"""
    if quote_no.startswith("B2B-BJ"):
        return "B2B-DD" + quote_no[6:]
    return quote_no


def revert_order_to_quote_no(order_no):
    if order_no.startswith("B2B-DD"):
        return "B2B-BJ" + order_no[6:]
    return order_no


def _load_orderid_mapping(orderid_file):
    if os.path.exists(orderid_file):
        try:
            with open(orderid_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_orderid_mapping(orderid_file, mapping):
    with open(orderid_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def resolve_target_mail(default_mail="mxnrq@airsworld.net"):
    token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                tokens_data = json.load(f)
                if tokens_data:
                    return list(tokens_data.keys())[0]
        except Exception:
            pass
    return default_mail


def get_latest_submitted_quote(target_mail):
    """读取本轮最新提交的报价单号（submit_order_record 首位）"""
    record_file = os.path.join(DATA_DIR, SUBMIT_RECORD_FILE)
    try:
        record_data = _load_orderid_mapping(record_file)
        records = record_data.get(target_mail, [])
        if records and isinstance(records[0], dict) and _matches_round(records[0]):
            return (records[0].get("quote_no") or "").strip()
    except Exception:
        pass
    return ""


def begin_quote_submission(target_mail):
    """Invalidate previous round before any new submission, including failed attempts."""
    if not os.environ.get("HUBBUYER_RUN_ID", "").strip():
        os.environ["HUBBUYER_RUN_ID"] = uuid4().hex
    order_path = os.path.join(DATA_DIR, "payment_orderid.json")
    clear_quote_audit_state(order_path, target_mail)
    mapping = _load_orderid_mapping(order_path)
    mapping[target_mail].update(current_round_binding())
    _save_orderid_mapping(order_path, mapping)
    record_file = os.path.join(DATA_DIR, SUBMIT_RECORD_FILE)
    records = _load_orderid_mapping(record_file)
    history = records.get(target_mail, [])
    records[target_mail] = [{
        "quote_no": "", "status": "submission_started",
        "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **current_round_binding(),
    }] + history[:19]
    _save_orderid_mapping(record_file, records)


def record_submitted_quote(target_mail, quote_no):
    """Accept only a newly returned quote for this submission attempt."""
    if not isinstance(quote_no, str) or not quote_no.startswith("B2B-BJ-"):
        raise RuntimeError("新增报价单号为空或格式无效")
    record_file = os.path.join(DATA_DIR, SUBMIT_RECORD_FILE)
    records = _load_orderid_mapping(record_file)
    history = records.get(target_mail, [])
    if not history or not _matches_round(history[0]) or history[0].get("status") != "submission_started":
        raise RuntimeError("缺少本轮新增报价提交上下文")
    if any(item.get("quote_no") == quote_no for item in history if isinstance(item, dict)):
        raise RuntimeError("报价单已存在于历史记录，禁止作为本轮新增订单")
    history[0].update(quote_no=quote_no, status="submitted")
    _save_orderid_mapping(record_file, records)


def mark_quote_audited(orderid_file, target_mail, quote_no):
    """报价单审核通过后，标记待前台支付"""
    mapping = _load_orderid_mapping(orderid_file)
    if not _matches_round(mapping.get(target_mail, {})) or get_latest_submitted_quote(target_mail) != quote_no:
        raise RuntimeError("报价单不属于本轮新增订单，禁止标记审核通过")
    if target_mail not in mapping:
        mapping[target_mail] = {"B2B": [], "D2C": []}
    mapping[target_mail]["B2B_quote_pending_pay"] = quote_no
    mapping[target_mail]["B2B_quote_audited"] = quote_no
    # 新一轮审核前清空已支付代购订单标记
    mapping[target_mail]["B2B_round_order"] = ""
    _save_orderid_mapping(orderid_file, mapping)


def clear_quote_audit_state(orderid_file, target_mail):
    """开始新一轮报价单审核前清理历史联动单号，避免后续支付误用旧单。"""
    mapping = _load_orderid_mapping(orderid_file)
    if target_mail not in mapping:
        mapping[target_mail] = {"B2B": [], "D2C": []}
    mapping[target_mail]["B2B_quote_pending_pay"] = ""
    mapping[target_mail]["B2B_quote_audited"] = ""
    mapping[target_mail]["B2B_round_quote"] = ""
    mapping[target_mail]["B2B_round_order"] = ""
    _save_orderid_mapping(orderid_file, mapping)


def get_audited_pending_pay_quote(orderid_file, target_mail):
    """读取已通过报价单审核、待前台支付的报价单号"""
    mapping = _load_orderid_mapping(orderid_file)
    info = mapping.get(target_mail, {})
    quote_no = (info.get("B2B_quote_pending_pay") or "").strip()
    if not _matches_round(info) or not quote_no or quote_no != get_latest_submitted_quote(target_mail):
        return ""
    return quote_no if info.get("B2B_quote_audited") == quote_no else ""


def update_orderid_after_pay(orderid_file, target_mail, quote_no):
    """前台支付成功后写入 DD 订单号，供代购订单审核读取"""
    if not quote_no or get_audited_pending_pay_quote(orderid_file, target_mail) != quote_no:
        raise RuntimeError("支付报价单不属于本轮已审核新增订单")
    order_no = convert_quote_to_order_no(quote_no)
    mapping = _load_orderid_mapping(orderid_file)
    if target_mail not in mapping:
        mapping[target_mail] = {"B2B": [], "D2C": []}
    b2b_list = mapping[target_mail].get("B2B", [])
    b2b_list = [x for x in b2b_list if x not in (quote_no, order_no)]
    b2b_list.insert(0, order_no)
    mapping[target_mail]["B2B"] = b2b_list
    mapping[target_mail]["B2B_quote_latest"] = quote_no
    mapping[target_mail]["B2B_order_latest"] = order_no
    mapping[target_mail]["B2B_round_quote"] = quote_no
    mapping[target_mail]["B2B_round_order"] = order_no
    mapping[target_mail]["B2B_quote_pending_pay"] = ""
    _save_orderid_mapping(orderid_file, mapping)
    return order_no


def get_round_paid_order(orderid_file, target_mail):
    """读取本轮已支付对应的代购订单号（DD），仅认 B2B_round_order"""
    mapping = _load_orderid_mapping(orderid_file)
    info = mapping.get(target_mail, {})
    quote_no = get_latest_submitted_quote(target_mail)
    if not _matches_round(info) or not quote_no or info.get("B2B_round_quote") != quote_no:
        return ""
    order_no = (info.get("B2B_round_order") or "").strip()
    return order_no if order_no == convert_quote_to_order_no(quote_no) else ""


def validate_round_order_matches_quote(target_mail, order_no):
    """校验代购订单号与本轮最新提交报价单一致（BJ→DD 后缀须相同）"""
    quote_no = get_latest_submitted_quote(target_mail)
    if not quote_no:
        raise RuntimeError("缺少本轮新增报价单，禁止使用历史代购订单")
    expected = convert_quote_to_order_no(quote_no)
    if order_no != expected:
        raise RuntimeError(
            f"代购订单号与本轮报价单不一致: got={order_no} expected={expected} (quote={quote_no})"
        )


def validate_shipping_round(context, target_mail):
    if not _matches_round(context):
        raise RuntimeError("发货上下文不属于本轮及当前环境，禁止使用历史入库数据")
    order_no = get_round_paid_order(os.path.join(DATA_DIR, "payment_orderid.json"), target_mail)
    if not order_no or context.get("order_no") != order_no:
        raise RuntimeError("发货上下文不是本轮新增且已支付的订单")
    validate_round_order_matches_quote(target_mail, order_no)
