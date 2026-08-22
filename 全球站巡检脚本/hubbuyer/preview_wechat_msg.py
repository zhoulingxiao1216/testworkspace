# -*- coding: utf-8 -*-
"""预览微信群推送内容（不实际发送）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.notifier import Notifier

SAMPLE_REPORT = {
    "B2B PC站点巡检": {"success": True, "message": "校验通过"},
    "介绍中心 pc站点巡检": {"success": True, "message": "校验通过"},
    "介绍中心 H5站点巡检": {"success": True, "message": "校验通过"},
    "登录接口校验": {"success": True, "message": "【main】mxnrq@airsworld.net:OK"},
    "B2B 商品图搜接口校验": {"success": True, "message": "B2B:OK(双200)"},
    "B2B 1688&淘宝 关键词搜索接口校验": {
        "success": True,
        "message": "B2B_1688_keyword:OK | B2B_taobao_keyword:OK",
    },
    "B2B&D2C 商品加购接口校验": {"success": True, "message": "B2B_1688:OK | B2B_taobao:OK"},
    "B2B 选择商品附加项": {
        "success": True,
        "message": "购物车列表:OK(获取到2个ID) | FBA编写保存:OK(2个)",
    },
    "B2B 提交委托报价": {
        "success": True,
        "message": "B2B提交委托报价:OK(订单号:B2B-BJ-KOR8-260616-398)",
    },
    "B2B报价单支付": {
        "success": True,
        "message": "B2B报价单支付:OK(B2B-BJ-KOR8-260616-398→B2B-DD-KOR8-260616-398)",
    },
    "后台报价单审核": {
        "success": True,
        "message": "报价单号获取:OK(B2B-BJ-KOR8-260616-398) | 后台登录:OK | 报价单审核:OK(B2B-BJ-KOR8-260616-398)",
    },
    "后台代购订单审核": {
        "success": True,
        "message": "代购订单号获取:OK(B2B-DD-KOR8-260616-398) | 代购订单审核:OK(B2B-DD-KOR8-260616-398)",
    },
    "后台管理检查点-代购仓配": {
        "success": True,
        "message": "入库:OK(丽恋歌旗舰店|5175x1|库位=35)",
    },
    "后台管理检查点-汇率": {
        "success": True,
        "message": "USD(银行:0.15 全球站:0.16) | JPY(银行:24 全球站:24.75)",
    },
    "后台管理检查点-发货链路": {
        "success": True,
        "message": "创建发货单:OK(WL-KOR8-260703-017) | 配货:OK | 配货完成:OK | 创建发货箱:OK(box_id=3272) | 商品入箱:OK | 满箱确认:OK | 发货附加项:OK(8项) | 装箱完成:OK | 移动待清算:OK | 待清算扣款:OK | 绑定运单号:OK(20260703-001) | 确认发货:OK(WL-KOR8-260703-017|运单:20260703-001)",
    },
}

FAIL_REPORT = dict(SAMPLE_REPORT)
FAIL_REPORT["B2B 选择商品附加项"] = {"success": False, "message": "执行超时(90s)"}


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(out_dir, exist_ok=True)

    ok_content = Notifier._build_dynamic_template(SAMPLE_REPORT, True)
    fail_content = Notifier._build_dynamic_template(FAIL_REPORT, False)

    with open(os.path.join(out_dir, "wechat_preview_latest.txt"), "w", encoding="utf-8") as f:
        f.write("=== 全通过 ===\n\n")
        f.write(ok_content)
        f.write("\n\n=== 有失败 ===\n\n")
        f.write(fail_content)

    print(f"字节长度(全通过): {len(ok_content.encode('utf-8'))}")
    print(f"已写入: reports/wechat_preview_latest.txt")


if __name__ == "__main__":
    main()
