# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\web\url_B2B_h5.py

#五、 url_B2B_h5.py 修改断言逻辑
import requests
import sys
import json
import os

# --- 1. 动态定位项目根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# --- 2. 导入核心组件 ---
try:
    from config.settings import API_CONFIG, ENV_TYPE, REQUEST_TIMEOUT_WEB
    from core.rules.validator import Validator
    from core.logger import InspectorLogger
    from core.rules.assertion import AssertionTool
except ImportError as e:
    print(json.dumps({"success": False, "message": f"导入失败: {str(e)}"}, ensure_ascii=False))
    sys.exit(1)

def run(config, logger=None):
    """
    核心执行逻辑
    :param config: 配置字典
    :param logger: 如果传入 logger，则会记录日志；不传则只返回结果
    """
    url = config.get("url")
    task_name = config.get("desc") or "B2B_H5站点巡检"
    rules = config.get("rules", {})

    if not url:
        return {"success": False, "message": "URL缺失，请检查配置", "url": None}

    try:
        # 执行请求
        response = requests.get(url, timeout=REQUEST_TIMEOUT_WEB, verify=False, proxies={'http': None, 'https': None})
        response.encoding = response.apparent_encoding 
        
        # 实例化校验器
        # 如果有传入 logger (手动模式)，validator 内部会记录日志
        # 如果 logger 为 None (批量模式)，validator 只返回校验字典
        validator = Validator(logger)
        
        # 调用标准化校验
        result = validator.validate(response, rules, task_name, url)
        
        result["env"] = ENV_TYPE
        result["url"] = url
        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"访问崩溃: {str(e)}",
            "url": url,
            "env": ENV_TYPE
        }

def main():
    script_key = os.path.basename(__file__).replace(".py", "")
    is_batch = len(sys.argv) > 1  # 判断是否为批量调用

    if is_batch:
        # --- 情况 A: BatchChecker 批量调用 ---
        try:
            config = json.loads(sys.argv[1])
        except:
            config = {}
        # 批量模式下，run 不传 logger，避免重复记录
        result = run(config, logger=None)
    else:
        # --- 情况 B: 手动右键调试 ---
        config = {}
        config["url"] = API_CONFIG.get(script_key)
        config["desc"] = f"手动测试_{script_key}"

        json_path = os.path.join(root_path, "config", "rules", "web_rules.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                web_rules_all = json.load(f)
                config["rules"] = web_rules_all.get(script_key, {}).get("rules", {})

        if config.get("url"):
            # 手动模式下，实例化 logger 并传入，这样控制台能看到日志
            manual_logger = InspectorLogger()
            result = run(config, logger=manual_logger)
        else:
            result = {"success": False, "message": f"无法获取URL，请检查API_CONFIG。Key: {script_key}"}

    # 统一输出给父进程或控制台
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()