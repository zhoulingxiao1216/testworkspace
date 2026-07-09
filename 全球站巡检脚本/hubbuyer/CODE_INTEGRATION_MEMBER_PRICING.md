# 会员定价检查点 - 代码集成示例

## 📝 目录概览

本文档提供了将member_pricing_complete_chain检查点集成到现有框架的代码示例。

---

## 1️⃣ 在runner.py中注册检查点

**文件**: `core/runner.py`

```python
# 在 CHECKPOINT_REGISTRY 字典中添加

CHECKPOINT_REGISTRY = {
    # ... 其他检查点 ...
    
    "member_pricing_complete_chain": {
        "module": "checker.api.member_pricing_complete_chain",
        "function": "run",
        "category": "api_chain",
        "priority": 85,
        "timeout": 300,
        "parallel": False,
        "description": "会员价格体系附加项专项巡检",
        "enabled": True,
        "depends_on": ["login"],
        "retry": {
            "max_attempts": 2,
            "delay_seconds": 60,
        },
        "notification": {
            "on_failure": True,
            "channels": ["email", "dingtalk"],
        },
    },
    
    # ... 继续其他检查点 ...
}


def execute_checkpoint(checkpoint_name, task_config=None):
    """执行指定的检查点"""
    task_config = task_config or {}
    checkpoint = CHECKPOINT_REGISTRY.get(checkpoint_name)
    
    if not checkpoint:
        return {
            "success": False,
            "message": f"检查点 {checkpoint_name} 不存在",
            "status_code": 404,
        }
    
    if not checkpoint.get("enabled", True):
        return {
            "success": False,
            "message": f"检查点 {checkpoint_name} 已禁用",
            "status_code": 503,
        }
    
    try:
        import importlib
        import time
        
        module = importlib.import_module(checkpoint["module"])
        func = getattr(module, checkpoint["function"])
        
        start = time.time()
        result = func(task_config)
        elapsed = time.time() - start
        
        # 补充元数据
        result.update({
            "checkpoint": checkpoint_name,
            "elapsed_seconds": elapsed,
            "_checkpoint_config": checkpoint,
        })
        
        return result
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"检查点执行异常: {str(e)}",
            "status_code": 500,
            "error_detail": traceback.format_exc(),
            "checkpoint": checkpoint_name,
        }
```

---

## 2️⃣ 在main.py中添加调用

**文件**: `main.py`

```python
# 在主执行流程中添加会员定价检查

import json
from core import runner
from core.logger import logger

def main():
    """主检查点执行流程"""
    
    # 当前执行的检查
    checkpoints_to_run = [
        "login",  # 必须首先执行登录
        "member_pricing_complete_chain",  # 会员定价检查
        "payment",
        "order_audit",
        # ... 其他检查 ...
    ]
    
    results = {}
    
    for cp in checkpoints_to_run:
        try:
            logger.info(f"执行检查点: {cp}")
            result = runner.execute_checkpoint(cp)
            results[cp] = result
            
            if result.get("success"):
                logger.info(f"✅ {cp} 通过")
            else:
                logger.warning(f"⚠️ {cp} 失败: {result.get('message')}")
                
        except Exception as e:
            logger.exception(f"❌ {cp} 执行异常", exc_info=e)
            results[cp] = {
                "success": False,
                "message": str(e),
                "status_code": 500,
            }
    
    # 生成最终报告
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "total_checkpoints": len(results),
        "passed": sum(1 for r in results.values() if r.get("success")),
        "failed": sum(1 for r in results.values() if not r.get("success")),
        "results": results,
    }
    
    print(json.dumps(final_report, ensure_ascii=False, indent=2))
    return final_report


if __name__ == "__main__":
    from datetime import datetime
    main()
```

---

## 3️⃣ 在报告生成器中添加支持

**文件**: `core/report_generator.py`

```python
def generate_checkpoint_report(checkpoint_result, checkpoint_name):
    """为单个检查点生成详细报告"""
    
    template = """
## 检查点: {checkpoint_name}
    
**状态**: {status}  
**执行时间**: {elapsed_seconds}s  
**通过项**: {passed}  
**失败项**: {failed}  
**跳过项**: {skipped}  

### 主要消息
{main_message}

### 子结果详情
{sub_results_table}

### 关键指标
- 成功率: {success_rate}%
- 总断言数: {total_assertions}
- 执行时间: {elapsed_seconds}s
    """
    
    passed = 0
    failed = 0
    skipped = 0
    sub_results = checkpoint_result.get("sub_results", {})
    
    for name, item in sub_results.items():
        if item.get("success"):
            passed += 1
        elif "SKIP" in item.get("message", ""):
            skipped += 1
        else:
            failed += 1
    
    # 生成子结果表格
    sub_results_table = "| 检查项 | 状态 | 消息 |\n|------|------|------|\n"
    for name, item in list(sub_results.items())[:20]:
        status = "✅" if item.get("success") else "❌"
        msg = item.get("message", "")[:50]
        sub_results_table += f"| {name} | {status} | {msg} |\n"
    
    if len(sub_results) > 20:
        sub_results_table += f"| ... | ... | 共{len(sub_results)}项 |\n"
    
    report = template.format(
        checkpoint_name=checkpoint_name,
        status="✅ PASS" if checkpoint_result.get("success") else "❌ FAIL",
        elapsed_seconds=checkpoint_result.get("elapsed_seconds", 0),
        passed=passed,
        failed=failed,
        skipped=skipped,
        main_message=checkpoint_result.get("message", ""),
        sub_results_table=sub_results_table,
        success_rate=int(100 * passed / (passed + failed) if passed + failed > 0 else 0),
        total_assertions=len(sub_results),
    )
    
    return report


# 在主报告生成函数中调用
def generate_full_report(all_results):
    """生成完整的检查报告"""
    
    report_content = """# 全球站巡检完整报告\n\n"""
    report_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # 摘要
    total = len(all_results)
    passed = sum(1 for r in all_results.values() if r.get("success"))
    failed = total - passed
    
    report_content += f"""## 摘要
- 总检查数: {total}
- 通过: {passed}
- 失败: {failed}
- 成功率: {100*passed/total:.1f}%

"""
    
    # 详细结果
    for cp_name, cp_result in all_results.items():
        report_content += generate_checkpoint_report(cp_result, cp_name)
        report_content += "\n\n---\n\n"
    
    return report_content
```

---

## 4️⃣ 在日志管理中添加支持

**文件**: `core/logger.py`

```python
def log_checkpoint_result(checkpoint_name, result):
    """记录检查点结果"""
    
    logger = get_logger("checkpoint")
    
    if result.get("success"):
        logger.info(f"✅ {checkpoint_name} 通过", extra={
            "checkpoint": checkpoint_name,
            "status": "PASS",
            "elapsed": result.get("elapsed_seconds"),
            "passed": count_passed(result),
            "failed": count_failed(result),
        })
    else:
        logger.error(f"❌ {checkpoint_name} 失败", extra={
            "checkpoint": checkpoint_name,
            "status": "FAIL",
            "message": result.get("message"),
            "detail": result.get("error_detail"),
        })
    
    # 记录子结果摘要
    sub_results = result.get("sub_results", {})
    if sub_results:
        logger.debug(f"子结果: {len(sub_results)}项", extra={
            "checkpoint": checkpoint_name,
            "sub_results_count": len(sub_results),
        })


def count_passed(result):
    """统计通过的sub_result数"""
    return sum(1 for r in result.get("sub_results", {}).values() if r.get("success"))


def count_failed(result):
    """统计失败的sub_result数"""
    return sum(1 for r in result.get("sub_results", {}).values() if not r.get("success"))
```

---

## 5️⃣ 配置日程任务

**文件**: `config/schedule.yaml`

```yaml
scheduled_tasks:
  
  # 会员定价检查 - 日常
  member_pricing_daily:
    checkpoint: "member_pricing_complete_chain"
    schedule: "0 2 * * *"  # 每天凌晨2点 (UTC)
    timezone: "UTC"
    timeout: 300
    
    config:
      # 使用基础配置（minimal）
      data_file: "config/data/member_pricing_complete_chain.json"
    
    notification:
      on_failure: true
      channels:
        - email:
            to: "qa-team@example.com,dev-lead@example.com"
            subject: "[告警] 会员定价检查失败"
        - dingtalk:
            webhook: "${DINGTALK_WEBHOOK_URL}"
            at_all: false
  
  # 会员定价检查 - 周合并
  member_pricing_weekly_strict:
    checkpoint: "member_pricing_complete_chain"
    schedule: "0 1 * * 0"  # 每周日凌晨1点
    timezone: "UTC"
    timeout: 600  # 10分钟，因为会跑更多的严格case
    
    config:
      # 使用严格配置
      data_file: "config/data/member_pricing_complete_chain_strict.json"
    
    notification:
      on_failure: true
      on_success: true  # 周报告也通知
      channels:
        - email:
            to: "qa-team@example.com"
            subject: "[报告] 周度会员定价巡检汇总"
        - dingtalk:
            webhook: "${DINGTALK_WEBHOOK_WEEKLY_URL}"
```

---

## 6️⃣ 添加API端点（可选）

**文件**: `checker/web/api.py`

```python
from flask import Flask, request, jsonify
from checker.api import member_pricing_complete_chain

app = Flask(__name__)

@app.route("/api/checkpoint/member_pricing", methods=["POST"])
def trigger_member_pricing_check():
    """
    手动触发会员定价检查
    
    POST body:
    {
        "login_account": "optional@example.com",
        "config_file": "optional_config_path.json",
        "timeout": 300
    }
    """
    try:
        data = request.get_json() or {}
        task_config = {
            "login_account": data.get("login_account"),
            "data_file": data.get("config_file"),
        }
        
        result = member_pricing_complete_chain.run(task_config)
        
        return jsonify({
            "status": "success" if result.get("success") else "failed",
            "result": result,
        }), (200 if result.get("success") else 400)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/api/checkpoint/member_pricing/results", methods=["GET"])
def get_member_pricing_results():
    """获取最近的检查结果"""
    import json
    from pathlib import Path
    from core.path_manager import DATA_DIR
    
    try:
        result_file = Path(DATA_DIR) / "member_pricing_latest_result.json"
        
        if not result_file.exists():
            return jsonify({"error": "暂无检查结果"}), 404
        
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## 7️⃣ 在CI/CD中集成

**文件**: `.github/workflows/global-site-checks.yml` (GitHub Actions示例)

```yaml
name: 全球站巡检 - 会员定价

on:
  schedule:
    # 每天北京时间上午10点(UTC+8) 运行
    - cron: "0 2 * * *"
  workflow_dispatch:  # 允许手动触发

jobs:
  member_pricing_check:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: 设置Python环境
        uses: actions/setup-python@v2
        with:
          python-version: "3.9"
      
      - name: 安装依赖
        run: |
          pip install -r requirements.txt
      
      - name: 运行会员定价检查
        env:
          LOGIN_ACCOUNT: ${{ secrets.TEST_ACCOUNT_EMAIL }}
          LOGIN_PASSWORD: ${{ secrets.TEST_ACCOUNT_PASSWORD }}
          API_BASE_URL: ${{ secrets.API_BASE_URL }}
        run: |
          python -c "
          from checker.api import member_pricing_complete_chain
          result = member_pricing_complete_chain.run({
              'login_account': '${{ secrets.TEST_ACCOUNT_EMAIL }}'
          })
          import sys
          sys.exit(0 if result['success'] else 1)
          "
      
      - name: 生成报告
        if: always()
        run: |
          python -m core.report_generator --checkpoint=member_pricing_complete_chain
      
      - name: 上传报告
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: member-pricing-report
          path: reports/巡检报告_*.md
      
      - name: 通知钉钉
        if: failure()
        uses: ding-team/dingtalk-action@v1
        with:
          webhook: ${{ secrets.DINGTALK_WEBHOOK }}
          message: "❌ 会员定价检查失败，请查看报告"
```

---

## 8️⃣ 监控和告警配置

**文件**: `config/monitoring/member_pricing_alerts.yaml`

```yaml
alerts:
  - name: "会员定价检查失败"
    condition: |
      checkpoint_status{checkpoint="member_pricing_complete_chain"} == 0
    duration: "5m"
    severity: "critical"
    actions:
      - dingtalk:
          title: "🚨 会员定价检查失败"
          message: "会员定价检查在过去5分钟内失败！"
          at_users: ["@qa-team"]
      - email:
          to: "qa-team@example.com,dev-lead@example.com"
          subject: "[紧急] 会员定价检查失败"
  
  - name: "会员定价检查超时"
    condition: |
      checkpoint_duration_seconds{checkpoint="member_pricing_complete_chain"} > 600
    duration: "1m"
    severity: "warning"
    actions:
      - dingtalk:
          title: "⚠️ 会员定价检查性能降低"
          message: "检查耗时超过10分钟，请检查API性能"
  
  - name: "会员定价检查频繁失败"
    condition: |
      rate(checkpoint_failures{checkpoint="member_pricing_complete_chain"}[1h]) > 0.3
    duration: "10m"
    severity: "high"
    actions:
      - email:
          to: "ops-team@example.com"
          subject: "[警告] 会员定价检查持续不稳定"
```

---

## 9️⃣ 数据持久化

**文件**: `core/persistence.py` (新增支持)

```python
import json
from pathlib import Path
from datetime import datetime
from core.path_manager import DATA_DIR

def save_checkpoint_result(checkpoint_name, result):
    """保存检查点结果到本地"""
    
    # 保存最新结果
    latest_file = Path(DATA_DIR) / f"{checkpoint_name}_latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 保存历史结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_dir = Path(DATA_DIR) / "checkpoint_history"
    history_dir.mkdir(exist_ok=True)
    
    history_file = history_dir / f"{checkpoint_name}_{timestamp}.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return str(latest_file), str(history_file)


def load_checkpoint_history(checkpoint_name, days=7):
    """加载检查点的历史结果"""
    
    history_dir = Path(DATA_DIR) / "checkpoint_history"
    if not history_dir.exists():
        return []
    
    cutoff = datetime.now().timestamp() - (days * 86400)
    results = []
    
    for f in sorted(history_dir.glob(f"{checkpoint_name}_*.json")):
        if f.stat().st_mtime > cutoff:
            with open(f, "r", encoding="utf-8") as file:
                results.append(json.load(file))
    
    return results
```

---

## 🔟 测试脚本

**文件**: `tests/test_member_pricing_integration.py`

```python
import unittest
import json
from checker.api import member_pricing_complete_chain
from core import runner

class TestMemberPricingIntegration(unittest.TestCase):
    
    def test_basic_execution(self):
        """测试基础执行"""
        result = member_pricing_complete_chain.run()
        
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("message", result)
        self.assertIn("status_code", result)
    
    def test_with_custom_config(self):
        """测试自定义配置"""
        task_config = {
            "login_account": "test@example.com",
        }
        result = member_pricing_complete_chain.run(task_config)
        
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
    
    def test_runner_integration(self):
        """测试runner集成"""
        result = runner.execute_checkpoint("member_pricing_complete_chain")
        
        self.assertIsInstance(result, dict)
        self.assertIn("checkpoint", result)
        self.assertEqual(result["checkpoint"], "member_pricing_complete_chain")
    
    def test_json_output_format(self):
        """测试JSON输出格式"""
        result = member_pricing_complete_chain.run()
        
        # 应能序列化为JSON
        json_str = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(json_str)
        
        self.assertEqual(result, parsed)


if __name__ == "__main__":
    unittest.main()
```

---

## 📦 完整集成检项

```bash
# 检查清单

☐ 1. runner.py 已注册检查点
☐ 2. main.py 已添加执行调用
☐ 3. report_generator.py 已提供报告支持
☐ 4. logger.py 已处理日志格式
☐ 5. schedule.yaml 已配置日程任务
☐ 6. 监控告警规则已部署
☐ 7. CI/CD集成已配置
☐ 8. 测试用例已编写
☐ 9. 文档已完善
☐ 10. 本地验证已通过
```

---

## ✅ 验证集成

```bash
# 验证集成成功的步骤

# 1. 检查注册
python -c "
from core.runner import CHECKPOINT_REGISTRY
print('member_pricing_complete_chain' in CHECKPOINT_REGISTRY)
"

# 2. 运行检查
python main.py

# 3. 查看结果
tail -f logs/all_execution/*.log | grep member_pricing

# 4. 验证报告
ls -lh reports/巡检报告_*.md | head -1
```

---

