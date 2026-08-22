# -*- coding: utf-8 -*-
# 报价单/代购订单号读写（提交→报价单审核→支付→代购订单审核）
import json
import os

from core.path_manager import DATA_DIR, TOKEN_DIR

SUBMIT_RECORD_FILE = "submit_order_record.json"


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
    if not os.path.exists(record_file):
        return ""
    try:
        with open(record_file, "r", encoding="utf-8") as f:
            record_data = json.load(f)
        records = record_data.get(target_mail, [])
        if records and isinstance(records[0], dict):
            return (records[0].get("quote_no") or "").strip()
    except Exception:
        pass
    return ""


def mark_quote_audited(orderid_file, target_mail, quote_no):
    """报价单审核通过后，标记待前台支付"""
    mapping = _load_orderid_mapping(orderid_file)
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
    return (info.get("B2B_quote_pending_pay") or "").strip()


def update_orderid_after_pay(orderid_file, target_mail, quote_no):
    """前台支付成功后写入 DD 订单号，供代购订单审核读取"""
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
    return (info.get("B2B_round_order") or "").strip()


def validate_round_order_matches_quote(target_mail, order_no):
    """校验代购订单号与本轮最新提交报价单一致（BJ→DD 后缀须相同）"""
    quote_no = get_latest_submitted_quote(target_mail)
    if not quote_no:
        return
    expected = convert_quote_to_order_no(quote_no)
    if order_no != expected:
        raise RuntimeError(
            f"代购订单号与本轮报价单不一致: got={order_no} expected={expected} (quote={quote_no})"
        )
