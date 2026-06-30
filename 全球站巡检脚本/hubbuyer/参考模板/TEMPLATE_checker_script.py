# -*- coding: utf-8 -*-
"""
通用模板：检查脚本

职责：执行具体的检查逻辑，返回 JSON 格式结果

返回格式必须是：
{
    "success": true/false,
    "message": "检查结果描述",
    "status_code": 200 或其他状态码,
    "expected": "预期值",
    "actual": "实际值"
}
"""

import json
import sys
import os

# ========== 路径初始化（必须在 import 之前）==========
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# ========== 导入配置（导入顺序很重要）==========
try:
    from config.settings import BASE_URL, TIMEOUT, ENV_TYPE
except ImportError:
    BASE_URL = "http://localhost"
    TIMEOUT = 10
    ENV_TYPE = "dev"

def check_something(task_config=None):
    """
    具体检查逻辑
    
    Args:
        task_config: BatchChecker 传入的任务配置字典
    
    Returns:
        dict: 包含 success, message, status_code, expected, actual 的结果
    """
    
    # 初始化结果字典
    result = {
        "success": False,
        "message": "未知错误",
        "status_code": 500,
        "expected": "预期结果",
        "actual": ""
    }
    
    try:
        # ========== 业务逻辑（自己修改这部分）==========
        
        # 1. 从 task_config 中获取参数
        target = task_config.get("target") if task_config else "default"
        rules = task_config.get("rules", {}) if task_config else {}
        
        # 2. 执行检查（示例：模拟 HTTP 请求）
        import requests
        
        url = f"{BASE_URL}/api/health"
        response = requests.get(url, timeout=TIMEOUT)
        response_json = response.json()
        
        # 3. 验证结果
        expected_status = rules.get("status_code", 200)
        actual_status = response.status_code
        
        if actual_status == expected_status:
            result["success"] = True
            result["message"] = f"检查通过 (状态码: {actual_status})"
            result["status_code"] = 200
            result["expected"] = f"状态码 = {expected_status}"
            result["actual"] = f"状态码 = {actual_status}"
        else:
            result["message"] = f"状态码不匹配: 期望 {expected_status}，实际 {actual_status}"
            result["expected"] = f"状态码 = {expected_status}"
            result["actual"] = f"状态码 = {actual_status}"
        
        # ========== 异常处理 ==========
    
    except requests.Timeout:
        result["message"] = f"请求超时 (>{TIMEOUT}s)"
        result["actual"] = f"超时"
    
    except requests.ConnectionError:
        result["message"] = "连接失败"
        result["actual"] = "无响应"
    
    except json.JSONDecodeError:
        result["message"] = "响应不是有效的 JSON"
        result["actual"] = "JSON 解析失败"
    
    except Exception as e:
        result["message"] = f"检查异常: {str(e)}"
        result["actual"] = repr(e)
    
    # ========== 输出结果（重要：必须是 JSON，且是最后一行）==========
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    # 支持从命令行接收任务配置（由 runner.py 传入）
    task_config = None
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
        except Exception as e:
            print(f"警告: 无法解析命令行参数: {e}", file=sys.stderr)
    
    check_something(task_config)
