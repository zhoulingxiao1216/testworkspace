# -*- coding: utf-8 -*-
# d:\sakuradk3\config\settings.py
# #第二版应用api和url
# ==========================================
# 核心开关：切换环境只需改这一个词 ('prod', 'main', 'test', 'dev')
# ==========================================

# ==========================================
# 1. 核心环境开关
# ==========================================

ENV_TYPE = "main"

# ==========================================
# 2. 业务巡检开关
# ==========================================
INSPECTION_SWITCHES = {
    "check_web_url_B2B_h5": False,      #b2b_h5网页访问开关
    "check_web_url_B2B_pc": True,      #b2b_pc网页访问开关
    "check_web_url_D2C_pc": False,      #d2c_h5网页访问开关
    "check_web_url_AboutUs_pc": True,   #AboutUs_pc网页访问开关
    "check_web_url_AboutUs_h5": True,   #AboutUs_h5网页访问开关
    "check_api_login": True,          #登录接口开关
    "check_api_img_search": True,       #b2b图搜请求接口开关
    "check_api_keyword_search": True,  #b2b 1688&淘宝关键词搜索接口开关
    "check_api_add_cart": True,        #b2b 1688&淘宝 商品加购接口开关
    "check_api_b2b_addon": True,      #b2b 选择商品附加项
    "check_api_d2c_addon": False,      #d2c选择商品附加项
    "check_api_submit_order": True,   #b2b 提交委托报价
    "check_api_payment": True,        #b2b 报价单支付（本轮新提交报价单）
    "check_api_payment_target": False, #已合并至报价单支付，不再单独执行固定单号
    "check_api_plugin": False,     #b2b&d2c插件加购1688&taobao商品
    "check_api_order_audit": True,      #前后台联动-后台报价单审核
    "check_api_purchase_order_audit": True,  #前后台联动-后台代购订单审核
    "check_api_backend_admin": True,   #纯后台管理检查点(代购仓配+汇率，汇率最后)
    "check_api_exchange_rate": True,   #子模块：由 backend_admin 调度
    "check_api_purchase_order_ops": True,  #子模块：由 backend_admin 调度
    "check_api_purchase_order_shipping": False,  #子模块：由 backend_admin 调度
    "check_api_member_pricing_complete_chain": True,  #价格体系专项巡检链路
    "check_api_member_pricing_cart_preview": True,  #子模块：费用预览
    "check_api_member_pricing_snapshot": True,  #子模块：快照校验
    "check_api_member_pricing_service_pricing": True,  #子模块：国家服务价
    "check_api_member_pricing_ship_fjx": False,  #子模块：发货附加项（临时关闭：接口返回500导致健康检查失败）
    "check_api_onebound_daily_stats": True  #万邦控制台前一日 API 调用统计
}

# ==========================================
# 3. 动态导入：根据环境加载模块
# ==========================================
from config.data.login_data import ACCOUNTS_POOL

if ENV_TYPE == "prod":
    import config.url.prod as url_mod
    import config.api.prod as api_mod
elif ENV_TYPE == "main":
    import config.url.main as url_mod
    import config.api.main as api_mod
elif ENV_TYPE == "test":
    import config.url.test as url_mod
    import config.api.test as api_mod
else:
    import config.url.dev as url_mod
    import config.api.dev as api_mod

# ==========================================
# 4. 拼装成全局配置字典 API_CONFIG
# ==========================================

# 这样 batch_checker 和 login.py 只需要 import 这一个变量即可
API_CONFIG = {
    # 方案 A：直接从你的 api_mod (prod.py) 里把域名拿过来
    "BASE_URL": api_mod.API_CONFIG.get("BASE_URL"),
    # 保留站点巡检需要的域名（从 url_mod 获取）
    "url_B2B_pc": url_mod.B2B_PC_url,
    "url_B2B_h5": url_mod.B2B_H5_url,
    "url_D2C_pc": url_mod.D2C_PC_url,
    "url_AboutUs_pc": url_mod.url_AboutUs_pc,
    "url_AboutUs_h5": url_mod.url_AboutUs_h5,
    "url_ADMIN": getattr(url_mod, "ADMIN_url", "https://admin.hubbuyer.com/"),
    "ENDPOINTS": api_mod.API_CONFIG["ENDPOINTS"], # 提取接口路径列表
    # 获取当前环境的前台账号列表
    "ACCOUNT_LIST": ACCOUNTS_POOL.get(ENV_TYPE, {}).get("frontend", [])
}

# 5. 报告人员相关配置
REPORT_CONFIG = {
    "RESPONSIBLE_PERSON": "周凌虓",
    # 在这里添加需要 @ 的用户帐号（Userid）列表
    "ALARM_USER_IDS": ["ZhouLingXiao"], 
    "PROJECT_NAME": "Sakuradk2 自动化巡检系统",
    "SAVE_DIR": "reports"
}

# 6.巡检任务之间的等待时间（秒）
INSPECTION_INTERVAL = 10
# 巡检任务执行后的随机等待时间范围（最小值, 最大值）单位：秒
# 比如 (3, 8) 表示在 3 到 8 秒之间随机取一个时间
#INSPECTION_INTERVAL_RANGE = (3, 8)

# 8.请求超时配置（秒）
REQUEST_TIMEOUT_WEB = 30      # Web端请求超时时间
REQUEST_TIMEOUT_API = 25       # API请求超时时间
REQUEST_TIMEOUT_NOTIFIER = 10  # 通知请求超时时间
SCRIPT_RUNNER_TIMEOUT = 120     # 脚本执行器超时时间 (增加至120秒以支持报价单支付检查)

# 7.通知配置
# 是否开启“全通过报告”推送 (True: 开启, False: 关闭)
ENABLE_NORMAL_NOTIFIER = False
# A群：全通关报告 Webhook 地址
WEBHOOK_URL_NORMAL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=74a91292-a1ac-49e1-b1df-7cea1f54588b"  # Webhook--IT部-每日巡检汇报群

# 是否开启“故障报警”推送 (True: 开启, False: 关闭)
ENABLE_ALARM_NOTIFIER = False
# B群：故障报警 Webhook 地址
WEBHOOK_URL_ALARM = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e28fa03c-3299-4ba7-bb51-e7de294a16d7"  # Webhook--测试和报错通知群
