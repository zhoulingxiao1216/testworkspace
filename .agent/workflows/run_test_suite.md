---
description: 测试用例执行引擎 — 按优先级驱动用例执行、结果记录与缺陷报告生成
---

# Agent 2 (测试执行官) 自动化执行引擎

> **执行提示**：本工作流专属服务于 **Agent 2 (测试执行官)**。当用户通过自然语言或 `/run_test_suite` 唤醒时，Agent 2 开始作业。
> Agent 2 将自动读取目标项目的交接清单或测试用例，按优先级编排执行队列，通过浏览器实操和 API 调用逐例验证，最终生成执行报告与缺陷清单。下文描述中的"引擎"即完全指代 Agent 2 本身。

**【前置加载】**

- 引擎启动后，必须先读取 `.agent/dependencies.yaml`，并使用 `deps.<alias>` 解析本文所有依赖路径。
- 必须先读取 `deps.skill_agent2_test_execution` 获取完整的执行约束与行为规范。
- 读取 `deps.execution_report_spec` 与 `deps.defect_report_spec`，锁定报告格式标准。
- **Memory 召回**: Agent 2 必须读取 `deps.memory_readme`，随后按项目名召回：
  - `deps.memory_shared_project_registry`
  - `deps.memory_shared_environment_registry`
  - `deps.memory_shared_known_issues`
  - `deps.memory_agent2_selector`
  - `deps.memory_agent2_api`
  - `deps.memory_agent2_env_blockers`
  - `deps.memory_agent2_execution_history`
  - `deps.memory_agent2_db_mock_audit`
  - `deps.memory_exchange_agent2_review_feedback`
  - `deps.memory_exchange_needs_more_cases`
- **Memory 使用边界**: Memory 只用于减少重复探索，不能覆盖当前用例、当前页面事实或环境预检结果。发现冲突时，以实时观察为准，并将旧记忆标记为 stale 或写入 `deps.evolution_rejected_learnings`。

**【工具能力预检】**

进入 E1 前，Agent 2 必须完成以下工具检查，并将结果写入执行日志：

| 工具能力 | 检查项 | 不通过处理 |
|----------|--------|------------|
| `playwright` | Python 可导入 `playwright.sync_api`，Chromium 可 `headless=True` 启动 | 标记 `Blocked-ENV`，停止执行 |
| `screenshots/` | 目标执行报告截图目录存在或可创建，且可写入 `.webp/.png` | 标记 `Blocked-ENV`，停止执行 |
| `screenshot` | Windows PowerShell 截图 helper 或等价系统截图能力可用 | 记录 `[Tool-Degrade] screenshot unavailable`，常规执行继续 |
| `playwright-interactive` | `js_repl` 已启用且可加载 Playwright 持久会话 | 记录 `[Tool-Degrade] playwright-interactive unavailable`，常规执行继续 |
| `db_helper` | `deps.runtime_db_helper` 存在；如用例需要 DB，确认 `deps.project_env_file_pattern` 存在且可通过 dry-run 校验 SQL 守卫 | 不需要 DB 时记录跳过；需要 DB 但缺失时标记 `Blocked-ENV` 或禁用 DB Mock Seed |
| `db_runtime` | 若需要真实连接数据库，Python 环境可导入 `pymysql`；若启用 SSH 隧道，还可导入 `sshtunnel` | 记录 `[Tool-Degrade] db_runtime unavailable`；DB Mock Seed 不可用，API/UI 通道继续 |

> `playwright-interactive` 只作为复杂问题诊断层，不是 E1/E3 的硬依赖；不得因为它不可用而阻塞常规 Headless 执行。

---

**【E1 环境预检（硬性门控）】**

- 确认目标测试环境 URL 可达（通过浏览器打开首页 + 检查 HTTP 状态码）。
- 使用测试账号执行登录验证（浏览器实操登录 → 校验登录态 cookie/token）。
- 读取项目 `superpowers.md` 中的【测试数据画像】段落，校验所需前置数据是否就绪。
- 截图记录环境状态，命名为 `env_precheck.webp`。
- **门控判定**：
  - **通过**：输出"环境预检通过，进入队列编排"。
  - **不通过**：生成阻塞报告（列明失败项），**强制中断执行**，等待人工修复后重启。

**【E2 队列编排】**

- 读取目标项目的 `deps.project_handoff_manifest_pattern`。
- 解析清单中的 `total_cases`、`env_requirements` 明确预检信息，按 `execution_queue` 与 `priority_distribution` 构建执行队列。
- 若无交接清单，作为后备方案降级为读取 Markdown 用例集文件（匹配 `*用例*.md`）并解析 `#### TC-` 锚点。
- 遵循降序优先级：
  ```
  Critical [SmokeTest] → Critical → High → Medium → Low
  ```
- 输出执行队列清单（表格形式），**挂起等待人工确认**。
- 用户可回复：
  - "全部执行" → 进入 E3。
  - "跳过 TC-XX-NNN, TC-XX-NNN" → 将指定用例标记 Skip 后进入 E3。
  - "仅执行 SmokeTest" → 仅执行带 `[SmokeTest]` 标签的用例。

**【E3 逐例执行】**

对队列中每条用例执行以下流程：

1. **读取用例**：提取"前置条件"、"操作步骤"、"预期结果"三个字段。
2. **前置数据自愈检查**：验证当前环境满足度。
   - **满足**：进入步骤执行。
   - **不满足**：禁止直接标记 Blocked！必须启动自愈协议，按顺序尝试：
     1. Layer 1 API Direct 构造数据；
     2. Layer 2 Playwright Headless UI 静默构造；
     3. Layer 1-DB DB Mock Seed 兜底，仅当 `deps.runtime_db_helper --mode mock_write` 的全部门禁通过。
   - 构造产生的数据在随后的执行日志中必须打上 `[Auto-Setup]` 标签；DB Mock Seed 还必须追加 `[DB-Mock-Seed]` 并写入 `deps.memory_agent2_db_mock_audit`。
   - **自愈失败**：若构造失败，才标记为 Blocked 并跳至下一条。
3. **逐步执行操作**：
   - **UI 操作**：按用例执行路由决策树选择执行层：
     - Layer 1 (API Direct)：纯数据操作，run_command 执行 curl/requests
     - Layer 2 (Playwright Headless)：UI 操作，生成无头脚本后台运行（不抢占键鼠）
     - Layer 3 (browser_subagent 只读)：仅用于选择器发现，不执行写操作
     - Layer 3.5 (playwright-interactive 条件诊断)：仅在 `js_repl` 可用且 Layer 2 连续失败时用于持久会话排查，诊断后必须回到 Layer 2/Layer 1 复核
   - **API 验证**：调用 `run_command` 执行 curl/脚本请求，捕获响应 JSON 做断言。
   - **混合操作**：先 Layer 2 UI 产生数据 → 再 Layer 1 API 校验后端状态 → 再 Layer 2 UI 检查前端展示（三方一致性）。
   - **写操作分级**：按「安全写操作判定」执行（🟢无风险 / 🟡可控+快照还原 / 🔴高危+人工确认）。
4. **记录结果**：将每步的实际响应写入执行日志。
5. **关键步骤自动截图**：优先通过 Playwright `page.screenshot()` 保存至 `执行报告/screenshots/`；若使用系统级 `screenshot` 兜底，必须标注 `[Evidence-Source: screenshot]`。

**【E4 结果判定】**

- 将每条用例的实际结果与预期结果逐项对比。
- 判定状态：✅ Pass / ❌ Fail / ⚠️🌐 Blocked-ENV / ⚠️📊 Blocked-DATA / ⚠️🔗 Blocked-DEP / ⏭️ Skip。
- **Fail 即时处理**：
  1. 在发现偏差的瞬间通过 Playwright 截图（`{用例编号}_fail.webp`）。
  2. 立即生成缺陷记录条目（格式遵循《缺陷记录模板》，包含严重性/缺陷类型/根因分析）。
  3. 在执行日志中标注"关联缺陷：BUG-XX-NNN"。
- **继续执行**：不因单条 Fail 中断整体队列，除非环境被破坏。

**【E5 报告生成】**

- 在 `deps.project_execution_report_dir_pattern` 目录下生成两份文件：
  1. `执行报告_YYYY-MM-DD.md`：含执行概览统计 + SmokeTest 结果 + 全量执行日志。
  2. `缺陷清单_YYYY-MM-DD.md`：仅包含 Fail 用例的缺陷详情（若全部 Pass 则不生成）。
- 格式严格遵循 `deps.execution_specs_dir` 下的对应规范文档。
- 在控制台输出执行概览摘要。

**【E6 Memory 沉淀与自进化候选】**

- 执行结束后，Agent 2 必须追加一条 JSONL 记录到 `deps.memory_agent2_execution_history`，字段至少包含 `date/project/role/event/summary/status`，不得包含密码、Token、Cookie 或客户隐私数据。
- 若本轮发现稳定选择器或页面路径，更新 `deps.memory_agent2_selector`，并标记 `confidence`。
- 若本轮验证出稳定 API 端点、参数或断言，更新 `deps.memory_agent2_api`，不得写入鉴权密钥。
- 若出现可复用环境阻塞与恢复方式，更新 `deps.memory_agent2_env_blockers`。
- 若本轮使用 DB Mock Seed，确认 `deps.memory_agent2_db_mock_audit` 已记录执行元数据；不得写入原始 SQL、密码、Token、Cookie 或客户隐私数据。
- 若发现 `[需补充用例]` 或可执行性缺口，写入 `deps.memory_exchange_needs_more_cases`，等待 Agent 1 处理。
- 达到晋升条件的稳定经验，写入 `deps.evolution_promotion_candidates`，等待人工审查。

**【终止通告】**

- 输出最终执行概览表格。
- 输出本轮 Memory 更新摘要：列明写入了哪些 memory 文件；若无新经验，明确说明"本轮无新增可复用记忆"。
- 声明通告："本次执行已完成，共执行 N 条用例，Pass N / Fail N / Blocked N / Skip N。"
- 若存在 Fail 项，追加提示："已生成 {M} 条缺陷记录，请查阅缺陷清单。"
