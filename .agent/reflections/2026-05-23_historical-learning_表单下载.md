# Reflection

| Field | Value |
|---|---|
| Date | 2026-05-23 |
| Project | form_download |
| Role | Orchestrator / Agent 1 / Agent 2 |
| Task | Historical project learning import |

## What Changed

This historical project was evaluated as a high-value export/template verification learning source. It is registered as a historical project and promoted as a candidate for export testing workflow evolution.

## Reusable Lessons

- Export features need a template-field matrix before case generation: each template, column, source field, fixed text, dynamic field, and empty-value behavior should be explicit.
- Artifact comparison should separate fixed structure failures from acceptable dynamic differences such as dates, order IDs, customer names, and row counts.
- Image columns need explicit checks for embedded image versus URL text, missing image fallback, and manual visual confirmation when automation cannot inspect rendering reliably.
- Multilingual templates need label-level assertions, not just file-generation assertions.
- Agent2 precheck must verify original templates, downloaded files, field-source files, account roles, QR/box data, and comparison tooling before full execution.

## One-Off Observations

- Some historical defect summaries reflect specific templates and should not become universal expected behavior.
- Agent2 suggested adding concrete credentials in YAML, but current governance prefers secure credential references rather than raw username/password in `.agent`.

## Memory Updates

- Added project registry entry `form_download`.
- Added Agent1 design pattern for template-field matrix and fixed/dynamic assertion split.
- Added Agent1 audit lesson for export source-of-truth, image embedding, multilingual labels, and template ownership.
- Added Agent1 coverage gap for artifact baseline and comparison method.
- Added Agent2 environment blocker for account, QR, template, and field-source prerequisites.

## Promotion Candidates

- Template-export verification workflow is a strong evolution candidate because it has many templates, batch comparison scripts, defect summaries, and final closure evidence.
- Credential-reference policy should override any historical advice to place raw credentials inside execution YAML.
