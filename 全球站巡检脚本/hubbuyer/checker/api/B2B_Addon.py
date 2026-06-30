# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\B2B_Addon.py
import json
import os
import sys
import random
import requests
import traceback
import urllib3
from datetime import datetime

# 禁用 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 定位根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_b2b_headers
# ==========================================
# 辅助函数
# ==========================================

def get_current_date_str():
    """获取当前日期字符串，格式：YYYY.M.D"""
    now = datetime.now()
    return f"{now.year}.{now.month}.{now.day}"

def emit_result(final_result):
    """输出 runner 可解析的最终 JSON，并返回原结果。"""
    print(json.dumps(final_result, ensure_ascii=False), flush=True)
    return final_result

def load_addon_payloads():
    """加载附加项请求参数"""
    payload_path = os.path.join(DATA_DIR, "B2B_Addon.json")
    if not os.path.exists(payload_path):
        raise FileNotFoundError(f"未找到核心数据文件: {payload_path}")
    with open(payload_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_fjx_ids():
    """加载检品方式ID配置"""
    fjx_path = os.path.join(DATA_DIR, "B2B_Addon_fjxid.json")
    if not os.path.exists(fjx_path):
        raise FileNotFoundError(f"未找到检品方式配置文件: {fjx_path}")
    with open(fjx_path, "r", encoding="utf-8") as f:
        return json.load(f)

def _is_enabled_uuid_item(item):
    """判断新版附加项列表里的配置是否可用于保存。"""
    return isinstance(item, dict) and item.get("uuid") and item.get("status", 200) == 200

def _language_text(value):
    """把新版配置里的多语言字段合并成便于关键词匹配的文本。"""
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if isinstance(v, (str, int, float)))
    if isinstance(value, list):
        return " ".join(_language_text(item) for item in value)
    return str(value or "")

def _item_search_text(group, item):
    fields = [
        group.get("name_language"),
        item.get("name_language"),
        item.get("tip_language"),
        item.get("before_language"),
        item.get("after_language"),
    ]
    return " ".join(_language_text(field) for field in fields).lower()

def _pick_first_matching_uuid(groups, keyword_groups):
    for keywords in keyword_groups:
        for group in groups:
            for item in group.get("fjx_config_data", []):
                if not _is_enabled_uuid_item(item):
                    continue
                text = _item_search_text(group, item)
                if all(keyword.lower() in text for keyword in keywords):
                    return item["uuid"]
    return None

def get_runtime_fjx_selection(base_url, endpoints, headers):
    """
    全球站改版后，检品/附加项 UUID 由 fjx iframe 实时列表提供。
    旧静态 C25/F25 清单可能已下架，直接保存会被后端判定为未选择检品。
    """
    list_path = endpoints.get("B2B_Addon_CheckFjxList") or "/api_b2b/cartQuoteStep1/getCheckFjxList"
    response = requests.post(
        f"{base_url}{list_path}",
        json={},
        headers=headers,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={'http': None, 'https': None}
    )
    check = AssertionTool.verify_api_common(response)
    if not check["success"]:
        raise RuntimeError(f"获取新版附加项列表失败: {check.get('message', '未知错误')}")

    data = response.json().get("data", {})
    check_items = [item for item in data.get("check_data", []) if _is_enabled_uuid_item(item)]
    if not check_items:
        raise RuntimeError("新版附加项列表无可用检品 UUID")

    groups = data.get("fjx_data", [])
    selected_fjx = []
    # 普通可选附加项只选择新版列表中明确存在的非设计项；吊牌/FBA/洗标等设计项由各自保存接口写入。
    preferred_uuid_rules = [
        [["贴纸"], ["sticker"]],
        [["fba"], ["opp", "四角"], ["4-fold"]],
    ]
    for keyword_groups in preferred_uuid_rules:
        uuid = _pick_first_matching_uuid(groups, keyword_groups)
        if uuid and uuid not in selected_fjx:
            selected_fjx.append(uuid)

    if not selected_fjx:
        for group in groups:
            for item in group.get("fjx_config_data", []):
                if _is_enabled_uuid_item(item) and not item.get("is_design"):
                    selected_fjx.append(item["uuid"])
                    break
            if selected_fjx:
                break

    return check_items[0]["uuid"], selected_fjx, []

def load_or_create_id_mapping():
    """加载或创建邮箱-ID映射文件"""
    id_file = os.path.join(DATA_DIR, "B2B_Addon_id.json")
    if os.path.exists(id_file):
        try:
            with open(id_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_id_mapping(mapping):
    """保存邮箱-ID映射"""
    id_file = os.path.join(DATA_DIR, "B2B_Addon_id.json")
    with open(id_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def get_random_fjx_ids(fjx_config):
    """随机获取检品方式ID（设计类随机1-4个 + 普通随机2-5个）"""
    # 设计类：随机取1-4个
    design_items = fjx_config.get("DESIGN_ITEMS", [])
    if design_items:
        # 随机选择1到min(4, len(design_items))个
        num_design = random.randint(1, min(4, len(design_items)))
        design_selected = random.sample(design_items, num_design)
    else:
        design_selected = []
    
    # 普通方式：随机取2-5个
    normal_items = fjx_config.get("NORMAL_ITEMS", [])
    if normal_items:
        # 随机选择2到min(5, len(normal_items))个
        num_normal = random.randint(2, min(5, len(normal_items)))
        normal_selected = random.sample(normal_items, num_normal)
    else:
        normal_selected = []
    
    # 合并所有选中的ID
    all_selected = design_selected + normal_selected
    return ",".join(map(str, all_selected))

def get_random_quality_fjx_id(fjx_config):
    """随机获取检品方式ID（固定取1个）"""
    quality_items = fjx_config.get("QUALITY_ITEMS", [])
    if quality_items:
        return random.choice(quality_items)
    return None

def get_random_additional_item(fjx_config):
    """获取AdditionalItem：设计类随机1-4个 + 普通随机2-5个，返回JSON字符串"""
    # 设计类：随机取1-4个
    design_items = fjx_config.get("DESIGN_ITEMS", [])
    if design_items:
        # 随机选择1到min(4, len(design_items))个
        num_design = random.randint(1, min(4, len(design_items)))
        design_selected = random.sample(design_items, num_design)
    else:
        design_selected = []
    
    # 普通方式：随机取2-5个
    normal_items = fjx_config.get("NORMAL_ITEMS", [])
    if normal_items:
        # 随机选择2到min(5, len(normal_items))个
        num_normal = random.randint(2, min(5, len(normal_items)))
        normal_selected = random.sample(normal_items, num_normal)
    else:
        normal_selected = []
    
    # 合并所有选中的ID
    all_additional = design_selected + normal_selected
    return json.dumps(all_additional)

def get_id_mapping_for_mail(target_mail):
    """获取指定邮箱的ID映射列表"""
    id_mapping = load_or_create_id_mapping()
    return id_mapping.get(target_mail, [])

def fill_payload_fields(base_payload, cart_id, iidsku_id, config_id, fjx_config, current_date):
    """
    根据字段名动态填充字段
    
    Args:
        base_payload: 从 B2B_Addon.json 读取的基础数据
        cart_id: 从 B2B_Addon_id.json 读取的 id
        iidsku_id: 从 B2B_Addon_id.json 读取的 iidsku_id
        config_id: 从 B2B_Addon_id.json 读取的 config_id（写死的值）
        fjx_config: 从 B2B_Addon_fjxid.json 读取的配置
        current_date: 当前日期字符串
    """
    filled_payload = base_payload.copy()
    
    # id、cart_id、cartId → 从 B2B_Addon_id.json 的 id
    if "id" in filled_payload:
        filled_payload["id"] = cart_id
    if "cart_id" in filled_payload:
        # 检查是否需要字符串类型
        if isinstance(filled_payload.get("cart_id"), str):
            filled_payload["cart_id"] = str(cart_id)
        else:
            filled_payload["cart_id"] = cart_id
    if "cartId" in filled_payload:
        filled_payload["cartId"] = cart_id
    # config_id → 从 B2B_Addon_id.json 读取的 config_id（写死的值）
    if "config_id" in filled_payload and config_id is not None:
        filled_payload["config_id"] = config_id
    
    # iidsku_id → 从 B2B_Addon_id.json 对应 id 下的 iidsku_id
    if "iidsku_id" in filled_payload:
        filled_payload["iidsku_id"] = iidsku_id
    
    # quality_fjx_id → 从 B2B_Addon_fjxid.json 的 QUALITY_ITEMS 随机选择
    if "quality_fjx_id" in filled_payload:
        filled_payload["quality_fjx_id"] = get_random_quality_fjx_id(fjx_config)
    
    # fjx_ids → 从 B2B_Addon_fjxid.json 的 DESIGN_ITEMS 和 NORMAL_ITEMS 随机组合
    if "fjx_ids" in filled_payload:
        filled_payload["fjx_ids"] = get_random_fjx_ids(fjx_config)
    
    # title → 当前日期（年月日格式）
    if "title" in filled_payload:
        filled_payload["title"] = current_date
    
    # a1 → 当前日期（年月日格式）
    if "a1" in filled_payload:
        filled_payload["a1"] = current_date
    
    # d1 → 当前日期 + "测试樱花站洗标"
    if "d1" in filled_payload:
        filled_payload["d1"] = f"{current_date}测试樱花站洗标"
    
    # AdditionalItem → 从 DESIGN_ITEMS 随机2个 + NORMAL_ITEMS 随机1个
    if "AdditionalItem" in filled_payload:
        filled_payload["AdditionalItem"] = get_random_additional_item(fjx_config)
    
    # jpRadioItem → 从 QUALITY_ITEMS 随机选择
    if "jpRadioItem" in filled_payload:
        quality_items = fjx_config.get("QUALITY_ITEMS", [])
        filled_payload["jpRadioItem"] = random.choice(quality_items) if quality_items else None
    
    return filled_payload

# ==========================================
# 主运行逻辑
# ==========================================

def run(task_config=None):
    """B2B购物车附加项流程执行器"""
    results_status, msgs = {}, []
    stored_ids = []  # 存储的ID列表
    error_details = []  # 收集步骤2-7的错误信息（到FBA）
    
    try:
        # 1. 加载配置与数据
        addon_payloads = load_addon_payloads()
        all_rules = AssertionTool.get_rules_dynamically("B2B_Addon", root_path)
        
        # 获取登录账号（从规则或配置中获取）
        target_mail = ""
        if all_rules and isinstance(all_rules.get("B2B_Addon_task"), dict):
            target_mail = all_rules["B2B_Addon_task"].get("login_account", "").strip()
        if not target_mail and task_config:
            target_mail = task_config.get("login_account", "").strip()
        # 如果配置文件中都没有设置，使用默认值（保持向后兼容）
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"  # 默认值（建议在 B2B_Addon.json 中配置 login_account）
        
        # 获取当前日期字符串
        current_date = get_current_date_str()
        
        # 2. 获取 Token 和 Cookie
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        b2b_token = ""
        tokens_data = {}
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    tokens_data = json.load(f)
                    b2b_token = tokens_data.get(target_mail, "") or tokens_data.get(target_mail.lower(), "")
                    if not b2b_token:
                        for key, val in tokens_data.items():
                            if key.strip() == target_mail.strip():
                                b2b_token = val
                                target_mail = key  # 更新为实际匹配到的账号
                                break
                    
                    # 如果配置的账号找不到 token，使用 current_tokens.json 中的第一个账号作为 fallback
                    if not b2b_token and tokens_data:
                        target_mail = list(tokens_data.keys())[0]
                        b2b_token = tokens_data[target_mail]
            except Exception as e:
                print(f"Token读取异常: {e}", file=sys.stderr)
        
        b2b_cookie = CookieManager.get_b2b_cookie(target_mail)
        
        if not b2b_token or not b2b_cookie:
            return emit_result({
                "success": False,
                "message": "缺失B2B凭据",
                "status_code": 500,
                "actual": "缺失B2B Token或Cookie"
            })
        
        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        endpoints = API_CONFIG.get("ENDPOINTS", {})
        
        # 3. 步骤1：B2B购物车列表调用
        shopping_list_url = f"{base_url}{endpoints.get('B2B_Addon_shoppinglist', '')}"
        shopping_list_payload = addon_payloads.get("B2B_Addon_shoppinglist", {"page": 1})
        # 为购物车附加项流程设置正确的headers（currpath和referer）
        shopping_list_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie)
        # 覆盖购物车相关的currpath和referer
        shopping_list_headers['currpath'] = '/user/shopping/b2b_carts/'
        shopping_list_headers['referer'] = f'{base_url}/web_view/user/shopping/b2b_carts/'
        fjx_headers = shopping_list_headers.copy()
        fjx_headers['Origin'] = 'https://fjx.hubbuyer.com'
        fjx_headers['origin'] = 'https://fjx.hubbuyer.com'
        fjx_headers['referer'] = 'https://fjx.hubbuyer.com/'
        
        try:
            response = requests.post(shopping_list_url, json=shopping_list_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
            check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_shoppinglist", {}))
            
            if not check["success"]:
                return emit_result({
                    "success": False,
                    "message": f"购物车列表获取失败: {check.get('message', '未知错误')}",
                    "status_code": response.status_code,
                    "actual": check.get('message', '未知错误')
                })
            
            # 提取 seller_data[].data[] 中每个商品的 id（嵌套结构）
            try:
                res_data = response.json()
                data = res_data.get("data", {})
                
                # 从 seller_data 数组中提取每个 seller 的 data 数组中的 id
                seller_data = data.get("seller_data", [])
                
                # 处理 seller_data 可能是字典或列表的情况
                if isinstance(seller_data, dict):
                    seller_data = seller_data.get("data", []) if "data" in seller_data else [seller_data]
                elif not isinstance(seller_data, list):
                    seller_data = []
                
                id_list = []
                # 遍历每个 seller
                for seller in seller_data:
                    if isinstance(seller, dict):
                        # 获取 seller 的 data 数组（商品列表）
                        seller_items = seller.get("data", [])
                        if isinstance(seller_items, list):
                            # 遍历每个商品，提取 id
                            for item in seller_items:
                                if isinstance(item, dict):
                                    item_id = item.get("id")
                                    if item_id:
                                        id_list.append(item_id)
                
                if not id_list:
                    return emit_result({
                        "success": False,
                        "message": "购物车列表为空，seller_data.data中无可用ID",
                        "status_code": response.status_code,
                        "actual": "seller_data.data为空"
                    })
                
                # 存储邮箱和ID的对应关系（只存储 id）
                id_mapping = load_or_create_id_mapping()
                id_mapping[target_mail] = [{"id": item_id} for item_id in id_list]
                save_id_mapping(id_mapping)
                stored_ids = id_list
                msgs.append(f"购物车列表:OK(获取到{len(id_list)}个ID)")
                
            except Exception as e:
                return emit_result({
                    "success": False,
                    "message": f"解析购物车列表响应失败: {str(e)}",
                    "status_code": response.status_code,
                    "actual": str(e)
                })
                
        except Exception as e:
            return emit_result({
                "success": False,
                "message": f"购物车列表请求异常: {str(e)}",
                "status_code": 500,
                "actual": str(e)
            })
        
        # 从 B2B_Addon_id.json 读取 id 映射
        id_list = get_id_mapping_for_mail(target_mail)
        if not id_list:
            return emit_result({
                "success": False,
                "message": "未找到ID映射数据，请先执行购物车列表获取",
                "status_code": 500,
                "actual": "B2B_Addon_id.json 中无对应邮箱的数据"
            })
        
        # 使用第一个ID
        cart_items = [item for item in id_list if isinstance(item, dict) and item.get("id")]
        cart_ids = [item["id"] for item in cart_items]
        first_item = cart_items[0] if cart_items else {}
        cart_id = first_item.get("id")
        
        if not cart_id:
            return emit_result({
                "success": False,
                "message": "ID映射数据无效",
                "status_code": 500,
                "actual": "B2B_Addon_id.json 中ID为空"
            })
        
        # 获取当前日期和时间字符串
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")  # 格式：20260130
        time_str = now.strftime("%H%M%S")  # 格式：134500
        
        # 4. 步骤2：选择商品附加项（新版从 fjx iframe 实时列表取有效 UUID）
        step2_url = f"{base_url}{endpoints.get('B2B_Addon_Servicefjx', '')}"
        step2_base_payload = addon_payloads.get("B2B_Addon_SelectAddon", {}).copy()
        check_config_uuid, selected_fjx, selected_user_fjx = get_runtime_fjx_selection(
            base_url,
            endpoints,
            fjx_headers
        )
        
        # 更新 payload 中的字段，作用于本次报价单会提交的所有购物车明细
        step2_base_payload["cart_detail_id_arr"] = cart_ids
        step2_base_payload["check_config_uuid"] = check_config_uuid
        step2_base_payload["fjx_config_uuid_arr"] = selected_fjx
        step2_base_payload["user_fjx_config_uuid_arr"] = selected_user_fjx
        step2_payload = step2_base_payload
        
        try:
            response = requests.post(step2_url, json=step2_payload, headers=fjx_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
            check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_Servicefjx", {}))
            if not check["success"]:
                error_msg = f"选择商品附加项失败: {check.get('message', '未知错误')}"
                error_details.append(error_msg)
                msgs.append(f"选择商品附加项:FAIL({check.get('message', '未知错误')})")
            else:
                msgs.append(f"选择商品附加项:OK({','.join(selected_fjx)})")
        except Exception as e:
            error_msg = f"选择商品附加项异常: {str(e)}"
            error_details.append(error_msg)
            msgs.append(f"选择商品附加项:FAIL({str(e)})")
        
        # 5. 步骤3：编号填写管理
        step3_url = f"{base_url}{endpoints.get('B2B_Addon_SKU', '')}"
        step3_base_payload = addon_payloads.get("B2B_Addon_SKU", {}).copy()
        
        step3_failures = []
        for current_cart_id in cart_ids:
            step3_payload = {
                "cart_detail_id": current_cart_id,
                "custom_sku": {
                    "sku": date_str
                },
                "amazon_sku": {
                    "sku": f"{time_str}SKU",
                    "url": "",
                    "asin": f"{time_str}ASIN",
                    "fnsku": f"{time_str}FNSKU",
                    "child_id": f"{time_str}Sub-ID"
                },
                "self_sku": []
            }
            try:
                response = requests.post(step3_url, json=step3_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_SKU", {}))
                if not check["success"]:
                    step3_failures.append(f"{current_cart_id}:{check.get('message', '未知错误')}")
            except Exception as e:
                step3_failures.append(f"{current_cart_id}:{str(e)}")

        if step3_failures:
            error_msg = f"编号填写管理失败: {'; '.join(step3_failures)}"
            error_details.append(error_msg)
            msgs.append(f"编号填写管理:FAIL({' ; '.join(step3_failures)})")
        else:
            msgs.append(f"编号填写管理:OK({len(cart_ids)}个)")
        
        # 6. 步骤4：贴纸编写保存
        step4_url = f"{base_url}{endpoints.get('B2B_Addon_PicNewspaper', '')}"
        step4_failures = []
        for current_cart_id in cart_ids:
            step4_payload = addon_payloads.get("B2B_Addon_PicNewspaper", {}).copy()
            if "cart_detail_id" in step4_payload:
                step4_payload["cart_detail_id"] = str(current_cart_id)
            try:
                response = requests.post(step4_url, json=step4_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_PicNewspaper", {}))
                if not check["success"]:
                    step4_failures.append(f"{current_cart_id}:{check.get('message', '未知错误')}")
            except Exception as e:
                step4_failures.append(f"{current_cart_id}:{str(e)}")

        if step4_failures:
            error_msg = f"贴纸编写保存失败: {'; '.join(step4_failures)}"
            error_details.append(error_msg)
            msgs.append(f"贴纸编写保存:FAIL({' ; '.join(step4_failures)})")
        else:
            msgs.append(f"贴纸编写保存:OK({len(cart_ids)}个)")
        
        # 7. 步骤5：吊牌编写保存
        step5_url = f"{base_url}{endpoints.get('B2B_Addon_PicBrand', '')}"
        step5_failures = []
        for current_cart_id in cart_ids:
            step5_payload = addon_payloads.get("B2B_Addon_PicBrand", {}).copy()
            if "cart_detail_id" in step5_payload:
                step5_payload["cart_detail_id"] = str(current_cart_id)
            try:
                response = requests.post(step5_url, json=step5_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_PicBrand", {}))
                if not check["success"]:
                    step5_failures.append(f"{current_cart_id}:{check.get('message', '未知错误')}")
            except Exception as e:
                step5_failures.append(f"{current_cart_id}:{str(e)}")

        if step5_failures:
            error_msg = f"吊牌编写保存失败: {'; '.join(step5_failures)}"
            error_details.append(error_msg)
            msgs.append(f"吊牌编写保存:FAIL({' ; '.join(step5_failures)})")
        else:
            msgs.append(f"吊牌编写保存:OK({len(cart_ids)}个)")
        
        # 8. 步骤6：洗标编写保存
        step6_url = f"{base_url}{endpoints.get('B2B_Addon_WashCollar', '')}"
        step6_failures = []
        for current_cart_id in cart_ids:
            step6_payload = addon_payloads.get("B2B_Addon_WashCollar", {}).copy()
            if "cart_detail_id" in step6_payload:
                step6_payload["cart_detail_id"] = str(current_cart_id)
            if "name" in step6_payload:
                step6_payload["name"] = date_str
            if "company_info" in step6_payload:
                step6_payload["company_info"] = date_str
            try:
                response = requests.post(step6_url, json=step6_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_WashCollar", {}))
                if not check["success"]:
                    step6_failures.append(f"{current_cart_id}:{check.get('message', '未知错误')}")
            except Exception as e:
                step6_failures.append(f"{current_cart_id}:{str(e)}")

        if step6_failures:
            error_msg = f"洗标编写保存失败: {'; '.join(step6_failures)}"
            error_details.append(error_msg)
            msgs.append(f"洗标编写保存:FAIL({' ; '.join(step6_failures)})")
        else:
            msgs.append(f"洗标编写保存:OK({len(cart_ids)}个)")
        
        # 9. 步骤7：FBA编写保存
        step7_url = f"{base_url}{endpoints.get('B2B_Addon_FBA', '')}"
        step7_failures = []
        for current_cart_id in cart_ids:
            step7_payload = addon_payloads.get("B2B_Addon_FBA", {}).copy()
            if "cart_detail_id" in step7_payload:
                step7_payload["cart_detail_id"] = str(current_cart_id)
            try:
                response = requests.post(step7_url, json=step7_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_Addon_FBA", {}))
                if not check["success"]:
                    step7_failures.append(f"{current_cart_id}:{check.get('message', '未知错误')}")
            except Exception as e:
                step7_failures.append(f"{current_cart_id}:{str(e)}")

        if step7_failures:
            error_msg = f"FBA编写保存失败: {'; '.join(step7_failures)}"
            error_details.append(error_msg)
            msgs.append(f"FBA编写保存:FAIL({' ; '.join(step7_failures)})")
        else:
            msgs.append(f"FBA编写保存:OK({len(cart_ids)}个)")
        
        # 汇总结果（包含所有步骤的执行记录，到FBA步骤）
        # 判断整体成功状态：如果所有步骤都成功，则success=True；否则success=False
        all_steps_success = len(error_details) == 0
        
        final_result = {
            "success": all_steps_success,
            "message": " | ".join(msgs),
            "status_code": 200 if all_steps_success else 500,
            "actual": f"B2B附加项流程: {' | '.join(msgs)}"
        }
        
    except Exception as e:
        final_result = {
            "success": False,
            "message": str(e),
            "status_code": 500,
            "actual": traceback.format_exc()
        }
    
    # 最终结果输出（必须是最后一行，runner 会取最后一行作为结果）
    return emit_result(final_result)

if __name__ == "__main__":
    # 处理命令行参数（batch_checker 会通过 sys.argv[1] 传递配置）
    task_config = None
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
        except:
            task_config = {}
    run(task_config)
