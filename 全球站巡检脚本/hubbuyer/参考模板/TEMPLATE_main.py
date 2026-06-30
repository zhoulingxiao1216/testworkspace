# -*- coding: utf-8 -*-
"""
通用模板：入口脚本 (main.py)

职责：初始化系统，协调各个模块执行
"""

import os
import sys
import traceback
from datetime import datetime

def initialize_environment():
    """初始化环境编码和路径"""
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.flush()
        sys.stderr.flush()
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        if 'PYTHONUNBUFFERED' not in os.environ:
            os.environ['PYTHONUNBUFFERED'] = '1'
    except:
        pass
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

def run_inspection():
    """主执行逻辑"""
    
    initialize_environment()
    
    try:
        from config.settings import ENV_TYPE
    except ImportError:
        ENV_TYPE = "Unknown"
    
    from core.logger import InspectorLogger
    from core.batch_checker import BatchChecker
    
    # 1. 初始化日志
    logger = InspectorLogger()
    logger.log_session_start(ENV_TYPE)
    
    # 2. 打印启动信息
    print("=" * 60)
    print(f"🚀 巡检系统启动 | 环境: {ENV_TYPE} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    report_data = {}
    
    try:
        # 3. 执行批量检查
        checker = BatchChecker(logger_instance=logger)
        results = checker.run_all_checks()
        
        # 4. 汇总结果
        report_data = results.get("巡检汇总报告", {})
        all_results = []
        
        for task_name, info in report_data.items():
            if isinstance(info, dict):
                all_results.append(info)
            else:
                all_results.append({"success": False, "message": str(info)})
        
        # 5. 统计
        total = len(all_results)
        success = sum(1 for r in all_results if r.get("success") is True)
        failed = total - success
        is_all_pass = (failed == 0) and (total > 0)
        
        # 6. 记录汇总日志
        logger.log_info(f"汇总: 共 {total} | ✅ {success} | ❌ {failed}")
        print(f"\n{'='*60}")
        print(f"📊 汇总: 共 {total} | ✅ 成功 {success} | ❌ 失败 {failed}")
        print(f"{'='*60}\n")
        
        if is_all_pass:
            print("✅ 所有检查通过！")
        else:
            print(f"⚠️  有 {failed} 个检查失败")
    
    except Exception as e:
        error_stack = traceback.format_exc()
        error_msg = f"系统执行崩溃: {str(e)}"
        print(f"\n❌ {error_msg}")
        logger.log_error(f"{error_msg}\n{error_stack}")

if __name__ == "__main__":
    run_inspection()
