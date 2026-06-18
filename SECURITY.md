# Security Policy

Self-Healing Code RPA is an experimental MVP. It is not recommended for production use without additional security review, authentication, scheduling, deployment hardening, and real-world reliability validation.

## Supported Versions

| Version | Supported |
| --- | --- |
| v0.1.x | Yes |

## Security Boundary

Current supported scope:

- Web RPA only.
- Python + Playwright.
- YAML-defined Skills.
- Selector-level self-healing.
- Repair Request -> Patch -> Sandbox -> Version -> Rollback.

Out of scope:

- OCR.
- Desktop RPA.
- Scheduler.
- Web UI.
- Multitenancy.
- Cloud execution.
- Real website integrations.
- Automatic LLM-driven browser control.
- LLM calls during normal execution.
- Arbitrary code patching.

## Sensitive Data Rules

- Do not commit secrets, tokens, passwords, cookies, session data, or production credentials.
- Do not write secrets to `repair_request.json`, logs, screenshots, DOM snapshots, or test fixtures.
- Use local fixtures or dedicated test systems for examples.
- Treat screenshots and DOM captures as sensitive until reviewed.

## Patch Safety Rules

The current repair model only allows selector-level patches.

- `code_changes` must remain `null`.
- Patches must not modify `rpa_runtime/`, `repair_agent/`, or `skill_registry/`.
- High-risk steps should require human confirmation.
- High-risk patches should not be applied automatically.
- Sandbox tests must pass before version creation.

## Reporting a Vulnerability

For now, report vulnerabilities privately through the GitHub repository owner rather than opening a public issue with exploit details.

Include:

- Affected version or commit.
- Steps to reproduce.
- Expected and actual behavior.
- Whether sensitive data can be exposed.
- Suggested mitigation, if known.

Please avoid sharing real credentials, production screenshots, cookies, or session data in reports.
