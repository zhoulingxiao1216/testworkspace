Agent templates

目录：`.agent/templates/`

包含：
- `agent1_prompt.md` — Agent1（测试设计）唤起模板，带结构化返回格式示例
- `agent2_prompt.md` — Agent2（测试执行）唤起模板，带 exchange item 说明
- `exchange_item_template.json` — 用于生成 `F-xxx` 交叉评审条目的 JSON 模板

使用建议：
- 在唤起长会话时，把对应模板的内容粘贴到会话首条消息并替换 `{}` 占位符。
- 要求 agent 在写 reflections 或 memory 时给出 `reflections_path` 与 `evidence` 引用，便于审计与追踪。
- 模板仅为建议，可按团队规范调整字段。
