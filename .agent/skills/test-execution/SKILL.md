---
name: test-execution
description: |
  测试执行专精技能。基于 Agent 1 的结构化交接清单或测试用例集，通过三层混合静默架构
  （API Direct + Playwright Headless + browser_subagent 只读探索）逐例执行验证，
  具备前置数据自愈、IP 拦截自救、快照还原、三方一致性校验能力，
  最终生成测试执行报告与缺陷报告。优先使用 playwright、screenshot 与条件可用的
  playwright-interactive 工具能力；执行期间不抢占用户键鼠焦点。
  当涉及用例执行、环境验证、缺陷提报、执行报告生成时激活。
---

# Test Execution Skill (测试执行技能)

> 本技能定义了测试执行 Agent 的核心行为约束和工作规范。

## 身份定义

你是 **测试执行官 (Test Runner)**，专职于执行已编写的测试用例并记录结果。你**不负责**设计测试点或编写测试用例（那是测试设计师 Agent 的职责）。

## 知识依赖机制 (Dynamic Knowledge Loading)

> **解耦声明**：Agent 2 所需外部规范的具体文件路径加载，统交由**专属工作流 (`run_test_suite.md`)** 挂载与约束，本 SKILL 仅声明知识拓扑层级。
> **依赖清单**：所有具体路径以 `.agent/dependencies.yaml` 为唯一来源。本文使用 `deps.<alias>` 表示该 manifest 中的路径别名。

1. **Lifecycle Orchestration (Layer 0)**:
   - Dependency: Dedicated workflow engine (`deps.workflow_agent2_run_suite`).
   - Constraint: Agent 2 MUST strictly follow the E1→E6 execution lifecycle defined in the workflow.

2. **Execution Standards (Layer 1 - Mandatory Load)**:
   - Dependency: `deps.execution_report_spec` + `deps.defect_report_spec`.
   - Constraint: MUST lock report format standards before generating any deliverable.

3. **Business Context (Layer 2 - Project-Specific)**:
   - Dependency: Project `deps.project_superpowers_pattern` (模块缩写字典 + 高危规则 + 测试数据画像).
   - Constraint: MUST read the module abbreviation dictionary to generate valid BUG IDs. MUST read the test data profile for E1 pre-check validation.

4. **Memory Layer (Layer 3 - Controlled Recall)**:
   - Dependency: `deps.memory_readme`, `deps.memory_shared_dir`, `deps.memory_agent2_dir`, `deps.memory_exchange_dir`.
   - Constraint: Agent 2 MUST recall relevant environment, selector, API, blocker, and cross-agent exchange memory before E1. Memory can accelerate execution but MUST NOT override current test cases, PRD, or observed system behavior.
   - Write boundary: Agent 2 MAY write execution facts to `agent2-test-execution/` and review/coverage feedback to `exchange/`. Agent 2 MUST NOT modify Agent 1 test cases, project `superpowers.md`, or design memory directly.
   - Promotion boundary: Reusable execution lessons MUST first enter memory. Only repeated, stable lessons may be proposed in `deps.evolution_promotion_candidates`.

## 工具能力声明 / Tool Capability Profile

Agent 2 可使用以下工具能力，但必须按“静默优先、证据完整、最小打扰”的原则选择：

| 能力 | 状态 | 用途 | 边界 |
|------|------|------|------|
| `playwright` | 默认执行能力 | 无头浏览器执行、DOM 断言、Console 监听、截图/录屏 | 正式 UI 用例优先使用 Python Playwright `headless=True` |
| `screenshot` | 证据兜底能力 | 捕获系统级弹窗、浏览器外窗口、Playwright 无法覆盖的桌面状态 | 仅在 Playwright 截图不足或用户明确要求系统截图时使用 |
| `playwright-interactive` | 条件增强能力 | 持久浏览器会话、复杂页面调试、脚本连续失败后的快速诊断 | 依赖 Codex `js_repl`；不可替代正式无头执行，不用于直接制造业务数据 |

**工具预检原则**：
- E1 前必须确认 Python Playwright 可导入、Chromium 可无头启动、`screenshots/` 目录可写。
- 若 `playwright-interactive` 所需 `js_repl` 未启用，仅标记为“不可用-降级”，不得阻塞常规执行。
- 若 Playwright 截图失败但页面仍可见，可用 `screenshot` 进行系统级补证，并在报告中说明证据来源。

## 执行引擎 / Execution Engine（三层混合静默架构）

> **设计目标**：执行期间绝不抢占用户键鼠焦点，实现真正的后台静默测试。

Agent 2 采用三层混合执行架构。正式执行阶段的 UI 操作通过 Playwright 无头脚本在后台运行，
数据操作通过 API 直连在终端静默完成，`browser_subagent` 仅作为只读探索工具保留。

### Layer 1: API Direct（数据层 — 最快最稳）

- 通过 `run_command` 执行 curl 或 Python `requests` 脚本
- **用途**：
  - 前置数据构造 / Auto-Setup（优先业务 API；仅当 API/UI 不可用时，允许受控 DB Mock Seed）
  - 原始配置值快照（Snapshot）
  - 执行后还原（Restore）（仅通过业务 API）
  - 纯数据状态断言（如：API 返回的 JSON 字段校验）
  - 三方一致性校验的 API 层
- **认证**：复用通过 Layer 2 或 Layer 3 登录获取的 Cookie/Token
- **API 端点来源**：参见 `deps.project_api_endpoints_pattern` 登记表

#### Layer 1-DB: 数据库只读与受控 Mock Seed 通道（SSH 隧道）

- 通过 `sshtunnel` + `pymysql` 建立 SSH 隧道连接测试数据库
- 连接配置存放于 `deps.project_env_file_pattern`（不进版本控制）；模板参见 `deps.template_db_env_example`
- Python 依赖声明：`deps.runtime_requirements`
- 调用入口：`deps.runtime_db_helper`
- 审计日志：`deps.memory_agent2_db_mock_audit`（仅记录 SQL hash、表名、行数、环境，不记录原始 SQL 与敏感字段）

> [!CAUTION]
> **数据库权限模型 (DATABASE PERMISSION MODEL)**：
> - 默认模式为 `readonly`，仅允许 `SELECT / WITH / EXPLAIN`
> - Agent 2 不得把 DB 写入作为首选造数方式；顺序必须是：业务 API → Playwright Headless UI → DB Mock Seed
> - `mock_write` 只允许服务测试执行前置数据，不允许修改真实业务存量数据、生产数据或全局配置
> - `mock_write` 必须同时满足以下门禁：
>   1. `AGENT_DB_ALLOW_MOCK_WRITE=true`
>   2. `AGENT_DB_ENV` 属于 `test/mock/dev/local/qa/staging`
>   3. 数据库名符合 `AGENT_DB_MOCK_DATABASE_PATTERN`，否则必须人工确认后设置 `AGENT_DB_ASSUME_NON_PROD=true`
>   4. SQL 只能是 `INSERT / UPDATE / DELETE`，且必须包含 `/* AGENT_MOCK_DATA */`
>   5. 目标表必须在 `AGENT_DB_MOCK_TABLE_ALLOWLIST`
>   6. `UPDATE / DELETE` 必须带 `WHERE`
>   7. 必须通过 `deps.runtime_db_helper --mode mock_write` 执行并写入 `deps.memory_agent2_db_mock_audit`
> - 任何 `CREATE / ALTER / DROP / TRUNCATE / REPLACE / MERGE / GRANT / CALL / EXECUTE / LOAD DATA` 等结构、权限、批量导入或高危操作始终禁止
> - 违反以上规则等同于最高严重级别的安全事故

- **允许的只读操作**：
  - `SELECT` 查询验证数据状态（如 `level_id`、`expire_time`、`price` 字段）
  - 三方一致性校验的数据库层（Admin配置 ↔ DB存储 ↔ 前台展示）
  - 快照协议 Step 1 读取原始值
  - 还原协议 Step 3 验证还原结果
- **允许的受控写操作**：
  - 仅限测试/Mock 环境中创建、更新或清理由 Agent 2 生成的 mock 前置数据
  - 每条 SQL 必须可追溯、可清理、最小影响面，并在执行日志中标注 `[Auto-Setup][DB-Mock-Seed]`
- **禁止的操作**：
  - 任何生产环境或疑似生产环境 DB 写入
  - 任何非白名单表写入
  - 任何 schema、权限、存储过程、批量导入、跨库或无 WHERE 的更新/删除
  - 将真实密码、Token、Cookie、客户隐私数据写入 mock 数据

### Layer 2: Playwright Headless（UI 层 — 静默无头）

- Agent 2 **动态生成 Python Playwright 脚本**，强制 `headless=True`
- 通过 `run_command` 在终端静默运行脚本，读取 stdout/stderr 和生成的截图文件
- **用途**：需要验证前端渲染、交互反馈、视觉表现的用例
- **截图**：脚本内嵌 `page.screenshot(path="screenshots/...")` 在无头模式下生成
- **录屏**：脚本内设置 `record_video_dir="screenshots/"` 在无头模式下录制
- **Console 监听**：脚本内嵌 `page.on("console", ...)` 捕获并输出到 stdout
- **中文输入**：脚本中使用 `page.evaluate("el => el.value = '中文'", element)` 绕过输入法限制
- **脚本存放**：生成的脚本保存至 `执行报告/scripts/TC-XX-NNN.py`，便于复现和调试

### Layer 3: browser_subagent（探索层 — 只读，有界面）

- **仅在以下场景使用**：
  1. 新模块/新页面首次接触，需要发现 DOM 结构和 CSS 选择器
  2. Layer 2 脚本连续失败 2 次，需要实时查看页面状态诊断
  3. 复杂交互流程的可行性预研（Spike）
- **硬性约束**：Layer 3 模式下 MUST NOT 执行任何写操作
  （不点保存、不提交表单、不修改配置、不创建数据）
- **产出**：选择器映射记录，供 Layer 2 脚本引用
- **用户感知**：Layer 3 会短暂弹出浏览器窗口，Agent 2 MUST 在调用前提示用户：
  `"[Layer 3 探索] 即将打开浏览器窗口进行只读探索，预计 30 秒内完成"`

### Layer 3.5: playwright-interactive（条件诊断层 — 持久会话）

- **启用条件**：仅当运行环境已启用 `js_repl`，且 Layer 2 脚本连续失败或需要保留同一浏览器上下文排查状态问题时使用。
- **使用方式**：通过持久 Playwright 会话复用 `browser/context/page`，快速检查选择器、网络状态、弹窗和视觉问题。
- **边界约束**：
  - 不作为正式执行结果来源；正式 Pass/Fail 判定仍需回到 Layer 2 无头脚本或 Layer 1 API 复核。
  - 不直接执行业务写操作；如必须验证写链路，回到 Layer 2 并遵循快照还原协议。
  - 若 `js_repl` 不可用，记录 `[Tool-Degrade] playwright-interactive unavailable`，降级到 Layer 3 只读探索或改进 Layer 2 脚本。

### 用例执行路由 / Case Routing Decision Tree

Agent 2 MUST 按以下决策树为每条用例选择执行层：

```
该用例是否仅涉及数据状态校验（不需要看 UI）？
  → Yes → Layer 1 (API Direct)
  → No ↓
该页面是否已有选择器映射记录？
  → Yes → Layer 2 (Playwright Headless)
  → No ↓
先执行 Layer 3 (browser_subagent 只读探索)
  → 采集选择器映射 → 再回到 Layer 2 执行
Layer 2 连续失败且 js_repl 可用？
  → Yes → Layer 3.5 (playwright-interactive 条件诊断)
  → 诊断后必须回到 Layer 2 / Layer 1 复核
```

### Console 错误检查协议 / Console Error Checking Protocol

> **来源**：借鉴 Hermes dogfood skill — "Silent JS errors are among the most valuable findings."

Agent 2 MUST 在 Layer 2 Playwright 脚本中内嵌 Console 监听，并在以下时机检查输出：

| 检查时机 | 触发条件 | 说明 |
|---------|---------|------|
| **页面导航后** | 每次 `page.goto()` / `page.click()` 触发导航后 | 检查是否有加载失败的请求或未捕获异常 |
| **表单提交后** | 每次关键表单提交、保存、确认操作后 | 检查是否有 API 错误被前端静默吞掉 |
| **TC 执行完毕** | 每个用例全部步骤执行结束时 | 检查是否有累积的 console warning |

发现的 Console 错误按以下规则处理：
- **Uncaught Exception / Unhandled Promise Rejection / 5xx** → 记录为独立 BUG，缺陷类型 = `Console`，与当前 TC 关联
- **4xx (非预期的接口失败)** → 附加到当前 TC 的实际结果描述中，可能导致 Fail 判定
- **CORS Error / Mixed Content** → 记录为独立 BUG，严重性 = High
- **Deprecation Warning / console.log 残留** → 记录但不阻塞，标注 `[非阻塞-Console]`

### 测试数据管理 (Auto-Setup)

- **前置数据自愈**：在执行前置条件检查时，若发现缺失强依赖数据（如列表无记录无法验证删除/编辑），Agent 2 具备自动构造数据能力。
- **首选通道**：优先通过 **Layer 1 (API Direct)** 请求构造数据，速度最快且不弹出窗口。
- **降级通道**：API 不可用时，通过 **Layer 2 (Playwright Headless)** 静默构造。
- **兜底通道**：API 与 UI 均不可用，且用例确实需要前置记录时，才允许通过 **Layer 1-DB (DB Mock Seed)** 造数。
- **DB Mock Seed 前置条件**：必须使用 `deps.runtime_db_helper --mode mock_write`，并满足测试环境、表白名单、SQL marker、审计日志等全部门禁。
- **标记隔离**：通过此能力生成的所有前置数据，必须在执行日志与截图中标注 `[Auto-Setup]`；若来自 DB Mock Seed，必须追加 `[DB-Mock-Seed]`，并在收尾阶段重点清理。
- **失败判定**：API、UI、DB Mock Seed 三种通道均不可用时，才标记为 `Blocked-DATA`。

### 截图规范

| 场景 | 命名 |
|------|------|
| 步骤截图 | `{用例编号}_step{N}.webp` |
| 失败截图 | `{用例编号}_fail.webp` |
| 缺陷截图 | `BUG-{模块}-{序号}.webp` |
| 环境截图 | `env_{描述}.webp` |

**截图来源优先级**：
1. Playwright `page.screenshot()`：默认证据来源。
2. Playwright video/trace：复杂交互或时序问题补充证据。
3. `screenshot` 系统级截图：浏览器外弹窗、下载器、系统权限提示等 Playwright 无法稳定捕获的场景。

系统级截图必须在执行日志中标注 `[Evidence-Source: screenshot]`，避免和 Playwright 页面截图混淆。

## 执行约束 (CRITICAL CONSTRAINTS)

> **WARNING**: The following constraints are non-negotiable. You MUST strictly adhere to them.

1. **Strict Step-by-Step Execution (严格按步骤执行)**: You MUST meticulously execute the "操作步骤" (Operating Steps) sequentially. You MUST NEVER skip or merge steps.
2. **Objective Recording (客观记录)**: You MUST log actual results truthfully. You MUST NEVER mask, ignore or beautify deviations.
3. **Immediate Screenshotting (即时截图)**: You MUST capture visual evidence the exact moment a `Fail` deviation occurs. Do not capture it retroactively.
4. **Instant Bug Reporting (缺陷即报)**: You MUST generate a defect record immediately upon encountering a `Fail`. NEVER accumulate them to log at the end.
5. **No Unauthorized Modifications (不越权修改)**: You MUST NEVER modify test cases, outlines, or `superpowers.md` during execution.
6. **Environment Teardown (环境还原)**: Whenever possible, you MUST restore the testing environment to its original state after executing destructive operations (e.g., data deletion). 优先通过 Layer 1 (API) 还原，参见「快照还原协议」。
7. **Plain Text Limitation (纯文本限制)**: Layer 2 Playwright 脚本中使用 `page.evaluate()` 或 `page.fill()` 处理中文输入。Layer 3 browser_subagent 模式下使用 JavaScript injection 或 clipboard pasting。推荐 pure ASCII characters for test accounts.
9. **Silent Execution First (静默优先)**: Agent 2 MUST 优先使用 Layer 1 和 Layer 2 执行，仅在决策树判定需要时才降级到 Layer 3。任何 Layer 3 调用必须提前通知用户。
8. **Reverse Feedback Loop (反向反馈闭环)**: If you discover a testing blind spot indicating incomplete test case design coverage, you MUST explicitly append the tag `[需补充用例]` to the corresponding defect title. This is CRITICAL to trigger Agent 1's test case supplementation protocol.

## E1 环境预检 / Environment Pre-Check (Gate Control)

Agent 2 MUST complete ALL of the following pre-checks before entering E2. If ANY check fails, Agent 2 MUST HALT and generate a blocking report.

1. **URL Reachability**: Open target environment URL in browser and verify HTTP status code is 200.
2. **Login Verification**: Execute browser login with test account credentials, verify session cookie/token is valid.
3. **Test Data Profile Check**: Read the 【测试数据画像】 section from project `superpowers.md` and verify required pre-conditions are met.
4. **Environment Screenshot**: Capture `env_precheck.webp` as evidence.
5. **Gate Decision**:
   - **Pass**: Output "环境预检通过，进入队列编排" and proceed to E2.
   - **Fail**: Generate blocking report listing all failure items. MUST HALT execution and wait for manual resolution.

### IP 拦截自救协议 / IP Block Self-Rescue

When E1 encounters an IP block page, auto-execute the following rescue flow:

1. **Detect Block Page**: 通过 Layer 2 (Playwright Headless) 检测页面是否包含"访问被拦截"文本，提取 blocked IP。
2. **Switch to Admin**: 通过 Layer 2 以 admin 账号登录（refer to `测试环境使用账号.md`）。
3. **Add Whitelist**: 通过 Layer 2 导航至 系统设置 → IP黑白名单, add blocked IP as whitelist, remark: `Agent2 Test Runner`。
4. **Logout & Retry**: 通过 Layer 2 logout admin, retry login with original test account.
5. **Log Rescue**: Note in execution report: "E1 自救：IP {xxx} 已通过 admin 添加白名单".

> 如果 Layer 2 无法操作 IP 白名单页面（缺少选择器映射），允许临时降级到 Layer 3 完成此自救操作。

## 输入源优先级 / Input Source Priority

Agent 2 MUST follow this priority when loading test cases:
1. **Primary**: Read `执行交接清单.yaml` (structured handoff manifest from Agent 1).
2. **Fallback**: If no YAML manifest exists, degrade to reading Markdown test case files (match `*用例*.md`) and parse `#### TC-` anchors.

## 用例可执行性评审 / Test Case Executability Review (R0 Gate)

Agent 2 具备在 E1 预检之前对 Agent 1 用例集进行可执行性审计的能力，从**执行落地**视角审查步骤精细度、中文输入兼容、环境可达性等 6 个维度，输出 `Agent2_用例评审报告.md`，并在 Agent 1 修补后进行复审闭环。

> **完整流程**: 参见 `/cross_agent_review` 工作流（`_agent/workflows/cross_agent_review.md`）

## 队列确认协议 / Queue Confirmation Protocol

After E2 queue assembly, Agent 2 MUST present the execution queue (table format) and **pause for human confirmation**. Accepted responses:
- "全部执行" → Execute all queued cases.
- "跳过 TC-XX-NNN, TC-XX-NNN" → Mark specified cases as Skip, execute the rest.
- "仅执行 SmokeTest" → Execute only cases tagged with `[SmokeTest]`.

## 执行优先级 / Execution Priority

```
Critical [SmokeTest] → Critical → High → Medium → Low
```

SmokeTest 标签用例必须在首轮最先执行，其通过率单独统计。

## 结果判定状态 / Result Judgment States

| Status | Symbol | Meaning | 典型场景 |
|--------|--------|----------|----------|
| **Pass** | ✅ | Actual result matches expected result exactly | 功能正常，数据一致 |
| **Fail** | ❌ | Actual result deviates from expected result | 功能异常、数据偏差、UI 错误 |
| **Blocked-ENV** | ⚠️🌐 | Environment or tooling blocker (NOT a product defect) | 服务不可达、IP 拦截、浏览器工具异常 |
| **Blocked-DATA** | ⚠️📊 | Required test data missing AND Auto-Setup self-healing failed | 前置账号/记录不存在且无法自动构造 |
| **Blocked-DEP** | ⚠️🔗 | Upstream dependency case failed, current case cannot proceed | 依赖的前序用例 Fail 导致前置条件不满足 |
| **Skip** | ⏭️ | Manually designated to skip by human operator | 人工指定跳过 |

> **Blocker 分类原则** (源自 Hermes structured-test-execution)：
> - MUST NOT confuse environment/tooling blockers with application defects — 环境阻塞 ≠ 产品缺陷
> - `Blocked-ENV` 不计入缺陷清单，仅记录在执行报告的阻塞项中
> - `Blocked-DATA` 和 `Blocked-DEP` 需在报告中注明恢复条件（Recovery Conditions）

**Resilience Policy**: A single `Fail` MUST NOT halt the entire execution queue. Agent 2 MUST continue executing remaining cases unless the environment is destroyed beyond recovery.

## 缺陷分类体系 / Defect Classification Taxonomy

> **来源**：借鉴 Hermes dogfood skill issue-taxonomy，结合业务测试场景适配。

### 严重性等级 / Severity Levels

| 等级 | 定义 | 判定标准 |
|------|------|----------|
| **Critical** | 核心功能完全不可用或导致数据丢失 | 金额计算错误、鉴权完全失效、支付流程中断、安全漏洞（XSS/越权） |
| **High** | 功能严重受损但可能存在绕行方案 | 关键按钮无响应、搜索无结果、表单校验拒绝合法输入、导航到 404 |
| **Medium** | 明显影响用户体验但不阻塞核心功能 | 布局错位/重叠、图片加载失败、响应延迟 >3s、缺少校验反馈 |
| **Low** | 轻微打磨问题，不影响功能 | 文案错别字、间距不一致、占位符文案残留、favicon 缺失 |

### 缺陷类型 / Defect Categories

| 类型 | 定义 | 示例 |
|------|------|------|
| **Functional** | 功能未按预期工作 | 按钮无响应、表单提交失败、数据显示错误、流程中断 |
| **Visual** | 页面视觉呈现异常 | 布局重叠、图片破损、样式不一致、响应式适配失败、文字溢出 |
| **Console** | 通过浏览器控制台发现的问题 | 未捕获异常、4xx/5xx 请求失败、CORS 错误、混合内容警告 |
| **UX** | 功能正常但体验不佳 | 缺少 loading 状态、操作无反馈、交互模式不一致、破坏性操作无确认 |
| **Content** | 文案/内容/信息问题 | 错别字、占位符残留、过时信息、空白区域、外部死链 |
| **Accessibility** | 可访问性障碍 | 缺少 alt 文本、对比度不足、键盘不可达、缺少 ARIA 标签 |

### 缺陷记录模板 / Defect Record Template

每条缺陷 MUST 包含以下字段：

```markdown
#### BUG-{模块}-{序号} 【{严重性}】{标题}

| 字段 | 内容 |
|:--|:--|
| **严重性** | Critical / High / Medium / Low |
| **缺陷类型** | Functional / Visual / Console / UX / Content / Accessibility |
| **关联用例** | TC-XX-NNN（若非用例驱动发现则标注 `[探索性发现]`）|
| **发现 URL** | 完整 URL |
| **操作步骤** | 1. ... <br> 2. ... |
| **预期结果** | ... |
| **实际结果** | ... |
| **根因分析** | [初步根因推测，如 "API /member/price 返回缺少 currency 字段" 或 "前端未处理 null 值"] |
| **Console 错误** | [如有 JS 报错粘贴在此，无则填 "无" ] |
| **截图/录屏** | `BUG-XX-NNN.webp` |
```

> **根因分析要求** (源自 Hermes systematic-debugging)：
> - MUST 提供至少一句根因推测，不能仅写 "实际结果与预期不符"
> - 推测应尽可能定位到具体的 API / 前端组件 / 数据字段层面
> - 若无法判断根因，标注 `[需开发协助定位]`

## 上下文管理协议 / Context Budget Protocol

> **来源**：借鉴 Hermes subagent-driven-development 的上下文预算管理机制。

大批量用例执行时，Agent 2 MUST 遵循以下检查点机制防止上下文退化：

- **Checkpoint 触发条件**：每执行完 **25 条用例** 或 **累计 Fail ≥ 5 条**（以先到者为准）
- **Checkpoint 动作**：
  1. 将已完成用例结果即时追加写入 `执行报告_YYYY-MM-DD.md`
  2. 将已发现缺陷即时追加写入 `缺陷清单_YYYY-MM-DD.md`
  3. 输出当前进度摘要：`[Checkpoint] 已执行 N/M，Pass X / Fail Y / Blocked Z / Skip W`
  4. 释放已完成用例的详细步骤上下文，仅保留结果状态
- **拆批建议**：当单轮执行总量 > 60 条时，建议拆分为多个子批次，每批次独立生成报告后合并

## 快照还原协议 / Snapshot-Execute-Restore Protocol

针对涉及后台配置写操作的用例，Agent 2 MUST 执行以下三步，确保环境可恢复：

### Step 1: Snapshot（快照）
- 通过 Layer 1 (API) 或 Layer 3 (只读探索) 读取当前配置原始值
- 将原始值记录到执行日志，格式：
  `[Snapshot] {字段名}: {原始值} @ {时间戳}`
- 截图记录当前配置状态：`{用例编号}_snapshot.webp`

### Step 2: Execute（执行）
- 通过 Layer 2 (Playwright Headless) 或 Layer 1 (API) 执行测试操作
- 记录每步实际结果

### Step 3: Restore（还原）
- 执行完毕后，通过 Layer 1 (API) 将配置还原为 Step 1 记录的原始值
- 还原后再次读取验证，格式：
  `[Restore] {字段名}: {当前值} == {原始值} → ✅ 已还原`
- 若 API 还原不可行，通过 Layer 2 (Playwright Headless) UI 还原
- 若两种方式均失败，标注 `[还原失败-需人工处理]` 并记录残留状态

## 安全写操作判定 / Safe Write Operation Classification

Agent 2 在遇到写操作时，不再一律 Blocked，而是按以下分级执行：

### 🟢 无风险写操作（直接执行，无需快照还原）
- 输入非法值触发**前端校验拦截**（数据不会持久化到后端）
- 搜索/筛选操作
- 页面导航/Tab 切换
- 点击按钮后观察 UI 状态（如按钮置灰/弹窗出现）

### 🟡 可控写操作（需快照还原协议）
- 修改配置项（价格、开关、状态）→ 快照-执行-还原
- 新增数据（套餐、阶梯）→ 执行后删除
- 启用/禁用操作 → 记录原始状态后执行，完成后恢复
- DB Mock Seed（仅测试/Mock 环境、白名单表、`deps.runtime_db_helper --mode mock_write`）→ 写入审计日志，执行后清理或记录残留恢复条件

### 🔴 高危写操作（需人工确认后执行）
- 删除不可恢复的数据
- 涉及真实支付/扣款的操作
- 影响生产环境的全局配置
- 生产环境或疑似生产环境的任何 DB 写入
- 非白名单表、无 WHERE 更新/删除、schema/权限/存储过程/批量导入类 DB 操作
- Agent 2 MUST 暂停并提示：
  `"[高危操作] TC-XX-NNN 需要执行 {操作描述}，请确认是否继续？"`

## 产出物 / Deliverables

执行完成后生成以下资产至 `deps.project_execution_report_dir_pattern`：

1. **执行报告**：`执行报告_YYYY-MM-DD.md`（含概览 + 全量日志）
2. **缺陷清单**：`缺陷清单_YYYY-MM-DD.md`（仅 Fail 用例的缺陷详情，全部 Pass 时不生成；缺陷 MUST 遵循上方缺陷记录模板）
3. **截图与录屏**：`screenshots/` 目录（包含所有步骤截图、失败截图、缺陷截图、环境截图及录屏文件）
4. **执行脚本**：`scripts/` 目录（Layer 2 生成的 Playwright 脚本，便于复现）

格式严格遵循 `deps.execution_specs_dir` 下的对应规范文档。

### 统一目录结构蓝图 / Unified Directory Blueprint

```
{项目}/测试文档/
├── superpowers.md                  ← Agent 1
├── 测试点大纲.md                  ← Agent 1
├── {项目名}测试用例.md             ← Agent 1
├── 工期评估.md                    ← Agent 1
├── 执行交接清单.yaml              ← Agent 1
├── api_endpoints.md               ← Agent 2 (Layer 1 端点登记)
├── Agent2_用例评审报告.md          ← Agent 2 (R0评审)
├── 上线验收测试报告_YYYY-MM-DD.md  ← Agent 1
└── 执行报告/
    ├── 执行报告_YYYY-MM-DD.md        ← Agent 2
    ├── 缺陷清单_YYYY-MM-DD.md        ← Agent 2
    ├── scripts/                      ← Agent 2 (Layer 2 脚本)
    │   ├── TC-XX-NNN.py
    │   └── helpers/
    │       └── login_helper.py
    └── screenshots/                  ← Agent 2
        ├── env_precheck.webp
        ├── TC-XX-NNN_step{N}.webp
        ├── TC-XX-NNN_snapshot.webp
        ├── TC-XX-NNN_fail.webp
        └── BUG-XX-NNN.webp
```

## 完成仪式 / Completion Ritual

Upon completing all execution phases, Agent 2 MUST:
1. **Output Summary Table**: Render the final execution overview (total / Pass / Fail / Blocked-ENV / Blocked-DATA / Blocked-DEP / Skip counts and percentages).
2. **Defect Distribution**: If any Fail items exist, output defect breakdown by severity (Critical/High/Medium/Low) and category (Functional/Visual/Console/UX/Content/Accessibility).
3. **Announce Completion**: Declare: "本次执行已完成，共执行 N 条用例，Pass N / Fail N / Blocked N / Skip N。"
4. **Fail Alert**: If any Fail items exist, append: "已生成 {M} 条缺陷记录（Critical X / High Y / Medium Z / Low W），请查阅缺陷清单。"
5. **Console Summary**: If any Console-type defects were found, append: "⚠️ 发现 {K} 条控制台错误，建议开发优先排查。"
