# -*- coding: utf-8 -*-
"""
规则加载器
动态读取 config/rules/*.json 中的断言规则和性能阈值
参照巡检系统 core/rules/assertion.py 的设计
"""
import os
import json

from config.settings import RULES_DIR


def load_rules(api_name):
    """
    加载指定接口的规则文件
    
    Args:
        api_name: 接口名称（对应 config/rules/{api_name}.json）
    
    Returns:
        dict: 规则配置，若文件不存在则返回空字典
    """
    rules_file = os.path.join(RULES_DIR, f"{api_name}.json")
    if not os.path.exists(rules_file):
        return {}
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_assertion_rules(api_name, task_key=None):
    """
    获取指定接口的断言规则
    
    Args:
        api_name: 接口名称
        task_key: 规则文件中的具体任务 key（如 "B2B_1688_keyword"）
    
    Returns:
        dict: {"status_code": 200, "json_match": {"code": 200}} 等
    """
    all_rules = load_rules(api_name)
    if task_key and task_key in all_rules:
        return all_rules[task_key].get("rules", {})
    # 默认取第一个包含 rules 的配置
    for key, val in all_rules.items():
        if isinstance(val, dict) and "rules" in val:
            return val.get("rules", {})
    return {}


def get_performance_threshold(api_name, task_key=None):
    """
    获取指定接口的性能阈值（毫秒）
    
    Args:
        api_name: 接口名称
        task_key: 具体任务 key
    
    Returns:
        int: 阈值毫秒数，默认 5000ms
    """
    all_rules = load_rules(api_name)
    if task_key and task_key in all_rules:
        return all_rules[task_key].get("performance", {}).get("threshold_ms", 5000)
    for key, val in all_rules.items():
        if isinstance(val, dict) and "performance" in val:
            return val.get("performance", {}).get("threshold_ms", 5000)
    return 5000


def extract_response_detail(response_json, max_len=200):
    """从响应体提取可读错误详情（msg/message 等）。"""
    if not isinstance(response_json, dict):
        return ""

    for key in ("msg", "message", "error", "errMsg", "err_msg", "desc", "description"):
        value = response_json.get(key)
        if value not in (None, ""):
            return str(value)[:max_len]

    data = response_json.get("data")
    if isinstance(data, dict):
        for key in ("msg", "message", "error", "errMsg", "err_msg"):
            value = data.get(key)
            if value not in (None, ""):
                return str(value)[:max_len]
    elif isinstance(data, str) and data.strip():
        return data.strip()[:max_len]

    return ""


def verify_response(response_json, rules):
    """
    基于规则校验 API 响应
    
    Args:
        response_json: 已解析的 JSON 响应体
        rules: 断言规则字典 {"json_match": {"code": 200}}
    
    Returns:
        tuple: (success: bool, error_msg: str)
    """
    detail = extract_response_detail(response_json)

    if not rules:
        # 无规则时，默认检查 code == 200
        code = response_json.get("code") or response_json.get("status")
        if code == 200:
            return True, ""
        err = f"业务码: {code}"
        if detail:
            err = f"{err} | {detail}"
        return False, err

    json_match = rules.get("json_match", {})
    for field, expected in json_match.items():
        actual = response_json.get(field)
        if actual != expected:
            err = f"{field}期望{expected},实际{actual}"
            if detail:
                err = f"{err} | {detail}"
            return False, err

    return True, ""


def verify_download_response(response, rules):
    """
    基于规则校验文件下载响应（非 JSON）。

    Args:
        response: requests.Response
        rules: {"status_code": 200, "min_response_bytes": 1024, ...}

    Returns:
        tuple: (success: bool, error_msg: str)
    """
    if not rules:
        if response.status_code == 200 and len(response.content) > 0:
            return True, ""
        return False, f"HTTP {response.status_code}"

    expected_status = rules.get("status_code", 200)
    if response.status_code != expected_status:
        return False, f"HTTP {response.status_code}"

    min_bytes = rules.get("min_response_bytes")
    if min_bytes is not None and len(response.content) < int(min_bytes):
        return False, f"响应体过小({len(response.content)}B < {min_bytes}B)"

    disposition_needle = rules.get("content_disposition_contains")
    if disposition_needle:
        disposition = response.headers.get("Content-Disposition", "")
        if disposition_needle.lower() not in disposition.lower():
            return False, f"Content-Disposition 未含『{disposition_needle}』"

    content_type_needle = rules.get("content_type_contains")
    if content_type_needle:
        content_type = response.headers.get("Content-Type", "")
        if content_type_needle.lower() not in content_type.lower():
            return False, f"Content-Type 未含『{content_type_needle}』"

    return True, ""
