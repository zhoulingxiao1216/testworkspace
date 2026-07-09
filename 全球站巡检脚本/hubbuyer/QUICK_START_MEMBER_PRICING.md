# 会员定价检查点 - 快速开始指南

## 📘 概述

`member_pricing_complete_chain.py` 是全球站B2B的**会员价格体系完整链路检查脚本**。它验证以下关键业务流程：

```
前台选择检品 → 添加附加项 → 计算费用 → 预览总额 → 后台配置验证 → 发货执行
```

---

## 🚀 快速开始 (3分钟)

### 步骤1: 基础检查 (推荐首次使用)

```bash
# 使用当前登录账号进行只读健康检查
cd d:\test_workspace\全球站巡检脚本\hubbuyer
python main.py
```

这会调用 `member_pricing_complete_chain.py:run()` 并检查：
- ✅ 附加项列表可访问性
- ✅ 至少存在1个检品
- ✅ 至少存在1个附加项
- ✅ 价格字段非空

**预期输出**: 
```json
{
  "success": true,
  "message": "会员价格体系附加项专项巡检: PASS | Passed=3 Failed=0 Skipped=0",
  "status_code": 200,
  "sub_results": { ... }
}
```

---

## 🔧 详细配置

### 配置文件位置
```
config/data/member_pricing_complete_chain.json
```

### 常见配置场景

#### 场景1: 验证特定附加项的价格

```json
{
  "name": "检验特定FJX价格正确性",
  "login_account": "test@example.com",
  "cartDetailIds": ["cart_123", "cart_456"],
  
  "expected": {
    "minCheckCount": 1,
    "requireAnyAddon": true,
    "visibleFjxUuids": ["fjx-uuid-001", "fjx-uuid-002"],
    
    "prices": {
      "fjx:fjx-uuid-001": 99.99,
      "fjx:fjx-uuid-002": 49.99
    },
    
    "forbiddenPrices": [0, -1, 999]
  }
}
```

**关键字段解释**:
- `visibleFjxUuids`: 期望可见的附加项UUID列表
- `prices`: 期望的价格映射 (格式: `"kind:uuid": price`)
- `forbiddenPrices`: 禁止出现的价格 (旧价格、错误价格)

#### 场景2: 验证费用预览准确性

```json
{
  "cartPreview": {
    "enabled": true,
    "cartDetailIds": ["cart_123"],
    "fjxUuids": ["fjx-uuid-001"],
    "expectedTotal": 149.98
  }
}
```

运行此用例会：
1. 调用 `/api_b2b/cartQuoteStep1/getCheckFjxFeeTotal`
2. 验证返回的 `total_check_fjx_fee` 等于期望值
3. 记录任何差异

#### 场景3: 国家服务价配置检查

```json
{
  "countryCode": "US",
  
  "servicePricing": {
    "enabled": true,
    "checkConfigUuid": "check-config-001",
    "fjxConfigUuid": "fjx-config-001",
    "expectNoBlankMemberLevel": true
  }
}
```

这会验证：
- 国家级服务价配置数据完整性
- 所有级别都有对应的费用信息

#### 场景4: 快照一致性验证

```json
{
  "snapshotChecks": [
    {
      "name": "报价详情保留定价来源",
      "auth": "user",
      "path": "/api_b2b/quoteDetail/detail",
      "body": {"quote_no": "B2B-123456"},
      "expectContains": ["pricing_source", "check_data"],
      "expectNotContains": ["error"]
    }
  ]
}
```


## 📊 检查输出解读

### 输出格式

```json
{
  "success": true,
  "message": "会员价格体系附加项专项巡检: PASS | Passed=45 Failed=0 Skipped=2",
  "status_code": 200,
  "expected": "会员价格/附加项只读巡检通过",
  "actual": "Passed=45 Failed=0 Skipped=2",
  "sub_results": {
    "test_case_name-check_point": {
      "success": true,
      "message": "test_case_name-check_point:PASS(验证成功)",
      "status_code": 200,
      "expected": "PASS",
      "actual": "实际值描述"
    }
  }
}
```

### 子结果代码解读

| 消息前缀 | 含义 | 示例 |
|---------|------|------|
| `test_name-附加项列表接口:PASS` | 接口调用成功 | ✅ |
| `test_name-检品列表数量:PASS` | 检品数量满足条件 | ✅ |
| `test_name-fjx-uuid-001可见:PASS` | 指定UUID可见 | ✅ |
| `test_name-fjx-uuid-001价格:PASS` | 价格匹配预期 | ✅ |
| `test_name-费用预览接口:FAIL` | 费用预览API异常 | ❌ |

---

## 🔍 故障诊断

### 问题1: "缺少 B2B token/cookie"

**原因**: 无有效的用户认证信息

**解决方案**:
```json
{
  "login_account": "your-email@example.com",
  // OR
  "userLoginToken": "actual-token-value"
}
```

如果两者都未提供，脚本会尝试：
1. 从 `current_tokens.json` 加载
2. 从 ACCOUNTS_POOL 在线登录

### 问题2: "check_data 数量不足"

**原因**: 附加项列表API返回空或检品数量 < minCheckCount

**解决方案**:
```python
# 选项A: 指定有效的购物车ID
"cartDetailIds": ["cart_id_with_items"]

# 选项B: 调整最小期望值
"expected": {
  "minCheckCount": 0  // 改为0
}
```

### 问题3: "价格对齐失败 actual=XXX expected=YYY"

**原因**: 实际价格与期望价格差异 > 0.01 (默认epsilon)

**解决方案**:

代码中修改epsilon（在 `almost_equal()` 函数）:
```python
def almost_equal(left, right, epsilon=0.01):  # 改为更大的值如 0.1
    ...
```

或在配置中设置宽松的期望:
```json
"prices": {
  "fjx:uuid-001": 99.99  // 使用区间而非精确值
}
```

### 问题4: "后台接口 403"

**原因**: 缺少管理员权限或token无效

**解决方案**:
```json
{
  "adminCustomPricing": {
    "enabled": false  // 临时禁用后台检查
  }
}
```

或检查 `_admin_login()` 是否成功（在 `order_audit.py` 中）


## 📈 监控与报告

### 集成日志系统

脚本自动输出JSON，可被 `core/logger.py` 和 `core/report_generator.py` 处理：

```python
# main.py 或 runner.py
result = member_pricing_complete_chain.run(task_config)
# 自动生成 ./logs/ 中的日志和报告
```

### 性能基准

典型运行时间 (单个用例):
| 检查模块 | 耗时 | 备注 |
|---------|------|------|
| 附加项列表 | 0.5-1s | 网络存在延迟 |
| 费用预览 | 0.5-1s | 需要cartDetailIds |
| 后台检查 | 1-2s | 需管理员登录 |
| 发货附加项 | 1-2s | 需订单信息 |
| **总计(5项)** | **3-5分钟** | 5个用例并行 |

---

## 💡 高级用法

### 自定义验证逻辑

如需扩展检查，修改 `run_case()` 函数署名中的 `recorder`:

```python
def run_custom_fjx_check(config, case, headers, recorder):
    """自定义检查示例"""
    name = case.get("name") or "未命名"
    
    # 调用API
    response = request_json(base_url, path, headers, payload)
    
    # 自定义断言
    data = response_data(response)
    recorder.assert_(
        condition=len(data.get("fjx", [])) > 0,
        name=f"{name}-自定义检查",
        fail_message="未找到任何附加项"
    )
    
    return recorder
```

然后在配置中引用:
```json
{
  "customChecks": [
    {
      "type": "custom_fjx_check",
      "enabled": true
    }
  ]
}
```

### 批量执行多个用例

```bash
# 当前支持，直接在JSON中添加多个case对象
python main.py
# 脚本会对每个case[i]执行完整的检查链路
```

### 生成HTML报告

```bash
# 结合 report_generator.py
python main.py | python core/report_generator.py --format=html
# 输出: ./reports/巡检报告_YYYYMMDD_HHMMSS.html
```

---

## ✅ 检查清单

部署前确认：

- [ ] 配置文件存在: `config/data/member_pricing_complete_chain.json`
- [ ] 至少有1个enabled=true的case
- [ ] login_account或userLoginToken有效
- [ ] 如需费用预览，cartDetailIds不为空
- [ ] 如需后台检查，有管理员账号访问权限
- [ ] config/settings.py中API_CONFIG配置正确
- [ ] 已运行 `requirements.txt` 中的依赖安装

---

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `checker/api/member_pricing_complete_chain.py` | 检查实现 |
| `config/data/member_pricing_complete_chain.json` | 检查配置 |
| `MEMBER_PRICING_CHECKPOINT_ANALYSIS.md` | 完整设计文档 |
| `core/logger.py` | 日志管理 |
| `core/report_generator.py` | 报告生成 |

---

## 🤝 获取帮助

- **配置问题** → 查看 `config/data/member_pricing_complete_chain.json` 中的 `exampleStrongAssertions`
- **API问题** → 检查 `API_CONFIG` 中的endpoints是否正确
- **扩展开发** → 参照 `run_ship_fjx_checks()` 函数写法

