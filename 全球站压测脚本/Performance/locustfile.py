# -*- coding: utf-8 -*-
"""
全球站 B2B 压测入口 —【全部】：接口检查项 + UI 页面检查项一起跑。

业务逻辑统一来自 core_stress.py；本文件只负责挂载任务（向后兼容旧调用）。

启动示例:
    locust -f locustfile.py
    locust -f locustfile.py --headless -u 100 -r 10 -t 30m

如需只跑接口或只跑 UI，请改用：
    locust -f locustfile_api.py   # 仅接口检查项
    locust -f locustfile_ui.py    # 仅 UI 页面检查项
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


class HubbuyerStressUser(RealUserBase):
    """真实账号用户：接口链路（登录/浏览/加购/下单）+ 登录态页面访问。"""
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

    @tag("page", "member_page")
    @task(TASK_WEIGHTS.get("member_page_visit", 2))
    def task_member_page_visit(self):
        self.run_member_page_visit()


class HubbuyerGuestBrowseUser(GuestUserBase):
    """虚拟访客：前台页面访问（UI）+ 关键词搜索接口。"""
    weight = GUEST_USER_WEIGHT

    @tag("guest", "page")
    @task(GUEST_TASK_WEIGHTS.get("page_visit", 2))
    def task_page_visit(self):
        self.run_page_visit()

    @tag("guest", "keyword_search")
    @task(GUEST_TASK_WEIGHTS.get("keyword_search", 3))
    def task_keyword_search(self):
        self.run_keyword_search()


if STRESS_USE_SPLIT_LOAD_SHAPE:
    SplitUserLoadShape = make_split_load_shape(HubbuyerStressUser, HubbuyerGuestBrowseUser)
