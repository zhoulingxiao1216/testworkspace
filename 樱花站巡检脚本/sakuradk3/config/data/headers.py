# -*- coding: utf-8 -*-
# d:\sakuradk3\config\data\headers.py

def get_base_headers(base_url):
    """基础请求头（不带 Token）"""
    return {
        'Content-Type': 'application/json',
        'Platform': 'PC',
        'Origin': base_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

def get_auth_headers(base_url, token):
    """B2B 专用：带 Token 的鉴权请求头"""
    headers = get_base_headers(base_url)
    if token:
        # B2B 的 authorization 直接是 token，不是 Bearer {token}
        clean_token = token.replace("Bearer ", "").strip()
        headers['authorization'] = clean_token
        # print(f"DEBUG B2B Auth: {headers.get('authorization')}")
    return headers

def get_b2b_headers(base_url, token, cookie_str, item_id=None, item_url=None):
    """
    B2B 加购专用：带 Token 和 Cookie 的完整请求头（基于实际请求格式）
    
    Args:
        base_url: B2B 的 base URL（从 API_CONFIG 获取）
        token: Token 字符串（从 current_tokens.json 获取）
        cookie_str: Cookie 字符串（通过 CookieManager.get_b2b_cookie 获取）
        item_id: 商品 ID（可选，用于动态生成 referer）
        item_url: 商品 URL（可选，用于判断商品类型：1688 或 taobao）
    """
    headers = get_auth_headers(base_url, token)
    
    # 动态生成 referer 和 currpath（根据商品类型）
    if item_id and item_url:
        if "detail.1688.com" in item_url or "offer" in item_url or "1688.com" in item_url:
            # 1688 商品
            currpath = '/Alibaba/details/'
            referer = f'{base_url}/web_view/Alibaba/details/?item_id={item_id}&key=&Lang=1&fg=0&sl=32&hot_desc=null&imageUrl=1'
        elif "item.taobao.com" in item_url or "taobao.com" in item_url:
            # taobao 商品
            currpath = '/Taobao/details/'
            referer = f'{base_url}/web_view/Taobao/details/?item_id={item_id}&key=&Lang=1&fg=0&sl=32&hot_desc=null&imageUrl=1'
        else:
            # 默认使用 Alibaba 格式
            currpath = '/Alibaba/details/'
            referer = f'{base_url}/web_view/Alibaba/details/?item_id={item_id}&key=&Lang=1&fg=0&sl=32&hot_desc=null&imageUrl=1'
    else:
        currpath = '/Alibaba/details/'
        referer = f'{base_url}/'
    
    # 添加完整的 headers（基于实际请求格式）
    headers.update({
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'content-type': 'application/json',
        'currpath': currpath,
        'origin': base_url,
        'platform': 'PC',
        'priority': 'u=1, i',  # B2B 使用 u=1，D2C 使用 u=0
        'referer': referer,
        'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'Cookie': cookie_str
    })
    return headers

def get_d2c_headers(d2c_cookie, d2c_base_url, item_url=None):
    """
    D2C 专用：表单格式 + 完整 Cookie 上下文（基于实际请求格式）
    注意：D2C 必须使用 application/x-www-form-urlencoded; charset=UTF-8
    D2C 只需要 Cookie 中的 loginToken，headers 中不需要单独的 loginToken 字段
    
    Args:
        d2c_cookie: Cookie 字符串（通过 CookieManager.get_d2c_cookie 获取）
        d2c_base_url: D2C 的 base URL（从 API_CONFIG 的 add_cart_D2C endpoint 提取）
        item_url: 商品 URL（可选，用于动态生成 referer，支持 1688 和 taobao）
    """
    # 动态生成 referer（如果有 item_url）
    if item_url:
        # 判断是 1688 还是 taobao，生成对应的 referer
        if "detail.1688.com" in item_url or "offer" in item_url:
            # 1688 商品：/Alibaba/Detail?itemURL=...
            referer = f'{d2c_base_url}/Alibaba/Detail?itemURL={item_url}'
        elif "item.taobao.com" in item_url or "taobao.com" in item_url:
            # taobao 商品：/Taobao/Detail?itemURL=...
            referer = f'{d2c_base_url}/Taobao/Detail?itemURL={item_url}'
        else:
            # 默认使用 Alibaba 格式
            referer = f'{d2c_base_url}/Alibaba/Detail?itemURL={item_url}'
    else:
        referer = f'{d2c_base_url}/'
    
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': d2c_base_url,
        'priority': 'u=0, i',
        'referer': referer,
        'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'x-requested-with': 'XMLHttpRequest',
        'Cookie': d2c_cookie  # 这里传入通过 CookieManager.get_d2c_cookie 加工好的完整字符串（包含 loginToken）
    }
    
    return headers