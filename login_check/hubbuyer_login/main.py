# -*- coding: utf-8 -*-
"""Entry point for the prod-only login check."""

import argparse
import json
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from checker.api.login import run_login_check
from config.settings import ENV_TYPE
from core.notifier import Notifier
from core.report_generator import LoginReportGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Run the prod login check.")
    parser.add_argument("task_config", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--email", type=str, help="Login email. Same as --mail.")
    parser.add_argument("--mail", type=str, help="Login email. Same as --email.")
    parser.add_argument("--password", type=str, help="Login password.")
    parser.add_argument(
        "--account-json",
        type=str,
        help='Account JSON, for example: {"email":"test@example.com","password":"123456"}',
    )
    parser.add_argument(
        "--account-file",
        type=str,
        help="JSON file path. The file can contain one account object or an account list.",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Force WeCom notification even if the notifier switch is off.",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Skip WeCom notification.",
    )
    return parser.parse_args()


def load_json_file(file_path):
    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"Account file not found: {path}")

    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def normalize_accounts(data):
    if data is None:
        return None
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("Account data must be a JSON object or list.")


def load_custom_accounts(args):
    if args.account_file:
        return normalize_accounts(load_json_file(args.account_file))

    if args.account_json:
        return normalize_accounts(json.loads(args.account_json))

    if args.email or args.mail or args.password:
        email = args.email or args.mail
        if not email or not args.password:
            raise ValueError("Please provide both --email/--mail and --password.")
        return [{"email": email, "password": args.password}]

    return None


def load_task_config(raw_value):
    if not raw_value:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return None


def save_reports(result, accounts):
    generator = LoginReportGenerator(result, accounts=accounts)
    return generator.save_reports()


def send_notification(result, report_path, args):
    try:
        return Notifier.send_login_report(
            result,
            report_path=report_path,
            force=args.notify,
            skip=args.no_notify,
        )
    except Exception as exc:
        return f"failed: {type(exc).__name__}: {exc}"


def main():
    args = parse_args()

    try:
        custom_accounts = load_custom_accounts(args)
        task_config = load_task_config(args.task_config)
        result = run_login_check(task_config=task_config, custom_accounts=custom_accounts)
        success = bool(result.get("success"))
        report_paths = save_reports(result, custom_accounts)
        report_path = report_paths["md"]
        json_report_path = report_paths["json"]
        notify_status = send_notification(result, report_path, args)

        print(
            json.dumps(
                {
                    "success": success,
                    "env": ENV_TYPE,
                    "message": result.get("message", ""),
                    "status_code": result.get("status_code"),
                    "report": report_path,
                    "json_report": json_report_path,
                    "notify": notify_status,
                },
                ensure_ascii=False,
            )
        )
        return 0 if success else 1
    except Exception as exc:
        result = {
            "success": False,
            "message": f"{type(exc).__name__}: {exc}",
            "status_code": None,
        }
        try:
            report_paths = save_reports(result, None)
            report_path = report_paths["md"]
            json_report_path = report_paths["json"]
        except Exception:
            report_path = None
            json_report_path = None

        notify_status = send_notification(result, report_path, args)

        print(
            json.dumps(
                {
                    "success": False,
                    "env": ENV_TYPE,
                    "message": result["message"],
                    "report": report_path,
                    "json_report": json_report_path,
                    "notify": notify_status,
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
