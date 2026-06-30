# -*- coding: utf-8 -*-
# d:\sakuradk3\core\validator.py
import json
import re
from typing import Optional
from core.logger import InspectorLogger


class Validator:
    """响应校验器：支持 HTML 标题和 JSON 字段校验"""
    
    def __init__(self, logger: Optional[InspectorLogger] = None):
        """
        初始化校验器
        
        Args:
            logger: InspectorLogger 实例（可选）。如果不传，则只校验不记录日志。
        """
        self.logger = logger
    
    def validate(self, response, rules: dict, task_name: str, url: str = None):
        """
        校验响应内容
        """
        result = {
            "success": False,
            "message": "",
            "expected": None,
            "actual": None,
            "status_code": getattr(response, 'status_code', 0)
        }
        
        # 获取响应内容
        try:
            response_text = response.text if hasattr(response, 'text') else str(response)
            content_type = response.headers.get('Content-Type', '').lower() if hasattr(response, 'headers') else ''
        except Exception as e:
            result["message"] = f"无法读取响应内容: {str(e)}"
            self._log_result(result, task_name, url)
            return result
        
        # 1. 校验 HTTP 状态码
        expected_status = rules.get('status_code', 200)
        actual_status = getattr(response, 'status_code', 0)
        
        if actual_status != expected_status:
            result["message"] = f"HTTP 状态码不匹配: 期望 {expected_status}, 实际 {actual_status}"
            result["expected"] = f"status_code={expected_status}"
            result["actual"] = f"status_code={actual_status}"
            self._log_result(result, task_name, url)
            return result
        
        # 2. 校验 HTML 标题
        if 'title_contains' in rules:
            title_check = self._validate_title(response_text, rules['title_contains'])
            if not title_check['success']:
                result["message"] = title_check['message']
                result["expected"] = title_check.get('expected')
                result["actual"] = title_check.get('actual')
                self._log_result(result, task_name, url)
                return result
        
        # 3. 校验 JSON 响应
        if 'application/json' in content_type or any(k in rules for k in ['json_code', 'json_has_data', 'json_field', 'json_field_exists']):
            json_check = self._validate_json(response_text, rules)
            if not json_check['success']:
                result["message"] = json_check['message']
                result["expected"] = json_check.get('expected')
                result["actual"] = json_check.get('actual')
                self._log_result(result, task_name, url)
                return result
        
        # 所有校验通过
        result["success"] = True
        result["message"] = "校验通过"
        self._log_result(result, task_name, url)
        return result
    
    def _validate_title(self, html_content: str, title_rule):
        # ... (此部分逻辑保持不变)
        result = {"success": False, "message": "", "expected": None, "actual": None}
        try:
            title_pattern = r'<title[^>]*>(.*?)</title>'
            match = re.search(title_pattern, html_content, re.IGNORECASE | re.DOTALL)
            if not match:
                result["message"] = "HTML 中未找到 <title> 标签"
                result["expected"] = f"title 应包含: {title_rule}"
                result["actual"] = "未找到 title 标签"
                return result
            
            title_text = match.group(1)
            title_text = re.sub(r'<[^>]+>', '', title_text)
            actual_title = title_text.strip()
            
            if isinstance(title_rule, list):
                found = any(title in actual_title for title in title_rule)
                if not found:
                    result["message"] = f"标题不包含任何期望的文本: {title_rule}"
                    result["expected"] = f"title 应包含以下之一: {title_rule}"
                    result["actual"] = f"实际标题: {actual_title}"
                    return result
            else:
                if title_rule not in actual_title:
                    result["message"] = f"标题不包含期望的文本: {title_rule}"
                    result["expected"] = f"title 应包含: {title_rule}"
                    result["actual"] = f"实际标题: {actual_title}"
                    return result
            
            result["success"] = True
            return result
        except Exception as e:
            result["message"] = f"解析 HTML 标题时出错: {str(e)}"
            return result

    def _validate_json(self, response_text: str, rules: dict):
        # ... (此部分逻辑保持不变)
        result = {"success": False, "message": "", "expected": None, "actual": None}
        try:
            try:
                response_json = json.loads(response_text)
            except json.JSONDecodeError as e:
                result["message"] = f"响应不是有效的 JSON: {str(e)}"
                return result
            
            if 'json_code' in rules:
                expected_code = rules['json_code']
                actual_code = response_json.get('code')
                if actual_code != expected_code:
                    result["message"] = f"JSON code 字段不匹配: 期望 {expected_code}, 实际 {actual_code}"
                    result["expected"] = f"code={expected_code}"
                    result["actual"] = f"code={actual_code}"
                    return result
            
            # ... (json_has_data, json_field 等其余逻辑保持不变)
            result["success"] = True
            return result
        except Exception as e:
            result["message"] = f"校验 JSON 时出错: {str(e)}"
            return result
    
    def _get_nested_value(self, data: dict, field_path: str):
        keys = field_path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _log_result(self, result: dict, task_name: str, url: str = None):
        """
        记录校验结果到日志（增加防御性判断）
        """
        # 核心修改：只有存在 logger 且其拥有 log_task 方法时才调用
        if self.logger and hasattr(self.logger, 'log_task'):
            self.logger.log_task(
                name=task_name,
                success=result["success"],
                message=result["message"],
                url=url,
                status_code=result.get("status_code"),
                expected=result.get("expected"),
                actual=result.get("actual")
            )