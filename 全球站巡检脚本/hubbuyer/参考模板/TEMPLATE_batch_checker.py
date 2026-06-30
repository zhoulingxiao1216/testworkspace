# -*- coding: utf-8 -*-
"""
通用模板：批量执行器

职责：遍历所有规则，按顺序执行检查脚本
"""

import os
import json
import time
from core.runner import ScriptRunner
from core.logger import InspectorLogger
from config.settings import INSPECTION_SWITCHES, ENV_TYPE, RETRY_INTERVAL

class BatchChecker:
    """通用批量执行器"""
    
    def __init__(self, logger_instance=None, rules_dir=None):
        self.results = {}
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rules_dir = rules_dir or os.path.join(self.project_root, "config", "rules")
        self.logger = logger_instance or InspectorLogger()
        
        print(f"[初始化] 规则目录: {self.rules_dir}")
        print(f"[初始化] 环境: {ENV_TYPE}")
        print(f"[初始化] 启用任务数: {sum(1 for v in INSPECTION_SWITCHES.values() if v)}")
    
    def run_all_checks(self):
        """执行所有已启用的检查"""
        
        print(f"\n🚀 启动批量检查...")
        
        if not os.path.exists(self.rules_dir):
            print(f"❌ 错误: 规则目录不存在 {self.rules_dir}")
            return {}
        
        batch_results = {}
        processed_keys = set()  # 防止重复执行
        
        # 读取所有规则文件（支持优先级排序）
        json_files = sorted([f for f in os.listdir(self.rules_dir) if f.endswith('.json')])
        
        print(f"📋 发现 {len(json_files)} 个规则文件\n")
        
        for file_name in json_files:
            try:
                with open(os.path.join(self.rules_dir, file_name), 'r', encoding='utf-8') as f:
                    task_group = json.load(f)
                
                # 遍历该规则文件中的所有任务
                for task_id, task_config in task_group.items():
                    task_key = task_config.get("key")
                    task_desc = task_config.get("desc")
                    script_path = task_config.get("script")
                    
                    # 校验配置完整性
                    if not task_key or not task_desc or not script_path:
                        print(f"⚠️  跳过不完整的任务配置: {task_id}")
                        continue
                    
                    # 防止重复执行
                    if task_key in processed_keys:
                        print(f"⏭️  跳过已执行的任务: {task_desc}")
                        continue
                    processed_keys.add(task_key)
                    
                    # 检查开关是否启用
                    if not INSPECTION_SWITCHES.get(task_key, False):
                        print(f"⏭️  禁用: {task_desc} (开关未启用)")
                        continue
                    
                    # 执行检查
                    print(f"正在检查: {task_desc}...")
                    try:
                        result = ScriptRunner.run(script_path, self.project_root, task_config)
                        
                        # 记录日志
                        self.logger.log_task(
                            name=task_desc,
                            success=result.get("success"),
                            message=result.get("message"),
                            expected=result.get("expected"),
                            actual=result.get("actual")
                        )
                        
                        # 输出结果
                        status_icon = "✅" if result.get("success") else "❌"
                        print(f"   {status_icon} {result.get('message')}")
                        
                        batch_results[task_desc] = result
                    
                    except Exception as e:
                        print(f"   ❌ 执行异常: {str(e)}")
                        self.logger.log_error(f"{task_desc} 崩溃: {str(e)}")
                    
                    # 任务间隔
                    if RETRY_INTERVAL > 0:
                        time.sleep(RETRY_INTERVAL)
            
            except json.JSONDecodeError as e:
                print(f"❌ 规则文件 JSON 格式错误: {file_name} - {str(e)}")
                continue
            except Exception as e:
                print(f"❌ 处理规则文件失败: {file_name} - {str(e)}")
                continue
        
        # 返回汇总结果
        print(f"\n✅ 批量检查完成，共处理 {len(batch_results)} 个任务")
        return {"巡检汇总报告": batch_results}
