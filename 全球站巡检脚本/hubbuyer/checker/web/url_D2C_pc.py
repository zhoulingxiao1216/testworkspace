# -*- coding: utf-8 -*-
#五、checker/web/url_D2C_pc.py 修改断言逻辑
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
except ImportError as e:
    print(json.dumps({"success": False, "message": f"导入失败: {str(e)}"}, ensure_ascii=False))
    sys.exit(1)

def run(config, logger=None):
    """
    执行 D2C PC 站点的巡检逻辑
    """
    url = config.get("url")
    task_name = config.get("desc") or "D2C_PC站点巡检"
    rules = config.get("rules", {"status_code": 200})

    if not url:
        return {"success": False, "message": "URL缺失", "url": None}

    try:
        headers = {'User-Agent': 'Mozilla/5.0 Sakuradk2-Inspector/1.0'}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_WEB, verify=False, proxies={'http': None, 'https': None})
        response.encoding = response.apparent_encoding 
        
        # 传入可选的 logger
        validator = Validator(logger)
        result = validator.validate(response, rules, task_name, url)
        
        result["env"] = ENV_TYPE
        result["url"] = url
        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"访问崩溃: {type(e).__name__}",
            "url": url,
            "env": ENV_TYPE
        }

def main():
    script_name = os.path.basename(__file__).replace(".py", "")
    is_batch = len(sys.argv) > 1

    if is_batch:
        # A. 批量模式
        try:
            config = json.loads(sys.argv[1])
        except:
            config = {}
        result = run(config, logger=None)
    else:
        # B. 手动模式
        manual_logger = InspectorLogger()
        json_path = os.path.join(root_path, "config", "rules", "web_rules.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                all_rules = json.load(f)
            config = all_rules.get(script_name, {})
            if config:
                config["url"] = API_CONFIG.get(script_name)
                config["desc"] = f"手动测试_{script_name}"
            else:
                config = {"message": f"在web_rules.json中找不到键值: {script_name}"}
        else:
            config = {"message": "找不到 web_rules.json"}
            
        result = run(config, logger=manual_logger)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
