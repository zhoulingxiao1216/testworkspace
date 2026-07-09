# -*- coding: utf-8 -*-
# checker/api/shipping_context_store.py
# 发货链路运行时上下文存储：入库信息 + 发货单动态 ID + 运单计数器
import json
import os

from core.path_manager import DATA_DIR

CONTEXT_FILE = "shipping_context.json"


def _path():
    return os.path.join(DATA_DIR, CONTEXT_FILE)


def load_shipping_context():
    p = _path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_shipping_context(updates):
    """合并写入，不覆盖已有字段（除非主动传入）。"""
    existing = load_shipping_context()
    existing.update({k: v for k, v in updates.items() if v is not None})
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def clear_shipping_context():
    p = _path()
    if os.path.exists(p):
        os.remove(p)


def allocate_waybill_counter():
    """读取并返回当天全局唯一计数（不递增写入，由调用方在成功后写回）。"""
    from datetime import datetime
    today = datetime.now().strftime("%m%d")
    ctx = load_shipping_context()
    saved_date = ctx.get("waybill_date", "")
    counter = int(ctx.get("waybill_counter", 0)) if saved_date == today else 0
    return counter + 1, today


def commit_waybill_counter(today, counter):
    """确认发货成功后持久化本次使用的计数，下次从 counter+1 开始。"""
    save_shipping_context({"waybill_date": today, "waybill_counter": counter})
