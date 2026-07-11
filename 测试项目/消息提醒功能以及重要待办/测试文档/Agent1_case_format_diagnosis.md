# Agent1 Case Format Diagnosis

| Item | Conclusion |
|:--|:--|
| Project | message reminder and important todo |
| Problem | Agent1 generated a horizontal summary table, not platform-importable case blocks. |
| Impact | The platform parser found 0 #### TC-... blocks, so import failed. |
| Fix | The main test case file was overwritten with platform-importable block format. |
| Original table backup | D:\test_workspace\消息提醒功能以及重要待办\测试文档\消息提醒功能以及重要待办测试用例_original_table_20260525_093259.md |
| Intermediate backup | D:\test_workspace\消息提醒功能以及重要待办\测试文档\消息提醒功能以及重要待办测试用例_original_table_20260525_093855.md |

## Evidence

- Original file had 62 horizontal rows starting with | <a id="TC-..."></a>TC-... |.
- Original file had 0 #### TC-... case anchors.
- The active parser splits cases only by #### TC-... and reads two-column **field** tables.
- The app upload help text also says it supports #### TC-XXX Markdown files.

## Root Cause

1. Agent1 skill/workflow already contained the correct format rule, but the run did not execute a parser-based import compatibility check.
2. The run artifact marked the file as standardized based on human-readable structure, not on parse_md_text verification.
3. Agent2 reviewed executability blockers, but did not check platform import compatibility.

## Prevention

- Before design_ready=true, Agent1 should run the platform parser and confirm parsed case count equals the handoff total_cases.
- If a test case file contains 0 #### TC- anchors, the run should fail before Agent2 review.
- Parser compatibility has been added as a candidate Agent1 design pattern.
