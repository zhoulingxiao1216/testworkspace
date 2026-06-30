# -*- coding: utf-8 -*-
"""报价单下载链路自测：压测脚本 + 测试平台环境变量注入。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PERF_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_PAGE = PERF_ROOT.parent / "测试平台自建" / "pages" / "3_性能压测.py"

sys.path.insert(0, str(PERF_ROOT))


def load_platform_helpers():
    source = PLATFORM_PAGE.read_text(encoding="utf-8")
    marker_start = "def _resolve_full_quote_flow(config):"
    marker_end = "def build_virtual_user_steps(config):"
    chunk = source[source.index(marker_start):source.index(marker_end)]
    namespace = {}
    exec(chunk, namespace)
    return namespace


def test_platform_env_mapping():
    page = load_platform_helpers()
    build_stress_runtime_env = page["build_stress_runtime_env"]
    build_real_user_steps = page["build_real_user_steps"]
    config = {
        "env_type": "main",
        "selected_emails": ["performance_test_004@126.com"],
        "real_users": 1,
        "virtual_users": 0,
        "real_spawn_rate": 1.0,
        "virtual_spawn_rate": 1.0,
        "duration": "1m",
        "browse_steps": 1,
        "enable_add_cart": True,
        "enable_taobao_keyword": False,
        "enable_taobao_detail": False,
        "enable_taobao_add_cart": False,
        "enable_submit_order": True,
        "enable_full_quote_flow": True,
        "enable_quote_download": True,
        "quote_download_language": "english",
        "quote_type": 2,
        "logistics_config_id": 28,
        "submit_order_max_cart_items": 1,
    }
    env = build_stress_runtime_env(config)
    assert env["STRESS_ENABLE_SUBMIT_ORDER"] == "1", env
    assert env["STRESS_ENABLE_QUOTE_DOWNLOAD"] == "1", env
    assert env["STRESS_QUOTE_DOWNLOAD_LANGUAGE"] == "english", env

    config["enable_quote_download"] = False
    env_off = build_stress_runtime_env(config)
    assert env_off["STRESS_ENABLE_QUOTE_DOWNLOAD"] == "0", env_off

    config["enable_submit_order"] = False
    env_submit_off = build_stress_runtime_env(config)
    assert env_submit_off["STRESS_ENABLE_QUOTE_DOWNLOAD"] == "0", env_submit_off

    steps = build_real_user_steps(config)
    assert any("downQuote" in step for step in steps) is False

    config["enable_submit_order"] = True
    config["enable_quote_download"] = True
    steps_on = build_real_user_steps(config)
    assert any("downQuote" in step for step in steps_on), steps_on
    print("[PASS] 测试平台环境变量与执行说明")


def test_stress_chain():
    os.environ["STRESS_ENV"] = "main"
    os.environ["STRESS_ACCOUNT_EMAILS"] = "performance_test_004@126.com"
    os.environ["STRESS_ENABLE_SUBMIT_ORDER"] = "1"
    os.environ["STRESS_ENABLE_FULL_QUOTE_FLOW"] = "1"
    os.environ["STRESS_ENABLE_QUOTE_DOWNLOAD"] = "1"
    os.environ["STRESS_QUOTE_DOWNLOAD_LANGUAGE"] = "english"

    # 重新加载配置以应用环境变量
    for name in list(sys.modules):
        if name == "config.settings" or name.startswith("config."):
            del sys.modules[name]
    if "core_stress" in sys.modules:
        del sys.modules["core_stress"]

    from core_stress import RealUserBase

    class T(RealUserBase):
        fixed_count = 1

    user = T(environment=None)
    user.on_start()
    assert user.ready, "登录预热失败"
    assert user.email == "performance_test_004@126.com", user.email

    before_ids = user._request_cart_list("购物车列表 [自测下单前]")
    user._browse_products()
    assert user._request_add_cart(), "加购失败"
    cart_ids = user._resolve_added_cart_ids(before_ids)
    assert cart_ids, "未解析到购物车明细"
    assert user._run_full_quote_flow(cart_ids), "完整报价链路失败"

    ok, quote_no = user._request_submit_order(cart_ids)
    assert ok, "提交报价单失败"
    assert quote_no and quote_no.startswith("B2B-BJ-"), quote_no

    dl_ok = user._request_down_quote(quote_no)
    assert dl_ok, f"下载报价单失败: {quote_no}"

    user.run_browse_add_cart_submit_order()
    print(f"[PASS] 压测链路自测 submit={quote_no} download=OK")


def main():
    print("=== 报价单下载链路自测 ===")
    test_platform_env_mapping()
    test_stress_chain()
    print("=== 全部通过 ===")


if __name__ == "__main__":
    main()
