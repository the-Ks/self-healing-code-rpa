# Contributing

Thank you for helping improve Self-Healing Code RPA.

This repository is currently in the Repository Engineering and Developer Experience phase. Contributions should improve packaging, documentation, examples, tests, and developer workflows without expanding the core RPA capability boundary.

## Development Setup

```powershell
git clone https://github.com/the-Ks/self-healing-code-rpa.git
cd self-healing-code-rpa
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m playwright install chromium
python -m pytest
```

Verify the CLI:

```powershell
code-rpa --help
code-rpa --project-root . skill validate web_report_export
code-rpa --project-root . skill run web_report_export
```

## Contribution Boundary

Allowed in the current phase:

- README and documentation improvements.
- GitHub Actions and repository engineering.
- Skill authoring documentation.
- Tests for existing behavior.
- Local fixture-based example improvements.
- CLI documentation and developer experience validation.

Not allowed without explicit approval:

- Runtime capability expansion.
- Repair pipeline capability expansion.
- Version system rewrites.
- AI Agent mode.
- LLM calls during normal execution.
- OCR.
- Desktop RPA.
- Scheduler or queue workers.
- Web UI.
- Cloud features.
- Multitenancy.
- Database restructuring.
- Real website integrations.

## Protected Core Modules

Do not modify these modules during repository-engineering work:

```text
rpa_runtime/
repair_agent/
skill_registry/
```

Changes to these modules require a separate architecture review and explicit approval.

## Pull Request Checklist

- The change stays inside the approved phase boundary.
- `python -m pytest` passes locally.
- New docs match the current implementation.
- No secrets, cookies, tokens, or real user data are committed.
- Example Skills use local fixtures or approved test environments.
- Any generated runtime artifacts under `storage/` are excluded from the commit.

## Skill Contributions

New Skills should follow the standard structure:

```text
example_skills/<skill_id>/
  skill.yaml
  selectors.yaml
  repair_policy.yaml
  main.py
  README.md
  tests/test_skill.py
```

Run validation before submitting:

```powershell
code-rpa --project-root . skill validate <skill_id>
```

Skills should remain Web RPA Skills using Python + Playwright and selector-level self-healing.
