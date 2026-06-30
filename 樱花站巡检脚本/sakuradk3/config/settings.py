# -*- coding: utf-8 -*-
# d:\sakuradk3\config\settings.py
# #第二版应用api和url
# ==========================================
# 核心开关：切换环境只需改这一个词 ('prod', 'test', 'dev')
# ==========================================

# ==========================================
# 1. 核心环境开关
# ==========================================

ENV_TYPE = "prod" 

# ==========================================
# 2. 业务巡检开关
# ==========================================
INSPECTION_SWITCHES = {
    "check_web_url_B2B_h5": True,      #b2b_h5网页访问开关
    "check_web_url_B2B_pc": True,      #b2b_pc网页访问开关
    "check_web_url_D2C_pc": True,      #d2c_h5网页访问开关
    "check_api_login": True,          #登录接口开关
    "check_api_img_search": True,       #b2b&d2c图片请求接口开关
    "check_api_keyword_search": True,  #b2b关键字搜索接口开关
    "check_api_d2c_keyword_search": True,  #d2c关键字搜索接口开关(1688)
    "check_api_add_cart": True,        #b2b&d2c 1688&淘宝 商品加购接口开关
    "check_api_b2b_addon": True,      #b2b选择商品附加项
    "check_api_d2c_addon": True,      #d2c选择商品附加项
    "check_api_submit_order": True,   #b2b&d2c提交自助报价单
    "check_api_payment": True,        #b2b&d2c报价单支付
    "check_api_plugin": True      #b2b&d2c插件加购1688&taobao商品
}

# ==========================================
# 3. 动态导入：根据环境加载模块
# ==========================================
from config.data.login_data import ACCOUNTS_POOL

if ENV_TYPE == "prod":
    import config.url.prod as url_mod
    import config.api.prod as api_mod
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
    "ENDPOINTS": api_mod.API_CONFIG["ENDPOINTS"], # 提取接口路径列表
    # 获取当前环境的所有账号列表，如果没有则默认为空列表
    "ACCOUNT_LIST": ACCOUNTS_POOL.get(ENV_TYPE, [])
}

# 5. 报告人员相关配置
REPORT_CONFIG = {
    "RESPONSIBLE_PERSON": "周凌虓",
    # 在这里添加需要 @ 的用户帐号（Userid）列表
    "ALARM_USER_IDS": ["ZhouLingXiao"], 
    "PROJECT_NAME": "Sakuradk3 自动化巡检系统",
    "SAVE_DIR": "reports"
}

# 6.巡检任务之间的等待时间（秒）
INSPECTION_INTERVAL = 10
# 巡检任务执行后的随机等待时间范围（最小值, 最大值）单位：秒
# 比如 (3, 8) 表示在 3 到 8 秒之间随机取一个时间
#INSPECTION_INTERVAL_RANGE = (3, 8)

#脚本执行超时配置（单位：秒）
SCRIPT_RUNNER_TIMEOUT = 60

# 7.通知配置
# 是否开启“全通过报告”推送 (True: 开启, False: 关闭)
ENABLE_NORMAL_NOTIFIER = False
# A群：全通关报告 Webhook 地址
WEBHOOK_URL_NORMAL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d866c272-218a-420b-aee6-c80138e22276"  # Webhook--IT部-每日巡检汇报群

# 是否开启"故障报警"推送 (True: 开启, False: 关闭)
ENABLE_ALARM_NOTIFIER = False
# B群：故障报警 Webhook 地址
WEBHOOK_URL_ALARM = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2971788f-d944-430d-84da-33bd6fab70a9"  # Webhook--测试和报错通知群