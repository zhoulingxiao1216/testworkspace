# -*- coding: utf-8 -*-
# batch_checker.py
import os
import time
import json
from core.runner import ScriptRunner
# --- 1：从 settings 导入 INSPECTION_INTERVAL ---
from config.settings import INSPECTION_SWITCHES, ENV_TYPE, API_CONFIG, INSPECTION_INTERVAL 
from core.logger import InspectorLogger

class BatchChecker:
    # --- 增加 logger_instance 参数 ---
    def __init__(self, logger_instance=None):
        self.results = {}
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rules_dir = os.path.join(self.project_root, "config", "rules")
        
        # --- 优先使用传入的实例，避免重复创建 ---
        self.logger = logger_instance if logger_instance else InspectorLogger()

    # --- 确保 run_all_checks 在类内部 ---
    def run_all_checks(self):
        print(f"\n🚀 启动全局动态巡检 | 环境: {ENV_TYPE}")
        
        if not os.path.exists(self.rules_dir):
            print(f"❌ 错误: 找不到配置目录 {self.rules_dir}")
            return {}

        # 按業務優先順序執行：web -> login -> 圖搜 -> 其他
        priority = ["web_rules.json", "login_rules.json", "img_search.json","keyword_search.json","d2c_keyword_search.json","add_cart.json","B2B_Addon.json","D2C_Addon.json","submit_order.json","payment.json"]
        json_files = [f for f in os.listdir(self.rules_dir) if f.endswith('.json')]
        json_files.sort(key=lambda x: (priority.index(x) if x in priority else len(priority), x))
        batch_results = {}
        processed_keys = set()  # 用于确保每个 Key 在整场巡检中只出现一次

        for file_name in json_files:
            print(f"\n📂 开始处理规则文件: {file_name}")  # 调试：文件加载
            try:
                with open(os.path.join(self.rules_dir, file_name), 'r', encoding='utf-8') as f:
                    task_group = json.load(f)
                print(f"   ✓ 成功加载 {len(task_group)} 个任务配置")  # 调试：确认加载成功
                
                for site_id, task_config in task_group.items():
                    task_key = task_config.get("key")
                    task_desc = task_config.get("desc")
                    
                    # --- 0. 验证任务配置完整性（跳过非任务配置项，如规则定义） ---
                    if not task_key or not task_desc:
                        # 跳过非任务配置项（如 B2B_img, D2C_img 等规则定义）
                        continue
                    
                    # --- 1. 唯一性拦截 ---
                    if task_key in processed_keys:
                        continue
                    
                    # 只要 Key 还没处理过，无论开关如何，先占位
                    processed_keys.add(task_key)

                    # --- 2. 检查开关 ---
                    if INSPECTION_SWITCHES.get(task_key, False):
                        # 动态注入 URL
                        task_config["url"] = API_CONFIG.get(site_id)
                        script_path = task_config.get("script")

                        # --- 移除了此处原本死板的 if batch_results: sleep(5) ---
                        
                        print(f"正在检查: {task_desc}...")

                        try:
                            # 执行并记录
                            result = ScriptRunner.run(script_path, self.project_root, task_config)
                            
                            self.logger.log_task(
                                name=task_desc,
                                success=result.get("success", False),
                                message=result.get("message", "未知错误"),
                                url=task_config.get("url"),
                                status_code=result.get("status_code"), 
                                expected=result.get("expected"),
                                actual=result.get("actual")
                            )

                            status_icon = "✅" if result.get("success") else "❌"
                            print(f"   {status_icon} 结论: {result.get('message')}")
                            
                            batch_results[task_desc] = {
                                "success": result.get("success"),
                                "message": result.get("message"),
                                "url": task_config.get("url"),
                                "status_code": result.get("status_code", 0),
                                "expected": result.get("expected"),
                                "actual": result.get("actual")
                            }
                        except Exception as e:
                            self.logger.log_error(f"{task_desc} 崩溃: {str(e)}")
                            print(f"   ❌ 结论: 执行异常")

                        # ---  3：统一在任务执行完（无论成功失败）后固定等待 ---
                        if INSPECTION_INTERVAL > 0:
                            time.sleep(INSPECTION_INTERVAL)
                        # # ---  3: 实现随机等待逻辑 ---
                        # min_sleep, max_sleep = INSPECTION_INTERVAL_RANGE
                        # wait_time = random.uniform(min_sleep, max_sleep)
                        # # print(f"   ⏳ 随机等待 {wait_time:.1f} 秒...") # 可选：打印等待时间
                        # time.sleep(wait_time)

                    else:
                        # PC 巡检因为关闭了，会走到这里
                        print(f"⏭️  跳过: {task_desc} (已关闭)")

            except Exception as e:
                import traceback
                print(f"   ❌ 处理文件 {file_name} 出错: {str(e)}")
                traceback.print_exc()  # 打印完整的错误堆栈
                self.logger.log_error(f"处理文件 {file_name} 异常: {str(e)}\n{traceback.format_exc()}")

        print(f"\n✅ 巡检完成 | 共收集 {len(batch_results)} 个任务结果")
        self.results = {"巡检汇总报告": batch_results}
        return self.results