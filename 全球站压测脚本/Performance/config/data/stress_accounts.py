# -*- coding: utf-8 -*-
"""
压测专用账号池
独立于巡检系统账号，可配置不同环境的压测账号
格式参照巡检系统 hubbuyer/config/data/login_data.py
"""

# ==========================================
# 压测账号池
# 结构：{ 环境: { "frontend": [...] } }
# ==========================================

TEST_B2B_JUMP_URL = "https://test-b2b.hubbuyer.com/jump_common"
MAIN_B2B_JUMP_URL = "https://main-b2b.hubbuyer.com/jump_common"


def _frontend_account(email, jump_url):
    return {
        "email": email,
        "password": "123456",
        "code": "",
        "type": "password",
        "jump_url": jump_url,
        "jump_site": "B2B",
    }


# mock 账号编号范围（test 与 main 共用同一批 performance_test_*** 账号）
MOCK_ACCOUNT_RANGE = range(3, 51)

TEST_MOCK_ACCOUNTS = [
    _frontend_account(f"performance_test_{index:03d}@126.com", TEST_B2B_JUMP_URL)
    for index in MOCK_ACCOUNT_RANGE
]

# main 环境登录异常账号：后端 LoginController 对其执行 strtotime(null) 稳定返回 HTTP 500，
# 属后端脏数据/代码问题（待后端修复），暂从 main 压测池剔除，避免预热登录每轮固定 1 个失败。
MAIN_MOCK_EXCLUDE = {3}  # performance_test_003@126.com 在 main 登录 500

# 由 test 环境同步而来的 mock 账号，仅 jump_url 切换为 main 站点
MAIN_MOCK_ACCOUNTS = [
    _frontend_account(f"performance_test_{index:03d}@126.com", MAIN_B2B_JUMP_URL)
    for index in MOCK_ACCOUNT_RANGE
    if index not in MAIN_MOCK_EXCLUDE
]

STRESS_ACCOUNTS_POOL = {
    "prod": {
        # 前台压测账号列表（可配置多账号轮询分担压力）
        "frontend": [
            {
                "email": "mxnrq@airsworld.net",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            },
            {
                "email": "zhoulingxiao1216@proton.me",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            },
            {
                "email": "a18767980276@126.com",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            },
            {
                "email": "zhoulingxiao@126.com",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            },
            {
                "email": "zhoulingxiao@qq.com",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            }
            # 如需多账号分担压力，在此添加更多账号：
            # {
            #     "email": "stress_test_02@xxx.com",
            #     "password": "xxx",
            #     "code": "",
            #     "type": "password",
            #     "jump_url": "https://b2b.hubbuyer.com/jump_common",
            #     "jump_site": "B2B"
            # }
        ]
    },
    "main": {
        # main 预发布环境前台压测账号列表（可配置多账号轮询分担压力）
        "frontend": [
            {
                "email": "mxnrq@airsworld.net",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://main-b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            }
            # 如需多账号分担压力，在此添加更多 main 环境账号：
            # {
            #     "email": "stress_main_02@xxx.com",
            #     "password": "xxx",
            #     "code": "",
            #     "type": "password",
            #     "jump_url": "https://main-b2b.hubbuyer.com/jump_common",
            #     "jump_site": "B2B"
            # }
        ] + MAIN_MOCK_ACCOUNTS
    },
    "test": {
        "frontend": [
            {
                "email": "369901314@qq.com",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://test-b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            }
        ] + TEST_MOCK_ACCOUNTS
    }
}
