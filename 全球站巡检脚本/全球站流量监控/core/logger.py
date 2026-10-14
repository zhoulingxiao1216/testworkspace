# -*- coding: utf-8 -*-
import os
from datetime import datetime


class InspectorLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "framework.log")

    def _write(self, level, message):
        line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{level}] {message}"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def log_session_start(self, env_type):
        self._write("INFO", f"巡检启动 | env={env_type}")

    def log_task(self, name, success, message, status_code=None, expected=None, actual=None):
        state = "PASS" if success else "FAIL"
        details = f"{name} | {state} | status={status_code} | message={message}"
        if expected is not None:
            details += f" | expected={expected}"
        if actual is not None:
            details += f" | actual={actual}"
        self._write("INFO", details)

    def log_summary(self, total, success, failed):
        self._write("INFO", f"汇总 | total={total} success={success} failed={failed}")

    def log_error(self, message):
        self._write("ERROR", message)
