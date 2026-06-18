# Self-Healing Code RPA Framework

A self-healing Code RPA framework that turns web automation workflows into runnable, testable, repairable, and versioned Skills.

The current MVP supports selector-level self-healing for Web RPA. A Skill is defined in YAML, executed by the Python runtime, observed on failure, repaired through a constrained `patch.json`, tested in a sandbox, and versioned with rollback support.

Chinese documentation is available in [README.zh-CN.md](README.zh-CN.md).

## Status

This project is an experimental MVP.

Current scope: Web RPA with selector-level self-healing.

It is not ready for production use without additional security review, scheduling, authentication, deployment hardening, and environment-specific approval controls.

## What This Is Not

- Not a traditional visual RPA designer.
- Not a full AI Agent that continuously controls the browser.
- Not a framework that calls an LLM during normal execution.
- Not a desktop RPA, OCR, scheduling, or real-website integration layer yet.

## Architecture

- Python Runtime: runs Skill steps, logs step results, captures failure snapshots.
- Skill Registry: loads YAML Skills from `example_skills/`.
- Repair Agent: generates `repair_request.json`, validates selector-only patches.
- Sandbox: copies the project, applies a patch in isolation, and runs tests.
- Version Manager: snapshots, creates new versions after passing tests, and rolls back.

## MVP Scope

The MVP is intentionally narrow:

- Web RPA with Playwright.
- `skill.yaml` workflow definitions.
- `selectors.yaml` primary and fallback selectors.
- Failure screenshots and DOM snapshots.
- Selector-only repair patches.
- Sandbox-tested version updates.
- Rollback to previous Skill versions.

## Install

For framework development or local GitHub checkout usage, install the project in editable mode:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m playwright install chromium
```

After installation, the CLI is available as either `code-rpa` or `code_rpa`.

If you only want to run from the source tree without installing the console script:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

If `python` is not on PATH, use the installed Python executable directly.

## Run Demo

```powershell
python -m code_rpa skill run web_report_export
```

The demo uses `tests/fixtures/report_demo.html`, logs in, opens the report page, selects a date range, exports the report, and verifies the success message.

You can also run the Skill entrypoint directly:

```powershell
python example_skills\web_report_export\main.py
```

## Run Tests

```powershell
python -m pytest
```

Run only unit tests:

```powershell
python -m pytest -m "not integration"
```

Run the real Chromium integration test:

```powershell
python -m pytest -m integration
```

## CLI

```powershell
code-rpa --version
code-rpa --project-root . skill list
code-rpa --project-root . skill show web_report_export
code-rpa --project-root . skill validate web_report_export
code-rpa --project-root . skill run web_report_export
code-rpa --project-root . skill test web_report_export
code-rpa --project-root . skill create my_new_skill
code-rpa --project-root . repair validate path\to\repair_request.json path\to\patch.json
code-rpa --project-root . version list web_report_export
code-rpa --project-root . version current web_report_export
code-rpa --project-root . version show web_report_export <version_id>
code-rpa --project-root . version rollback web_report_export <version_id>
```

The same commands work through the module entrypoint:

```powershell
python -m code_rpa skill list
python -m code_rpa skill show web_report_export
python -m code_rpa skill validate web_report_export
python -m code_rpa skill run web_report_export
python -m code_rpa skill test web_report_export
python -m code_rpa skill create my_new_skill
python -m code_rpa repair validate path\to\repair_request.json path\to\patch.json
python -m code_rpa version list web_report_export
python -m code_rpa version current web_report_export
python -m code_rpa version show web_report_export <version_id>
python -m code_rpa version rollback web_report_export <version_id>
```

## repair_request.json

When a step fails after retry and fallback selectors, the runtime captures failure context and writes `storage/repair_requests/<run_id>/repair_request.json`.

The request includes:

- Skill identity and version.
- Failed step ID and goal.
- Error type and message.
- Current URL.
- Screenshot and DOM snapshot paths.
- Original selector and fallback selectors.
- `allowed_repair_scope` with `scope_type: selector_only`.
- Test command and rollback version.
- Risk level and human approval flag.

The request is for repair planning only. It does not call an LLM.

## patch.json

`patch.json` is the proposed local repair. Phase three only allows selector-level patches:

- `selector_update`
- `fallback_selector_add`

Required fields include:

- `patch_id`
- `skill_id`
- `skill_name`
- `base_version`
- `target_step_id`
- `patch_type`
- `selector_changes`
- `code_changes: null`
- `allowed_repair_scope`
- `reason`
- `risk_level`
- `test_command`
- `created_at`

`selector_changes.target_file` must be a full repository-relative path such as:

```text
example_skills/web_report_export/selectors.yaml
```

## Sandbox Testing

`SandboxRunner` never modifies the live project. It:

1. Copies the project to a temporary directory.
2. Applies the selector patch in the copy.
3. Runs the patch `test_command`.
4. Returns `success`, `stdout`, `stderr`, `duration`, and `patched_skill_path`.

Only a successful sandbox result may be passed to `VersionManager.create_new_version`.

## Versions And Rollback

`VersionManager` stores Skill versions under `storage/versions/<skill_id>/`.

It supports:

- `snapshot`
- `create_new_version`
- `list_versions`
- `get_current_version`
- `rollback_to_version`

Every version stores `metadata.json` with patch ID, base version, test result, changed files, and creation time. Rollback restores the Skill files and updates the current version pointer.

## Create A New RPA Skill

Use the CLI scaffold:

```powershell
python -m code_rpa skill create invoice_export
```

This creates:

```text
example_skills/invoice_export/
  skill.yaml
  selectors.yaml
  repair_policy.yaml
  main.py
  README.md
  tests/test_skill.py
```

Then edit:

- `skill.yaml` for workflow steps.
- `selectors.yaml` for primary and fallback selectors.
- `repair_policy.yaml` for retry and sandbox policy.
- `README.md` for Skill-specific boundaries and commands.
- `tests/test_skill.py` for Skill-level pytest coverage.

Generated Skills are intentionally minimal. They do not introduce new RPA capabilities; they provide the standard file layout expected by the runtime, repair pipeline, sandbox tests, and future Codex agents.

## Skill SDK

You can create a standard Skill directory from Python without invoking the CLI:

```python
from code_rpa.sdk import SkillBuilder

skill = SkillBuilder("invoice_export")
skill.add_step(
    id="open_invoice_page",
    type="navigate",
    goal="Open the invoice export page.",
    url="about:blank",
)
skill.add_step(
    id="click_export",
    type="click",
    goal="Click the invoice export button.",
    selector_ref="export_button",
    target_description="Button that starts invoice export.",
)
skill.add_selector(
    "export_button",
    primary="#export-invoices",
    fallbacks=["button[data-testid='export-invoices']"],
)
skill.save()
```

The SDK only builds Skill files. It does not execute Skills, call an LLM, or add new RPA capabilities.

## Codex Development Contract

This repository includes a local Codex Skill at:

```text
.agents/skills/self-healing-rpa-engineer/
```

Future Codex work should use that Skill for repository-specific rules. The current Phase 3 engineering boundary is:

- Package and document the framework for GitHub use.
- Improve CLI and Skill scaffolding ergonomics.
- Preserve the existing runtime, repair, registry, sandbox, and rollback architecture.
- Do not expand the RPA capability boundary without explicit approval.
- Do not introduce LLM calls into normal Skill execution.
- Do not proceed from P0 to P1, or P1 to P2, without approval.

## Current Capability Boundary

Supported today:

- Web RPA only.
- Python + Playwright runtime.
- YAML-defined Skills under `example_skills/`.
- Primary and fallback selector resolution.
- Failure snapshots and `repair_request.json`.
- Selector-only `patch.json` validation.
- Sandbox-tested Skill version creation.
- Rollback to a previous Skill version.

Not supported yet:

- Desktop RPA.
- OCR RPA.
- Scheduler or queue workers.
- Production authentication and secret management.
- General code patching by an LLM.
- Automatic patch generation from `repair_request.json`.
- Production deployment hardening.

## Safety Boundaries

- Normal execution must not call an LLM.
- Patches must not modify runtime code, repair framework code, registry code, or arbitrary Python files.
- Phase three only allows selector-level patches.
- `code_changes` must be `null`.
- High-risk steps must require human confirmation.
- High-risk patches are rejected for automatic application.
- Secrets, passwords, tokens, cookies, and session data must not be written to logs or repair requests.
