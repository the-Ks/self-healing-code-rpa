# Skill Spec

A Skill is a versioned Web RPA workflow stored under `example_skills/<skill_id>/`.

## Required Directory Structure

```text
example_skills/<skill_id>/
  skill.yaml
  selectors.yaml
  repair_policy.yaml
  main.py
  README.md
  tests/test_skill.py
```

The current validator requires:

- `skill.yaml`
- `selectors.yaml`
- `repair_policy.yaml`
- `main.py`
- `tests/test_skill.py`
- required `skill.yaml` fields
- unique step IDs
- valid selector references
- valid selector definitions
- valid repair policy structure

## `skill.yaml`

Required top-level fields:

```yaml
id: web_report_export
name: Web Report Export
version: 0.2.0
entrypoint: main.py
selectors: selectors.yaml
repair_policy: repair_policy.yaml
steps: []
```

Each step must have:

- `id`
- `type`
- `goal`

Supported step types:

- `navigate`
- `click`
- `fill`
- `login`
- `select_date_range`
- `wait_for_selector`

### `navigate`

```yaml
- id: open_page
  type: navigate
  goal: Open the starting page.
  url: "about:blank"
```

### `click`

```yaml
- id: click_export
  type: click
  goal: Click the export button.
  selector_ref: export_button
  target_description: Button that starts export.
```

### `fill`

```yaml
- id: fill_search
  type: fill
  goal: Fill the search input.
  selector_ref: search_input
  value: invoice
```

### `login`

```yaml
- id: login
  type: login
  goal: Enter credentials and submit the login form.
  selector_refs:
    username: username_input
    password: password_input
    submit: login_submit_button
  username_value: demo_user
  password_value: demo_password
```

### `select_date_range`

```yaml
- id: select_date_range
  type: select_date_range
  goal: Select the report date range.
  selector_refs:
    start_date: date_start_input
    end_date: date_end_input
  start_date: "2026-06-01"
  end_date: "2026-06-17"
```

### `wait_for_selector`

```yaml
- id: verify_success
  type: wait_for_selector
  goal: Wait for the success state.
  selector_ref: export_success_message
```

## `selectors.yaml`

Selectors are keyed by logical `selector_ref` names.

```yaml
export_button:
  primary: "#export-button-primary"
  fallbacks:
    - "button[data-testid='export-button']"
    - "text=Export Report"
```

Rules:

- `selector_ref` values in `skill.yaml` must exist in `selectors.yaml`.
- `primary` must be a non-empty string.
- `fallbacks` must be a list of strings when present.
- Keep selectors specific enough for deterministic automation.

## `repair_policy.yaml`

```yaml
retry:
  max_attempts: 1
  delay_seconds: 0
allowed_patch_scope:
  - failed_step
  - selectors
sandbox:
  required: true
  command:
    - python
    - -m
    - pytest
```

Validator checks:

- `retry` is a mapping when present.
- `retry.max_attempts` is an integer greater than or equal to 1.
- `retry.delay_seconds` is a non-negative number.
- `allowed_patch_scope` is a list when present.
- `sandbox` is required.
- `sandbox.required` is a boolean.
- `sandbox.command` is a non-empty list of strings.

## Validation

```powershell
code-rpa --project-root . skill validate <skill_id>
```

Expected successful output:

```text
PASS
```

Expected failure output:

```text
FAIL
- Missing selectors.yaml
- Missing required skill.yaml field: entrypoint
- Duplicate step_id: click_export
- Unknown selector_ref: export_button
- Selector 'export_button' fallbacks must be a list of strings
```

## CLI Generation

```powershell
code-rpa --project-root . skill create invoice_export
```

The generated default Skill can be validated, run, and tested immediately:

```powershell
code-rpa --project-root . skill validate invoice_export
code-rpa --project-root . skill run invoice_export
code-rpa --project-root . skill test invoice_export
```

## SDK Generation

```python
from code_rpa.sdk import SkillBuilder

skill = SkillBuilder("invoice_export")
skill.add_step(
    id="open_invoice_page",
    type="navigate",
    goal="Open the invoice export page.",
    url="about:blank",
)
skill.add_selector(
    "export_button",
    primary="#export-invoices",
    fallbacks=["button[data-testid='export-invoices']"],
)
skill.save()
```

The SDK only generates Skill files. It does not execute Skills, call an LLM, or expand the runtime boundary.
