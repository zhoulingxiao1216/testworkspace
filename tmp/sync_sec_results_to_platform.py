#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 Agent2 安全优化执行结果同步到测试平台 test_mission.db"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(ROOT, "测试平台自建")
sys.path.insert(0, PLATFORM)

from db_manager import get_connection, update_case_status  # noqa: E402

# 平台仅支持 Untested / Pass / Fail / Blocked
# Conditional 映射为 Blocked，并在 actual_result 说明原因
RESULTS = {
    "TC-SEC-SECRET-001": (
        "Pass",
        "main 环境 GET .pem/.env/.key 均为 404 JSON，无私钥泄露。Agent2 2026-06-16",
    ),
    "TC-SEC-SECRET-003": (
        "Pass",
        "错误密码登录响应无 token/secret 明文泄漏。Agent2 2026-06-16",
    ),
    "TC-SEC-AUTH-001": (
        "Pass",
        "匿名与伪造 admin token 写 admin_index 均被拒绝（请先登录/令牌解析失败）。Agent2 2026-06-16",
    ),
    "TC-SEC-AUTH-002": (
        "Pass",
        "admin 账号合法访问 admin_index/deeplConfig 返回 200。Agent2 2026-06-16",
    ),
    "TC-SEC-AUTH-003": (
        "Pass",
        "匿名 refreshToken 返回请先登录/site_empty，未无鉴权刷新成功。Agent2 2026-06-16",
    ),
    "TC-SEC-AUTH-004": (
        "Pass",
        "refreshToken 响应未返回 token/secret 长明文。Agent2 2026-06-16",
    ),
    "TC-SEC-AUTH-008": (
        "Pass",
        "抽样注册/发码接口未发现明显邮箱枚举差异（部分路由404）。Agent2 2026-06-16",
    ),
    "TC-SEC-IDOR-004": (
        "Pass",
        "用户A查用户B quote_no B2B-BJ-JPN49-260616-105 返回无权限，data 为空。Agent2 2026-06-16",
    ),
    "TC-SEC-FIN-008": (
        "Pass",
        "amount=0/-1 提现返回 amount_invalid，未成功入账。Agent2 2026-06-16",
    ),
    "TC-SEC-FIN-001": (
        "Blocked",
        "user_b 无可退 payment_intent/order 样本，未能完成越权退款探测。Agent2 2026-06-16",
    ),
    "TC-SEC-FIN-007": (
        "Blocked",
        "已探测 withdrawalFunds；需未设/已设支付密码专项账号才能闭合 P0-4。Agent2 2026-06-16",
    ),
    "TC-SEC-IDOR-001": (
        "Blocked",
        "跨用户 update 无副作用，但未返回明确403，待开发确认归属拦截。Agent2 2026-06-16",
    ),
    "TC-SEC-IDOR-002": (
        "Blocked",
        "跨用户 del/default 未改 B 地址；/del 返回操作失败，无标准403。Agent2 2026-06-16",
    ),
    "TC-SEC-IDOR-003": (
        "Blocked",
        "user_b 无进口商地址或 list 接口无数据。Agent2 2026-06-16",
    ),
    "TC-SEC-AUTH-007": (
        "Blocked",
        "缺有效 client_key，无法验证失败频控阈值。Agent2 2026-06-16",
    ),
    "TC-SEC-AUD-004": (
        "Blocked",
        "P0 Smoke 未全量执行，暂不满足上线门禁。Agent2 2026-06-16",
    ),
}


def main():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, tc_id, status FROM test_cases WHERE tc_id LIKE 'TC-SEC-%'"
    ).fetchall()
    updated = 0
    for row in rows:
        tc_id = row["tc_id"]
        if tc_id not in RESULTS:
            continue
        status, actual = RESULTS[tc_id]
        update_case_status(row["id"], status, actual_result=actual)
        updated += 1
    print(f"synced {updated} cases")
    # verify 1384
    r = conn.execute(
        "SELECT id, tc_id, status, actual_result FROM test_cases WHERE id=1384"
    ).fetchone()
    print(dict(r))


if __name__ == "__main__":
    main()
