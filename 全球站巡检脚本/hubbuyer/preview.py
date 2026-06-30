import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from core.notifier import Notifier

report_data = {
    'B2B PC站点巡检': {'success': True, 'message': '校验通过'},
    '介绍中心 pc站点巡检': {'success': False, 'message': '访问崩溃: ConnectionError'},
    '介绍中心 H5站点巡检': {'success': True, 'message': '校验通过'},
    '登录接口校验': {'success': True, 'message': '【prod】mxnrq@airsworld.net:OK'},
    '当日汇率检测': {'success': False, 'message': 'USD(银行:0.1465 全球站:0.1538) | JPY(银行:N/A 全球站:24.31):银行汇率未获取'},
    'B2B 商品图搜接口校验': {'success': True, 'message': 'B2B:OK(双200)'},
    'B2B&D2C 商品加购接口校验': {'success': True, 'message': 'B2B_1688:OK | B2B_taobao:OK'},
    'B2B 选择商品附加项': {'success': False, 'message': "FBA编写保存:FAIL(('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))"},
    'B2B 提交自助报价单': {'success': True, 'message': 'B2B提交自助报价单:OK'},
    'B2B报价单支付': {'success': True, 'message': 'B2B报价单列表:OK | B2B报价单支付:跳过(距离上次支付未满3天)'},
    'B2B 1688&淘宝 关键词搜索接口校验': {'success': True, 'message': 'B2B_1688_keyword:OK | B2B_taobao_keyword:OK'},
}
content = Notifier._build_dynamic_template(report_data, False)
with open('wechat_preview_latest.txt', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
