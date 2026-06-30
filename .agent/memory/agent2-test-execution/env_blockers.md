# Agent 2 Environment Blockers

Record reusable environment blockers here. Do not store passwords, tokens, cookies, or raw private data.

| Date | Project | Blocker | Detection | Recovery | Status |
|---|---|---|---|---|---|
| 2026-05-23 | 历史项目导入 | Historical project docs may contain raw test credentials or credential-like examples. | Keyword scan found credential fields in project execution handoff/records. | Do not import raw values into `.agent`; replace with role, permission scope, and secure credential reference. | Active |
| 2026-05-23 | 国内包裹签收处理功能 | Scanner/PDA integration and dated package fixtures are required for reliable execution. | Handoff and report mention扫码签收、跨日超时、私人包裹隔离. | Confirm device path or provide mock scan input plus signed/unprocessed/weekend/private-package fixtures. | Active |
| 2026-05-23 | 黑白名单及采购账号 | Token expiry, authorized procurement accounts, IP/middleware environment, and concurrent enablement are not self-provisioned by Agent2. | Historical report contains延期/阻塞 and account/token risks. | Use secure credential refs, controlled token state, mock external provider, or dev-assisted manual verification. | Active |
| 2026-05-23 | 全球站批量导入功能 | Valid/invalid 1688 data, customer ownership, browser downloads, and template files must be prepared before execution. | Agent2 execution record and handoff list external data blockers. | Inventory templates and fixtures, record external API mock strategy, and keep failed-row evidence. | Active |
| 2026-05-23 | 表单下载 | Admin/user accounts, QR/box data, original templates, and field-source files are required for full artifact verification. | Agent2 review identified high-priority execution prerequisites. | Provide secure credential refs and artifact baseline before E1 precheck; use manual/dev-assisted mode for impossible API failure simulation. | Active |
