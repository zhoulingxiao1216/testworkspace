Sessions 说明

目录：`.agent/sessions/`

用途：
- 存放用于“长会话”第一条消息的可复制模板，方便在聊天工具中一键建立或恢复 Agent1/Agent2 的长期会话。

使用步骤：
1. 打开对应的 Agent 长会话窗口（你的聊天系统或对话工具）。
2. 打开 `.agent/sessions/agent1_session.md` 或 `agent2_session.md`，替换花括号中的 `{}` 字段为实际值。
3. 将整个文件内容作为会话的第一条消息粘贴并发送——长会话即建立（或恢复）。
4. 若需在会话中使用凭据，请**私下**提供凭据给 agent，或使用本地凭据文件引用（例如 `测试环境使用账号.md#hlc-admin`）。

注意：
- 模板中已明确要求不要把明文密码或客户隐私写入 `memory/` 或 `reflections`。
- 若你希望我替你把模板中的字段填好（project/run_id/owner/test_cases_path 等），告诉我具体值，我会写入并保存为 `.agent/runs/{run_id}/agent*_start.txt` 以便直接复制。