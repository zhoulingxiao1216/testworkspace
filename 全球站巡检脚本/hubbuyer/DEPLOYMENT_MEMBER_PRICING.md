# 会员定价检查点 - 集成方案与部署清单

## 📋 检查链路集成方案

### 方案架构图

```mermaid
graph TD
    A["members_pricing_complete_chain.py<br/>检查脚本"] -->|load_config| B["member_pricing_complete_chain.json<br/>配置文件"]
    B -->|cases[]| C{"FOR EACH<br/>CASE"}
    
    C -->|1.认证| D["resolve_user_credentials"]
    D -->|2.获取列表| E["POST /getCheckFjxList"]
    E -->|3.解析| F["flatten_check_fjx_list"]
    F -->|4.核心验证| G["run_check_fjx_assertions<br/>可见性/价格/完整性"]
    
    G -->|PASS| H{"启用<br/>可选检查?"}
    
    H -->|费用预览| I["run_cart_preview<br/>POST /getCheckFjxFeeTotal"]
    H -->|快照校验| J["run_snapshot_checks<br/>自定义API验证"]
    H -->|后台配置| K["run_admin_custom_pricing<br/>POST /listByUser"]
    H -->|国家服务价| L["run_service_pricing<br/>POST /serviceCountryConfig/*"]
    H -->|发货流程| M["run_ship_fjx_checks<br/>POST /shipOrderDetail/fjxList"]
    
    I & J & K & L & M -->|结果聚合| N["InspectionRecorder<br/>.to_result"]
    N -->|JSON输出| O["emit_result<br/>stdout"]
    O -->|解析| P["core/runner.py<br/>日志+报告生成"]
```

### 集成步骤

#### 第1步：验证前置条件

```bash
# 检查必要文件是否存在
ls -la config/data/member_pricing_complete_chain.json
ls -la checker/api/member_pricing_complete_chain.py

# 验证依赖安装
pip list | grep requests
```

#### 第2步：更新runner注册表

编辑 `core/runner.py`:

```python
# 在 CHECKPOINT_REGISTRY 中添加
"member_pricing_complete_chain": {
    "module": "checker.api.member_pricing_complete_chain",
    "function": "run",
    "category": "api_chain",    # 链路级检查
    "priority": 85,              # 按顺序执行
    "timeout": 300,              # 5分钟超时
    "parallel": False,           # 串行执行（要求登录状态）
    "description": "会员价格体系附加项专项巡检",
    "enabled": True,
    "depends_on": ["login"],     # 依赖前置登录
}
```

#### 第3步：准备测试数据

创建 `scripts/setup_member_pricing_data.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化会员定价检查所需的测试数据
"""
import json
import os
from config.settings import API_CONFIG
from core.path_manager import DATA_DIR

def collect_sample_data():
    """收集样本购物车ID和UUID"""
    config_path = os.path.join(DATA_DIR, "member_pricing_complete_chain.json")
    
    print("请登录后运行以下API获取必要信息:")
    print()
    print("1. 获取购物车ID列表:")
    print("   curl 'https://api.globalshop.com/api_b2b/cart/list' -H 'Cookie: ...'")
    print()
    print("2. 获取附加项UUID:")
    print("   curl -X POST 'https://api.globalshop.com/api_b2b/cartQuoteStep1/getCheckFjxList'")
    print("   -d '{\"cart_detail_id_arr\": [\"cart_id\"]}'")
    print()
    print("3. 获取用户UUID和国家代码:")
    print("   curl 'https://api.globalshop.com/api/user/profile' -H 'Cookie: ...'")
    print()
    print("收集上述信息后更新 config/data/member_pricing_complete_chain.json")

if __name__ == "__main__":
    collect_sample_data()
```

#### 第4步：配置示例用例

创建 `config/data/member_pricing_test_cases.json`:

```json
{
  "comment": "测试用例示例 - 请根据实际环境修改",
  
  "case_us": {
    "name": "美国账号-基础链路",
    "enabled": true,
    "login_account": "us-test-buyer@example.com",
    "language": "english",
    "currency": "USD",
    "nation": "USA",
    "cartDetailIds": [],
    "useStoredCartDetailIds": true,
    "expected": {
      "minCheckCount": 1,
      "requireAnyAddon": true
    }
  },
  
  "case_korea": {
    "name": "韩国账号-专项检查",
    "enabled": true,
    "login_account": "kr-test-buyer@example.com",
    "language": "korean",
    "currency": "KRW",
    "nation": "Korea",
    "cartDetailIds": [],
    "useStoredCartDetailIds": true,
    "expected": {
      "minCheckCount": 1,
      "requireAnyAddon": true
    },
    "cartPreview": {
      "enabled": true,
      "cartDetailIds": [],
      "useStoredCartDetailIds": true,
      "expectedTotal": null
    }
  },
  
  "case_strict": {
    "name": "严格断言-价格源与金额验证",
    "enabled": false,
    "login_account": "strict-test@example.com",
    "userMainUuid": "user_uuid_123",
    "countryCode": "US",
    "expected": {
      "minCheckCount": 2,
      "requireAnyAddon": true,
      "requirePricingSourceOnPricedItems": true,
      "pricingSources": {
        "check:uuid-001": "manual"
      },
      "prices": {
        "fjx:uuid-001": 99.99
      }
    }
  }
}
```

#### 第5步：配置调度规则

编辑或创建 `config/rules/member_pricing_rules.yaml`:

```yaml
checkpoint_name: "会员定价完整链路检查"

targets:
  frontend:
    - /api_b2b/cartQuoteStep1/getCheckFjxList
    - /api_b2b/cartQuoteStep1/getCheckFjxFeeTotal
  admin:
    - /admin_b2b/serviceCountryConfig/checkList
    - /admin_b2b/shipOrderDetail/fjxList

schedule:
  # 每天凌晨2点执行 (UTC)
  daily:
    time: "02:00"
    timezone: "UTC"
  
  # 部署后立即执行
  on_deployment: true
  
  # 允许手动触发
  on_demand: true

execution:
  timeout_seconds: 300
  max_parallel_users: 3
  retry_on_failure: true
  retry_count: 2
  retry_delay_seconds: 60

notifications:
  on_success: false
  on_failure: true
  
  channels:
    - type: "email"
      recipients: ["qa-team@example.com"]
    - type: "dingtalk"
      webhook: "${DINGTALK_WEBHOOK_URL}"
    - type: "slack"
      channel: "#global-site-checks"

severity: "HIGH"
impact_areas:
  - "B2B Frontend"
  - "Pricing System"
  - "Order Fulfillment"
```

#### 第6步：集成日志和报告

修改 `core/runner.py` 的检查点执行函数:

```python
def execute_member_pricing_check(checkpoint_config, task_config):
    """执行会员定价检查"""
    import importlib
    
    try:
        start_time = datetime.now()
        
        # 动态导入检查模块
        module = importlib.import_module("checker.api.member_pricing_complete_chain")
        result = module.run(task_config)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 补充元数据
        result.update({
            "checkpoint": "member_pricing_complete_chain",
            "executed_at": start_time.isoformat(),
            "elapsed_seconds": elapsed,
            "task_config": task_config,
        })
        
        # 生成报告
        if result.get("success"):
            logger.info("✅ 会员定价检查通过 | passed=%s failed=%s" % (
                result.get("sub_results", {}).get("passed", 0),
                result.get("sub_results", {}).get("failed", 0)
            ))
        else:
            logger.error("❌ 会员定价检查失败 | %s" % result.get("message"))
        
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "message": f"会员定价检查执行异常: {str(e)}",
            "status_code": 500,
            "checkpoint": "member_pricing_complete_chain"
        }
        logger.exception("会员定价检查异常", exc_info=e)
        return error_result
```

---

## 📊 部署检查清单

### 基础部署 (必需)

- [ ] **配置文件**
  - [ ] `config/data/member_pricing_complete_chain.json` 存在
  - [ ] 至少配置1个enabled=true的case
  - [ ] 指定有效的login_account或userLoginToken

- [ ] **认证准备**
  - [ ] 测试账号有有效的B2B权限
  - [ ] 账号密码存储在config的ACCOUNTS_POOL中
  - [ ] 或提前生成token存储在current_tokens.json

- [ ] **API配置**
  - [ ] API_CONFIG中的BASE_URL正确
  - [ ] 所有endpoint在ENDPOINTS中定义:
    - [ ] /api_b2b/cartQuoteStep1/getCheckFjxList
    - [ ] /api_b2b/cartQuoteStep1/getCheckFjxFeeTotal

- [ ] **环境验证**
  - [ ] requests库已安装: `pip show requests`
  - [ ] urllib3已安装（用于禁用SSL警告）
  - [ ] Python版本 >= 3.6

### 扩展部署 (可选但推荐)

- [ ] **后台检查**
  - [ ] 有效的管理员账号
  - [ ] 管理员token自动获取流程已验证
  - [ ] 后台API endpoints在config中定义

- [ ] **购物车数据**
  - [ ] 至少准备3个不同国家的样本购物车ID
  - [ ] 每个cartDetailId都有有效的商品和附加项
  - [ ] 费用预览数据已准备 (expectedTotal值)

- [ ] **集成配置**
  - [ ] core/runner.py中的CHECKPOINT_REGISTRY已更新
  - [ ] 调度规则config/rules/member_pricing_rules.yaml已创建
  - [ ] 通知渠道(email/dingtalk/slack)已配置

### 测试验证 (部署前必做)

- [ ] **单个用例测试**
  ```bash
  # 基础健康检查
  python main.py
  # 预期: PASS状态，passed >= 3
  ```

- [ ] **完整用例测试**
  ```bash
  # 使用配置文件中的第一个enabled case
  python main.py
  # 应输出JSON格式的完整结果
  ```

- [ ] **错误场景测试**
  ```bash
  # 测试认证失败场景
  # 修改login_account为无效值，应返回FAIL并给出明确错误
  ```

- [ ] **性能测试**
  ```bash
  # 测试执行时间
  time python main.py
  # 预期: 单用例下 < 3秒，5个用例 < 5分钟
  ```

---

## 🔧 故障恢复步骤

### 如果检查失败

1. **检查日志**
   ```bash
   tail -f logs/all_execution/latest.log
   # 查看详细错误信息
   ```

2. **验证配置**
   ```bash
   # 检查JSON语法
   python -m json.tool config/data/member_pricing_complete_chain.json
   ```

3. **测试认证**
   ```bash
   python -c "
   from config.data.login_data import ACCOUNTS_POOL
   print(ACCOUNTS_POOL)
   "
   ```

4. **测试API连接**
   ```bash
   curl -X POST https://api.globalshop.com/api_b2b/cartQuoteStep1/getCheckFjxList \
        -H 'Authorization: Bearer YOUR_TOKEN' \
        -d '{}'
   ```

---

## 📈 部署后监控

### 关键指标

| 指标 | 阈值 | 告警规则 |
|------|------|--------|
| 检查成功率 | > 95% | 连续3次失败 → 页面告警 |
| 平均耗时 | 3-5分钟 | 超过10分钟 → 性能告警 |
| 检查项数 | > 40 | 降低 > 20% → 数据告警 |
| 子项FAIL数 | = 0 | 任何FAIL → 高级告警 |

### 日常维护

```bash
# 每周检查执行历史
python scripts/check_execution_history.py --days=7

# 生成对比报告
python scripts/generate_trend_report.py member_pricing_complete_chain

# 清理过期日志
python -m core.cleanup_logs --days=30 --pattern="member_pricing*"
```

---

## 📞 支持和文档

| 文档 | 位置 | 用途 |
|------|------|------|
| 完整设计文档 | MEMBER_PRICING_CHECKPOINT_ANALYSIS.md | 了解设计细节 |
| 快速开始 | QUICK_START_MEMBER_PRICING.md | 3分钟快速上手 |
| 集成方案 | 本文档 | 部署和集成指南 |
| 配置示例 | config/data/member_pricing_complete_chain.json | 实际配置参考 |
| 维护脚本 | scripts/ | 运维自动化 |

---

## ✅ 部署完成检验

部署完成后执行：

```bash
# 运行基础检查
python main.py

# 验证输出格式
python main.py | python -m json.tool

# 检查日志输出
cat logs/巡检报告_*.md | grep -i "会员定价"

# 验证报告生成
ls -lh reports/巡检报告_*.md
```

**成功标志**：
- ✅ stderr无异常
- ✅ stdout输出有效JSON
- ✅ success字段为true（或majority检查通过）
- ✅ 生成了检查报告文件

---

## 🎯 V2.0 扩展方向

后续版本中计划支持：

- [ ] 多地区并行检查 (支持中国、亚洲、欧美分部同时运行)
- [ ] AI异常检测 (识别异常价格、缺失字段)
- [ ] 历史数据对比 (发现定价逐日变化趋势)
- [ ] 自动修复建议 (给出故障修复指导)

