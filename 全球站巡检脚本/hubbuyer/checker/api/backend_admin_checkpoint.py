# -*- coding: utf-8 -*-
# checker/api/backend_admin_checkpoint.py
# 后台管理检查点：代购仓配操作 + 当日汇率（汇率最后执行）
import json
import os
import sys
import traceback

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import INSPECTION_SWITCHES
from core.path_manager import DATA_DIR

CONFIG_FILE = "backend_admin.json"
SUB_OPS_DESC = "后台管理检查点-代购仓配"
SUB_RATE_DESC = "后台管理检查点-汇率"
SUB_SHIPPING_DESC = "后台管理检查点-发货链路"


def _load_config():
    path = os.path.join(DATA_DIR, CONFIG_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"modules": {}}


def _module_enabled(cfg, module_name, legacy_switch_key):
    modules = cfg.get("modules") or {}
    module_cfg = modules.get(module_name) or {}
    if "enabled" in module_cfg:
        return bool(module_cfg.get("enabled"))
    return bool(INSPECTION_SWITCHES.get(legacy_switch_key, True))


def _normalize_sub_result(desc, result):
    if not isinstance(result, dict):
        return {
            "success": False,
            "message": f"{desc}:FAIL(子模块返回无效)",
            "status_code": 500,
            "actual": str(result),
        }
    return {
        "success": bool(result.get("success")),
        "message": result.get("message") or "",
        "status_code": result.get("status_code", 200 if result.get("success") else 500),
        "actual": result.get("actual") or result.get("message") or "",
    }


def run(task_config=None):
    cfg = _load_config()
    sub_results = {}
    summary_parts = []

    try:
        if _module_enabled(cfg, "purchase_order_ops", "check_api_purchase_order_ops"):
            from checker.api.purchase_order_ops import run as run_purchase_order_ops

            ops_result = _normalize_sub_result(
                SUB_OPS_DESC, run_purchase_order_ops(task_config)
            )
            sub_results[SUB_OPS_DESC] = ops_result
            summary_parts.append(f"代购仓配:{'OK' if ops_result['success'] else 'FAIL'}")
        else:
            sub_results[SUB_OPS_DESC] = {
                "success": True,
                "message": "代购仓配:跳过(未启用)",
                "status_code": 200,
                "actual": "代购仓配:跳过(未启用)",
            }
            summary_parts.append("代购仓配:跳过")

        if _module_enabled(cfg, "exchange_rate", "check_api_exchange_rate"):
            from checker.api.exchange_rate import run_exchange_rate_check

            rate_result = _normalize_sub_result(
                SUB_RATE_DESC, run_exchange_rate_check(task_config)
            )
            sub_results[SUB_RATE_DESC] = rate_result
            summary_parts.append(f"汇率:{'OK' if rate_result['success'] else 'FAIL'}")
        else:
            sub_results[SUB_RATE_DESC] = {
                "success": True,
                "message": "汇率:跳过(未启用)",
                "status_code": 200,
                "actual": "汇率:跳过(未启用)",
            }
            summary_parts.append("汇率:跳过")

        if _module_enabled(cfg, "purchase_order_shipping", "check_api_purchase_order_shipping"):
            from checker.api.purchase_order_shipping import run as run_purchase_order_shipping

            shipping_result = _normalize_sub_result(
                SUB_SHIPPING_DESC, run_purchase_order_shipping(task_config)
            )
            sub_results[SUB_SHIPPING_DESC] = shipping_result
            summary_parts.append(f"发货链路:{'OK' if shipping_result['success'] else 'FAIL'}")
        else:
            sub_results[SUB_SHIPPING_DESC] = {
                "success": True,
                "message": "发货链路:跳过(未启用)",
                "status_code": 200,
                "actual": "发货链路:跳过(未启用)",
            }
            summary_parts.append("发货链路:跳过")

        active_results = [
            item
            for item in sub_results.values()
            if ":跳过(未启用)" not in str(item.get("message", ""))
        ] or list(sub_results.values())

        all_ok = all(item.get("success") for item in active_results)
        detail_msgs = [
            sub_results[desc]["message"]
            for desc in (SUB_OPS_DESC, SUB_RATE_DESC, SUB_SHIPPING_DESC)
            if sub_results.get(desc, {}).get("message")
        ]

        result = {
            "success": all_ok,
            "message": " | ".join(summary_parts) + " || " + " | ".join(detail_msgs),
            "status_code": 200 if all_ok else 500,
            "actual": " | ".join(detail_msgs),
            "sub_results": sub_results,
        }
    except Exception as e:
        result = {
            "success": False,
            "message": f"执行异常:{type(e).__name__}: {str(e)}",
            "status_code": 500,
            "actual": traceback.format_exc(),
            "sub_results": sub_results,
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
