# -*- coding: utf-8 -*-
import json
import os
import sys
import traceback
from datetime import datetime

from config.settings import ENV_TYPE, REPORT_CONFIG
from core.batch_checker import BatchChecker
from core.logger import InspectorLogger
from core.notifier import Notifier


def initialize_environment():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)


def run_inspection():
    initialize_environment()
    logger = InspectorLogger()
    logger.log_session_start(ENV_TYPE)

    print("=" * 60)
    print(
        f"1688 应用流量巡检 | 环境: {ENV_TYPE} | 启动: "
        f"{datetime.now().strftime('%H:%M:%S')}"
    )
    print("=" * 60)

    try:
        checker = BatchChecker(logger_instance=logger)
        results = checker.run_all_checks()
        report_data = results.get("巡检汇总报告", {})
        all_results = [item for item in report_data.values() if isinstance(item, dict)]

        total = len(all_results)
        success = sum(1 for item in all_results if item.get("success") is True)
        failed = total - success
        is_all_pass = total > 0 and failed == 0

        logger.log_summary(total, success, failed)
        print(f"汇总: 共 {total} | 成功 {success} | 异常 {failed}")

        latest_path = os.path.join(REPORT_CONFIG.get("SAVE_DIR", "logs"), "latest-framework-result.json")
        os.makedirs(os.path.dirname(latest_path), exist_ok=True)
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        Notifier.send_wechat_report(report_data, is_all_pass)
        print(f"结果已保存: {os.path.abspath(latest_path)}")
        return results
    except Exception as e:
        error_stack = traceback.format_exc()
        msg = f"巡检框架执行异常: {type(e).__name__}: {e}"
        logger.log_error(f"{msg}\n{error_stack}")
        print(msg)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_inspection()
