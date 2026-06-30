# -*- coding: utf-8 -*-
"""
全球站 B2B 压测入口 —【UI 页面检查项】专用脚本。

仅运行前台页面（UI）检查项（SPA 文档级：状态码 + 标题关键字断言）：
    - 虚拟访客：免登录页面（B2B 首页、关键词搜索结果页）
    - 真实账号：登录态页面（购物车、购物车附加项、订单提交确认）
        * 真实账号仅在 on_start 登录一次以获取 token/cookie，登录不计为页面任务。
不运行加购、下单、关键词搜索等接口检查项。

业务逻辑统一来自 core_stress.py。

启动示例:
    locust -f locustfile_ui.py --headless -u 100 -r 10 -t 30m
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


class UiMemberUser(RealUserBase):
    """真实账号用户：仅访问登录态前台页面（购物车/附加项/订单确认）。"""
    fixed_count = AUTH_BUYER_FIXED_COUNT

    @tag("page", "member_page")
    @task(TASK_WEIGHTS.get("member_page_visit", 2))
    def task_member_page_visit(self):
        self.run_member_page_visit()


class UiGuestUser(GuestUserBase):
    """虚拟访客：仅访问免登录前台页面（首页/搜索结果）。"""
    weight = GUEST_USER_WEIGHT

    @tag("guest", "page")
    @task(GUEST_TASK_WEIGHTS.get("page_visit", 2))
    def task_page_visit(self):
        self.run_page_visit()


if STRESS_USE_SPLIT_LOAD_SHAPE:
    UiLoadShape = make_split_load_shape(UiMemberUser, UiGuestUser)
