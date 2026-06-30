# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import csv
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st


st.set_page_config(page_title="性能压测", page_icon="🚦", layout="wide")


def apply_sku_like_theme():
    st.markdown(
        """
        <style>
        :root {
            --perf-bg: #ffffff;
            --perf-panel: #ffffff;
            --perf-sidebar: #f6f7fb;
            --perf-sidebar-active: #e8edf7;
            --perf-border: #e5e7eb;
            --perf-text: #111827;
            --perf-muted: #6b7280;
            --perf-blue-soft: #eef6ff;
        }

        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {
            background: var(--perf-bg) !important;
            color: var(--perf-text) !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div:first-child {
            background: var(--perf-sidebar) !important;
            border-right: 1px solid var(--perf-border) !important;
        }

        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {
            color: #374151 !important;
        }

        [data-testid="stSidebar"] a[aria-current="page"],
        [data-testid="stSidebar"] li:has(a[aria-current="page"]) {
            background: var(--perf-sidebar-active) !important;
            border-radius: 8px !important;
        }

        h1, h2, h3, h4, h5, h6,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
            color: var(--perf-text) !important;
        }

        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] * {
            color: var(--perf-muted) !important;
        }

        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stForm"]) {
            background: var(--perf-panel) !important;
            border: 1px solid var(--perf-border) !important;
            border-radius: 10px !important;
            padding: 1rem 1.25rem !important;
        }

        [data-testid="stAlert"] {
            background: var(--perf-blue-soft) !important;
            color: #1f2937 !important;
            border: 1px solid #dbeafe !important;
            border-radius: 8px !important;
        }

        .stTextInput input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            background: #ffffff !important;
            color: var(--perf-text) !important;
            border-color: #d1d5db !important;
        }

        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stSelectbox div[data-baseweb="select"] > div:focus-within,
        .stMultiSelect div[data-baseweb="select"] > div:focus-within {
            border-color: #ef4444 !important;
            box-shadow: 0 0 0 1px #ef4444 !important;
        }

        [data-testid="stMetric"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }

        code, pre,
        [data-testid="stCodeBlock"] {
            background: #f8fafc !important;
            color: #111827 !important;
            border-radius: 8px !important;
        }

        [data-testid="stCodeBlock"] pre {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }

        .stButton > button,
        [data-testid="stDownloadButton"] button {
            border-radius: 8px !important;
            border: 1px solid #d1d5db !important;
            background: #ffffff !important;
            color: #111827 !important;
        }

        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] button {
            background: #ef4444 !important;
            border-color: #ef4444 !important;
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_sku_like_theme()


APP_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = APP_ROOT.parent
PERFORMANCE_ROOT = WORKSPACE_ROOT / "全球站压测脚本" / "Performance"
REPORT_DIR = PERFORMANCE_ROOT / "reports"
STATE_PATH = REPORT_DIR / ".streamlit_locust_run.json"
HISTORY_PATH = REPORT_DIR / ".streamlit_locust_runs.json"
MAX_HISTORY_ITEMS = 100

# 压测类型 -> 入口 locustfile 映射
SCRIPT_TYPE_OPTIONS = {
    "接口压测": "locustfile_api.py",
    "UI 压测": "locustfile_ui.py",
    "全部（接口+UI）": "locustfile.py",
}
DEFAULT_SCRIPT_TYPE = "接口压测"


def ensure_session_default(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


def init_stress_form_defaults():
    ensure_session_default("stress_env_type", "test")
    ensure_session_default("stress_script_type", DEFAULT_SCRIPT_TYPE)
    ensure_session_default("stress_virtual_users", 20)
    ensure_session_default("stress_real_spawn_rate", 1.0)
    ensure_session_default("stress_virtual_spawn_rate", 10.0)
    ensure_session_default("stress_duration", "10m")
    ensure_session_default("stress_browse_steps", 2)
    ensure_session_default("stress_enable_add_cart", True)
    ensure_session_default("stress_enable_taobao_keyword", False)
    ensure_session_default("stress_enable_taobao_detail", False)
    ensure_session_default("stress_enable_taobao_add_cart", False)
    ensure_session_default("stress_enable_submit_order", False)
    ensure_session_default("stress_enable_full_quote_flow", True)
    ensure_session_default("stress_enable_quote_download", True)
    ensure_session_default("stress_quote_download_language", "english")
    ensure_session_default("stress_quote_type", 2)
    ensure_session_default("stress_logistics_config_id", 28)
    ensure_session_default("stress_submit_order_max_cart_items", 1)


def resolve_locustfile(script_type):
    return SCRIPT_TYPE_OPTIONS.get(script_type, "locustfile.py")


def load_accounts_pool():
    config_path = PERFORMANCE_ROOT / "config" / "data" / "stress_accounts.py"
    if not config_path.exists():
        return {}

    namespace = {}
    exec(compile(config_path.read_text(encoding="utf-8"), str(config_path), "exec"), namespace)
    return namespace.get("STRESS_ACCOUNTS_POOL", {})


def read_state():
    if not STATE_PATH.exists():
        return None
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_state(state):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def read_history():
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def write_history(history):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history[:MAX_HISTORY_ITEMS], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_history(task):
    if not task:
        return
    history = read_history()
    run_id = task.get("run_id")
    updated = False
    next_history = []
    for item in history:
        if run_id and item.get("run_id") == run_id:
            next_history.append(task)
            updated = True
        else:
            next_history.append(item)
    if not updated:
        next_history.insert(0, task)
    write_history(next_history)


def is_pid_running(pid):
    if not pid:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        return str(pid) in result.stdout

    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def parse_timestamp(raw):
    if not raw:
        return None
    value = str(raw).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S.%f%z", "%Y%m%d%H%M%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_elapsed(started_at, finished_at=None):
    started = parse_timestamp(started_at)
    if not started:
        return "-"
    finished = parse_timestamp(finished_at) if finished_at else datetime.now(started.tzinfo)
    seconds = max(0, int((finished - started).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def normalize_for_match(value):
    return str(value or "").replace("\\", "/").lower()


def command_belongs_to_performance(command_line):
    command = normalize_for_match(command_line)
    performance_root = normalize_for_match(PERFORMANCE_ROOT)
    report_dir = normalize_for_match(REPORT_DIR)
    return bool(re.search(r"locustfile(_\w+)?\.py", command)) and (
        performance_root in command
        or report_dir in command
        or "全球站压测脚本" in str(command_line or "")
    )


def list_locust_processes():
    if os.name == "nt":
        script = r"""
$items = @(
  Get-CimInstance Win32_Process |
    Where-Object {
      $_.CommandLine -and
      ($_.CommandLine -match 'locustfile(_\w+)?\.py') -and
      ($_.Name -notmatch '^(powershell|pwsh)\.exe$')
    } |
    ForEach-Object {
      [PSCustomObject]@{
        pid = [int]$_.ProcessId
        parent_pid = [int]$_.ParentProcessId
        name = $_.Name
        created_at = if ($_.CreationDate) { $_.CreationDate.ToString('yyyy-MM-dd HH:mm:ss') } else { '' }
        executable = $_.ExecutablePath
        command_line = $_.CommandLine
      }
    }
)
$items | ConvertTo-Json -Compress
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=8,
            )
        except Exception:
            return []
        if result.returncode != 0 or not result.stdout.strip():
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        items = data if isinstance(data, list) else [data]
    else:
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid=,ppid=,comm=,lstart=,args="],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=8,
            )
        except Exception:
            return []
        items = []
        for line in result.stdout.splitlines():
            if not re.search(r"locustfile(_\w+)?\.py", line):
                continue
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            items.append(
                {
                    "pid": parts[0],
                    "parent_pid": parts[1],
                    "name": parts[2],
                    "created_at": " ".join(parts[3:8]),
                    "executable": parts[2],
                    "command_line": parts[8],
                }
            )

    processes = []
    for item in items:
        try:
            pid = int(item.get("pid"))
        except (TypeError, ValueError):
            continue
        command_line = item.get("command_line", "")
        processes.append(
            {
                "pid": pid,
                "parent_pid": item.get("parent_pid", ""),
                "name": item.get("name", ""),
                "created_at": item.get("created_at", ""),
                "elapsed": format_elapsed(item.get("created_at")),
                "executable": item.get("executable", ""),
                "command_line": command_line,
                "safe_to_stop": command_belongs_to_performance(command_line),
            }
        )
    return sorted(processes, key=lambda item: item.get("created_at") or "", reverse=True)


def is_pid_in_processes(pid, processes):
    try:
        target_pid = int(pid)
    except (TypeError, ValueError):
        return False
    return any(process.get("pid") == target_pid for process in processes or [])


def find_process(pid, processes):
    try:
        target_pid = int(pid)
    except (TypeError, ValueError):
        return None
    for process in processes or []:
        if process.get("pid") == target_pid:
            return process
    return None


def find_related_task(process, tasks):
    command_line = process.get("command_line", "") if process else ""
    pid = process.get("pid") if process else None
    for task in tasks:
        if not task:
            continue
        if pid and str(task.get("pid")) == str(pid):
            return task
        run_id = task.get("run_id")
        if run_id and run_id in command_line:
            return task
    return None


def refresh_history(history, processes):
    running_pids = {process.get("pid") for process in processes or []}
    changed = False
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    refreshed = []
    for item in history:
        status = item.get("status")
        try:
            pid = int(item.get("pid"))
        except (TypeError, ValueError):
            pid = None
        if status == "running" and pid and pid not in running_pids:
            item = dict(item)
            item["status"] = "finished"
            item["finished_at"] = item.get("finished_at") or now
            changed = True
        refreshed.append(item)
    if changed:
        write_history(refreshed)
    return refreshed


def refresh_state(state, processes=None):
    if not state:
        return None, False
    if processes is None:
        running = is_pid_running(state.get("pid"))
    else:
        running = is_pid_in_processes(state.get("pid"), processes)
    if not running and state.get("status") == "running":
        state["status"] = "finished"
        state["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        write_state(state)
        upsert_history(state)
    return state, running


def stop_process(pid, process=None, known_task=None):
    if not pid:
        return False, "缺少 PID，无法停止进程。"

    if process is None:
        process = find_process(pid, list_locust_processes())
    if not known_task and process and not process.get("safe_to_stop"):
        return False, "出于安全考虑，只允许停止属于当前 Performance 目录或平台历史任务的 Locust 进程。"
    if not known_task and process is None:
        return False, "未在系统进程列表中找到该 Locust 进程。"

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    else:
        result = subprocess.run(
            ["kill", "-TERM", str(pid)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    if result.returncode != 0:
        return False, result.stderr or result.stdout or "停止进程失败。"
    return True, "已发送停止命令。"


def stop_run(state, processes=None):
    pid = state.get("pid") if state else None
    process = find_process(pid, processes or list_locust_processes())
    success, message = stop_process(pid, process=process, known_task=state)
    if not success:
        return False, message

    state["status"] = "stopped"
    state["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_state(state)
    upsert_history(state)
    return True, message


def parse_duration_seconds(raw):
    value = str(raw or "").strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s|m|h)?", value)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2) or "s"
    factor = {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return max(1, int(number * factor))


def safe_run_id(env_type, real_users, virtual_users, duration):
    duration_part = re.sub(r"[^0-9a-zA-Z]+", "", str(duration)) or "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"stress_{env_type}_{real_users}r_{virtual_users}v_{duration_part}_{ts}"


def quote_cmd(command):
    parts = []
    for item in command:
        item = str(item)
        if " " in item:
            parts.append(f'"{item}"')
        else:
            parts.append(item)
    return " ".join(parts)


def read_tail(path, lines=80):
    path = Path(path)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def read_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = []
        for row in reader:
            cleaned = {
                str(key).strip(): str(value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            if any(cleaned.values()):
                rows.append(cleaned)
    return rows


def to_float(value, default=0.0):
    try:
        return float(str(value or "").replace(",", ""))
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        return int(float(str(value or "").replace(",", "")))
    except (TypeError, ValueError):
        return default


def format_number(value):
    return f"{to_int(value):,}"


def format_ms(value):
    number = to_float(value)
    if number >= 1000:
        return f"{number / 1000:.2f}s"
    return f"{number:.0f}ms"


def format_percent(value):
    return f"{to_float(value):.2f}%"


def get_artifact_paths(task):
    csv_prefix = Path(task.get("csv_prefix", "")) if task else Path("")
    if not csv_prefix or str(csv_prefix) == ".":
        report_path = Path(task.get("html_report", "")) if task else Path("")
        csv_prefix = report_path.with_suffix("") if report_path else Path("")
    return {
        "stats": Path(f"{csv_prefix}_stats.csv"),
        "failures": Path(f"{csv_prefix}_failures.csv"),
        "failure_details": Path(f"{csv_prefix}_failure_details.jsonl"),
        "exceptions": Path(f"{csv_prefix}_exceptions.csv"),
        "history": Path(f"{csv_prefix}_stats_history.csv"),
    }


def find_aggregate_row(stats_rows):
    for row in stats_rows:
        if row.get("Name") == "Aggregated":
            return row
    return stats_rows[-1] if stats_rows else {}


def failure_rate(row):
    requests = to_float(row.get("Request Count"))
    failures = to_float(row.get("Failure Count"))
    if requests <= 0:
        return 0.0
    return failures / requests * 100


def build_request_rows(stats_rows):
    rows = []
    for row in stats_rows:
        name = row.get("Name", "")
        if not name or name == "Aggregated":
            continue
        rows.append(
            {
                "类型": row.get("Type", "-"),
                "名称": name,
                "请求数": to_int(row.get("Request Count")),
                "失败数": to_int(row.get("Failure Count")),
                "失败率": format_percent(failure_rate(row)),
                "平均": format_ms(row.get("Average Response Time")),
                "中位": format_ms(row.get("Median Response Time")),
                "P95": format_ms(row.get("95%")),
                "最大": format_ms(row.get("Max Response Time")),
                "RPS": round(to_float(row.get("Requests/s")), 2),
            }
        )
    return rows


def build_failure_rows(failure_rows):
    account_pattern = re.compile(r"\[账号:([^\]]+)\]")
    detail_pattern = re.compile(r"详情:(.+)$")
    rows = []
    for row in failure_rows:
        error_text = row.get("Error", "-")
        account_match = account_pattern.search(error_text)
        account = account_match.group(1) if account_match else "-"
        summary = account_pattern.sub("", error_text).strip()
        detail_match = detail_pattern.search(summary)
        detail = detail_match.group(1).strip() if detail_match else ""
        if detail:
            summary = detail_pattern.sub("", summary).strip()
        rows.append(
            {
                "类型": row.get("Method", "-"),
                "名称": row.get("Name", "-"),
                "账号": account,
                "错误": summary or error_text,
                "详情": detail or "-",
                "次数": to_int(row.get("Occurrences")),
                "首次出现": row.get("First Seen", "-"),
                "最后出现": row.get("Last Seen", "-"),
            }
        )
    return sorted(rows, key=lambda item: item["次数"], reverse=True)


def read_failure_detail_rows(path, limit=100):
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(
            {
                "时间": item.get("time", "-"),
                "类型": item.get("type", "-"),
                "名称": item.get("name", "-"),
                "账号": item.get("account", "-"),
                "错误": item.get("error", "-"),
                "URL": item.get("url", "-"),
                "HTTP": item.get("http_status", "-"),
                "响应摘要": item.get("response", "-"),
            }
        )
    return list(reversed(rows))


def filter_log_text(path, lines=120, keyword=""):
    text = read_tail(path, lines=lines)
    if not keyword:
        return text
    keyword_lower = keyword.lower()
    return "\n".join(line for line in text.splitlines() if keyword_lower in line.lower())


def _resolve_full_quote_flow(config):
    """提交报价单关闭时，完整报价链路强制关闭。"""
    if not config.get("enable_submit_order"):
        return False
    return bool(config.get("enable_full_quote_flow", True))


def _resolve_quote_download(config):
    """提交报价单关闭时，报价单下载检查点强制关闭。"""
    if not config.get("enable_submit_order"):
        return False
    return bool(config.get("enable_quote_download", True))


def build_stress_runtime_env(config):
    """平台注入 Locust 的 STRESS_* 环境变量。"""
    enable_full_quote = _resolve_full_quote_flow(config)
    enable_quote_download = _resolve_quote_download(config)
    return {
        "STRESS_ENV": config["env_type"],
        "STRESS_ACCOUNT_EMAILS": ",".join(config.get("selected_emails", [])),
        "STRESS_REAL_USERS": str(config["real_users"]),
        "STRESS_VIRTUAL_USERS": str(config["virtual_users"]),
        "STRESS_REAL_SPAWN_RATE": str(config["real_spawn_rate"]),
        "STRESS_VIRTUAL_SPAWN_RATE": str(config["virtual_spawn_rate"]),
        "STRESS_RUN_TIME": config["duration"],
        "STRESS_USE_SPLIT_LOAD_SHAPE": "1",
        "STRESS_ENABLE_ADD_CART": "1" if config["enable_add_cart"] else "0",
        "STRESS_ENABLE_SUBMIT_ORDER": "1" if config["enable_submit_order"] else "0",
        "STRESS_ENABLE_FULL_QUOTE_FLOW": "1" if enable_full_quote else "0",
        "STRESS_ENABLE_QUOTE_DOWNLOAD": "1" if enable_quote_download else "0",
        "STRESS_QUOTE_DOWNLOAD_LANGUAGE": str(config.get("quote_download_language", "english")),
        "STRESS_ENABLE_TAOBAO_KEYWORD": "1" if config.get("enable_taobao_keyword", False) else "0",
        "STRESS_ENABLE_TAOBAO_DETAIL": "1" if config.get("enable_taobao_detail", False) else "0",
        "STRESS_ENABLE_TAOBAO_ADD_CART": "1" if config.get("enable_taobao_add_cart", False) else "0",
        "STRESS_BROWSE_STEPS": str(config["browse_steps"]),
        "STRESS_SUBMIT_ORDER_MAX_CART_ITEMS": str(config["submit_order_max_cart_items"]),
        "STRESS_QUOTE_TYPE": str(config.get("quote_type", 2)),
        "STRESS_LOGISTICS_CONFIG_ID": str(config.get("logistics_config_id", 28)),
    }


def build_preview_command(config):
    env_lines = [f"$env:{key} = \"{value}\"" for key, value in build_stress_runtime_env(config).items()]
    env_lines.extend(
        [
            "",
            f"locust -f {resolve_locustfile(config.get('script_type', DEFAULT_SCRIPT_TYPE))} "
            "--headless --html reports/<run_id>.html --csv reports/<run_id>",
        ]
    )
    return "\n".join(env_lines)


def build_real_user_steps(config):
    if config["real_users"] <= 0:
        return ["本次不启动真实账号用户。"]

    steps = [
        "按账号池分配真实注册账号，缺少 Token 时先登录预热。",
        f"每个链路任务内随机执行 {config['browse_steps']} 次图搜或关键词搜索。",
    ]
    if config["enable_add_cart"]:
        steps.append("执行浏览 + 加购链路，并读取购物车列表确认加购结果。")
    else:
        steps.append("加购链路关闭，只保留登录刷新和浏览类行为。")

    if config["enable_submit_order"]:
        max_items = config["submit_order_max_cart_items"]
        if _resolve_full_quote_flow(config):
            quote_type = config.get("quote_type", 2)
            logistics_id = config.get("logistics_config_id", 28)
            steps.extend(
                [
                    f"执行浏览 + 加购 + 完整报价链路，每次最多提交 {max_items} 条购物车明细。",
                    "附加项（FJX）：getCheckFjxList → updateCheckFjx → getCheckFjxFeeTotal → cartQuoteStep1/cartDetailList。",
                    "订单确认（B2B）：cartQuoteStep2/cartDetailList → cartDetailListTotalFee → quote/create。",
                    f"quote/create 参数：quote_type={quote_type}，logistics_config_id={logistics_id}。",
                ]
            )
        else:
            steps.append(
                f"执行简化下单链路：加购后直接 quote/create，每次最多提交 {max_items} 条购物车明细。"
            )
        if _resolve_quote_download(config):
            language = config.get("quote_download_language", "english")
            steps.append(
                f"提交报价单成功后接力下载当轮报价单（quotedetail/downQuote，language={language}）。"
            )
        else:
            steps.append("报价单下载检查点关闭，提交报价单后不会执行 downQuote。")
    else:
        steps.append("提交报价单链路关闭，不会提交报价单。")
    return steps


def build_virtual_user_steps(config):
    if config["virtual_users"] <= 0:
        return ["本次不启动虚拟账号用户。"]

    return [
        "不登录，不占用真实注册账号池。",
        "访问 B2B 页面，模拟普通在线访客浏览。",
        "调用关键词搜索接口，形成轻量查询流量。",
        "不执行加购、购物车列表、提交报价单等写入链路。",
    ]


def render_step_list(title, subtitle, steps):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(subtitle)
        for index, step in enumerate(steps, start=1):
            st.markdown(f"{index}. {step}")


def start_locust_run(config):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    run_id = safe_run_id(
        config["env_type"],
        config["real_users"],
        config["virtual_users"],
        config["duration"],
    )
    html_path = REPORT_DIR / f"{run_id}.html"
    csv_prefix = REPORT_DIR / run_id
    stdout_path = REPORT_DIR / f"{run_id}_run.out.log"
    stderr_path = REPORT_DIR / f"{run_id}_run.err.log"

    locustfile_name = resolve_locustfile(config.get("script_type", DEFAULT_SCRIPT_TYPE))
    command = [
        "locust",
        "-f",
        locustfile_name,
        "--headless",
        "--html",
        str(html_path),
        "--csv",
        str(csv_prefix),
    ]

    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", **build_stress_runtime_env(config)})
    env["STRESS_FAILURE_DETAIL_PATH"] = f"{csv_prefix}_failure_details.jsonl"

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    stdout_file = stdout_path.open("w", encoding="utf-8")
    stderr_file = stderr_path.open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(PERFORMANCE_ROOT),
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
        )
    finally:
        stdout_file.close()
        stderr_file.close()

    state = {
        "run_id": run_id,
        "pid": proc.pid,
        "status": "running",
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": "",
        "command": quote_cmd(command),
        "config": config,
        "html_report": str(html_path),
        "csv_prefix": str(csv_prefix),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }
    write_state(state)
    upsert_history(state)
    return state


st.title("🚦 性能压测")

if st.button("⬅️ 返回项目首页"):
    st.switch_page("app.py")

if not PERFORMANCE_ROOT.exists():
    st.error(f"未找到压测工程目录：{PERFORMANCE_ROOT}")
    st.stop()

accounts_pool = load_accounts_pool()
locust_processes = list_locust_processes()
state, state_running = refresh_state(read_state(), locust_processes)
state_config = state.get("config") if isinstance(state, dict) else None
state_run_id = state.get("run_id") if isinstance(state, dict) else None
active_state_config = state_config if state_running and isinstance(state_config, dict) else None
if isinstance(state_config, dict) and state_run_id:
    hydrate_key = "stress_hydrated_from_run_id"
    if active_state_config or st.session_state.get(hydrate_key) != state_run_id:
        state_env = state_config.get("env_type", "test")
        if state_env in {"test", "main", "prod"}:
            st.session_state["stress_env_type"] = state_env
            st.session_state[f"stress_real_accounts_{state_env}"] = state_config.get("selected_emails", [])
            st.session_state[f"stress_real_users_{state_env}"] = int(state_config.get("real_users", 0))
        st.session_state["stress_virtual_users"] = int(state_config.get("virtual_users", 20))
        st.session_state["stress_real_spawn_rate"] = float(state_config.get("real_spawn_rate", 1.0))
        st.session_state["stress_virtual_spawn_rate"] = float(state_config.get("virtual_spawn_rate", 10.0))
        st.session_state["stress_duration"] = state_config.get("duration", "10m")
        st.session_state["stress_browse_steps"] = int(state_config.get("browse_steps", 2))
        st.session_state["stress_enable_add_cart"] = bool(state_config.get("enable_add_cart", True))
        st.session_state["stress_enable_submit_order"] = bool(state_config.get("enable_submit_order", False))
        st.session_state["stress_enable_full_quote_flow"] = bool(
            state_config.get("enable_full_quote_flow", state_config.get("enable_submit_order", False))
        )
        st.session_state["stress_enable_quote_download"] = bool(
            state_config.get("enable_quote_download", state_config.get("enable_submit_order", False))
        )
        st.session_state["stress_quote_download_language"] = state_config.get("quote_download_language", "english")
        st.session_state["stress_enable_taobao_keyword"] = bool(state_config.get("enable_taobao_keyword", False))
        st.session_state["stress_enable_taobao_detail"] = bool(state_config.get("enable_taobao_detail", False))
        st.session_state["stress_enable_taobao_add_cart"] = bool(state_config.get("enable_taobao_add_cart", False))
        st.session_state["stress_submit_order_max_cart_items"] = int(state_config.get("submit_order_max_cart_items", 1))
        st.session_state["stress_quote_type"] = int(state_config.get("quote_type", 2))
        st.session_state["stress_logistics_config_id"] = int(state_config.get("logistics_config_id", 28))
        st.session_state.confirmed_stress_config = state_config
        st.session_state[hydrate_key] = state_run_id
if state:
    upsert_history(state)
history = refresh_history(read_history(), locust_processes)
running = state_running or bool(locust_processes)

status_col, action_col = st.columns([3, 1])
with status_col:
    if state:
        status = "运行中" if state_running else state.get("status", "unknown")
        st.info(
            f"当前任务：`{state.get('run_id')}`  |  状态：**{status}**  |  PID：`{state.get('pid')}`"
        )
        if locust_processes and not state_running:
            st.caption(f"系统另外检测到 {len(locust_processes)} 个 Locust 压测进程，请在下方进程监控查看。")
    else:
        if locust_processes:
            st.info(f"当前没有平台登记任务，但系统检测到 {len(locust_processes)} 个 Locust 压测进程。")
        else:
            st.info("当前没有由测试平台启动的压测任务。")

with action_col:
    if state_running and st.button("停止当前压测", type="primary", use_container_width=True):
        success, message = stop_run(state, locust_processes)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)
    if st.button("刷新进程", use_container_width=True):
        st.rerun()

st.markdown("---")

form_col, preview_col = st.columns([1, 1], gap="large")

with form_col:
    st.subheader("启动配置")
    init_stress_form_defaults()

    env_options = ["test", "main", "prod"]
    env_type = st.selectbox("压测环境", env_options, key="stress_env_type")

    script_type_options = list(SCRIPT_TYPE_OPTIONS.keys())
    script_type = st.selectbox(
        "压测类型",
        script_type_options,
        key="stress_script_type",
        help="接口压测：登录/浏览/加购/附加项 Step1·Step2/quote/create/downQuote 等 API；UI 压测：仅前台页面访问；全部：两者一起跑。",
    )
    st.caption(f"入口脚本：`{resolve_locustfile(script_type)}`")

    env_accounts = accounts_pool.get(env_type, {}).get("frontend", [])
    account_labels = [
        account.get("email") or account.get("mail") or f"account_{index + 1}"
        for index, account in enumerate(env_accounts)
    ]
    account_options = set(account_labels)
    mock_account_labels = [
        email for email in account_labels
        if str(email).startswith("performance_test_")
    ]
    accounts_key = f"stress_real_accounts_{env_type}"
    batch_count_key = f"stress_batch_mock_count_{env_type}"
    checkbox_prefix = f"{accounts_key}_checked_"
    active_selected_emails = []
    if active_state_config and active_state_config.get("env_type") == env_type:
        active_selected_emails = [
            email for email in active_state_config.get("selected_emails", [])
            if email in account_options
        ]
        st.session_state[accounts_key] = active_selected_emails
        st.session_state[f"stress_real_users_{env_type}"] = int(active_state_config.get("real_users", 0))

    def sync_account_checkboxes(next_selected):
        selected_set = set(next_selected)
        st.session_state[accounts_key] = [
            email for email in account_labels
            if email in selected_set
        ]
        for index, email in enumerate(account_labels):
            st.session_state[f"{checkbox_prefix}{index}"] = email in selected_set

    st.session_state[batch_count_key] = min(
        max(0, int(st.session_state.get(batch_count_key, min(50, len(mock_account_labels))))),
        len(mock_account_labels),
    )

    if accounts_key not in st.session_state:
        st.session_state[accounts_key] = account_labels[: min(5, len(account_labels))]
    else:
        st.session_state[accounts_key] = [
            email for email in st.session_state.get(accounts_key, [])
            if email in account_options
        ]

    selected_set = set(st.session_state.get(accounts_key, []))
    for index, email in enumerate(account_labels):
        checkbox_key = f"{checkbox_prefix}{index}"
        if active_state_config and active_state_config.get("env_type") == env_type:
            st.session_state[checkbox_key] = email in selected_set
        elif checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = email in selected_set

    st.caption(f"当前 `{env_type}` 环境账号池：{len(account_labels)} 个真实注册账号")
    st.markdown("**快捷选择账号**")
    st.caption("可一键选择全部账号、全部 mock，或输入数量后选择前 N 个 mock。")
    batch_cols = st.columns([1, 1, 1, 0.9, 1.1], gap="small")
    with batch_cols[0]:
        if st.button("全选全部", use_container_width=True, disabled=not account_labels):
            sync_account_checkboxes(account_labels)
            st.rerun()
    with batch_cols[1]:
        if st.button("全选 mock", use_container_width=True, disabled=not mock_account_labels):
            sync_account_checkboxes(mock_account_labels)
            st.rerun()
    with batch_cols[2]:
        if st.button("清空", use_container_width=True, disabled=not account_labels):
            sync_account_checkboxes([])
            st.rerun()
    with batch_cols[3]:
        batch_count = st.number_input(
            "前 N 个 mock",
            min_value=0,
            max_value=max(0, len(mock_account_labels)),
            step=1,
            key=batch_count_key,
            label_visibility="collapsed",
        )
    with batch_cols[4]:
        if st.button("选择前 N 个", use_container_width=True, disabled=not mock_account_labels):
            sync_account_checkboxes(mock_account_labels[: int(batch_count)])
            st.rerun()

    selected_emails = []
    with st.expander("账号明细（展开后可单独勾选/取消）", expanded=False):
        if account_labels:
            checkbox_cols = st.columns(3, gap="small")
            for index, email in enumerate(account_labels):
                checkbox_key = f"{checkbox_prefix}{index}"
                with checkbox_cols[index % 3]:
                    if st.checkbox(email, key=checkbox_key):
                        selected_emails.append(email)
        else:
            st.info("当前环境没有可选真实注册账号。")

    st.session_state[accounts_key] = selected_emails
    st.caption(
        f"已勾选 `{len(selected_emails)}` 个账号；"
        f"mock 可选 `{len(mock_account_labels)}` 个。"
    )

    with st.container(border=True):
        real_users_key = f"stress_real_users_{env_type}"
        if real_users_key not in st.session_state:
            default_real = min(5, len(selected_emails)) if selected_emails else 0
            st.session_state[real_users_key] = default_real
        real_users = st.number_input(
            "真实账号并发数",
            min_value=0,
            max_value=10000,
            step=1,
            key=real_users_key,
            help="允许大于账号数，脚本会按账号池轮询复用；建议优先补足账号池。",
        )
        if real_users > len(selected_emails) and selected_emails:
            st.warning(
                f"当前选择 {len(selected_emails)} 个真实账号，但真实账号并发数是 {int(real_users)}；"
                "压测时会轮询复用这些账号。"
            )
        if not account_labels:
            st.warning("当前环境没有配置真实注册账号，只能运行虚拟账号模型。")
        virtual_users = st.number_input(
            "虚拟账号数量",
            min_value=0,
            max_value=100000,
            step=1,
            key="stress_virtual_users",
        )

        rate_c1, rate_c2 = st.columns(2)
        with rate_c1:
            real_spawn_rate = st.number_input(
                "真实账号加载速率 / 秒",
                min_value=0.1,
                max_value=10000.0,
                step=0.5,
                key="stress_real_spawn_rate",
            )
        with rate_c2:
            virtual_spawn_rate = st.number_input(
                "虚拟账号加载速率 / 秒",
                min_value=0.1,
                max_value=10000.0,
                step=1.0,
                key="stress_virtual_spawn_rate",
            )

        duration = st.text_input(
            "压测时间",
            key="stress_duration",
            help="支持 30s、10m、1h 这类写法。",
        )

        st.markdown("**压测策略**")
        browse_steps = st.number_input(
            "每个真实链路浏览步数",
            min_value=1,
            max_value=20,
            step=1,
            key="stress_browse_steps",
        )
        enable_add_cart = st.checkbox("启用浏览 + 加购链路", key="stress_enable_add_cart")
        enable_taobao_keyword = st.checkbox(
            "启用淘宝关键词搜索",
            key="stress_enable_taobao_keyword",
            help="关闭后关键词浏览与动态加购前置搜索仅走 1688。",
        )
        enable_taobao_detail = st.checkbox(
            "启用淘宝详情页接口",
            key="stress_enable_taobao_detail",
            help="关闭后跳过 /api_tb/product/detail；动态加购也不会走淘宝链路。",
        )
        enable_taobao_add_cart = st.checkbox(
            "启用淘宝商品加购",
            key="stress_enable_taobao_add_cart",
            help="关闭后跳过 商品加购_taobao；动态加购需同时开启关键词与详情。",
        )
        enable_submit_order = st.checkbox(
            "启用浏览 + 加购 + 提交报价单链路",
            key="stress_enable_submit_order",
        )
        enable_full_quote_flow = st.checkbox(
            "启用完整报价链路（附加项 Step1/Step2 + quote/create）",
            disabled=not enable_submit_order,
            key="stress_enable_full_quote_flow",
            help="开启后依次调用 updateCheckFjx、getCheckFjxFeeTotal、cartQuoteStep1/Step2 cartDetailList 等接口；关闭则加购后直接 quote/create。",
        )
        enable_quote_download = st.checkbox(
            "启用报价单下载（提交成功后接力 downQuote）",
            disabled=not enable_submit_order,
            key="stress_enable_quote_download",
            help="开启后 quote/create 成功即下载当轮压测产生的报价单；关闭则只提交不下载。",
        )
        quote_download_language = st.text_input(
            "报价单下载 language 参数",
            disabled=not enable_submit_order or not enable_quote_download,
            key="stress_quote_download_language",
            help="downQuote 接口 language 参数，main 环境浏览器默认 english。",
        )
        quote_flow_cols = st.columns(2)
        with quote_flow_cols[0]:
            quote_type = st.number_input(
                "quote_type",
                min_value=1,
                max_value=99,
                step=1,
                disabled=not enable_submit_order or not enable_full_quote_flow,
                key="stress_quote_type",
                help="完整链路 quote/create 的 quote_type，main 环境浏览器默认 2。",
            )
        with quote_flow_cols[1]:
            logistics_config_id = st.number_input(
                "logistics_config_id",
                min_value=1,
                max_value=9999,
                step=1,
                disabled=not enable_submit_order or not enable_full_quote_flow,
                key="stress_logistics_config_id",
                help="完整链路 quote/create 的物流配置 ID，main 环境浏览器默认 28。",
            )
        submit_order_max_cart_items = st.number_input(
            "每次提交报价单最多购物车明细数",
            min_value=1,
            max_value=20,
            step=1,
            disabled=not enable_submit_order,
            key="stress_submit_order_max_cart_items",
        )

        prod_confirm = True
        submit_confirm = True
        if env_type == "prod":
            prod_confirm = st.checkbox("我确认在 prod 环境发起压测", value=False, key="stress_prod_confirm")
        if enable_submit_order:
            submit_confirm = st.checkbox(
                "我确认允许执行提交报价单链路",
                value=False,
                key="stress_submit_confirm",
            )

        config_confirmed = st.button(
            "确认配置",
            type="primary",
            use_container_width=True,
            key="stress_config_confirm_button",
        )

        duration_seconds = parse_duration_seconds(duration)
        total_users = int(real_users) + int(virtual_users)
        draft_config = {
            "env_type": env_type,
            "script_type": script_type,
            "selected_emails": selected_emails,
            "real_users": int(real_users),
            "virtual_users": int(virtual_users),
            "real_spawn_rate": float(real_spawn_rate),
            "virtual_spawn_rate": float(virtual_spawn_rate),
            "duration": duration,
            "duration_seconds": duration_seconds,
            "browse_steps": int(browse_steps),
            "enable_add_cart": bool(enable_add_cart),
            "enable_taobao_keyword": bool(enable_taobao_keyword),
            "enable_taobao_detail": bool(enable_taobao_detail),
            "enable_taobao_add_cart": bool(enable_taobao_add_cart),
            "enable_submit_order": bool(enable_submit_order),
            "enable_full_quote_flow": bool(enable_full_quote_flow) if enable_submit_order else False,
            "enable_quote_download": bool(enable_quote_download) if enable_submit_order else False,
            "quote_download_language": (quote_download_language or "english").strip() or "english",
            "quote_type": int(quote_type),
            "logistics_config_id": int(logistics_config_id),
            "submit_order_max_cart_items": int(submit_order_max_cart_items),
        }

        confirmed_before = st.session_state.get("confirmed_stress_config")
        errors = []
        if duration_seconds is None:
            errors.append("压测时间格式不正确，请使用 30s、10m、1h 这类写法。")
        if total_users <= 0:
            errors.append("真实账号并发数 + 虚拟账号数量必须大于 0。")
        if int(real_users) > 0 and not selected_emails:
            errors.append("真实账号并发数大于 0 时，请至少选择一个真实注册账号。")
        if env_type == "prod" and not prod_confirm:
            errors.append("prod 环境压测需要勾选确认。")
        if enable_submit_order and not submit_confirm:
            errors.append("提交报价单链路需要单独勾选确认。")

        if errors:
            if config_confirmed:
                for error in errors:
                    st.error(error)
        elif active_state_config:
            st.session_state.confirmed_stress_config = active_state_config
        elif config_confirmed or draft_config != confirmed_before:
            st.session_state.confirmed_stress_config = draft_config
            if config_confirmed:
                st.success("配置已确认，执行预览已更新。")

with preview_col:
    st.subheader("执行预览")
    confirmed_config = active_state_config or st.session_state.get("confirmed_stress_config")

    if not confirmed_config:
        st.info("请先在左侧完成配置并点击「确认配置」，这里会展示即将执行的压测参数。")
        with st.container(border=True):
            st.markdown("**预览会包含**")
            st.markdown("1. 本次用户规模、加载速率和时长。")
            st.markdown("2. 真实账号链路会执行哪些动作。")
            st.markdown("3. 虚拟账号链路会执行哪些动作。")
            st.markdown("4. 平台注入 Locust 的核心环境变量和启动命令。")
    else:
        confirmed_total = confirmed_config["real_users"] + confirmed_config["virtual_users"]
        st.markdown("**本次参数**")
        metric_cols = st.columns(4)
        metric_cols[0].metric("真实账号", confirmed_config["real_users"])
        metric_cols[1].metric("虚拟账号", confirmed_config["virtual_users"])
        metric_cols[2].metric("总用户", confirmed_total)
        metric_cols[3].metric("时长", f"{confirmed_config.get('duration_seconds') or '-'}s")

        summary_cols = st.columns(2)
        with summary_cols[0]:
            st.caption(f"环境：`{confirmed_config['env_type']}`")
            _stype = confirmed_config.get("script_type", DEFAULT_SCRIPT_TYPE)
            st.caption(f"压测类型：`{_stype}` → `{resolve_locustfile(_stype)}`")
            st.caption(f"真实账号加载：`{confirmed_config['real_spawn_rate']}/s`")
            st.caption(f"虚拟账号加载：`{confirmed_config['virtual_spawn_rate']}/s`")
        with summary_cols[1]:
            st.caption(f"加购链路：{'启用' if confirmed_config['enable_add_cart'] else '关闭'}")
            st.caption(f"淘宝关键词搜索：{'启用' if confirmed_config.get('enable_taobao_keyword') else '关闭'}")
            st.caption(f"淘宝详情页接口：{'启用' if confirmed_config.get('enable_taobao_detail') else '关闭'}")
            st.caption(f"淘宝商品加购：{'启用' if confirmed_config.get('enable_taobao_add_cart') else '关闭'}")
            st.caption(f"提交报价单链路：{'启用' if confirmed_config['enable_submit_order'] else '关闭'}")
            if confirmed_config["enable_submit_order"]:
                full_quote = _resolve_full_quote_flow(confirmed_config)
                st.caption(f"完整报价链路：{'启用' if full_quote else '关闭（简化 quote/create）'}")
                if full_quote:
                    st.caption(
                        f"quote/create：quote_type={confirmed_config.get('quote_type', 2)}，"
                        f"logistics_config_id={confirmed_config.get('logistics_config_id', 28)}"
                    )
                quote_dl = _resolve_quote_download(confirmed_config)
                st.caption(
                    f"报价单下载：{'启用（下单后接力 downQuote）' if quote_dl else '关闭'}"
                )
                if quote_dl:
                    st.caption(
                        f"downQuote language：`{confirmed_config.get('quote_download_language', 'english')}`"
                    )
            st.caption(f"报价单明细上限：`{confirmed_config['submit_order_max_cart_items']}`")

        st.markdown("**执行内容**")
        real_flow_col, virtual_flow_col = st.columns(2)
        with real_flow_col:
            render_step_list(
                "真实账号链路",
                f"{confirmed_config['real_users']} 个用户，账号池 {len(confirmed_config['selected_emails'])} 个账号",
                build_real_user_steps(confirmed_config),
            )
        with virtual_flow_col:
            render_step_list(
                "虚拟账号链路",
                f"{confirmed_config['virtual_users']} 个用户，不使用真实账号",
                build_virtual_user_steps(confirmed_config),
            )

        if confirmed_config["selected_emails"]:
            with st.expander("查看本次真实账号", expanded=False):
                for email in confirmed_config["selected_emails"]:
                    st.code(email, language="text")

        with st.expander("查看平台注入参数和启动命令", expanded=True):
            st.code(build_preview_command(confirmed_config), language="powershell")

        if running:
            st.caption("检测到已有 Locust 压测进程，结束后才能启动新的平台压测任务。")

        if st.button("确认执行", type="primary", disabled=running, use_container_width=True):
            try:
                state = start_locust_run(confirmed_config)
                st.success(f"已启动压测任务：{state['run_id']}，PID：{state['pid']}")
                st.rerun()
            except Exception as exc:
                st.error(f"启动失败：{exc}")

    if state:
        with st.expander("最近一次启动命令", expanded=False):
            st.code(state.get("command", ""), language="powershell")

st.markdown("---")
st.subheader("压测进程监控")

monitor_cols = st.columns(3)
monitor_cols[0].metric("系统 Locust 进程", len(locust_processes))
monitor_cols[1].metric("平台历史任务", len(history))
monitor_cols[2].metric("运行状态", "运行中" if locust_processes else "空闲")

known_tasks = [state] + history
if locust_processes:
    process_rows = []
    for process in locust_processes:
        related_task = find_related_task(process, known_tasks)
        process_rows.append(
            {
                "PID": process.get("pid"),
                "任务": related_task.get("run_id") if related_task else "系统扫描发现",
                "进程名": process.get("name") or "-",
                "启动时间": process.get("created_at") or "-",
                "运行时长": process.get("elapsed") or "-",
                "可停止": "是" if related_task or process.get("safe_to_stop") else "否",
            }
        )
    st.dataframe(process_rows, use_container_width=True)

    for process in locust_processes:
        related_task = find_related_task(process, known_tasks)
        title = f"PID {process.get('pid')} · {related_task.get('run_id') if related_task else '系统扫描发现'}"
        with st.expander(title, expanded=False):
            detail_cols = st.columns(4)
            detail_cols[0].metric("PID", process.get("pid"))
            detail_cols[1].metric("父 PID", process.get("parent_pid") or "-")
            detail_cols[2].metric("运行时长", process.get("elapsed") or "-")
            detail_cols[3].metric("来源", "平台任务" if related_task else "系统扫描")

            st.caption("进程命令行")
            st.code(process.get("command_line", ""), language="powershell")

            if related_task:
                report_path = Path(related_task.get("html_report", ""))
                stderr_path = related_task.get("stderr_log", "")
                stdout_path = related_task.get("stdout_log", "")
                task_cols = st.columns(3)
                task_cols[0].caption(f"状态：{related_task.get('status', '-')}")
                task_cols[1].caption(f"开始：{related_task.get('started_at', '-')}")
                task_cols[2].caption(f"报告：{'已生成' if report_path.is_file() else '未生成'}")
                st.caption("该任务日志")
                task_log_tabs = st.tabs(["stderr", "stdout"])
                with task_log_tabs[0]:
                    st.code(read_tail(stderr_path, lines=80) or "暂无 stderr 日志", language="text")
                with task_log_tabs[1]:
                    st.code(read_tail(stdout_path, lines=80) or "暂无 stdout 日志", language="text")

            can_stop = bool(related_task or process.get("safe_to_stop"))
            if can_stop:
                if st.button("停止此进程", key=f"stop_process_{process.get('pid')}", type="primary"):
                    success, message = stop_process(
                        process.get("pid"),
                        process=process,
                        known_task=related_task,
                    )
                    if success:
                        if related_task:
                            stopped_task = dict(related_task)
                            stopped_task["status"] = "stopped"
                            stopped_task["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            if state and stopped_task.get("run_id") == state.get("run_id"):
                                write_state(stopped_task)
                            upsert_history(stopped_task)
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.warning("该进程没有匹配到平台任务，也无法确认属于当前 Performance 目录，暂不提供停止操作。")
else:
    st.success("当前未检测到 Locust 压测进程。")

with st.expander("平台压测任务历史", expanded=True):
    if history:
        history_rows = []
        for item in history[:20]:
            config = item.get("config", {}) or {}
            report_path = Path(item.get("html_report", ""))
            history_rows.append(
                {
                    "任务": item.get("run_id", "-"),
                    "状态": item.get("status", "-"),
                    "PID": item.get("pid", "-"),
                    "环境": config.get("env_type", "-"),
                    "类型": config.get("script_type", "-"),
                    "用户": f"{config.get('real_users', 0)} + {config.get('virtual_users', 0)}",
                    "启动时间": item.get("started_at", "-"),
                    "运行时长": format_elapsed(item.get("started_at"), item.get("finished_at")),
                    "报告": "已生成" if report_path.is_file() else "未生成",
                }
            )
        st.dataframe(history_rows, use_container_width=True)
    else:
        st.caption("暂无平台启动的压测任务历史。")

st.markdown("---")
report_title_col, report_refresh_col = st.columns([5, 1])
with report_title_col:
    st.subheader("日志与报告")
with report_refresh_col:
    st.write("")
    if st.button("刷新", key="refresh_report_section", use_container_width=True):
        st.rerun()

if state:
    report_path = Path(state.get("html_report", ""))
    artifact_paths = get_artifact_paths(state)
    stats_rows = read_csv_rows(artifact_paths["stats"])
    failure_rows = build_failure_rows(read_csv_rows(artifact_paths["failures"]))
    failure_detail_rows = read_failure_detail_rows(artifact_paths["failure_details"])
    aggregate = find_aggregate_row(stats_rows)
    request_rows = build_request_rows(stats_rows)
    failed_request_rows = build_request_rows(
        sorted(
            [row for row in stats_rows if row.get("Name") != "Aggregated" and to_int(row.get("Failure Count")) > 0],
            key=lambda item: to_int(item.get("Failure Count")),
            reverse=True,
        )
    )
    slow_request_rows = build_request_rows(
        sorted(
            [row for row in stats_rows if row.get("Name") and row.get("Name") != "Aggregated"],
            key=lambda item: (to_float(item.get("95%")), to_float(item.get("Max Response Time"))),
            reverse=True,
        )[:10]
    )

    result_tabs = st.tabs(["总览", "失败", "慢接口", "请求明细", "日志", "报告"])

    with result_tabs[0]:
        if stats_rows:
            total_requests = to_int(aggregate.get("Request Count"))
            total_failures = to_int(aggregate.get("Failure Count"))
            total_failure_rate = failure_rate(aggregate)

            summary_cols = st.columns(5)
            summary_cols[0].metric("总请求", format_number(total_requests))
            summary_cols[1].metric("失败", format_number(total_failures), format_percent(total_failure_rate))
            summary_cols[2].metric("平均响应", format_ms(aggregate.get("Average Response Time")))
            summary_cols[3].metric("P95", format_ms(aggregate.get("95%")))
            summary_cols[4].metric("RPS", round(to_float(aggregate.get("Requests/s")), 2))

            if total_failures:
                st.warning(f"本次压测存在 {total_failures} 次失败，优先查看「失败」页签。")
            else:
                st.success("本次统计未发现失败请求。")

            if to_float(aggregate.get("95%")) >= 3000:
                st.warning(f"整体 P95 为 {format_ms(aggregate.get('95%'))}，建议查看「慢接口」页签定位高延迟接口。")

            overview_cols = st.columns(2)
            with overview_cols[0]:
                st.markdown("**失败接口 Top**")
                if failed_request_rows:
                    st.dataframe(failed_request_rows[:6], use_container_width=True, hide_index=True)
                else:
                    st.caption("暂无失败接口。")
            with overview_cols[1]:
                st.markdown("**慢接口 Top**")
                if slow_request_rows:
                    st.dataframe(slow_request_rows[:6], use_container_width=True, hide_index=True)
                else:
                    st.caption("暂无慢接口数据。")
        else:
            st.info("暂未读取到 Locust stats CSV，任务运行中时可先查看「日志」。")

    with result_tabs[1]:
        if failure_rows:
            st.warning(f"失败类型 {len(failure_rows)} 类，按出现次数降序展示（含账号与响应详情）。")
            st.dataframe(failure_rows, use_container_width=True, hide_index=True)
        elif failed_request_rows:
            st.warning("失败明细 CSV 暂不可用，先展示 stats 中的失败接口。")
            st.dataframe(failed_request_rows, use_container_width=True, hide_index=True)
        else:
            st.success("暂无失败记录。")

        if failure_detail_rows:
            st.markdown("**失败样本明细（最近记录，含完整响应摘要）**")
            detail_limit = st.selectbox("样本条数", [20, 50, 100], index=0, key="stress_failure_detail_limit")
            st.dataframe(failure_detail_rows[:detail_limit], use_container_width=True, hide_index=True)
        elif failure_rows:
            st.caption("本次运行的逐条失败明细尚未生成（需使用更新后的压测脚本重新执行）。")

    with result_tabs[2]:
        if slow_request_rows:
            slow_threshold = st.slider("仅显示 P95 大于等于", min_value=0, max_value=20000, value=0, step=500, format="%d ms")
            filtered_slow_rows = []
            for row in stats_rows:
                if row.get("Name") == "Aggregated":
                    continue
                if to_float(row.get("95%")) >= slow_threshold:
                    filtered_slow_rows.append(row)
            filtered_slow_rows = sorted(
                filtered_slow_rows,
                key=lambda item: (to_float(item.get("95%")), to_float(item.get("Max Response Time"))),
                reverse=True,
            )
            st.dataframe(build_request_rows(filtered_slow_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("暂无慢接口数据。")

    with result_tabs[3]:
        if request_rows:
            detail_cols = st.columns([1, 1, 1])
            with detail_cols[0]:
                only_failed = st.checkbox("只看失败接口", value=False)
            with detail_cols[1]:
                min_requests = st.number_input("最小请求数", min_value=0, value=0, step=10)
            with detail_cols[2]:
                name_keyword = st.text_input("接口名称筛选", placeholder="例如 taobao / 购物车")

            filtered_stats = []
            keyword = name_keyword.strip().lower()
            for row in stats_rows:
                if row.get("Name") == "Aggregated":
                    continue
                if only_failed and to_int(row.get("Failure Count")) <= 0:
                    continue
                if to_int(row.get("Request Count")) < int(min_requests):
                    continue
                if keyword and keyword not in row.get("Name", "").lower():
                    continue
                filtered_stats.append(row)
            st.dataframe(build_request_rows(filtered_stats), use_container_width=True, hide_index=True)
        else:
            st.info("暂无请求明细 CSV。")

    with result_tabs[4]:
        log_cols = st.columns([1, 1, 2])
        with log_cols[0]:
            log_source = st.radio("日志来源", ["stderr", "stdout"], horizontal=True)
        with log_cols[1]:
            log_lines = st.selectbox("显示尾部行数", [80, 160, 300, 600], index=1)
        with log_cols[2]:
            log_keyword = st.text_input("日志关键字过滤", placeholder="例如 Error / taobao / EOF")

        log_path = state.get("stderr_log", "") if log_source == "stderr" else state.get("stdout_log", "")
        log_text = filter_log_text(log_path, lines=int(log_lines), keyword=log_keyword.strip())
        if log_text:
            st.code(log_text, language="text")
        else:
            st.info("当前筛选条件下没有日志内容。")

    with result_tabs[5]:
        if report_path.is_file():
            st.success(f"HTML 报告已生成：{report_path}")
            st.download_button(
                "下载 HTML 报告",
                data=report_path.read_bytes(),
                file_name=report_path.name,
                mime="text/html",
                use_container_width=True,
            )
        else:
            st.info("报告将在任务完成或 Locust flush 后生成。")
else:
    st.caption("启动一次压测后，这里会显示日志和报告下载入口。")

with st.expander("历史 HTML 报告", expanded=False):
    reports = sorted(REPORT_DIR.glob("*.html"), key=lambda item: item.stat().st_mtime, reverse=True)[:12]
    if not reports:
        st.caption("暂无历史报告。")
    for report in reports:
        cols = st.columns([2, 1, 1])
        cols[0].caption(report.name)
        cols[1].caption(datetime.fromtimestamp(report.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
        cols[2].download_button(
            "下载",
            data=report.read_bytes(),
            file_name=report.name,
            mime="text/html",
            key=f"download_{report.name}",
            use_container_width=True,
        )
