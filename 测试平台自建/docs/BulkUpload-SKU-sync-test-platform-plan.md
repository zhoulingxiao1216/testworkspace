# 测试平台：批量上传模板同步后台 SKU — 方案

> 目标：在 `D:\test_workspace\测试平台自建` 增加工具页，读取贴纸/吊牌批量上传 Excel 中的「贵社SKU」，按「商品番号」更新 Sakura 后台 `orderdetail.order_ExternalID`。

**结论：可行。** 无需先改 Sakura 主工程，可在测试平台自建 Streamlit 工具中实现 MVP；与后续 api-open 正式回写方案互补。

---

## 1. 业务映射

| Excel 字段 | 后台字段 | 匹配键 |
|-----------|---------|--------|
| 商品番号（列 E，如 `1370019`） | `orderdetail.order_id`（后台「番号」） | 主键 |
| 贵社SKU（如 `32223`） | `orderdetail.order_ExternalID`（后台「SKU」） | 待更新值 |

Sakura 批量上传解析（`NewOrderController::insert_new`）同样使用：

- `item[4]` → 商品番号 → `user_order_id` / 校验 `orderdetail.order_id`
- `item[13]` → 贵社SKU → `pub_api_order_new.sku`

**注意：** 界面上可见列位置与 PHP 数组下标可能不一致（模板含隐藏列/多表头）。测试平台应 **按表头文字识别列**，不要写死列号。

---

## 2. 测试平台现状与约束

| 能力 | 现状 |
|------|------|
| 框架 | Streamlit（`app.py` + `pages/`） |
| 已有 SKU 工具 | `pages/2_sku_verify.py`（OCR 比对，含 admin Session + 客户 Token） |
| 正式库 | `modules/readonly_db.py` — **仅允许 SELECT** |
| README 约束 | **严禁直接修改正式库** |

因此 MVP 推荐走 **HTTP API 更新**，而非直连 PolarDB 写 `orderdetail`。

---

## 3. 推荐架构

```
上传 Excel（贴纸/吊牌模板）
    ↓ openpyxl/pandas 解析（表头识别 商品番号 / 贵社SKU）
    ↓ 预览：更新前 SKU → 更新后 SKU（Dry-run）
    ↓ 用户确认
    ↓ 管理员 Session → 模拟进入客户中心 → 获取 login_token
    ↓ 逐行调用 User API 更新
POST /User/Agentorder/saveExternalID
    type=1 & itemId={商品番号} & usku={贵社SKU}
    ↓
orderdetail.order_ExternalID 更新
    ↓
后台订单列表 SKU 刷新
```

### 3.1 为何用 API 而非直连 DB

- 符合测试平台「正式库只读」安全策略
- 复用现有 `2_sku_verify.py` 的 `get_user_token()` 模式
- 走业务校验（订单归属 uid、产品是否存在）
- 无需新增 xierun 写库账号

### 3.2 可选扩展（Phase 2）

- 同步 `quotedetail.order_ExternalID`（需额外 API 或测试库写权限）
- 同步 `pub_api_order_new.sku`（api-all 库，需单独写连接或 api-open 接口）
- 同步 `sku_management` 貴社SKU 平台数据

---

## 4. 功能设计

### 4.1 新页面

**路径：** `pages/4_📦_SKU批量同步.py`  
**入口：** `app.py` 增加 page_link

### 4.2 页面流程

1. **配置区**（复用 `sku_accounts.json`）
   - 管理员 PHPSESSID
   - 选择客户 UID（订单所属账号，如 8113）

2. **上传区**
   - 接受 `.xlsx`（与批量上传模板相同）
   - 跳过前 3 行表头（与 `insert_new` 一致）
   - 表头识别：
     - `商品番号` / `注文番号` 邻近列 → order_id
     - `贵社SKU` / `貴社 SKU` → external_id

3. **预览区（Dry-run）**
   - 调用现有订单 API 拉取当前 SKU（或只读 SELECT 若后续开放 xierun 只读）
   - 表格列：商品番号 | 当前 SKU | Excel SKU | 状态（将更新/跳过/异常）

4. **跳过规则**
   - Excel 贵社SKU 为空 → 跳过
   - 商品番号为空 → 报错行
   - 当前 SKU 与 Excel 相同 → 跳过（幂等）
   - API 返回产品不存在 → 失败行

5. **执行区**
   - 「确认同步」按钮（二次确认）
   - 逐行 `saveExternalID`，显示进度条
   - 结果汇总：成功 / 跳过 / 失败

6. **审计**
   - 本地写入 `sku_sync_logs/YYYYMMDD_HHMMSS.json`（文件名、uid、每行结果）

---

## 5. 核心接口

### 5.1 获取客户 Token（已有）

```python
# pages/2_sku_verify.py
get_user_token(admin_sessid, uid)
# → GET /user/userShow?uid={uid}&type=1
```

### 5.2 更新 SKU（单条）

```
POST https://www.sakuradk2.com/User/Agentorder/saveExternalID
Cookie: PHPSESSID, login_token, login_user_id
Body/Query: type=1&itemId={order_id}&usku={external_id}
```

对应 Sakura 代码：`web/application/user/controller/Agentorder.php::saveExternalID`

### 5.3 校验当前 SKU（可选）

```
POST /api_user/agent/orderDetail
json: {"orderId": "{主订单号}"}
→ lists[].order_id + order_ExternalID
```

或按商品番号单查（若后续有接口）；MVP 可在预览阶段只对 Excel 解析结果做「待更新列表」，执行后再 spot-check。

---

## 6. Excel 解析示例

```python
import pandas as pd

HEADER_ROWS = 3  # 与 insert_new 一致

def parse_bulk_template(file_bytes) -> list[dict]:
    df = pd.read_excel(file_bytes, header=None)
    df = df.iloc[HEADER_ROWS:].copy()
    header = df.iloc[0].astype(str).tolist()
    data = df.iloc[1:]

    def find_col(*names):
        for i, h in enumerate(header):
            h_norm = str(h).replace(" ", "").strip()
            for n in names:
                if n.replace(" ", "") in h_norm:
                    return i
        return None

    col_order = find_col("商品番号")
    col_sku = find_col("贵社SKU", "貴社 SKU")
    if col_order is None or col_sku is None:
        raise ValueError("未找到「商品番号」或「贵社SKU」列，请检查模板")

    rows = []
    for _, r in data.iterrows():
        order_id = str(r.iloc[col_order]).strip().replace(".0", "")
        sku = str(r.iloc[col_sku]).strip()
        if not order_id or order_id.lower() == "nan":
            continue
        rows.append({"order_id": order_id, "external_id": sku})
    return rows
```

---

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 商品番号不属于所选 UID | API 返回「产品不存在」；预览阶段可选校验 |
| 误更新生产数据 | 默认 Dry-run；二次确认；日志归档 |
| 列映射错误 | 表头识别 + 预览前 5 行人工核对 |
| Token 过期 | 复用 2_sku_verify 的 Session 更新 UI |
| 只更新 orderdetail，不更新 pub_api_order_new | 文档说明；Phase 2 扩展 |

---

## 8. 与 Sakura 正式方案关系

| 层级 | 方案 | 作用 |
|------|------|------|
| 测试平台工具（本方案） | Streamlit + saveExternalID API | **测试/运维手工批量修正**，不动主工程 |
| Sakura 正式改造（已规划） | `BulkUploadSkuSyncService` 在生成任务中回写 | **生产自动化**，上传生成贴纸/吊牌时自动同步 |

两者可并存：测试平台用于验证与补数据；正式改造用于根治。

---

## 9. 实施任务（约 0.5~1 天）

- [ ] 新建 `pages/4_sku_bulk_sync.py`
- [ ] 抽取 `modules/sku_sync.py`（解析、API 调用、日志）
- [ ] 复用 `2_sku_verify.py` 的 Session / Token 逻辑（可抽到 `modules/sakura_client.py`）
- [ ] `app.py` 添加入口链接
- [ ] 用测试订单（如 1370019 / 32223）走通 Dry-run + 执行
- [ ] README 补充使用说明

---

## 10. 验收标准

- [ ] 上传含「商品番号 + 贵社SKU」的模板，预览正确
- [ ] 执行后后台「番号」对应行 SKU 与 Excel 一致
- [ ] Excel SKU 为空行不更新
- [ ] 错误行有明确提示，不影响其它行
- [ ] 全程无直连正式库 UPDATE
