# 会员定价完整链路检查点分析方案

## 📋 执行概述
**检查点文件**: `member_pricing_complete_chain.py`  
**检查类型**: API 链路完整性检查  
**核心业务**: 全球站B2B会员价格体系、附加项（FJX）与费用计算  
**部署时间**: 2026年7月9日

---

## 1️⃣ 检查点内容分析

### 1.1 核心检查内容

| 检查模块 | 目标 | 验证重点 |
|---------|------|--------|
| **附加项列表** | `/api_b2b/cartQuoteStep1/getCheckFjxList` | 检品(check)、附加项(fjx)、用户附加项(user_fjx)的可见性 |
| **费用预览** | `/api_b2b/cartQuoteStep1/getCheckFjxFeeTotal` | 购物车附加项费用总额计算准确性 |
| **快照校验** | 用户/管理员自定义API | 跨环境数据一致性、关键字段包含性 |
| **国家服务价** | `/admin_b2b/serviceCountryConfig/{checkList\|fjxList}` | 按国家配置的价格、会员等级映射 |
| **发货附加项** | `/admin_b2b/shipOrderDetail/fjxList` | 订单发货时的附加项可用性、价格来源覆盖 |

### 1.2 数据结构流转

```
getCheckFjxList响应
    ↓
├─ check_data[]       (检品) → 验证可见性、数量
├─ fjx_data[]         (附加项) → 嵌套在分类下
│   └─ fjx_config_data[]
└─ user_fjx_data[]    (用户附加项) → 直接数组

扁平化处理 flatten_check_fjx_list()
    ↓
{
  checks: [],      // 所有检品项
  fjx: [],         // 所有附加项
  userFjx: [],     // 所有用户附加项
  all: []          // 统一编码格式: {kind: "check|fjx|user_fjx", item: {...}}
}

断言验证 run_check_fjx_assertions()
    ↓
├─ 数量断言 (minCheckCount)
├─ 必需性断言 (requireAnyAddon)
├─ 可见性断言 (visibleXxxUuids/hiddenXxxUuids)
├─ 价格来源断言 (pricingSources)
├─ 价格值断言 (prices/forbiddenPrices)
└─ 完整性断言 (requirePricingSourceOnPricedItems)
```

### 1.3 关键字段说明

#### 认证链
```python
resolve_user_credentials()
├─ 优先级1: 用例内指定的 userLoginToken
├─ 优先级2: 从 current_tokens.json 按 login_account 查询
├─ 优先级3: 从 ACCOUNT_LIST 配置在线登录
└─ 输出: (email, token, cookie)
```

#### 价格查询链
```python
price_of(item) -> float | None
根据优先级查找价格字段:
  1. user_price (用户自定义价)
  2. display_user_price (显示用户价)
  3. price (默认价)
  4. fee_info.user_price
  5. fee_info.talk_user_price
  6. fee_info.step_price
  7. fee_info.start_fee
```

#### 编码方案
```
项目唯一标识: "{kind}:{uuid}"
  Where kind ∈ {check, fjx, user_fjx}
  
示例: "fjx:c8f7e3d9-4a2b-11eb-ae93-0242ac120002"
```

---

## 2️⃣ 完整检查链路设计

### 2.1 执行流程图

```
┌─────────────────────────────────────────┐
│  01. 加载配置                            │
│     └─ member_pricing_complete_chain.json │
└────────────────┬────────────────────────┘
                 ↓
         ┌───────────────┐
         │  FOR EACH CASE│ (并行或串行)
         └───────┬───────┘
                 ↓
         ┌─────────────────────┐
         │ 02. 认证             │
         │ resolve_user_...()   │
         └────────┬────────────┘
                  ↓
      ┌───────────────────────────┐
      │ 03. 获取附加项列表        │
      │ /getCheckFjxList          │
      └────────┬──────────────────┘
               ▼
    ┌──────────────────────────┐
    │ 04. 扁平化数据            │
    │ flatten_check_fjx_list()  │
    └────────┬─────────────────┘
             ▼
    ┌──────────────────────────┐
    │ 05. 核心断言检查          │
    │ run_check_fjx_assertions()│
    │ ├─ 可见性验证            │
    │ ├─ 价格验证              │
    │ └─ 完整性验证            │
    └────────┬─────────────────┘
             ▼
  ┌────────────────────────────────┐
  │ 06-10. 并行检查 (可选)         │
  │ ├─ 费用预览 (run_cart_preview) │
  │ ├─ 快照校验 (run_snapshot_...) │
  │ ├─ 用户专属价 (run_admin_...)  │
  │ ├─ 服务价格 (run_service_...)  │
  │ └─ 发货附加项 (run_ship_fjx..) │
  └────────┬─────────────────────┘
           ▼
  ┌──────────────────┐
  │ 11. 聚合结果汇总 │
  │ InspectionRecorder│
  │ .to_result()     │
  └────────┬─────────┘
           ▼
       ┌────────────┐
       │ JSON输出   │
       │ emit_result│
       └────────────┘
```

### 2.2 配置文件结构

**路径**: `config/data/member_pricing_complete_chain.json`

```json
{
  "defaults": {
    "language": "korean",
    "currency": "KRW",
    "nation": "Korea",
    "apiBaseUrl": "https://www.globalshop.com"
  },
  
  "cases": [
    {
      "name": "美国账号-基础附加项链路",
      "enabled": true,
      
      "login_account": "us-test@example.com",
      "userLoginToken": "",
      "cookie": "",
      
      "language": "english",
      "currency": "USD",
      "nation": "USA",
      
      "checkFjxListPath": "/api_b2b/cartQuoteStep1/getCheckFjxList",
      "checkFjxListPayload": null,
      "cartDetailIds": ["cart_123", "cart_456"],
      "useStoredCartDetailIds": false,
      
      "expected": {
        "minCheckCount": 1,
        "requireAnyAddon": true,
        "requirePricingSourceOnPricedItems": false,
        
        "visibleCheckUuids": ["check_uuid_1"],
        "hiddenCheckUuids": [],
        "visibleFjxUuids": ["fjx_uuid_1", "fjx_uuid_2"],
        "hiddenFjxUuids": ["fjx_uuid_old"],
        
        "pricingSources": {
          "fjx:fjx_uuid_1": "manual",
          "fjx:fjx_uuid_2": "template"
        },
        
        "prices": {
          "fjx:fjx_uuid_1": 99.99,
          "fjx:fjx_uuid_2": 49.99
        },
        
        "forbiddenPrices": [0, -1, 999999]
      },
      
      "cartPreview": {
        "enabled": true,
        "path": "/api_b2b/cartQuoteStep1/getCheckFjxFeeTotal",
        "cartDetailIds": ["cart_123"],
        "useStoredCartDetailIds": false,
        "checkUuids": ["check_uuid_1"],
        "fjxUuids": ["fjx_uuid_1"],
        "userFjxUuids": [],
        "expectedTotal": 149.98
      },
      
      "snapshotChecks": [
        {
          "name": "用户视图快照",
          "path": "/api_b2b/cartQuoteStep1/getCheckFjxList",
          "auth": "user",
          "body": {"cart_detail_id": "cart_123"},
          "expectContains": ["check_data", "fjx_data"],
          "expectNotContains": ["error", "null"]
        }
      ],
      
      "servicePricing": {
        "enabled": true,
        "checkConfigUuid": "check_config_uuid_1",
        "fjxConfigUuid": "fjx_config_uuid_1",
        "expectNoBlankMemberLevel": true
      },
      
      "shipFjxChecks": [
        {
          "name": "发货附加项",
          "path": "/admin_b2b/shipOrderDetail/fjxList",
          "body": {"ship_order_id": "ship_123"},
          "requireAnyShipAddon": true,
          "requiredPricingSources": ["template", "manual"]
        }
      ]
    }
  ]
}
```

---

## 3️⃣ 实施方案

### 3.1 部署清单

**前置条件**:
- ✅ 已有有效的B2B账号和登录token
- ✅ 已配置 `config/settings.py` 中的 API_CONFIG
- ✅ 已安装 requests 库

**步骤**:

| # | 任务 | 负责 | 状态 |
|---|------|------|------|
| 1 | 编写配置文件 `member_pricing_complete_chain.json` | QA | ⏳ |
| 2 | 获取测试账号的token和cartDetailIds | Dev/QA | ⏳ |
| 3 | 收集UUIDs和预期价格 | QA | ⏳ |
| 4 | 执行脚本并调试 | QA | ⏳ |
| 5 | 集成到日常巡检流程 | DevOps | ⏳ |

### 3.2 测试账号准备

需要为不同国家/站点准备至少3个测试账号:

```python
{
  "US": {
    "email": "us-test@example.com",
    "password": "***",
    "currency": "USD",
    "nation": "USA",
    "language": "english",
    "sampleCartIds": ["cart_1001", "cart_1002"]
  },
  "Korea": {
    "email": "kr-test@example.com",
    "password": "***",
    "currency": "KRW",
    "nation": "Korea",
    "language": "korean",
    "sampleCartIds": ["cart_2001"]
  },
  "Europe": {
    "email": "eu-test@example.com", 
    "password": "***",
    "currency": "EUR",
    "nation": "Germany",
    "language": "german",
    "sampleCartIds": ["cart_3001"]
  }
}
```

### 3.3 关键数据收集工具

创建辅助脚本 `scripts/collect_member_pricing_uuids.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
收集会员定价检查所需的UUIDs和价格信息
"""
def main():
    # 1. 调用 getCheckFjxList API
    # 2. 遍历响应，收集所有UUID
    # 3. 输出到JSON格式的配置文件
    print("请运行以下命令手动收集UUIDs:")
    print("  py .\main.py member_pricing_complete_chain --mode=collect")
    pass
```

### 3.4 常见故障排查

| 症状 | 原因 | 解决方法 |
|------|------|--------|
| 附加项列表为空 | 账号无权限或购物车为空 | 检查cartDetailIds，确保购物车有有效项目 |
| token过期 | 凭据失效 | 更新current_tokens.json或重新登录 |
| 价格对齐失败 | epsilon阈值设置过小 | 检查almost_equal()中的epsilon(默认0.01) |
| 后台接口403 | 管理员权限不足 | 检查_admin_login()返回的token是否有效 |

---

## 4️⃣ 检查链路集成方案

### 4.1 与现有框架集成

在 `core/runner.py` 中注册此检查点:

```python
# core/runner.py

CHECKPOINT_REGISTRY = {
    # ... 其他检查点 ...
    "member_pricing_complete_chain": {
        "module": "checker.api.member_pricing_complete_chain",
        "function": "run",
        "category": "api_chain",
        "priority": 85,
        "timeout": 300,  # 5分钟
        "parallel": False,
        "description": "会员价格体系附加项专项巡检"
    }
}
```

### 4.2 定时执行配置

在 `config/rules/` 中添加规则配置:

```yaml
# config/rules/member_pricing_rules.yaml
name: 会员定价完整链路检查
target_endpoints:
  - /api_b2b/cartQuoteStep1/getCheckFjxList
  - /api_b2b/cartQuoteStep1/getCheckFjxFeeTotal
  - /admin_b2b/serviceCountryConfig/checkList
  - /admin_b2b/shipOrderDetail/fjxList

schedule:
  daily: "02:00 UTC"  # 凌晨2点运行
  on_deployment: true # 部署后立即运行
  
severity: HIGH
notification:
  on_failure: true
  channels: [email, dingtalk]
```

### 4.3 结果上报格式

脚本输出JSON格式（已通过 InspectionRecorder实现）:

```json
{
  "success": true,
  "message": "会员价格体系附加项专项巡检: PASS | Passed=45 Failed=0 Skipped=2 || ...",
  "status_code": 200,
  "expected": "会员价格/附加项只读巡检通过",
  "actual": "Passed=45 Failed=0 Skipped=2",
  "sub_results": {
    "check_1_name": {
      "success": true,
      "message": "check_1_name:PASS(...)",
      "status_code": 200,
      "expected": "PASS",
      "actual": "通过"
    },
    // ... 更多子项 ...
  }
}
```

---

## 5️⃣ 优化建议

### 5.1 短期优化（当前）
- [x] **编写配置示例** - 帮助使用者快速上手
- [x] **完善错误消息** - 便于故障诊断
- [ ] **并行执行可选检查** - 减少总耗时

### 5.2 中期优化（1-2月）
- [ ] **增加性能基准** - 跟踪接口性能变化
- [ ] **支持差分模式** - 对比历史数据，发现异常
- [ ] **导出Prometheus指标** - 集成监控系统

### 5.3 长期优化（3+月）
- [ ] **自动数据收集** - 定期从生产环境采样UUIDs
- [ ] **AI异常检测** - 识别异常价格、缺失字段
- [ ] **多租户支持** - 同时检查多个商业部门

---

## 📊 检查覆盖矩阵

| 功能模块 | API接口 | 覆盖度 | 备注 |
|---------|--------|------|------|
| 前台附加项展示 | getCheckFjxList | ⭐⭐⭐⭐⭐ | 核心功能，完全覆盖 |
| 费用预览 | getCheckFjxFeeTotal | ⭐⭐⭐⭐ | 需要购物车数据支持 |
| 快照一致性 | 自定义 | ⭐⭐⭐ | 可配扩展 |
| 后台配置数据 | /admin_b2b/* | ⭐⭐⭐ | 需管理员权限 |
| 发货流程 | shipOrderDetail | ⭐⭐⭐ | 订单相关 |

---

## 🎯 成功指标

部署完成后的验证:

```
✓ 日运行成功率 > 95%
✓ 平均耗时 < 3 分钟 (5个用例)
✓ 检查项数 > 40
✓ 子结果详度 > 100条断言消息
✓ 新增故障发现率 > 3个/月
```

---

## 📞 联系与支持

- **配置问题**: 参考 `member_pricing_complete_chain.json` 示例
- **API问题**: 检查 `API_CONFIG` 和网络连接
- **扩展开发**: 参照 `run_case()` 函数署名增加新检查点

