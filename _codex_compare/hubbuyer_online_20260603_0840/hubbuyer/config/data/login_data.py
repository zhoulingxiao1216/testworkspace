# config/data/login_data.py
# 登录测试数据（前台 + 后台统一管理）

# 所有的账号池
# 结构：{ 环境: { "frontend": [...], "admin": {...} } }
ACCOUNTS_POOL = {
    "prod": {
        # 前台巡检账号列表（支持多账号轮询）
        "frontend": [
            {
                "email": "mxnrq@airsworld.net",
                "password": "123456",
                "code": "",
                "type": "password",
                "jump_url": "https://b2b.hubbuyer.com/jump_common",
                "jump_site": "B2B"
            }
        ],
        # 后台管理员账号（用于后台接口巡检，如汇率检测）
        "admin": {
            "account": "test-zhou",
            "password": "123456qwe"
        }
    },
    "test": {
        "frontend": [
            {"email": "", "password": ""}
        ],
        "admin": {
            "account": "",
            "password": ""
        }
    }
}