---
name: superpowers-base
description: |
  全局通用测试超能力基础规约。所有项目的 superpowers.md 必须继承此文件。
  涵盖设计先行、TDD 驱动、逻辑挑战三大通用协议。
version: 1.0
scope: global
---

# Superpowers Base Rules (全局通用规约)

> 本文件为所有项目的 superpowers.md 基础规约。各项目通过 `inherits: superpowers-base` 继承本文件，
> 并在各自的 superpowers.md 中定义领域专属规则。严禁在项目文件中重复定义以下通用规则。

---

## 1. Design First (设计先行)
- 严禁直接写代码。
- 必须先运行 `brainstorming` 技能，并在 Artifact 中输出设计文档。
- 必须获得用户确认后方可进入下一阶段。

## 2. TDD Protocol (测试驱动协议)
- **Red Phase**: 先写一个必然失败的测试用例（针对大纲中的逻辑）。
- **Green Phase**: 编写最精简的代码/Mock 数据使测试通过。
- **Refactor**: 在不破坏测试的前提下优化结构。

## 3. Brainstorming (逻辑挑战)
- 主动挑战用户需求中的模糊地带。
- 针对业务逻辑中的边界条件，必须自发进行边界值审计。
- 各项目可在自身 superpowers.md 中追加领域特定的审计重点。
