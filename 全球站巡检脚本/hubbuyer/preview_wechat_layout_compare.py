# -*- coding: utf-8 -*-
"""预览微信推送方案 A（固定宽双列）与方案 C（markdown_v2 表格）"""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from config.settings import REPORT_CONFIG
from core.notifier import Notifier

# main 环境最近一次全绿结果
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
    "B2B 提交自助报价单": {
        "success": True,
        "message": "B2B提交自助报价单:OK(订单号:B2B-BJ-KOR8-260616-398)",
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
}

SECTIONS = [
    ("📍 全球站生产站点访问检查", Notifier.WEB_ITEMS),
    ("💼 前台核心业务检查", Notifier.FRONTEND_API_ITEMS),
    ("🔗 前后台联动检查", Notifier.BRIDGE_API_ITEMS),
    ("🔧 后台管理检查点", Notifier.BACKEND_ADMIN_ITEMS),
]

COL_SEP = "｜"
FW_SPACE = "\u3000"
MAX_COL_WIDTH = 28


def clean_label(label):
    return label.rstrip(" 　\t")


def display_width(text):
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        elif ord(ch) > 0xFFFF:
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text, target_width):
    text = clean_label(text)
    gap = target_width - display_width(text)
    if gap <= 0:
        return text
    return text + FW_SPACE * (gap // 2) + (" " if gap % 2 else "")


def collect_executed(items, report_data):
    rows = []
    for label, key in items:
        if key not in report_data:
            continue
        result = report_data[key]
        rows.append(
            {
                "label": clean_label(label),
                "key": key,
                "success": bool(result.get("success")),
                "message": result.get("message", ""),
            }
        )
    return rows


def section_col_width(rows):
    if not rows:
        return 0
    return min(MAX_COL_WIDTH, max(display_width(r["label"]) for r in rows))


def render_item_cell(row, col_width):
    icon = "✅" if row["success"] else "❌"
    return f"{icon} {pad_to_width(row['label'], col_width)}"


def bridge_extra_lines(report_data):
    lines = []
    for key, (order_type, order_label) in Notifier._BRIDGE_ORDER_DETAIL.items():
        order_no = Notifier._resolve_bridge_order_no(report_data, key, order_type)
        if order_no:
            lines.append(f"　{order_label}: {order_no}")
    return lines


def rate_extra_line(report_data):
    item = report_data.get("后台管理检查点-汇率", {})
    if item.get("success") and item.get("message"):
        return f"　{item['message']}"
    return ""


def build_plan_a(report_data, is_all_pass=True):
    now_date = datetime.now().strftime("%Y年%m月%d日")
    person = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未知负责人")

    if is_all_pass:
        content = "批量巡检执行通知\n以下项目已完成自动检查并生成报告：\n\n"
    else:
        content = "🚨 巡检告警通知\n以下项目已完成自动检查，存在异常项，请及时处理：\n\n"

    for title, items in SECTIONS:
        rows = collect_executed(items, report_data)
        if not rows:
            continue
        col_w = section_col_width(rows)
        content += f"{title}\n"
        for i in range(0, len(rows), 2):
            left = render_item_cell(rows[i], col_w)
            if i + 1 < len(rows):
                right = render_item_cell(rows[i + 1], col_w)
                content += f"{left}　｜　{right}\n"
            else:
                content += f"{left}　｜\n"
        if "联动" in title:
            for line in bridge_extra_lines(report_data):
                content += f"{line}\n"
        if "后台管理" in title:
            extra = rate_extra_line(report_data)
            if extra:
                content += f"{extra}\n"
        content += "\n"

    content += f"📅 巡检时间: {now_date}\n👥 负责人: {person}\n\n【报告自动生成】"
    return content


def table_cell(row):
    if not row:
        return " "
    icon = "✅" if row["success"] else "❌"
    return f"{row['label']} {icon}"


def build_plan_c(report_data, is_all_pass=True):
    now_date = datetime.now().strftime("%Y年%m月%d日")
    person = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未知负责人")

    if is_all_pass:
        content = "# 批量巡检执行通知\n以下项目已完成自动检查并生成报告：\n\n"
    else:
        content = "# 🚨 巡检告警通知\n以下项目已完成自动检查，存在异常项，请及时处理：\n\n"

    for title, items in SECTIONS:
        rows = collect_executed(items, report_data)
        if not rows:
            continue
        content += f"### {title}\n"
        content += "| 检查项 | 检查项 |\n"
        content += "| :----- | :----- |\n"
        for i in range(0, len(rows), 2):
            left = table_cell(rows[i])
            right = table_cell(rows[i + 1]) if i + 1 < len(rows) else " "
            content += f"| {left} | {right} |\n"
        if "联动" in title:
            for line in bridge_extra_lines(report_data):
                content += f"\n>{line.strip()}\n"
        if "后台管理" in title:
            extra = rate_extra_line(report_data)
            if extra:
                content += f"\n>{extra.strip()}\n"
        content += "\n"

    content += f"---\n📅 巡检时间: {now_date}　👥 负责人: {person}\n\n【报告自动生成】"
    return content


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(out_dir, exist_ok=True)

    plan_a = Notifier._build_dynamic_template(SAMPLE_REPORT, True)
    plan_c = build_plan_c(SAMPLE_REPORT, True)
    current = plan_a  # 已切换为方案 A，保留 plan_c 对照

    with open(os.path.join(out_dir, "wechat_preview_plan_a.txt"), "w", encoding="utf-8") as f:
        f.write("=== 方案 A：markdown v1 · 固定宽双列（按区块列宽）===\n")
        f.write(f"字节长度: {len(plan_a.encode('utf-8'))}\n\n")
        f.write(plan_a)

    with open(os.path.join(out_dir, "wechat_preview_plan_c.txt"), "w", encoding="utf-8") as f:
        f.write("=== 方案 C：markdown_v2 · 双列表格 ===\n")
        f.write(f"字节长度: {len(plan_c.encode('utf-8'))}\n\n")
        f.write(plan_c)

    with open(os.path.join(out_dir, "wechat_preview_current.txt"), "w", encoding="utf-8") as f:
        f.write("=== 当前模板（对照）===\n\n")
        f.write(current)

    print("预览已写入 reports/wechat_preview_plan_a.txt")
    print("预览已写入 reports/wechat_preview_plan_c.txt")
    print("预览已写入 reports/wechat_preview_current.txt")


if __name__ == "__main__":
    main()
