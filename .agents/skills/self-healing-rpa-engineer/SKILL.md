---
name: self-healing-rpa-engineer
description: Build, modify, test, or repair RPA Skills in this Self-Healing Code RPA repository. Use when creating a new Python + Playwright Skill, updating skill.yaml/selectors.yaml/repair_policy.yaml, handling repair_request.json or patch.json, validating selector-only self-healing patches, running sandbox repair tests, managing versions or rollback, or enforcing this repo's RPA safety rules.
---

# Self-Healing RPA Engineer

Use this skill when working inside this repository on RPA Skills or selector-level repair flows.

## Core Rules

- Normal Skill execution must not call an LLM.
- Web RPA runs through Python + Playwright and YAML Skill definitions.
- On failure, the runtime must retry and try fallback selectors before generating `repair_request.json`.
- Phase three repair is selector-only.
- `patch.json` may use only `selector_update` or `fallback_selector_add`.
- `code_changes` must be `null`.
- Patches must pass `PatchValidator`.
- Patches must pass `SandboxRunner`.
- Only `VersionManager` may apply a tested patch to the live Skill.
- High-risk steps require human confirmation and must not be auto-patched.
- Every Skill must include pytest coverage.
- Do not bypass safety checks, logs, snapshots, sandbox tests, or versioning.

## Phase 3 Engineering Gate

The repository is now in Phase 3 engineering mode. The goal is packaging, operability, reuse, and Codex maintainability.

Do not refactor core modules while doing Phase 3 packaging work:

- `rpa_runtime/`
- `repair_agent/`
- `skill_registry/`

Do not expand the RPA capability boundary without explicit approval. Web RPA and selector-level repair remain the active scope.

Phase priorities:

- **P0**: README, CLI, Skill Generator, Codex Repo Skill.
- **P1**: Skill Validator, Skill SDK, Version CLI.
- **P2**: Real business Skill examples.

After finishing a phase, report:

1. Modified files.
2. New commands.
3. Test results.
4. Current capability boundary.
5. Recommended next phase.

Stop after each phase and wait for explicit approval before starting the next phase.

## Workflow

1. Read `AGENTS.md` before major runtime or repair changes.
2. For architecture context, read `references/architecture.md`.
3. For creating or updating a Skill, read `references/rpa-skill-spec.md` and use the templates in `assets/`.
4. For patch work, read `references/patch-json-spec.md`.
5. For repair flow or rollback work, read `references/repair-pipeline.md`.
6. Run relevant pytest tests after changes.

## Skill Creation

Create Skills under `example_skills/<skill_id>/` with:

- `skill.yaml`
- `selectors.yaml`
- `repair_policy.yaml`
- `main.py`
- `tests/test_skill.py`

Prefer `python -m code_rpa skill create <skill_id>` for scaffolding.

## Repair Constraints

Allowed repair targets:

- The failed step's selector ref in `selectors.yaml`.
- Full repository-relative selector file paths such as `example_skills/web_report_export/selectors.yaml`.

Forbidden repair targets:

- `main.py`
- `rpa_runtime/`
- `repair_agent/`
- `skill_registry/`
- unrelated steps
- high-risk steps
