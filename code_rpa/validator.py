"""Validation helpers for repository RPA Skill directories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SkillValidationResult:
    skill_id: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)


class SkillValidator:
    """Validate Skill files without executing runtime code."""

    REQUIRED_SKILL_FIELDS = ["id", "name", "version", "entrypoint", "selectors", "repair_policy", "steps"]
    SUPPORTED_STEP_TYPES = {"navigate", "click", "fill", "login", "select_date_range", "wait_for_selector"}
    SELECTOR_REF_STEP_TYPES = {"click", "fill", "wait_for_selector"}
    SELECTOR_REFS_BY_STEP_TYPE = {
        "login": {"username", "password", "submit"},
        "select_date_range": {"start_date", "end_date"},
    }

    def __init__(self, skills_root: Path):
        self.skills_root = skills_root

    def validate(self, skill_id: str) -> SkillValidationResult:
        skill_dir = self.skills_root / skill_id
        errors: list[str] = []

        self._validate_base_structure(skill_dir, errors)

        skill_path = skill_dir / "skill.yaml"
        selectors_path = skill_dir / "selectors.yaml"
        repair_policy_path = skill_dir / "repair_policy.yaml"

        skill = self._read_yaml_if_present(skill_path, errors)
        selectors = self._read_yaml_if_present(selectors_path, errors)
        repair_policy = self._read_yaml_if_present(repair_policy_path, errors)

        if skill is not None:
            self._validate_skill_header(skill_dir, skill, errors)
            self._validate_steps(skill, selectors or {}, errors)

        if selectors is not None:
            self._validate_selectors(selectors, errors)

        if repair_policy is not None:
            self._validate_repair_policy(repair_policy, errors)

        return SkillValidationResult(skill_id=skill_id, is_valid=not errors, errors=errors)

    def _validate_base_structure(self, skill_dir: Path, errors: list[str]) -> None:
        required_files = [
            "skill.yaml",
            "selectors.yaml",
            "repair_policy.yaml",
            "main.py",
            "tests/test_skill.py",
        ]
        if not skill_dir.exists():
            errors.append(f"Missing Skill directory: {skill_dir.name}")
            return
        if not skill_dir.is_dir():
            errors.append(f"Skill path is not a directory: {skill_dir.name}")
            return
        for relative_path in required_files:
            if not (skill_dir / relative_path).exists():
                errors.append(f"Missing {relative_path}")

    def _read_yaml_if_present(self, path: Path, errors: list[str]) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as error:
            errors.append(f"Invalid YAML in {path.name}: {error}")
            return None
        if not isinstance(data, dict):
            errors.append(f"{path.name} root must be a mapping")
            return None
        return data

    def _validate_skill_header(
        self,
        skill_dir: Path,
        skill: dict[str, Any],
        errors: list[str],
    ) -> None:
        for field_name in self.REQUIRED_SKILL_FIELDS:
            if field_name not in skill:
                errors.append(f"Missing required skill.yaml field: {field_name}")

        for field_name in ["id", "name", "version", "entrypoint", "selectors", "repair_policy"]:
            value = skill.get(field_name)
            if value is not None and not isinstance(value, str):
                errors.append(f"skill.yaml field '{field_name}' must be a string")

        skill_id = skill.get("id")
        if isinstance(skill_id, str) and skill_id != skill_dir.name:
            errors.append(f"skill.yaml id must match directory name: expected {skill_dir.name}, got {skill_id}")

        entrypoint = skill.get("entrypoint")
        if isinstance(entrypoint, str) and not (skill_dir / entrypoint).exists():
            errors.append(f"Missing entrypoint file: {entrypoint}")

    def _validate_selectors(self, selectors: dict[str, Any], errors: list[str]) -> None:
        for selector_ref, selector in selectors.items():
            if not isinstance(selector_ref, str) or not selector_ref:
                errors.append("Selector refs must be non-empty strings")
                continue
            if not isinstance(selector, dict):
                errors.append(f"Selector '{selector_ref}' must be a mapping")
                continue

            primary = selector.get("primary")
            if not isinstance(primary, str) or not primary:
                errors.append(f"Selector '{selector_ref}' primary must be a non-empty string")

            fallbacks = selector.get("fallbacks", [])
            if fallbacks is not None:
                if not isinstance(fallbacks, list) or not all(isinstance(item, str) for item in fallbacks):
                    errors.append(f"Selector '{selector_ref}' fallbacks must be a list of strings")

    def _validate_steps(
        self,
        skill: dict[str, Any],
        selectors: dict[str, Any],
        errors: list[str],
    ) -> None:
        steps = skill.get("steps")
        if not isinstance(steps, list):
            errors.append("skill.yaml steps must be a list")
            return

        seen_step_ids: set[str] = set()
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step at index {index} must be a mapping")
                continue

            step_id = step.get("id")
            if not step_id:
                errors.append(f"Step at index {index} is missing id")
                continue
            if step_id in seen_step_ids:
                errors.append(f"Duplicate step_id: {step_id}")
            seen_step_ids.add(str(step_id))

            step_type = step.get("type")
            if not step_type:
                errors.append(f"Step {step_id} is missing type")
                continue
            if step_type not in self.SUPPORTED_STEP_TYPES:
                errors.append(f"Unsupported step type in step {step_id}: {step_type}")
                continue

            if not step.get("goal"):
                errors.append(f"Step {step_id} is missing goal")

            if step_type == "navigate":
                url = step.get("url")
                if not isinstance(url, str) or not url:
                    errors.append(f"Step {step_id} navigate url must be a non-empty string")

            if step_type in self.SELECTOR_REF_STEP_TYPES:
                selector_ref = step.get("selector_ref")
                if not selector_ref:
                    errors.append(f"Missing selector_ref in step: {step_id}")
                    continue
                self._validate_selector_ref(str(selector_ref), selectors, errors)

            required_selector_refs = self.SELECTOR_REFS_BY_STEP_TYPE.get(str(step_type), set())
            if required_selector_refs:
                selector_refs = step.get("selector_refs")
                if not isinstance(selector_refs, dict):
                    errors.append(f"Missing selector_refs in step: {step_id}")
                    continue
                for ref_name in sorted(required_selector_refs):
                    selector_ref = selector_refs.get(ref_name)
                    if not selector_ref:
                        errors.append(f"Missing selector_ref '{ref_name}' in step: {step_id}")
                        continue
                    self._validate_selector_ref(str(selector_ref), selectors, errors)

    def _validate_selector_ref(
        self,
        selector_ref: str,
        selectors: dict[str, Any],
        errors: list[str],
    ) -> None:
        if selector_ref not in selectors:
            errors.append(f"Unknown selector_ref: {selector_ref}")

    def _validate_repair_policy(self, repair_policy: dict[str, Any], errors: list[str]) -> None:
        retry = repair_policy.get("retry")
        if retry is not None:
            if not isinstance(retry, dict):
                errors.append("repair_policy.retry must be a mapping")
            else:
                max_attempts = retry.get("max_attempts", 1)
                delay_seconds = retry.get("delay_seconds", 0)
                if not isinstance(max_attempts, int) or max_attempts < 1:
                    errors.append("repair_policy.retry.max_attempts must be an integer >= 1")
                if not isinstance(delay_seconds, (int, float)) or delay_seconds < 0:
                    errors.append("repair_policy.retry.delay_seconds must be a number >= 0")

        allowed_patch_scope = repair_policy.get("allowed_patch_scope")
        if allowed_patch_scope is not None and not isinstance(allowed_patch_scope, list):
            errors.append("repair_policy.allowed_patch_scope must be a list")

        sandbox = repair_policy.get("sandbox")
        if sandbox is None:
            errors.append("repair_policy.sandbox is required")
            return
        if not isinstance(sandbox, dict):
            errors.append("repair_policy.sandbox must be a mapping")
            return

        required = sandbox.get("required")
        if not isinstance(required, bool):
            errors.append("repair_policy.sandbox.required must be a boolean")

        command = sandbox.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            errors.append("repair_policy.sandbox.command must be a non-empty list of strings")
