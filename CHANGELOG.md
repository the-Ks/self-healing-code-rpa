# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Improvements

- Hardened the selector-level repair pipeline with an explicit validation, sandbox, apply, version, and rollback orchestration layer.
- Added `code-rpa repair apply` for end-to-end selector repair using existing `repair_request.json` and static `patch.json` artifacts.
- Added audit fields to repair requests and version metadata, including attempted selectors, run log paths, repair request paths, source versions, new versions, and apply results.
- Added safer sandbox selector patch writes and safer live Skill replacement during version application.
- Strengthened patch validation for path traversal, absolute paths, protected framework directories, unknown patch types, selector scope, and target file scope.
- Locked sandbox command execution to framework-generated `repair_request.json` `test_command` arrays and reject any `test_command` supplied by `patch.json`.

### Tests

- Added end-to-end repair pipeline coverage for original success, selector failure, repair request creation, static patch validation, sandbox verification, live apply, version creation, rerun success, and rollback.
- Added negative coverage for target file overreach, selector ref overreach, failed step mismatch, skill mismatch, non-null `code_changes`, path traversal, unknown patch type, sandbox failure, idempotent fallback application, and rollback content restoration.

### Boundaries

- Normal Skill execution still does not call an LLM.
- Patches remain selector-only.
- `code_changes` must remain `null`.
- Sandbox success is required before live Skill modification.
- No Web UI, Scheduler, OCR, Desktop RPA, real website integration, account management, or multitenancy was added.

## v0.1.0 - 2026-06-18

### New Features

- **Self-healing RPA loop**: Introduced the end-to-end workflow from Skill execution to failure capture, repair request generation, selector-level patch validation, sandbox testing, version creation, and rollback.
- **YAML-defined Skills**: Added a structured Skill format using `skill.yaml`, `selectors.yaml`, and `repair_policy.yaml`.
- **Python + Playwright runtime**: Added the Web RPA runtime for deterministic browser automation, selector resolution, step execution, and failure observation.
- **Repair pipeline**: Added `repair_request.json` generation, constrained `patch.json` validation, and isolated sandbox patch testing.
- **Version management**: Added filesystem-backed Skill snapshots, current version tracking, version creation after successful sandbox tests, and rollback support.
- **CLI packaging**: Added the `code-rpa` and `code_rpa` console entrypoints for Skill inspection, creation, validation, execution, repair validation, and version operations.
- **Skill SDK**: Added `SkillBuilder` for generating standard Skill directories through Python code.
- **Codex repository Skill**: Added repository-specific Codex guidance for preserving architecture boundaries during future development.

### Improvements

- **Developer onboarding**: Expanded README documentation with install, demo, testing, CLI, SDK, repair, sandbox, versioning, and safety boundary sections.
- **Skill scaffolding**: Added generated Skill templates for `skill.yaml`, `selectors.yaml`, `repair_policy.yaml`, `main.py`, `README.md`, and `tests/test_skill.py`.
- **Skill validation**: Added checks for required files, duplicate step IDs, selector references, repair policy structure, and standard Skill directory layout.

### Tests

- Added unit coverage for Skill validation success and failure paths.
- Added coverage for SDK-generated Skill files.
- Added coverage for Version CLI list/current/show/rollback commands.
- Preserved runtime, selector resolver, patch pipeline, CLI, docs, and Chromium integration coverage.
- Current verified baseline: `27 passed`.

### Current Capability Boundary

- Supported: Web RPA, Python + Playwright, YAML Skills, selector-level self-healing, repair requests, selector patches, sandbox testing, versioning, and rollback.
- Not supported: OCR, Desktop RPA, LLM calls during normal execution, AI Agent mode, scheduling, Web UI, multitenancy, cloud features, database restructuring, and real website integrations.

### Breaking Changes

- None. This is the first tagged framework release.
