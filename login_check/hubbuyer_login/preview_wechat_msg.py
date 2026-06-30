# -*- coding: utf-8 -*-
"""Preview the WeCom login notification without sending it."""

import argparse
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.notifier import Notifier


def parse_args():
    parser = argparse.ArgumentParser(description="Preview the login check WeCom message.")
    parser.add_argument("--fail", action="store_true", help="Preview the alarm template.")
    parser.add_argument("--report-path", default="reports/登录检查报告_示例.md")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.fail:
        result = {
            "success": False,
            "message": "【prod】mxnrq@airsworld.net:ERR(接口返回code非200)",
            "status_code": 200,
        }
    else:
        result = {
            "success": True,
            "message": "【prod】mxnrq@airsworld.net:OK",
            "status_code": 200,
        }

    print(Notifier.build_login_template(result, report_path=args.report_path))


if __name__ == "__main__":
    main()
