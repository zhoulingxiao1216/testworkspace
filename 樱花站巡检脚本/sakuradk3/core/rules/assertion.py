# -*- coding: utf-8 -*-
# core/rules/assertion.py
import os
import json
import re
from core.path_manager import RULES_DIR  # 引用统一路径

def _smart_compare(actual, expected):
    """智能比较：支持数字与字符串的自动转换"""
    if actual is None:
        return expected is None
    # 如果类型相同，直接比较
    if type(actual) == type(expected):
        return actual == expected
    # 尝试转换为字符串比较
    if str(actual) == str(expected):
        return True
    # 尝试数字比较（如果两者都可以转换为数字）
    try:
        actual_num = float(actual) if isinstance(actual, (int, float, str)) else None
        expected_num = float(expected) if isinstance(expected, (int, float, str)) else None
        if actual_num is not None and expected_num is not None:
            return actual_num == expected_num
    except (ValueError, TypeError):
        pass
    return False

class AssertionTool:
    @staticmethod
    def get_rules_dynamically(task_key, root_path=None):
        """约定逻辑：JSON文件名 = 任务Key"""
        if not task_key: return None
        # 直接使用 path_manager 定义的 RULES_DIR
        rule_file = os.path.join(RULES_DIR, f"{task_key}.json")
        if os.path.exists(rule_file):
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return None
        return None

    @staticmethod
    def verify_api_common(response, rules=None):
        # 1. 校验 HTTP 状态码
        expected_http = rules.get("status_code", 200) if rules else 200
        if response.status_code != expected_http:
            return {
                "success": False, 
                "message": f"HTTP状态异常: {response.status_code}",
                "expected": f"Status Code: {expected_http}",
                "actual": f"Status Code: {response.status_code}"
            }

        try:
            res_text = response.text.strip()
            
            # 空响应检查（包括只有空白字符或极短响应）
            if not res_text or len(res_text) < 3:
                actual_content = repr(res_text) if res_text else "(空响应)"
                return {
                    "success": False,
                    "message": f"响应为空或过短（长度: {len(res_text)}）",
                    "expected": "Non-empty response with valid JSONP/JSON",
                    "actual": f"响应内容: {actual_content} | 状态码: {response.status_code}"
                }
            
            # 处理 JSONP 格式：flightHandler1({...json...})
            if "(" in res_text and res_text.endswith(")"):
                # 提取括号内的 JSON 内容（支持多行）
                match = re.search(r'\((\{.*\}|\[.*\])\)', res_text, re.S | re.M)
                if match:
                    json_str = match.group(1).strip()
                    if not json_str or json_str in ['{}', '[]', '']:
                        return {
                            "success": False,
                            "message": "JSONP回调内容为空",
                            "expected": "Valid JSONP format with non-empty JSON content",
                            "actual": f"响应内容: {repr(res_text)} | 状态码: {response.status_code}"
                        }
                    try:
                        res_data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        # JSONP 解析失败，返回详细错误
                        return {
                            "success": False,
                            "message": f"JSONP解析失败: {str(e)}",
                            "expected": "Valid JSONP format (callback({...json...}))",
                            "actual": f"响应内容: {repr(res_text[:200])} | JSON片段: {repr(json_str[:100])}"
                        }
                else:
                    # 正则匹配失败，可能是空回调如 "flightHandler1()"
                    if res_text.strip() in ['()', 'flightHandler1()', 'callback()']:
                        return {
                            "success": False,
                            "message": "JSONP回调为空（可能是token无效或参数错误）",
                            "expected": "Valid JSONP format with JSON content",
                            "actual": f"响应内容: {repr(res_text)} | 状态码: {response.status_code}"
                        }
                    # 尝试直接解析 JSON
                    try:
                        res_data = response.json()
                    except json.JSONDecodeError as json_err:
                        return {
                            "success": False,
                            "message": f"无法解析JSONP或JSON格式: {str(json_err)}",
                            "expected": "Valid JSONP (callback({...})) or JSON format",
                            "actual": f"响应内容: {repr(res_text[:300])} | 状态码: {response.status_code}"
                        }
            else:
                # 普通 JSON 格式
                res_data = response.json()

            # 2. 校验业务逻辑 (JSON 字段匹配)
            if rules and "json_match" in rules:
                for k, v in rules["json_match"].items():
                    # 尝试从顶层取，如果取不到，尝试从 data 层取
                    actual_v = res_data.get(k)
                    if actual_v is None and "data" in res_data and isinstance(res_data["data"], dict):
                        actual_v = res_data["data"].get(k)
                    
                    expected_list = v if isinstance(v, list) else [v]
                    matched = any(_smart_compare(actual_v, x) for x in expected_list)
                    
                    # 关键修改：在 matched 为 False 时打印完整 JSON
                    if not matched:
                        # 获取完整 JSON 字符串，方便你分析 2 到底是什么意思
                        full_response = json.dumps(res_data, ensure_ascii=False)
                        return {
                            "success": False, 
                            "message": f"字段匹配失败: {k} (实际值: {actual_v}) | 完整响应: {full_response}",
                            "expected": f"{k} == {v}",
                            "actual": full_response  # 这里直接输出完整内容
                        }
            
            # 3. 校验关键字
            if rules and "must_contain" in rules:
                for target in rules["must_contain"]:
                    if target not in str(res_data):
                        return {
                            "success": False, 
                            "message": f"缺失关键字: {target}",
                            "expected": f"Must contain: {target}",
                            "actual": "Keyword not found"
                        }

            return {"success": True, "message": "校验通过", "expected": "PASS", "actual": "PASS"}
        except Exception as e:
            return {"success": False, "message": f"解析失败: {str(e)}", "expected": "JSON", "actual": "Non-JSON"}