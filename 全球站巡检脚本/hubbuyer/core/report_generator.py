# -*- coding: utf-8 -*-
# d:\sakuradk3\core\report_generator.py

#三、第3版版本优化识别新架构中 validator 返回的 success 状态 core/report_generator.py
import os
from datetime import datetime
from config.settings import REPORT_CONFIG

class ReportGenerator:
    """报告生成器 - 优化版：支持动态模糊匹配逻辑"""
    
    def __init__(self, checker_results, responsible_person):
        self.results = checker_results
        self.responsible_person = responsible_person
        
    def generate_report(self):
        """生成报告内容"""
        current_date = datetime.now().strftime("%Y年%m月%d日")
        
        # 1. 扁平化所有结果数据，方便查找
        # 将嵌套字典转换为：{"任务描述": {"success": True, ...}}
        flat_results = {}
        for section in self.results.values():
            if isinstance(section, dict):
                flat_results.update(section)
        
        # 2. 定义【智能匹配】辅助函数
        def get_status_by_keyword(keyword, default="⚪"):
            """
            在结果中搜索包含关键字的任务
            例如：keyword="H5" 能够匹配到 "B2B H5站点巡检..."
            """
            for desc, info in flat_results.items():
                if keyword.upper() in desc.upper(): # 不区分大小写匹配
                    return "✅" if info.get("success") else "❌"
            return default
        
        # 3. 预解析各个关键项的状态（基于关键字匹配，防止因 desc 修改导致失效）
        status_b2b_h5 = get_status_by_keyword("B2B H5")
        status_b2b_pc = get_status_by_keyword("B2B PC")
        status_d2c_pc = get_status_by_keyword("D2C PC")
        status_aboutus_h5 = get_status_by_keyword("介绍中心 H5")
        status_aboutus_pc = get_status_by_keyword("介绍中心 PC")
        status_login  = get_status_by_keyword("登录")
        # status_register = get_status_by_keyword("注册")  # register.py 未实现，暂时移除
        status_img_search = get_status_by_keyword("商品图搜")
        status_keyword_search = get_status_by_keyword("关键词搜索")
        status_member_pricing = get_status_by_keyword("会员价格")

        # 解析商品加购任务的子任务状态（从消息中查找）
        add_cart_message = ""
        for desc, info in flat_results.items():
            if "商品加购" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                add_cart_message = f"{msg} | {actual}".upper()
                break
        # 检查子任务状态（简化：直接字符串查找）
        def check_task(task_name):
            if not add_cart_message:
                return "⚪"
            return "✅" if f"{task_name}:OK" in add_cart_message else ("❌" if f"{task_name}:FAIL" in add_cart_message else "⚪")
        b2b_1688 = check_task("B2B_1688")
        d2c_1688 = check_task("D2C_1688")
        b2b_taobao = check_task("B2B_TAOBAO")
        d2c_taobao = check_task("D2C_TAOBAO")
        
        # 判断是否有 D2C 任务（如果消息中没有 D2C 相关任务，则只检查 B2B）
        has_d2c_1688 = "D2C_1688" in add_cart_message
        has_d2c_taobao = "D2C_TAOBAO" in add_cart_message
        
        # 汇总：如果 D2C 存在，需要 B2B 和 D2C 都成功；如果 D2C 不存在，只检查 B2B
        if has_d2c_1688:
            status_add_cart_1688 = "✅" if (b2b_1688 == "✅" and d2c_1688 == "✅") else ("❌" if (b2b_1688 == "❌" or d2c_1688 == "❌") else "⚪")
        else:
            # 只有 B2B 任务，只检查 B2B
            status_add_cart_1688 = b2b_1688
        
        if has_d2c_taobao:
            status_add_cart_taobao = "✅" if (b2b_taobao == "✅" and d2c_taobao == "✅") else ("❌" if (b2b_taobao == "❌" or d2c_taobao == "❌") else "⚪")
        else:
            # 只有 B2B 任务，只检查 B2B
            status_add_cart_taobao = b2b_taobao

        # 解析B2B编辑保存附加项任务的子任务状态
        b2b_addon_message = ""
        for desc, info in flat_results.items():
            if "B2B" in desc and "附加项" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                b2b_addon_message = f"{msg} | {actual}"
                break
        # B2B附加项需要检查的步骤（与B2B_Addon.py中实际记录的步骤名称保持一致）
        # 注意：每个步骤都通过AssertionTool.verify_api_common校验，确保双200（HTTP 200 + JSON code 200）
        b2b_steps = ["购物车列表", "选择商品附加项", "编号填写管理", "贴纸编写保存", "吊牌编写保存", "洗标编写保存", "FBA编写保存"]
        b2b_all_ok = True
        b2b_has_fail = False
        b2b_fail_steps = []  # 记录失败的步骤，用于提示
        if b2b_addon_message:
            for step in b2b_steps:
                if f"{step}:OK" in b2b_addon_message:
                    continue  # 该步骤通过（双200校验通过）
                elif f"{step}:FAIL" in b2b_addon_message:
                    # 提取失败原因
                    fail_start = b2b_addon_message.find(f"{step}:FAIL")
                    if fail_start != -1:
                        # 找到失败消息的结束位置（下一个" | "或消息结尾）
                        fail_end = b2b_addon_message.find(" | ", fail_start)
                        if fail_end == -1:
                            fail_end = len(b2b_addon_message)
                        fail_msg = b2b_addon_message[fail_start:fail_end]
                        b2b_fail_steps.append(fail_msg)
                    b2b_all_ok = False
                    b2b_has_fail = True
                else:
                    # 步骤缺失或未执行
                    b2b_all_ok = False
                    b2b_fail_steps.append(f"{step}:未执行或缺失")
        else:
            b2b_all_ok = False
        
        # 生成状态：全部通过显示✅，任意失败显示❌并给出提示
        # 注意：每个步骤都通过AssertionTool.verify_api_common校验双200（HTTP 200 + JSON code 200）
        if b2b_all_ok:
            status_b2b_addon = "✅"
        elif b2b_has_fail:
            # 如果有失败步骤，显示❌并给出第一个失败步骤的提示
            if b2b_fail_steps:
                # 提取第一个失败步骤的名称（简化显示）
                first_fail = b2b_fail_steps[0]
                # 提取步骤名称（去掉FAIL后面的内容）
                step_name = first_fail.split(":FAIL")[0] if ":FAIL" in first_fail else first_fail.split(":")[0]
                if len(b2b_fail_steps) > 1:
                    status_b2b_addon = f"❌ ({step_name}等{len(b2b_fail_steps)}个步骤失败)"
                else:
                    status_b2b_addon = f"❌ ({step_name}失败)"
            else:
                status_b2b_addon = "❌"
        else:
            status_b2b_addon = "⚪"

        # 解析D2C选择商品附加项任务的子任务状态
        d2c_addon_message = ""
        for desc, info in flat_results.items():
            if "D2C" in desc and "附加项" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                d2c_addon_message = f"{msg} | {actual}"
                break
        # D2C附加项需要检查的步骤
        d2c_steps = ["购物车列表", "D2C添加附加项"]
        d2c_all_ok = True
        d2c_has_fail = False
        if d2c_addon_message:
            for step in d2c_steps:
                if f"{step}:OK" in d2c_addon_message:
                    continue
                elif f"{step}:FAIL" in d2c_addon_message:
                    d2c_all_ok = False
                    d2c_has_fail = True
                    break
                else:
                    d2c_all_ok = False
        else:
            d2c_all_ok = False
        status_d2c_addon = "✅" if d2c_all_ok else ("❌" if d2c_has_fail else "⚪")

        # 解析B2B提交自助报价单任务的子任务状态（D2C流程已注释）
        submit_order_message = ""
        for desc, info in flat_results.items():
            if "提交自助报价单" in desc or "自助报价单" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                submit_order_message = f"{msg} | {actual}"
                break
        # 提交自助报价单需要检查的步骤（只检查B2B）
        submit_order_steps = ["B2B提交自助报价单"]
        submit_order_all_ok = True
        submit_order_has_fail = False
        if submit_order_message:
            for step in submit_order_steps:
                if f"{step}:OK" in submit_order_message:
                    continue
                elif f"{step}:FAIL" in submit_order_message:
                    submit_order_all_ok = False
                    submit_order_has_fail = True
                    break
                else:
                    submit_order_all_ok = False
        else:
            submit_order_all_ok = False
        status_submit_order = "✅" if submit_order_all_ok else ("❌" if submit_order_has_fail else "⚪")

        # 解析B2B支付报价单任务的子任务状态（D2C流程已注释）
        payment_message = ""
        for desc, info in flat_results.items():
            if "支付报价单" in desc or "报价单支付" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                payment_message = f"{msg} | {actual}"
                break
        # 支付报价单需要检查的步骤（只检查B2B）
        payment_steps = ["B2B报价单列表", "B2B报价单支付"]
        payment_all_ok = True
        payment_has_fail = False
        if payment_message:
            for step in payment_steps:
                # 先检查失败
                if f"{step}:FAIL" in payment_message:
                    payment_all_ok = False
                    payment_has_fail = True
                    break
                # 再检查成功
                elif f"{step}:OK" in payment_message:
                    continue
                # 检查跳过：只有"距离上次支付未满3天"的跳过才算通过
                elif f"{step}:跳过" in payment_message:
                    # 提取该步骤的完整消息（从步骤名开始到下一个"|"或消息结尾）
                    step_start = payment_message.find(f"{step}:")
                    if step_start != -1:
                        # 找到该步骤消息的结束位置（下一个"|"或消息结尾）
                        step_end = payment_message.find(" | ", step_start)
                        if step_end == -1:
                            step_end = len(payment_message)
                        step_msg = payment_message[step_start:step_end]
                        
                        # 检查跳过原因是否为"距离上次支付未满3天"
                        skip_reason = "距离上次支付未满3天"
                        if skip_reason in step_msg:
                            # 这是正常的3天间隔控制，视为通过
                            continue
                        else:
                            # 其他原因的跳过，视为未完成
                            payment_all_ok = False
                    else:
                        payment_all_ok = False
                else:
                    # 如果步骤既不是OK也不是FAIL也不是跳过，说明可能缺失该步骤
                    payment_all_ok = False
        else:
            payment_all_ok = False
        status_payment = "✅" if payment_all_ok else ("❌" if payment_has_fail else "⚪")

        # 解析B2B关键词搜索任务的子任务状态（从消息中查找）
        keyword_search_message = ""
        for desc, info in flat_results.items():
            if "关键词搜索" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                keyword_search_message = f"{msg} | {actual}".upper()
                break
        # 检查子任务状态（简化：直接字符串查找）
        def check_keyword_task(task_name):
            if not keyword_search_message:
                return "⚪"
            return "✅" if f"{task_name}:OK" in keyword_search_message else ("❌" if f"{task_name}:FAIL" in keyword_search_message or f"{task_name}:ERROR" in keyword_search_message else "⚪")
        keyword_1688 = check_keyword_task("B2B_1688_KEYWORD")
        keyword_taobao = check_keyword_task("B2B_TAOBAO_KEYWORD")
        # 汇总：需要两个任务都成功才算通过
        if keyword_search_message:
            keyword_search_all_ok = (keyword_1688 == "✅" and keyword_taobao == "✅")
            keyword_search_has_fail = (keyword_1688 == "❌" or keyword_taobao == "❌")
            status_keyword_search = "✅" if keyword_search_all_ok else ("❌" if keyword_search_has_fail else "⚪")
        else:
            status_keyword_search = "⚪"

        # 解析B2B&D2C插件添加1688&淘宝商品任务的子任务状态
        plugin_message = ""
        for desc, info in flat_results.items():
            if "插件添加" in desc or "插件" in desc:
                msg = info.get("message") or ""
                actual = info.get("actual") or ""
                plugin_message = f"{msg} | {actual}"
                break
        # 插件添加商品需要检查的步骤
        plugin_steps = ["B2B插件添加1688商品", "B2B插件添加淘宝商品", "D2C插件添加1688商品"]
        plugin_all_ok = True
        plugin_has_fail = False
        if plugin_message:
            for step in plugin_steps:
                # 先检查失败
                if f"{step}:FAIL" in plugin_message:
                    plugin_all_ok = False
                    plugin_has_fail = True
                    break
                # 再检查成功
                elif f"{step}:OK" in plugin_message:
                    continue
                else:
                    # 如果步骤既不是OK也不是FAIL，说明可能缺失该步骤
                    plugin_all_ok = False
        else:
            plugin_all_ok = False
        status_plugin = "✅" if plugin_all_ok else ("❌" if plugin_has_fail else "⚪")

        # 4. 构建排版内容
        report_lines = [
            "",
            "📋批量巡检执行通知",
            "以下项目已完成自动检查并生成报告：",
            "",
            "📍 全球站生产站点访问检查",
            "",
            f"• B2B H5站点巡检      {status_b2b_h5}",
            f"• B2B PC站点巡检      {status_b2b_pc}",
            f"• D2C PC站点巡检      {status_d2c_pc}",
            f"• 介绍中心 H5站点巡检      {status_aboutus_h5}",
            f"• 介绍中心 PC站点巡检      {status_aboutus_pc}",
            "",
            "💼 核心业务检查",
            "",
            f"• B2B 登录        {status_login}",
            f"• B2B 商品图搜        {status_img_search}",
            f"• B2B 关键词搜索        {status_keyword_search}",
            f"• B2B 加购1688商品       {status_add_cart_1688}",
            f"• B2B 加购淘宝商品        {status_add_cart_taobao}",
            f"• B2B 编辑保存附加项           {status_b2b_addon}",
            f"• 会员价格/附加项专项           {status_member_pricing}",
            f"• D2C 选择商品附加项           {status_d2c_addon}",
            f"• B2B 提交自助报价单           {status_submit_order}",
            f"• B2B 支付报价单               {status_payment}",
            f"• B2B&D2C 谷歌浏览器插件（淘宝/1688）      {status_plugin}",
            "",
            f"📅 巡检时间: {current_date}",
            f"👥 负责人: {self.responsible_person}",
            "",
            "【报告自动生成】"
        ]
        
        return "\n".join(report_lines)
    
    def save_report(self, report_content, filename=None):
        """保存报告到文件"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"巡检报告_{timestamp}.md"
        
        save_dir_name = REPORT_CONFIG.get("SAVE_DIR", "reports")
        reports_dir = os.path.join(project_root, save_dir_name)
        os.makedirs(reports_dir, exist_ok=True)
        
        filepath = os.path.join(reports_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filepath
