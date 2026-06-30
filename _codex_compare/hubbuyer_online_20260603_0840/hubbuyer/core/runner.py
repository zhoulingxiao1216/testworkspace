# -*- coding: utf-8 -*-
# d:\hubbuyer\core\runner.py

import subprocess
import sys
import os
import json
from config.settings import SCRIPT_RUNNER_TIMEOUT

class ScriptRunner:
    """底层工具类：纯粹负责执行子脚本并捕获其 JSON 输出"""
    
    @staticmethod
    def run(script_relative_path, project_root, task_config):
        """
        核心修正：增加第3个参数 task_config
        """
        script_abs_path = os.path.join(project_root, script_relative_path)
        
        # 预设返回结构
        response = {"success": False, "message": "", "status_code": 500}

        if not os.path.exists(script_abs_path):
            response["message"] = f"脚本不存在: {script_relative_path}"
            return response

        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8' # 强制 UTF-8 编码

            # --- 【核心新增】 ---
            # 将 task_config 序列化为字符串，以便通过命令行参数传给子脚本
            config_json_str = json.dumps(task_config, ensure_ascii=False)

            # 执行子进程：使用最原始的兼容性写法
            process = subprocess.run(
                [sys.executable, script_abs_path, config_json_str], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                # 不再使用 text=True，改用 universal_newlines=True
                universal_newlines=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=SCRIPT_RUNNER_TIMEOUT, 
                cwd=project_root, 
                env=env
            )

            stdout_data = process.stdout.strip()
            
            # 只有当脚本正常退出且有输出时才尝试解析 JSON
            if process.returncode == 0 and stdout_data:
                try:
                    # 获取输出的最后一行（防止子脚本中有其他 print 干扰）
                    last_line = stdout_data.split('\n')[-1]
                    parsed_data = json.loads(last_line)
                    
                    response["success"] = parsed_data.get("success", False)
                    response["message"] = parsed_data.get("message", "执行成功")
                    response["status_code"] = parsed_data.get("status_code", 200 if response["success"] else 500)
                    # 提取 validator 相关的字段
                    response["expected"] = parsed_data.get("expected")
                    response["actual"] = parsed_data.get("actual")
                except json.JSONDecodeError:
                    response["message"] = f"输出非合法JSON: {stdout_data[:50]}..."
            else:
                # 抓取脚本报错信息 (stderr)
                response["message"] = process.stderr.strip() or f"脚本异常退出(Code:{process.returncode})"

        except subprocess.TimeoutExpired:
            response["message"] = f"执行超时({SCRIPT_RUNNER_TIMEOUT}s)"
        except Exception as e:
            response["message"] = f"Runner内部异常: {str(e)}"

        return response