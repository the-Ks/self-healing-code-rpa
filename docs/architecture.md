# Architecture

Self-Healing Code RPA is built around deterministic automation first and constrained repair second.

The framework does not use AI during normal execution. A Skill runs as Python + Playwright code. If deterministic execution fails after retries and fallback selectors, the runtime captures failure evidence and writes a structured repair request. A selector-level patch can then be validated, tested in a sandbox, versioned, and rolled back.

## End-to-End Repair Lifecycle

```text
Skill run
  -> selector failure
  -> failure snapshot
  -> repair_request.json
  -> static patch.json fixture
  -> strict patch validation
  -> sandbox replay of the failed step or smoke test
  -> safe live apply
  -> version snapshot
  -> rerun success check
  -> rollback if needed
```

The important rule is simple:

- normal execution does not call an LLM
- the patch is only constrained data
- sandbox success is required before the live Skill changes
- sandbox commands come only from framework-generated `repair_request.json`, never from `patch.json`
- rollback must restore the previous selector content and version pointer

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
- run log path
- repair request path

## Repair Flow

```text
repair_request.json
  -> patch.json
  -> PatchValidator
  -> SandboxRunner
  -> RepairPipeline
  -> VersionManager.snapshot
  -> VersionManager.create_new_version
  -> rollback_to_version when needed
```

Only sandbox-tested selector patches are eligible for new Skill versions.
`repair_request.json` and `patch.json` are both constrained to selector-only scope.
The live Skill is only updated after validation and sandbox checks succeed.

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

Changes to this module should stay tied to runtime execution and failure capture. It must not call an LLM during normal execution.

### `repair_agent/`

Owns repair artifacts and safety checks:

- repair request generation
- patch validation
- sandbox patch testing
- end-to-end repair pipeline orchestration

Changes to this module should preserve selector-only repair, strict validation, sandbox-first application, and auditability.

### `skill_registry/`

Owns Skill loading and version management:

- YAML Skill loading
- Skill snapshots
- current version tracking
- version rollback

Changes to this module should preserve version snapshots, current-version tracking, safe live replacement, and rollback consistency.

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
- Repair pipeline audit data.

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
- Automatic live patching without sandbox.

## Design Principle

Stable automation should stay code. AI, if used by a human or external workflow, should operate only after failure and only against constrained repair artifacts.
