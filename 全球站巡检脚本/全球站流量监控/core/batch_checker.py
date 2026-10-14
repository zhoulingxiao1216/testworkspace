# -*- coding: utf-8 -*-
import json
import os
import time

from config.settings import INSPECTION_INTERVAL, INSPECTION_SWITCHES
from core.logger import InspectorLogger
from core.runner import ScriptRunner


class BatchChecker:
    def __init__(self, logger_instance=None):
        self.results = {}
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rules_dir = os.path.join(self.project_root, "config", "rules")
        self.logger = logger_instance if logger_instance else InspectorLogger()

    def run_all_checks(self):
        print("\n启动独立流量巡检")
        if not os.path.exists(self.rules_dir):
            print(f"配置目录不存在: {self.rules_dir}")
            return {}

        batch_results = {}
        json_files = sorted(f for f in os.listdir(self.rules_dir) if f.endswith(".json"))

        for file_name in json_files:
            file_path = os.path.join(self.rules_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                task_group = json.load(f)

            for _, task_config in task_group.items():
                task_key = task_config.get("key")
                task_desc = task_config.get("desc")
                if not task_key or not task_desc:
                    continue

                if not INSPECTION_SWITCHES.get(task_key, False):
                    print(f"跳过: {task_desc} (已关闭)")
                    continue

                print(f"正在检查: {task_desc}...")
                result = ScriptRunner.run(task_config.get("script"), self.project_root, task_config)
                status_icon = "OK" if result.get("success") else "FAIL"
                print(f"   {status_icon}: {result.get('message')}")

                self.logger.log_task(
                    name=task_desc,
                    success=result.get("success", False),
                    message=result.get("message", ""),
                    status_code=result.get("status_code"),
                    expected=result.get("expected"),
                    actual=result.get("actual"),
                )

                batch_results[task_desc] = {
                    "success": result.get("success"),
                    "message": result.get("message"),
                    "status_code": result.get("status_code", 0),
                    "expected": result.get("expected"),
                    "actual": result.get("actual"),
                    "raw": result.get("raw"),
                }

                if INSPECTION_INTERVAL > 0:
                    time.sleep(INSPECTION_INTERVAL)

        self.results = {"巡检汇总报告": batch_results}
        return self.results
