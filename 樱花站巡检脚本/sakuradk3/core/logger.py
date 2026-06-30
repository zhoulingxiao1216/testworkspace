# -*- coding: utf-8 -*-
# d:\sakuradk3\core\logger.py
import logging
import os
from datetime import datetime

class InspectorLogger:
    def __init__(self):
        # 1. 自动定位项目根目录下的 logs 文件夹
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 2. 获取当前分钟的时间戳
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
        
        # 3. 创建子目录用于分类日志
        all_execution_dir = os.path.join(log_dir, "all_execution")
        error_summary_dir = os.path.join(log_dir, "error_summary")
        os.makedirs(all_execution_dir, exist_ok=True)
        os.makedirs(error_summary_dir, exist_ok=True)
        
        # 4. 获取 Logger 实例 (同一分钟内名称相同，会返回同一个实例)
        self.logger = logging.getLogger(f"Inspector_{timestamp}")
        self.logger.setLevel(logging.INFO)

        # --- 核心改进：单例保护逻辑 ---
        # 如果 self.logger 已经有 handlers，说明该对象在 main.py 中已经配置过了
        # 直接跳过 Handler 的重复创建，避免重置日志文件
        if not self.logger.handlers:
            # Handler 1: 全量执行日志
            all_execution_file = os.path.join(all_execution_dir, f"{timestamp}.log")
            # 显式使用 mode='a' (追加模式)
            all_execution_handler = logging.FileHandler(all_execution_file, mode='a', encoding='utf-8')
            all_execution_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            all_execution_handler.setFormatter(all_execution_formatter)
            all_execution_handler.setLevel(logging.INFO)
            
            self.logger.addHandler(all_execution_handler)
            # 防止日志向上层 root logger 传递导致控制台双倍打印
            self.logger.propagate = False

        # 5. 错误汇总日志配置 (由于是延迟创建，只需保存路径信息)
        self.error_summary_file = os.path.join(error_summary_dir, f"{timestamp}.log")
        self.error_summary_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.error_summary_handler = None 

    def _ensure_error_handler(self):
        """确保错误日志 handler 已创建（延迟创建）"""
        if self.error_summary_handler is None:
            # 检查是否已经通过之前的实例添加过 error handler
            # 防止重复添加导致错误日志重复打印
            error_summary_file_normalized = os.path.normpath(self.error_summary_file)
            has_error_handler = any(
                isinstance(h, logging.FileHandler) and 
                os.path.normpath(h.baseFilename) == error_summary_file_normalized
                for h in self.logger.handlers
            )
            
            if not has_error_handler:
                self.error_summary_handler = logging.FileHandler(self.error_summary_file, mode='a', encoding='utf-8')
                self.error_summary_handler.setFormatter(self.error_summary_formatter)
                self.error_summary_handler.setLevel(logging.ERROR)
                self.logger.addHandler(self.error_summary_handler)

    def log_session_start(self, env):
        self.logger.info(f"--- 巡检开始 | 环境: {env} ---")

    def log_task(self, name, success, message, url=None, status_code=None, expected=None, actual=None):
        status = "PASS" if success else "FAIL"
        basic_info = f"[{status}] {name}: {message}"
        if url: basic_info += f" | URL: {url}"
        if status_code: basic_info += f" | Status: {status_code}"
        
        self.logger.info(basic_info)
        
        if not success:
            self._ensure_error_handler()
            error_details = [
                f"\n{'='*20} 业务校验失败详情 {'='*20}",
                f"任务名称: {name}",
                f"结论状态: {status}",
                f"失败原因: {message}"
            ]
            if url: error_details.append(f"请求地址: {url}")
            if status_code: error_details.append(f"HTTP状态: {status_code}")
            if expected: error_details.append(f"预期规则: {expected}")
            if actual:
                actual_str = str(actual)
                if len(actual_str) > 500: actual_str = actual_str[:500] + "... (已截断)"
                error_details.append(f"实际返回: {actual_str}")
            error_details.append(f"{'='*54}")
            
            self.logger.error("\n".join(error_details))

    def log_info(self, message):
        self.logger.info(message)
    
    def log_error(self, message):
        self._ensure_error_handler()
        self.logger.error(message)

    def log_summary(self, total, success, failed):
        self.logger.info(f"📊 汇总结果 | 总计: {total}, 成功: {success}, 失败: {failed}")
        self.logger.info("--- 巡检结束 ---" + "\n")