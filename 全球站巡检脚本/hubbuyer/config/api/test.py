# -*- coding: utf-8 -*-
# 全球站测试环境 API 配置

# 统一使用 API_CONFIG 变量名，方便导入
API_CONFIG = {
    "BASE_URL": "https://test-api.hubbuyer.com",
    "ENDPOINTS": {
        "login": "/api/login/login",
        "image_search_B2B": "/api_ali/product/imageSearch",
        "image_search_D2C": "",
        "keyword_search_B2B_1688": "/api_ali/product/keyword",
        "keyword_search_B2B_taobao": "/api_tb/product/keyword",
        "add_cart_B2B_1688": "/api_b2b/cart/add1688",
        "add_cart_B2B_taobao": "/api_b2b/cart/addTb",
        "add_cart_D2C": "",
        "B2B_Addon_shoppinglist": "/api_b2b/cart/list",
        "B2B_Addon_CheckFjxList": "/api_b2b/cartQuoteStep1/getCheckFjxList",
        "B2B_Addon_Servicefjx": "/api_b2b/cartQuoteStep1/updateCheckFjx",
        "B2B_Addon_SKU": "/api_b2b/cartQuoteStep1/updateSkuNumberData",
        "B2B_Addon_PicNewspaper": "/api_b2b/designFjxSticker/updateByCart",
        "B2B_Addon_PicBrand": "/api_b2b/designFjxHangTag/updateByCart",
        "B2B_Addon_FBA": "/api_b2b/designFjxFba/updateByCart",
        "B2B_Addon_WashCollar": "/api_b2b/designFjxWash/create",
        "D2C_Addon_shoppinglist": "",
        "D2C_Addon_add": "",
        "submit_order_B2B": "/api_b2b/quote/create",
        "submit_order_D2C": "",
        "payment_B2B_list": "/api_b2b/quote/list",
        "payment_B2B_pay": "/api_b2b/quote/pay",
        "payment_D2C_list": "",
        "payment_D2C_pay": "",
        "plugin_B2B": "",
        "plugin_D2C": "",
    }
}
