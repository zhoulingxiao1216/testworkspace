# VS Code Long-Term Sessions

This directory stores VS Code terminal session state for the local agents defined in `.agent/agents.yaml`.

- `agent1/`: durable terminal context for `agent1_test_design`
- `agent2/`: durable terminal context for `agent2_test_execution`

These files are runtime/session state. Reusable project knowledge should still go into the controlled memory layer under `.agent/memory/`.
