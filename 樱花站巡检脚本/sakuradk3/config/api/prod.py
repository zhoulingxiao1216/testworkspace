# -*- coding: utf-8 -*-
# d:\sakuradk3\config\api\prod.py

# 统一使用 API_CONFIG 变量名，方便导入
API_CONFIG = {
    "BASE_URL": "https://www.sakuradk2.com",
    "ENDPOINTS": {
        "login": "/api_user/login/login",
        "image_search_B2B": "/v1/ali_product/img_search",
        #"image_search_D2C": "https://ali.sakuradk2.com/picSearch_alibaba_list.php",域名变更
        "image_search_D2C": "https://pro-api-task.sakuradk2.com/common/upload/image",
        "keyword_search_taobao": "/v1/tb_product/keyword_search",  #关键字搜索(淘宝)
        "keyword_search_1688": "/v1/ali_product/keyword_search",  #关键字搜索(1688)
        "d2c_keyword_search_1688": "https://ali.sakuradk2.com/newalibaba_list.php",  #D2C关键字搜索(1688)
        "add_cart_B2B": "/api_user/Shopping/add",
        "add_cart_D2C": "https://b2c.sakuradk2.com/Shopping/add",
        "B2B_Addon_shoppinglist":"/api_user/shopping/cart", #购物车列表
        "B2B_Addon_Servicefjx":"/api_user/Servicefjx/computedFjxCartId", #检品方式
        "B2B_Addon_PicNewspaper":"/api_user/Pic_Newspaper/updateCartTag", #贴纸
        "B2B_Addon_PicBrand":"/api_user/Pic_Brand/updateCartBrandTag", #吊牌
        "B2B_Addon_FBA":"/api_user/Pic_Fba/updateCartTag", #FBA
        "B2B_Addon_WashCollar":"/api_user/wash_collar_label/collar_generate", #洗标
        "B2B_Addon_save":"/api_user/Fjx/saveFjxV2", #确认附加项
        "D2C_Addon_shoppinglist":"/api_user/d2c_shopping/cart",
        "D2C_Addon_add":"/api_user/d2c_fjx/saveB2cFjx",
        "submit_order_B2B":"/api_user/shopping/createQuoteV2", #提交自助报价单
        "submit_order_saveAddress_D2C":"/api_user/d2c_shopping/saveAddress", #选择收货地址
        "submit_order_D2C":"/api_user/d2c_shopping/createdQuote", #提交报价单
        "payment_B2B_list":"/api_user/quote_api/QuoteList", #B2B报价单列表
        "payment_B2B_pay":"/api_user/quote_api/QuoteBalance", #B2B报价单支付
        "payment_D2C_list":"/api_user/d2c_quote/QuoteList", #D2C报价单列表
        "payment_D2C_pay":"/api_user/d2c_quote/quoteBalance", #D2C报价单支付
        "plugin_B2B":"/Shopping/add", #B2B插件加购1688&taobao商品
        "plugin_D2C":"/Shopping/addD2C", #D2C插件加购1688商品
    }
}