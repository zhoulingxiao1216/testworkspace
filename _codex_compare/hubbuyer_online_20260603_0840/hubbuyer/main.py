# -*- coding: utf-8 -*-
# d:\sakuradk3\main.py
import os
import sys
import traceback
from datetime import datetime
from config.settings import REPORT_CONFIG
from core.logger import InspectorLogger

def initialize_environment():
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        # 确保输出不被缓冲
        sys.stdout.flush()
        sys.stderr.flush()
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        # 如果环境变量未设置，则设置 PYTHONUNBUFFERED
        if 'PYTHONUNBUFFERED' not in os.environ:
            os.environ['PYTHONUNBUFFERED'] = '1'
    except: pass
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

def run_inspection():
    initialize_environment()
    
    report_data = {}
    is_all_pass = False
    
    try:
        from config.settings import ENV_TYPE
    except ImportError:
        ENV_TYPE = "Unknown"
    
    logger = InspectorLogger()
    logger.log_session_start(ENV_TYPE)

    print("=" * 60)
    print(f"🚀 全球站 巡检系统 | 环境: {ENV_TYPE} | 启动: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    try:
        from core.batch_checker import BatchChecker
        from core.report_generator import ReportGenerator
        from core.notifier import Notifier 

        # 2. 执行检查 
        checker = BatchChecker(logger_instance=logger) 
        results = checker.run_all_checks()
        
        # 3. 结果汇总分析
        report_data = results.get("巡检汇总报告", {}) 
        all_results = []
        
        for task_name, info in report_data.items():
            if isinstance(info, dict):
                all_results.append(info)
                # 注意：任务结果已在 batch_checker.py 中记录，此处不再重复记录
                # 避免重复写入 error_summary 日志
            else:
                all_results.append({"success": False, "message": str(info)})

        total = len(all_results)
        success = sum(1 for r in all_results if r.get("success") is True)
        failed = total - success
        is_all_pass = (failed == 0) and (total > 0)
        
        # 4. 写入汇总日志
        logger.log_summary(total, success, failed)
        print(f"📊 汇总: 共计 {total} | ✅ 成功 {success} | ❌ 失败 {failed}")

        # 5. 生成可视化报告 
        inspector = REPORT_CONFIG.get("RESPONSIBLE_PERSON", "未知负责人")
        generator = ReportGenerator(results, inspector)        
        report_content = generator.generate_report()
        report_file = generator.save_report(report_content)
        
        print("-" * 60)
        print(f"✅ 报告已存: {os.path.abspath(report_file)}")
        print("-" * 60)

        # 6. 执行通知 (包含 @张洪博 等人的强提醒)
        if report_data:
            Notifier.send_wechat_report(report_data, is_all_pass)

    except Exception as e:
        # --- 捕获系统级崩溃并通知 ---
        from core.notifier import Notifier
        error_stack = traceback.format_exc()
        msg = f"系统执行崩溃: {str(e)}"
        print(f"\n❌ {msg}")
        
        if 'logger' in locals():
            logger.log_error(f"{msg}\n{error_stack}")
        
        emergency_data = {
            "🚨 系统运行异常": {
                "success": False,
                "message": f"错误类型: {type(e).__name__}\n详细堆栈:\n{error_stack[:500]}..."
            }
        }
        Notifier.send_wechat_report(emergency_data, False)
        traceback.print_exc()

if __name__ == "__main__":
    run_inspection()
    