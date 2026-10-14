# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys

current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import NODE_BIN, SCRIPT_RUNNER_TIMEOUT


def _abs_project_path(value):
    if not value:
        return value
    return value if os.path.isabs(value) else os.path.abspath(os.path.join(project_root, value))


def _parse_last_json(stdout_data):
    for line in reversed(stdout_data.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError("Node 脚本未输出 JSON")


def _traffic_text(data):
    if data.get("used") is not None and data.get("limit") is not None:
        app_name = data.get("appName") or "1688应用"
        return f"**{app_name}**  应用流量：{data['used']}/{data['limit']}"
    return data.get("message") or "-"


def _adapt_result(raw, task_config):
    code = raw.get("code", 500)
    msg = raw.get("msg", "runtime_error")
    data = raw.get("data") or {}
    actual = _traffic_text(data)
    expected = task_config.get("expected", "1688 应用流量低于阈值")

    success = code == 200 and msg == "normal"
    if code == 200 and msg == "warning":
        message = actual
    elif code == 200:
        message = actual
    else:
        message = data.get("message") or msg

    return {
        "success": success,
        "message": message,
        "status_code": code,
        "expected": expected,
        "actual": actual,
        "raw": raw,
    }


def run_open1688_traffic_check(task_config=None):
    task_config = task_config or {}
    node_script = _abs_project_path(task_config.get("node_script", "check-traffic.mjs"))
    runner_timeout = int(task_config.get("runner_timeout") or SCRIPT_RUNNER_TIMEOUT)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Node 脚本只负责采集，微信由当前独立巡检框架统一推送，避免重复。
    env["MONITOR_NOTIFY_ENABLED"] = "false"

    config_file = env.get("MONITOR_CONFIG") or task_config.get("config_file")
    if config_file:
        env["MONITOR_CONFIG"] = _abs_project_path(config_file)

    try:
        process = subprocess.run(
            [NODE_BIN, node_script],
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
        raw = _parse_last_json(stdout_data)
        result = _adapt_result(raw, task_config)
        if process.returncode != 0 and raw.get("code") == 200:
            result["success"] = False
            result["status_code"] = 500
            result["message"] = process.stderr.strip() or result["message"]
    except Exception as e:
        result = {
            "success": False,
            "message": f"1688 流量检查失败: {type(e).__name__}: {e}",
            "status_code": 500,
            "expected": task_config.get("expected", "成功读取 1688 应用流量"),
            "actual": str(e),
        }

    print(json.dumps(result, ensure_ascii=False))
    return result


run = run_open1688_traffic_check


if __name__ == "__main__":
    config = {}
    if len(sys.argv) > 1:
        try:
            config = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            config = {}
    run_open1688_traffic_check(config)
