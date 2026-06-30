# -*- coding: utf-8 -*-
# core/notifier.py
import requests
from datetime import datetime
from config.settings import (
    WEBHOOK_URL_NORMAL, WEBHOOK_URL_ALARM,
    ENABLE_NORMAL_NOTIFIER, ENABLE_ALARM_NOTIFIER,
    REPORT_CONFIG, REQUEST_TIMEOUT_NOTIFIER
)

class Notifier:
    # =====================================================
    # 巡检项展示列表：(模板显示名称, report_data 中的 desc 键)
    # 开关关闭的任务不会出现在 report_data 中，会被自动跳过
    # =====================================================
    WEB_ITEMS = [
        ("B2B H5站点巡检 　　　 ",    "B2B H5站点巡检"),
        ("B2B PC站点巡检 　　　 ",    "B2B PC站点巡检"),
        ("D2C PC站点巡检 　　　 ",    "D2C pc站点巡检"),
        ("介绍中心 PC站点巡检 　　　 ", "介绍中心 pc站点巡检"),
        ("介绍中心 H5站点巡检 　　　 ", "介绍中心 H5站点巡检"),
    ]
    API_ITEMS = [
        ("B2B 登录   　　　",           "登录接口校验"),
        ("B2B 图搜   　　　",           "B2B 商品图搜接口校验"),
        ("B2B 关键词搜索   　　　",      "B2B 1688&淘宝 关键词搜索接口校验"),
        ("B2B 加购1688&淘宝商品　　　",  "B2B&D2C 商品加购接口校验"),
        ("B2B 编辑保存附加项　　　　",  "B2B 选择商品附加项"),
        ("D2C 选择商品附加项　　　　",  "D2C 选择商品附加项"),
        ("B2B 提交自助报价单　　　　",  "B2B 提交自助报价单"),
        ("B2B 支付报价单　　　　　　",      "B2B报价单支付"),
        ("B2B&D2C 插件加购　　　　　",   "B2B&D2C插件添加1688&淘宝商品"),
        ("💱 当日汇率检测　　　　　　",  "当日汇率检测"),
    ]

    @staticmethod
    def send_wechat_report(report_data, is_all_pass):
        """
        统一使用动态美化模板推送：
        - 全通过 → 发 A群（报平安）
        - 有失败 → 发 B群（告警），失败项显示 ❌ 并附错误详情
        """
        if is_all_pass:
            if not ENABLE_NORMAL_NOTIFIER:
                return
            url = WEBHOOK_URL_NORMAL
        else:
            if not ENABLE_ALARM_NOTIFIER:
                return
            url = WEBHOOK_URL_ALARM

        content = Notifier._build_dynamic_template(report_data, is_all_pass)

        try:
            requests.post(
                url,
                json={"msgtype": "markdown", "markdown": {"content": content}},
                timeout=REQUEST_TIMEOUT_NOTIFIER
            )
        except Exception as e:
            print(f"❌ 推送失败: {e}")

    @staticmethod
    def _build_dynamic_template(report_data, is_all_pass):
        """
        动态美化模板：
        - 根据 report_data 实际结果渲染 ✅ / ❌
        - 未执行的项目（开关关闭）自动跳过，不显示
        - 有失败项时，底部附带「失败详情」区块
        """
        now_date = datetime.now().strftime("%Y年%m月%d日")
        now_time = datetime.now().strftime("%H:%M:%S")
        responsible_person = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未知负责人")
        at_user_ids = REPORT_CONFIG.get("ALARM_USER_IDS", [])

        # ── 顶部标题 ──
        if is_all_pass:
            content = "批量巡检执行通知\n"
            content += "以下项目已完成自动检查并生成报告：\n\n"
        else:
            at_text = "".join([f"<@{uid}>" for uid in at_user_ids]) if at_user_ids else ""
            content = "🚨 巡检告警通知\n"
            content += "以下项目已完成自动检查，存在异常项，请及时处理：\n\n"
            if at_text:
                content += f"> 报警时间：{now_time}　提醒：{at_text}\n\n"

        error_details = []  # 收集失败项，用于底部详情区块

        # ── 网页访问巡检 ──
        web_executed = [(label, key) for label, key in Notifier.WEB_ITEMS if key in report_data]
        if web_executed:
            content += "　\n"
            content += "📍 全球站生产站点访问检查\n\n"
            content += "　\n"
            for label, key in web_executed:
                result = report_data[key]
                icon = "✅" if result.get("success") else "❌"
                content += f"• {label}{icon}\n"
                if not result.get("success"):
                    error_details.append((label, result.get("message", "未知错误")))
            content += "\n"

        # ── 核心业务巡检 ──
        api_executed = [(label, key) for label, key in Notifier.API_ITEMS if key in report_data]
        if api_executed:
            content += "　\n"
            content += "💼 核心业务检查\n\n"
            content += "　\n"
            for label, key in api_executed:
                result = report_data[key]
                icon = "✅" if result.get("success") else "❌"
                content += f"• {label}{icon}\n"
                if not result.get("success"):
                    error_details.append((label, result.get("message", "未知错误")))
                elif key == "当日汇率检测" and result.get("message"):
                    content += f"  {result['message']}\n"
            content += "\n"

        # ── 页脚 ──
        content += "　\n"
        content += f"📅 巡检时间: {now_date}\n"
        content += f"👥 负责人: {responsible_person}\n\n"

        # ── 失败详情区块（仅有失败项时显示）──
        if error_details:
            content += "　\n"
            content += "----------------------------------------\n"
            content += "**【失败详情】**\n\n"
            for name, msg in error_details:
                clean_msg = str(msg)[:300] + ("..." if len(str(msg)) > 300 else "")
                content += f"❌ **{name}**\n"
                content += f"原因：{clean_msg}\n\n"

        content += "【报告自动生成】"
        return content