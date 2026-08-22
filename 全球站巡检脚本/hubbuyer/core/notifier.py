# -*- coding: utf-8 -*-
# core/notifier.py
import re
import unicodedata
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
        ("B2B H5站点巡检", "B2B H5站点巡检"),
        ("B2B PC站点巡检", "B2B PC站点巡检"),
        ("D2C PC站点巡检", "D2C pc站点巡检"),
        ("介绍中心 PC站点巡检", "介绍中心 pc站点巡检"),
        ("介绍中心 H5站点巡检", "介绍中心 H5站点巡检"),
    ]
    FRONTEND_API_ITEMS = [
        ("B2B 登录", "登录接口校验"),
        ("B2B 图搜", "B2B 商品图搜接口校验"),
        ("B2B 关键词搜索", "B2B 1688&淘宝 关键词搜索接口校验"),
        ("B2B 加购1688&淘宝商品", "B2B&D2C 商品加购接口校验"),
        ("B2B 编辑保存附加项", "B2B 选择商品附加项"),
        ("D2C 选择商品附加项", "D2C 选择商品附加项"),
        ("B2B 提交委托报价", "B2B 提交委托报价"),
        ("B2B 支付报价单", "B2B报价单支付"),
        ("B2B 指定报价单支付", "B2B指定报价单支付"),
        ("B2B&D2C 插件加购", "B2B&D2C插件添加1688&淘宝商品"),
    ]
    PRICING_API_ITEMS = [
        ("💰 价格体系专项", "价格体系专项巡检链路"),
    ]
    BRIDGE_API_ITEMS = [
        ("📋 报价单审核(联动)", "后台报价单审核"),
        ("📦 代购订单审核(联动)", "后台代购订单审核"),
    ]
    BACKEND_ADMIN_ITEMS = [
        ("🛠 后台管理-代购仓配", "后台管理检查点-代购仓配"),
        ("💱 后台管理-汇率", "后台管理检查点-汇率"),
        ("🚚 后台管理-发货链路", "后台管理检查点-发货链路"),
    ]
    EXTERNAL_API_ITEMS = [
        ("📊 万邦API调用统计", "万邦 API 前日调用统计"),
    ]
    SECTIONS = [
        ("📍 全球站生产站点访问检查", WEB_ITEMS),
        ("💼 前台核心业务检查", FRONTEND_API_ITEMS),
        ("💰 价格体系专项检查", PRICING_API_ITEMS),
        ("🔗 前后台联动检查", BRIDGE_API_ITEMS),
        ("🔧 后台管理检查点", BACKEND_ADMIN_ITEMS),
        ("📊 外部 API 用量统计", EXTERNAL_API_ITEMS),
    ]
    _FW_SPACE = "\u3000"
    _MAX_COL_WIDTH = 28
    _BJ_ORDER_RE = re.compile(r"B2B-BJ-[A-Z0-9-]+")
    _DD_ORDER_RE = re.compile(r"B2B-DD-[A-Z0-9-]+")
    _BRIDGE_ORDER_DETAIL = {
        "后台报价单审核": ("quote", "报价单"),
        "后台代购订单审核": ("purchase", "代购订单"),
    }
    _ONEBOUND_KEY = "万邦 API 前日调用统计"
    _ONEBOUND_MSG_PART_RE = re.compile(
        r"(?P<label>[^|]+?)\s+实际:(?P<real>\d+)\s+总计:(?P<all>\d+)"
    )
    _MEMBER_PRICING_KEY = "价格体系专项巡检链路"
    _MEMBER_PRICING_STATS_RE = re.compile(
        r"Passed=(?P<passed>\d+)\s+Failed=(?P<failed>\d+)\s+Skipped=(?P<skipped>\d+)"
    )

    @staticmethod
    def _clean_label(label):
        return str(label).rstrip(" 　\t")

    @staticmethod
    def _display_width(text):
        width = 0
        for ch in text:
            if unicodedata.east_asian_width(ch) in ("F", "W"):
                width += 2
            elif ord(ch) > 0xFFFF:
                width += 2
            else:
                width += 1
        return width

    @staticmethod
    def _pad_to_width(text, target_width):
        text = Notifier._clean_label(text)
        gap = target_width - Notifier._display_width(text)
        if gap <= 0:
            return text
        return text + Notifier._FW_SPACE * (gap // 2) + (" " if gap % 2 else "")

    @staticmethod
    def _collect_section_rows(items, report_data):
        rows = []
        for label, key in items:
            if key not in report_data:
                continue
            result = report_data[key]
            rows.append({
                "label": Notifier._clean_label(label),
                "key": key,
                "success": bool(result.get("success")),
                "message": result.get("message", ""),
            })
        return rows

    @staticmethod
    def _section_col_width(rows):
        if not rows:
            return 0
        return min(
            Notifier._MAX_COL_WIDTH,
            max(Notifier._display_width(row["label"]) for row in rows),
        )

    @staticmethod
    def _render_item_cell(row, col_width):
        icon = "✅" if row["success"] else "❌"
        return f"{icon} {Notifier._pad_to_width(row['label'], col_width)}"

    @staticmethod
    def _extract_order_no(text, order_type):
        pattern = Notifier._BJ_ORDER_RE if order_type == "quote" else Notifier._DD_ORDER_RE
        matches = pattern.findall(str(text or ""))
        return matches[-1] if matches else None

    @staticmethod
    def _resolve_bridge_order_no(report_data, key, order_type):
        """从联动项或其上游步骤 message 中解析本轮单号"""
        if key in report_data:
            order_no = Notifier._extract_order_no(report_data[key].get("message"), order_type)
            if order_no:
                return order_no

        fallback_keys = {
            "quote": ["B2B 提交委托报价", "B2B 提交自助报价单", "B2B报价单支付", "B2B指定报价单支付"],
            "purchase": ["B2B报价单支付", "B2B指定报价单支付"],
        }
        for fb_key in fallback_keys.get(order_type, []):
            if fb_key not in report_data:
                continue
            order_no = Notifier._extract_order_no(report_data[fb_key].get("message"), order_type)
            if order_no:
                return order_no

        if order_type == "purchase":
            quote_no = Notifier._resolve_bridge_order_no(report_data, "后台报价单审核", "quote")
            if quote_no and quote_no.startswith("B2B-BJ"):
                return "B2B-DD" + quote_no[6:]
        return None

    @staticmethod
    def _bridge_extra_lines(report_data):
        lines = []
        for key, (order_type, order_label) in Notifier._BRIDGE_ORDER_DETAIL.items():
            order_no = Notifier._resolve_bridge_order_no(report_data, key, order_type)
            if order_no:
                lines.append(f"　{order_label}: {order_no}")
        return lines

    @staticmethod
    def _rate_extra_line(report_data):
        item = report_data.get("后台管理检查点-汇率", {})
        if item.get("success") and item.get("message"):
            return f"　{item['message']}"
        return ""

    @staticmethod
    def _shipping_extra_line(report_data):
        item = report_data.get("后台管理检查点-发货链路", {})
        if not item.get("success"):
            return ""
        msg = item.get("message", "")
        # 提取发货单号和运单号
        import re as _re
        ship_no = (_re.search(r"WL-[A-Z0-9\-]+", msg) or _re.search(r"创建发货单:OK\(([^)]+)\)", msg))
        waybill = _re.search(r"运单:([0-9\-]+)", msg)
        if ship_no and waybill:
            no = ship_no.group(0) if ship_no.lastindex is None else ship_no.group(1)
            return f"　发货单: {no} | 运单: {waybill.group(1)}"
        return ""

    @staticmethod
    def _short_onebound_api_label(label):
        parts = str(label).split("/")
        if len(parts) >= 3:
            return "/".join(parts[1:])
        return str(label)

    @staticmethod
    def _onebound_extra_lines(report_data):
        """万邦 API 统计明细：合计 + 各接口实际/总调用数"""
        item = report_data.get(Notifier._ONEBOUND_KEY, {})
        message = str(item.get("message") or "").strip()
        if not message:
            return []

        lines = []
        stats = item.get("stats") or {}
        if stats.get("date") and stats.get("total"):
            total = stats["total"]
            lines.append(
                f"　{stats['date']} 合计 实际:{total.get('use_real', 0)} "
                f"总计:{total.get('use_all', 0)}"
            )
            details = stats.get("details") or {}
            for label in sorted(details.keys()):
                detail = details[label]
                short_label = Notifier._short_onebound_api_label(label)
                lines.append(
                    f"　· {short_label} 实际:{detail.get('use_real', 0)} "
                    f"总计:{detail.get('use_all', 0)}"
                )
            return lines

        parts = [part.strip() for part in message.split("|") if part.strip()]
        if not parts:
            return [f"　{message}"]

        summary = parts[0]
        if "合计" in summary:
            summary = re.sub(r"\s*缓存:\d+", "", summary)
            lines.append(f"　{summary.strip()}")

        for part in parts[1:]:
            match = Notifier._ONEBOUND_MSG_PART_RE.search(part)
            if not match:
                continue
            short_label = Notifier._short_onebound_api_label(match.group("label").strip())
            lines.append(
                f"　· {short_label} 实际:{match.group('real')} 总计:{match.group('all')}"
            )

        if not lines:
            lines.append(f"　{message}")
        return lines

    @staticmethod
    def _member_pricing_extra_lines(report_data):
        """价格体系专项巡检摘要：展示断言通过、失败、跳过数量。"""
        item = report_data.get(Notifier._MEMBER_PRICING_KEY, {})
        message = str(item.get("message") or "")
        if not message:
            return []

        match = Notifier._MEMBER_PRICING_STATS_RE.search(message)
        if match:
            return [
                "　价格体系断言: Passed={passed} Failed={failed} Skipped={skipped}".format(
                    passed=match.group("passed"),
                    failed=match.group("failed"),
                    skipped=match.group("skipped"),
                )
            ]

        short_msg = message[:120] + ("..." if len(message) > 120 else "")
        return [f"　{short_msg}"]

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
    def _render_section_two_column(items, report_data, error_details, section_title):
        """方案 A：按区块固定列宽，一行两列展示检查项"""
        rows = Notifier._collect_section_rows(items, report_data)
        if not rows:
            return ""

        col_width = Notifier._section_col_width(rows)
        content = f"{section_title}\n"
        for i in range(0, len(rows), 2):
            left = Notifier._render_item_cell(rows[i], col_width)
            if not rows[i]["success"]:
                error_details.append((rows[i]["label"], rows[i]["message"] or "未知错误"))
            if i + 1 < len(rows):
                right = Notifier._render_item_cell(rows[i + 1], col_width)
                if not rows[i + 1]["success"]:
                    error_details.append((rows[i + 1]["label"], rows[i + 1]["message"] or "未知错误"))
                content += f"{left}　｜　{right}\n"
            else:
                content += f"{left}　｜\n"

        if "联动" in section_title:
            for line in Notifier._bridge_extra_lines(report_data):
                content += f"{line}\n"
        if "后台管理" in section_title:
            extra = Notifier._rate_extra_line(report_data)
            if extra:
                content += f"{extra}\n"
            shipping_extra = Notifier._shipping_extra_line(report_data)
            if shipping_extra:
                content += f"{shipping_extra}\n"
        if "价格体系" in section_title:
            for line in Notifier._member_pricing_extra_lines(report_data):
                content += f"{line}\n"
        if "外部 API" in section_title:
            for line in Notifier._onebound_extra_lines(report_data):
                content += f"{line}\n"
        return content

    @staticmethod
    def _build_dynamic_template(report_data, is_all_pass):
        """
        动态美化模板（方案 A：固定宽双列）：
        - 根据 report_data 实际结果渲染 ✅ / ❌
        - 未执行的项目（开关关闭）自动跳过，不显示
        - 有失败项时，底部附带「失败详情」区块
        """
        now_date = datetime.now().strftime("%Y年%m月%d日")
        now_time = datetime.now().strftime("%H:%M:%S")
        responsible_person = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未知负责人")
        at_user_ids = REPORT_CONFIG.get("ALARM_USER_IDS", [])

        if is_all_pass:
            content = "批量巡检执行通知\n"
            content += "以下项目已完成自动检查并生成报告：\n\n"
        else:
            at_text = "".join([f"<@{uid}>" for uid in at_user_ids]) if at_user_ids else ""
            content = "🚨 巡检告警通知\n"
            content += "以下项目已完成自动检查，存在异常项，请及时处理：\n\n"
            if at_text:
                content += f"> 报警时间：{now_time}　提醒：{at_text}\n\n"

        error_details = []

        for section_title, items in Notifier.SECTIONS:
            section_content = Notifier._render_section_two_column(
                items, report_data, error_details, section_title
            )
            if section_content:
                content += section_content + "\n"

        content += f"📅 巡检时间: {now_date}\n"
        content += f"👥 负责人: {responsible_person}\n\n"

        if error_details:
            content += "----------------------------------------\n"
            content += "**【失败详情】**\n\n"
            for name, msg in error_details:
                clean_msg = str(msg)[:300] + ("..." if len(str(msg)) > 300 else "")
                content += f"❌ **{name}**\n"
                content += f"原因：{clean_msg}\n\n"

        content += "【报告自动生成】"
        return content
