# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.0] - 2026-06-18

### Added

- Added `code-rpa skill create` for generating standard Skill directories from repository templates.
- Added standard Skill template generation for `skill.yaml`, `selectors.yaml`, `repair_policy.yaml`, `main.py`, `README.md`, and `tests/test_skill.py`.
- Added the `SkillBuilder` SDK for creating Skill scaffolds from Python code.
- Enhanced Skill validation for required files, YAML structure, required fields, duplicate step IDs, selector references, repair policy structure, and standard directory layout.
- Added the Skill developer flow for `skill validate`, `skill run`, and `skill test`.
- Added `RepairPipeline` orchestration for validation, sandbox verification, live apply, version creation, and rollback-safe failure handling.
- Added `code-rpa repair apply` stage output for validation, sandbox, apply, version, and repair results.
- Added isolated sandbox execution for selector-only repair patches.
- Added Skill snapshots, version metadata, current-version tracking, and rollback support.
- Added end-to-end Repair Pipeline regression coverage for original success, selector failure, repair request creation, static patch validation, sandbox verification, live apply, version creation, rerun success, and rollback.
- Added CONTRIBUTING, SECURITY, architecture documentation, Skill specification documentation, repository Codex guidance, and GitHub Actions test workflow.

### Changed

- Improved Skill creation next-step guidance after scaffolding.
- Improved Skill validation error messages for missing files, duplicate step IDs, unknown selector refs, and malformed policy files.
- Expanded repair request failure context with URL, screenshot and DOM paths, logs, failed step data, attempted selectors, allowed files, and allowed selector refs.
- Added independent `--basetemp` directories for pytest subprocesses started by Skill tests and sandbox tests.
- Configured pytest with `--import-mode=importlib` so multiple Skills can keep the standard `tests/test_skill.py` filename.
- Improved Windows and multi-Skill test stability without changing Runtime, Repair, Registry, or Version behavior.

### Fixed

- Fixed Windows `pytest-current` cleanup failures that could make successful nested pytest runs return failure.
- Fixed `import file mismatch` when multiple Skills each contain `tests/test_skill.py`.
- Fixed sandbox failure handling so a failed sandbox cannot modify the live Skill.
- Fixed live Skill restoration when version creation or live replacement fails partway through.
- Fixed repeated patch or version replay cases from duplicating fallback selectors or claiming success incorrectly.
- Fixed temporary file and partial version cleanup paths around selector patch application and version writes.

### Security

- Kept patch scope constrained to selector-only changes.
- Rejected absolute paths and `..` traversal in patch targets.
- Rejected unauthorized target files outside allowed repair files.
- Rejected unauthorized selector references outside allowed selector refs.
- Rejected unknown patch types.
- Rejected unknown patch fields.
- Rejected non-null `code_changes`.
- Kept `test_command` trusted only when it comes from a framework-generated `repair_request.json`.
- Kept subprocess execution as argument arrays.
- Kept sandbox command execution on `shell=False`.
- Rejected shell strings and dangerous shell metacharacters in sandbox test commands.
- Added symlink and junction escape protection for selector patch paths.
- Used atomic YAML replacement for selector writes.
- Preserved failure recovery and rollback behavior before live Skill changes are accepted.

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
