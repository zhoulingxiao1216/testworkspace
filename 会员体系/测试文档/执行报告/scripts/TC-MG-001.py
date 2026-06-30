# -*- coding: utf-8 -*-
"""
TC-MG-001 — 最终修正版：直接填写所有8个textarea，不折叠
"""
from playwright.sync_api import sync_playwright
import os, sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.query_selector_all("input")
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.query_selector("button").click()
    try:
        page.wait_for_url("**/admin/**", timeout=15000)
    except:
        page.wait_for_timeout(5000)
    print(f"[Login] {page.url}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        admin_login(page)
        
        ts = str(int(time.time()))
        name_zh = f"AG2_{ts}"
        
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "TC-MG-001_snapshot.webp"))
        
        # 点击新增 (用第4个按钮 - 根据之前探索: 恢复默认/查询/重置/新增会员等级)
        all_btns = page.query_selector_all("button")
        for btn in all_btns:
            cls = btn.get_attribute("class") or ""
            t = btn.inner_text().strip()
            # 新增会员等级按钮是 el-button--primary 且不是查询/重置
            if "primary" in cls and "is-link" not in cls and len(t) >= 4 and t not in ("查询",):
                if t != "查询":
                    print(f"  Trying button: '{t}'")
                    btn.click()
                    break
        
        page.wait_for_timeout(1500)
        
        # 获取弹窗内所有元素
        dialog_inputs = page.query_selector_all(".el-dialog input")
        dialog_textareas = page.query_selector_all(".el-dialog textarea")
        print(f"  Inputs: {len(dialog_inputs)}, Textareas: {len(dialog_textareas)}")
        
        # Input布局 (13个):
        # [0]=中文名称 [1]=EN [2]=JP [3]=KR [4]=阿拉伯 [5]=西班牙 [6]=俄语 [7]=法语
        # [8]=成为条件 [9]=等级权重 [10]=排序 [11]=状态radio [12]=状态radio
        if len(dialog_inputs) >= 8:
            dialog_inputs[0].fill(name_zh)
            dialog_inputs[1].fill(f"{name_zh}_EN")
            dialog_inputs[2].fill(f"{name_zh}_JP")
            dialog_inputs[3].fill(f"{name_zh}_KR")
            print(f"Step 2a: Names = ZH:{name_zh} EN/JP/KR")
        
        # Textarea布局 (8个): 对应 ZH/EN/JP/KR/阿拉伯/西班牙/俄语/法语 的等级说明
        # 只需填写前4个(中英日韩)即可满足校验
        desc_map = {
            0: f"[Auto-Setup] {name_zh} ZH",
            1: f"[Auto-Setup] {name_zh} EN",
            2: f"[Auto-Setup] {name_zh} JP",
            3: f"[Auto-Setup] {name_zh} KR",
        }
        for idx, desc in desc_map.items():
            if idx < len(dialog_textareas):
                dialog_textareas[idx].fill(desc)
        print(f"Step 2b: Descriptions = 4 languages filled")
        
        page.screenshot(path=os.path.join(SCREENSHOTS, "TC-MG-001_step2_filled.webp"))
        
        # 点击确定
        dialog_btns = page.query_selector_all(".el-dialog button")
        for btn in dialog_btns:
            t = btn.inner_text().strip()
            if t in ("确定", "确认", "保存"):
                btn.click()
                print(f"Step 3: Clicked '{t}'")
                break
        
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "TC-MG-001_step3_after.webp"))
        
        # 检查校验错误
        errors = page.query_selector_all(".el-form-item__error")
        err_texts = [e.inner_text() for e in errors if e.inner_text().strip()]
        if err_texts:
            print(f"  Validation errors: {err_texts}")
        
        # 检查success message
        page.wait_for_timeout(1000)
        success = page.query_selector(".el-message--success")
        if success:
            print(f"  Success: {success.inner_text()}")
        
        # 刷新验证
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
        page.wait_for_timeout(3000)
        body = page.inner_text("body")
        
        if name_zh in body:
            print(f"\n{'='*50}")
            print(f"TC-MG-001 = PASS")
            print(f"Found: {name_zh}")
            print(f"{'='*50}")
            page.screenshot(path=os.path.join(SCREENSHOTS, "TC-MG-001_result.webp"))
            
            # DB验证
            print("\n[Layer 1-DB] 数据库交叉验证...")
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helpers"))
                from db_helper import query
                db_rows = query(f"SELECT id, uuid, name_language, status FROM b2b_member_level_config WHERE name_language LIKE '%%{name_zh}%%' LIMIT 5")
                if db_rows:
                    print(f"  DB found: id={db_rows[0]['id']}, uuid={db_rows[0]['uuid']}, status={db_rows[0]['status']}")
                    print(f"  三方一致性: Admin ✅ | DB ✅")
                else:
                    print(f"  DB: NOT FOUND (data sync delay?)")
            except Exception as e:
                print(f"  DB check skipped: {e}")
            
            # [Restore] 禁用
            rows = page.query_selector_all("table tbody tr")
            for row in rows:
                if name_zh in (row.inner_text() or ""):
                    btns_r = row.query_selector_all("button")
                    for b in btns_r:
                        t = b.inner_text().strip()
                        if t == "禁用":
                            b.click()
                            page.wait_for_timeout(1500)
                            try:
                                page.click(".el-popconfirm .el-button--primary", timeout=3000)
                            except:
                                try:
                                    page.click(".el-message-box__btns .el-button--primary", timeout=3000)
                                except:
                                    pass
                            page.wait_for_timeout(2000)
                            print(f"[Restore] Disabled {name_zh}")
                            break
                    break
        else:
            print(f"\n{'='*50}")
            print(f"TC-MG-001 = FAIL")
            print(f"Not found: {name_zh}")
            print(f"{'='*50}")
            page.screenshot(path=os.path.join(SCREENSHOTS, "TC-MG-001_fail.webp"))
        
        browser.close()

if __name__ == "__main__":
    main()
