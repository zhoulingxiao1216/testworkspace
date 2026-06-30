# -*- coding: utf-8 -*-
"""检查 prod/main 环境配置是否齐全（本地运行，不发起网络请求）"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_env(env_type):
    os.environ.pop("HUBBUYER_TOKEN_DIR", None)
    import importlib
    import config.settings as settings
    importlib.reload(settings)
    settings.ENV_TYPE = env_type
    if env_type == "prod":
        import config.url.prod as url_mod
        import config.api.prod as api_mod
    elif env_type == "main":
        import config.url.main as url_mod
        import config.api.main as api_mod
    else:
        raise ValueError(env_type)
    settings.API_CONFIG = {
        "BASE_URL": api_mod.API_CONFIG.get("BASE_URL"),
        "url_B2B_pc": url_mod.B2B_PC_url,
        "url_B2B_h5": url_mod.B2B_H5_url,
        "url_D2C_pc": url_mod.D2C_PC_url,
        "url_AboutUs_pc": url_mod.url_AboutUs_pc,
        "url_AboutUs_h5": url_mod.url_AboutUs_h5,
        "url_ADMIN": getattr(url_mod, "ADMIN_url", "https://admin.hubbuyer.com/"),
        "ENDPOINTS": api_mod.API_CONFIG["ENDPOINTS"],
        "ACCOUNT_LIST": settings.ACCOUNTS_POOL.get(env_type, {}).get("frontend", []),
    }
    return settings


def check_env(env_type):
    settings = load_env(env_type)
    cfg = settings.API_CONFIG
    issues = []

    required = [
        ("BASE_URL", cfg.get("BASE_URL")),
        ("url_B2B_pc", cfg.get("url_B2B_pc")),
        ("url_ADMIN", cfg.get("url_ADMIN")),
        ("url_AboutUs_pc", cfg.get("url_AboutUs_pc")),
        ("url_AboutUs_h5", cfg.get("url_AboutUs_h5")),
    ]
    for name, value in required:
        if not value:
            issues.append(f"缺少 {name}")

    admin = settings.ACCOUNTS_POOL.get(env_type, {}).get("admin", {})
    if not admin.get("account") or not admin.get("password"):
        issues.append("后台 admin 账号未配置")

    frontend = settings.ACCOUNTS_POOL.get(env_type, {}).get("frontend", [])
    if not frontend or not (frontend[0].get("email") or frontend[0].get("mail")):
        issues.append("前台账号未配置")

    from core.path_manager import (
        normalize_purchase_order_audit_config,
        normalize_purchase_order_ops_config,
    )

    data_dir = os.path.join(ROOT, "config", "data")
    with open(os.path.join(data_dir, "purchase_order_audit.json"), encoding="utf-8") as f:
        audit_cfg = normalize_purchase_order_audit_config(json.load(f))
    with open(os.path.join(data_dir, "purchase_order_ops.json"), encoding="utf-8") as f:
        ops_cfg = normalize_purchase_order_ops_config(json.load(f))

    audit_url = audit_cfg["audit_api"]["url"]
    if env_type not in (ops_cfg.get("allowed_envs") or []):
        issues.append(f"purchase_order_ops allowed_envs 未包含 {env_type}")

    if env_type == "prod":
        for token in ("main-api", "main-admin", "main-b2b", "main-www"):
            blob = json.dumps({"audit": audit_cfg, "ops": ops_cfg}, ensure_ascii=False)
            if token in blob:
                issues.append(f"仍含 main 硬编码: {token}")
        if not audit_url.startswith("https://api.hubbuyer.com/"):
            issues.append(f"代购订单审核 URL 异常: {audit_url}")
    if env_type == "main":
        if not audit_url.startswith("https://main-api.hubbuyer.com/"):
            issues.append(f"代购订单审核 URL 异常: {audit_url}")

    print(f"\n=== {env_type} ===")
    print(f"BASE_URL: {cfg.get('BASE_URL')}")
    print(f"B2B_PC:   {cfg.get('url_B2B_pc')}")
    print(f"ADMIN:    {cfg.get('url_ADMIN')}")
    print(f"审核URL:  {audit_url}")
    print(f"仓配URL:  {ops_cfg['detail_api']['url']}")
    if issues:
        print("[FAIL] 问题:")
        for item in issues:
            print(f"  - {item}")
    else:
        print("[OK] 配置检查通过")
    return issues


def main():
    all_issues = []
    for env in ("prod", "main"):
        all_issues.extend(check_env(env))
    sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()
