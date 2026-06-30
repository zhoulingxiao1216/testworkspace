# -*- coding: utf-8 -*-
"""
全球站 B2B 压测入口 —【接口检查项】专用脚本。

仅运行接口（API）检查项：
    - 真实账号：登录刷新、浏览（图搜/关键词）、加购、购物车、提交报价单
    - 虚拟访客：关键词搜索接口
不运行任何前台页面（UI）检查项。

业务逻辑统一来自 core_stress.py。

启动示例:
    locust -f locustfile_api.py --headless -u 100 -r 10 -t 30m
"""
from locust import tag, task

from core_stress import (
    RealUserBase,
    GuestUserBase,
    make_split_load_shape,
    AUTH_BUYER_FIXED_COUNT,
    GUEST_USER_WEIGHT,
    TASK_WEIGHTS,
    GUEST_TASK_WEIGHTS,
    STRESS_USE_SPLIT_LOAD_SHAPE,
)


class ApiRealUser(RealUserBase):
    """真实账号用户：仅接口链路（登录/浏览/加购/购物车/下单）。"""
    fixed_count = AUTH_BUYER_FIXED_COUNT

    @tag("login")
    @task(TASK_WEIGHTS.get("login_refresh", 1))
    def task_login_refresh(self):
        self.run_login_refresh()

    @tag("browse", "img_search", "keyword_search")
    @task(TASK_WEIGHTS.get("browse_only", 6))
    def task_browse_only(self):
        self.run_browse_only()

    @tag("browse", "add_cart")
    @task(TASK_WEIGHTS.get("browse_add_cart", 3))
    def task_browse_add_cart(self):
        self.run_browse_add_cart()

    @tag("journey", "browse", "add_cart", "submit_order")
    @task(TASK_WEIGHTS.get("browse_add_cart_submit_order", 1))
    def task_browse_add_cart_submit_order(self):
        self.run_browse_add_cart_submit_order()


class ApiGuestUser(GuestUserBase):
    """虚拟访客：仅关键词搜索接口（不访问页面）。"""
    weight = GUEST_USER_WEIGHT

    @tag("guest", "keyword_search")
    @task(GUEST_TASK_WEIGHTS.get("keyword_search", 3))
    def task_keyword_search(self):
        self.run_keyword_search()


if STRESS_USE_SPLIT_LOAD_SHAPE:
    ApiLoadShape = make_split_load_shape(ApiRealUser, ApiGuestUser)
