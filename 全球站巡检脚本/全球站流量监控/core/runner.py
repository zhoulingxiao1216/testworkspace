# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys

from config.settings import SCRIPT_RUNNER_TIMEOUT


class ScriptRunner:
    @staticmethod
    def run(script_relative_path, project_root, task_config):
        script_abs_path = os.path.join(project_root, script_relative_path)
        response = {"success": False, "message": "", "status_code": 500}

        if not os.path.exists(script_abs_path):
            response["message"] = f"脚本不存在: {script_relative_path}"
            return response

        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            runner_timeout = int(task_config.get("runner_timeout") or SCRIPT_RUNNER_TIMEOUT)
            config_json = json.dumps(task_config, ensure_ascii=False)

            process = subprocess.run(
                [sys.executable, script_abs_path, config_json],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                timeout=runner_timeout,
                cwd=project_root,
                env=env,
            )

            stdout_data = process.stdout.strip()
            if process.returncode == 0 and stdout_data:
                last_line = stdout_data.splitlines()[-1]
                parsed_data = json.loads(last_line)
                response["success"] = bool(parsed_data.get("success"))
                response["message"] = parsed_data.get("message", "")
                response["status_code"] = parsed_data.get("status_code", 200 if response["success"] else 500)
                response["expected"] = parsed_data.get("expected")
                response["actual"] = parsed_data.get("actual")
                response["raw"] = parsed_data.get("raw")
                return response

            response["message"] = process.stderr.strip() or stdout_data or f"脚本异常退出 Code:{process.returncode}"
            return response
        except subprocess.TimeoutExpired:
            response["message"] = f"执行超时({SCRIPT_RUNNER_TIMEOUT}s)"
            return response
        except Exception as e:
            response["message"] = f"Runner 内部异常: {type(e).__name__}: {e}"
            return response
