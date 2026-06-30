# -*- coding: utf-8 -*-
# d:\sakuradk3\config\api\prod.py

# 统一使用 API_CONFIG 变量名，方便导入
API_CONFIG = {
    "BASE_URL": "https://api.hubbuyer.com",
    "ENDPOINTS": {
        "login": "/api/login/login",
        "image_search_B2B": "/api_ali/product/imageSearch", #图搜
        "image_search_D2C": "",
        "keyword_search_B2B_1688": "/api_ali/product/keyword", #B2B关键词搜索1688
        "keyword_search_B2B_taobao": "/api_tb/product/keyword", #B2B关键词搜索淘宝
        "add_cart_B2B_1688": "/api_b2b/cart/add1688", #B2B加购1688
        "add_cart_B2B_taobao": "/api_b2b/cart/addTb", #B2B加购淘宝
        "add_cart_D2C": "",
        "B2B_Addon_shoppinglist":"/api_b2b/cart/list", #购物车列表
        "B2B_Addon_CheckFjxList":"/api_b2b/cartQuoteStep1/getCheckFjxList", #新版附加项列表
        "B2B_Addon_Servicefjx":"/api_b2b/cartQuoteStep1/updateCheckFjx", #附加项
        "B2B_Addon_SKU":"/api_b2b/cartQuoteStep1/updateSkuNumberData", #编号管理
        "B2B_Addon_PicNewspaper":"/api_b2b/designFjxSticker/updateByCart", #贴纸
        "B2B_Addon_PicBrand":"/api_b2b/designFjxHangTag/updateByCart", #吊牌
        "B2B_Addon_FBA":"/api_b2b/designFjxFba/updateByCart", #FBA
        "B2B_Addon_WashCollar":"/api_b2b/designFjxWash/create", #洗标
        "D2C_Addon_shoppinglist":"",
        "D2C_Addon_add":"",
        "submit_order_B2B":"/api_b2b/quote/create", #提交自助报价单
        #"submit_order_saveAddress_D2C":"/api_user/d2c_shopping/saveAddress", #选择收货地址
        "submit_order_D2C":"", #提交报价单
        "payment_B2B_list":"/api_b2b/quote/list", #B2B报价单列表
        "payment_B2B_pay":"/api_b2b/quote/pay", #B2B报价单支付
        "payment_D2C_list":"", #D2C报价单列表
        "payment_D2C_pay":"", #D2C报价单支付
        "plugin_B2B":"", #B2B插件加购1688&taobao商品
        "plugin_D2C":"", #D2C插件加购1688商品
    }
}
