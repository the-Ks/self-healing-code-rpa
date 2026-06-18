# Self-Healing Code RPA Framework

[![Tests](https://github.com/the-Ks/self-healing-code-rpa/actions/workflows/tests.yml/badge.svg)](https://github.com/the-Ks/self-healing-code-rpa/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Playwright](https://img.shields.io/badge/playwright-chromium-2EAD33)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A self-healing Code RPA framework that turns web automation workflows into runnable, testable, repairable, and versioned Skills.

The current MVP supports selector-level self-healing for Web RPA. A Skill is defined in YAML, executed by the Python runtime, observed on failure, repaired through a constrained `patch.json`, tested in a sandbox, and versioned with rollback support.

Chinese documentation is available in [README.zh-CN.md](README.zh-CN.md).

## Status

This project is an experimental MVP.

Current scope: Web RPA with selector-level self-healing.

It is not ready for production use without additional security review, scheduling, authentication, deployment hardening, and environment-specific approval controls.

## Quick Start

```powershell
git clone https://github.com/the-Ks/self-healing-code-rpa.git
cd self-healing-code-rpa
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m playwright install chromium
code-rpa --help
code-rpa --project-root . skill validate web_report_export
code-rpa --project-root . skill run web_report_export
python -m pytest
```

The demo Skill runs against a local HTML fixture. It does not automate a real website.

## What This Is Not

- Not a traditional visual RPA designer.
- Not a full AI Agent that continuously controls the browser.
- Not a framework that calls an LLM during normal execution.
- Not a desktop RPA, OCR, scheduling, or real-website integration layer yet.

## Project Structure

```text
self-healing-code-rpa/
  README.md
  README.zh-CN.md
  LICENSE
  CHANGELOG.md
  CONTRIBUTING.md
  SECURITY.md
  AGENTS.md
  pyproject.toml
  requirements.txt
  pytest.ini
  code_rpa/
  rpa_runtime/
  repair_agent/
  skill_registry/
  example_skills/
  tests/
  docs/
  .agents/
    skills/
      self-healing-rpa-engineer/
  .github/
    workflows/
      tests.yml
  storage/
```

The `code_rpa/` package contains developer-facing CLI, validation, and SDK entrypoints. The core runtime, repair pipeline, and versioning modules remain in `rpa_runtime/`, `repair_agent/`, and `skill_registry/`.

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution boundaries.

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
code-rpa --project-root . repair apply path\to\repair_request.json path\to\patch.json
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
python -m code_rpa repair apply path\to\repair_request.json path\to\patch.json
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
- Run log path and attempted selectors.
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
- `created_at`

`selector_changes.target_file` must be a full repository-relative path such as:

```text
example_skills/web_report_export/selectors.yaml
```

## Sandbox Testing

`SandboxRunner` never modifies the live project. It:

1. Copies the project to a temporary directory.
2. Applies the selector patch in the copy.
3. Runs `repair_request.json` `test_command` with an argument array and `shell=False`.
4. Returns `success`, `stdout`, `stderr`, `duration`, and `patched_skill_path`.

Only a successful sandbox result may be passed to `VersionManager.create_new_version`.

## Minimal Selector Repair Example

The repair path uses a static `patch.json` artifact. It does not call an LLM during normal execution, and P3 does not connect to any real LLM API.

1. Run a Skill. If a selector fails, the runtime writes a repair request:

```powershell
code-rpa --project-root . skill run web_report_export
```

The failure artifact is written under:

```text
storage/repair_requests/<run_id>/repair_request.json
```

2. Validate a selector-only patch:

```powershell
code-rpa --project-root . repair validate storage\repair_requests\<run_id>\repair_request.json patch.json
```

3. Apply the patch through the hardened repair pipeline:

```powershell
code-rpa --project-root . repair apply storage\repair_requests\<run_id>\repair_request.json patch.json
```

The pipeline performs:

```text
repair_request.json
  -> patch.json
  -> strict validation
  -> sandbox test command
  -> original Skill snapshot
  -> new Skill version
  -> live Skill replacement
```

The patch remains constrained:

- `patch_type` must be `selector_update` or `fallback_selector_add`.
- `code_changes` must be `null`.
- `selector_changes.target_file` must be in `allowed_files`.
- `selector_changes.selector_ref` must be in `allowed_selector_refs`.
- Absolute paths, `..` traversal, runtime files, repair files, registry files, and CLI/framework files are rejected.

If validation or sandbox testing fails, the live Skill is not modified. After a successful repair, use `version rollback` to restore the previous Skill version.

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
code-rpa --project-root . skill create invoice_export
```

The command creates the Skill from repository templates under `.agents/skills/self-healing-rpa-engineer/assets/`, adds a runnable Python entrypoint, and prints the next commands:

```text
created example_skills/invoice_export
files:
- example_skills/invoice_export/skill.yaml
- example_skills/invoice_export/selectors.yaml
- example_skills/invoice_export/repair_policy.yaml
- example_skills/invoice_export/main.py
- example_skills/invoice_export/README.md
- example_skills/invoice_export/tests/test_skill.py
next:
- code-rpa --project-root . skill validate invoice_export
- code-rpa --project-root . skill run invoice_export
- code-rpa --project-root . skill test invoice_export
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

### Validate The Skill

```powershell
code-rpa --project-root . skill validate invoice_export
```

Successful output:

```text
PASS
```

Failed validation prints friendly errors:

```text
FAIL
- Missing selectors.yaml
- Duplicate step_id: click_export
- Unknown selector_ref: export_button
```

### Run The Skill

The generated Skill starts with a safe default navigation step:

```yaml
steps:
  - id: open_page
    type: navigate
    goal: Open the starting page for this Skill.
    url: "about:blank"
```

It can run immediately after creation:

```powershell
code-rpa --project-root . skill run invoice_export
```

Then run the generated Skill test:

```powershell
code-rpa --project-root . skill test invoice_export
```

### Complete Edit Example

To turn the scaffold into a real Skill, edit `skill.yaml` and `selectors.yaml` together:

```yaml
# example_skills/invoice_export/skill.yaml
id: invoice_export
name: Invoice Export
version: 0.1.0
entrypoint: main.py
selectors: selectors.yaml
repair_policy: repair_policy.yaml
steps:
  - id: open_invoice_page
    type: navigate
    goal: Open the invoice export page.
    url: "about:blank"

  - id: click_export
    type: click
    goal: Click the invoice export button.
    selector_ref: export_button
    target_description: Button that starts invoice export.
```

```yaml
# example_skills/invoice_export/selectors.yaml
export_button:
  primary: "#export-invoices"
  fallbacks:
    - "button[data-testid='export-invoices']"
```

Then validate again:

```powershell
code-rpa --project-root . skill validate invoice_export
```

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

## Developer Docs

- [Architecture](docs/architecture.md)
- [Skill Spec](docs/skill-spec.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

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

## Roadmap

### v0.1.x Repository Engineering

- Improve repository presentation and contributor documentation.
- Keep installation, CLI, and example Skill workflows easy to verify.
- Preserve current Runtime, Repair, Registry, Sandbox, and Version boundaries.

### P2 Business Skill Examples

- Add realistic business Skill examples that still run against controlled local fixtures or explicitly approved test environments.
- Avoid real account automation, secret handling, and production website integrations until the security model is reviewed.

### Later Production Hardening

- Security review and secret-handling policy.
- Authentication and approval controls.
- Scheduling and deployment design.
- Reliability validation against real-world workflows.

Any roadmap item that expands Runtime, Repair, Version, AI Agent, OCR, Scheduler, or Web UI capability requires explicit approval before implementation.
