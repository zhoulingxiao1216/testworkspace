# 简化流程图 — Reflections → Memory → Evolution

下面的 Mermaid 图用于说明 `reflections`、`memory`、`evolution` 三者的关系，适合直接在支持 Mermaid 的 Markdown 预览器中打开查看。

```mermaid
flowchart LR
  A[Run 完成]
  B[写 reflections]
  C{是可复用经验?}
  D[写入 memory (shared / agent1 / agent2)]
  E{重复且稳定?}
  F[写入 evolution/promotion_candidates]
  H{Orchestrator 审核结果?}
  I[通过：合并为 skill/workflow<br/>或写入 shared，并记录 decision_log.md]
  J[拒绝：标注 rejected<br/>写回 reflections 或 deps.evolution_rejected_learnings]
  K[需补充：通知作者补充样例/数据<br/>保持 candidate 打开]
  G[结束]

  A --> B --> C
  C -- 否 --> G
  C -- 是 --> D --> E
  E -- 否 --> G
  E -- 是 --> F --> H
  H -- 通过 --> I --> G
  H -- 拒绝 --> J --> G
  H -- 需补充 --> K --> G
```

使用提示：在 VS Code 中打开此文件并使用 Markdown + Mermaid 预览插件（或内置预览）可以直接查看渲染效果。
