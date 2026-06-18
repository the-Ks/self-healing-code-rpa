# Architecture

Self-Healing Code RPA is built around deterministic automation first and constrained repair second.

The framework does not use AI during normal execution. A Skill runs as Python + Playwright code. If deterministic execution fails after retries and fallback selectors, the runtime captures failure evidence and writes a structured repair request. A selector-level patch can then be validated, tested in a sandbox, versioned, and rolled back.

## Runtime Flow

```text
Skill
  -> SkillLoader
  -> RPAExecutor
  -> StepRunner
  -> SelectorResolver
  -> RunLogger
  -> Observer
  -> RepairRequestGenerator
```

Successful execution ends after all steps complete. Failed execution captures:

- step result
- error message
- attempted selectors
- current URL
- screenshot path
- DOM snapshot path
- repair request path

## Repair Flow

```text
repair_request.json
  -> patch.json
  -> PatchValidator
  -> SandboxRunner
  -> VersionManager.create_new_version
  -> rollback_to_version when needed
```

Only sandbox-tested selector patches are eligible for new Skill versions.

## Modules

### `code_rpa/`

Developer-facing package for repository engineering:

- CLI entrypoint
- Skill validation
- Skill SDK and scaffolding helpers

### `rpa_runtime/`

Runs Skills and observes failures:

- browser lifecycle
- step execution
- selector fallback
- retry policy
- run logs
- screenshots and DOM snapshots

This module is protected during the current P1 phase.

### `repair_agent/`

Owns repair artifacts and safety checks:

- repair request generation
- patch validation
- sandbox patch testing

This module is protected during the current P1 phase.

### `skill_registry/`

Owns Skill loading and version management:

- YAML Skill loading
- Skill snapshots
- current version tracking
- version rollback

This module is protected during the current P1 phase.

### `example_skills/`

Contains example Skills. The current `web_report_export` example runs against a local HTML fixture.

### `storage/`

Runtime output root. Generated run logs, snapshots, repair requests, and versions are ignored by Git except `.gitkeep` placeholders.

## Capability Boundary

Supported today:

- Web RPA.
- Python + Playwright.
- YAML Skills.
- Primary and fallback selectors.
- Failure snapshots.
- Selector-only patch validation.
- Sandbox patch testing.
- Versioned Skill repair.
- Rollback.

Not supported today:

- OCR.
- Desktop RPA.
- Scheduler.
- Web UI.
- Multitenancy.
- Cloud execution.
- Real website integration.
- LLM calls during normal execution.
- AI Agent mode.
- Arbitrary code patching.

## Design Principle

Stable automation should stay code. AI, if used by a human or external workflow, should operate only after failure and only against constrained repair artifacts.
