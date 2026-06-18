"""Run selector-only repair patches in an isolated project copy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

from repair_agent.path_security import resolve_allowed_selector_target


@dataclass(frozen=True)
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    duration: float
    sandbox_project_path: str
    patched_skill_path: str
    test_command: list[str]


class SandboxRunner:
    """Copy the project, apply a patch, and run tests in isolation."""

    def __init__(self, sandbox_root: Path | None = None):
        self.sandbox_root = sandbox_root

    def run_patch(
        self,
        *,
        skill: Any,
        patch: dict[str, Any],
        test_command: list[str],
        project_root: Path | None = None,
    ) -> SandboxResult:
        source_project = (project_root or self._infer_project_root(skill)).resolve()
        sandbox_parent = self._make_sandbox_parent()
        sandbox_project = sandbox_parent / source_project.name
        sandbox_skill = sandbox_project / skill.base_path.resolve().relative_to(source_project)

        started = perf_counter()
        try:
            command = self._normalize_test_command(test_command, sandbox_parent=sandbox_parent)
            shutil.copytree(source_project, sandbox_project, ignore=self._ignore_runtime_artifacts)
            sandbox_skill_root = sandbox_project / skill.base_path.resolve().relative_to(source_project)
            self.apply_patch_to_project(sandbox_project, patch, skill_root=sandbox_skill_root)
            completed = subprocess.run(
                command,
                cwd=sandbox_project,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                shell=False,
            )
            duration = perf_counter() - started
            return SandboxResult(
                success=completed.returncode == 0,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                duration=duration,
                sandbox_project_path=str(sandbox_project),
                patched_skill_path=str(sandbox_skill),
                test_command=command,
            )
        except Exception as error:
            duration = perf_counter() - started
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(error),
                duration=duration,
                sandbox_project_path=str(sandbox_project),
                patched_skill_path=str(sandbox_skill),
                test_command=test_command if isinstance(test_command, list) else [],
            )

    def apply_patch_to_project(
        self,
        sandbox_project_root: Path,
        patch: dict[str, Any],
        *,
        skill_root: Path | None = None,
    ) -> None:
        patch_type = patch["patch_type"]
        selector_changes = patch["selector_changes"]
        skill_root = skill_root or sandbox_project_root / "example_skills" / patch["skill_id"]
        if patch_type == "selector_update":
            self._apply_selector_update(sandbox_project_root, skill_root, patch, selector_changes)
            return
        if patch_type == "fallback_selector_add":
            self._apply_fallback_selector_add(sandbox_project_root, skill_root, patch, selector_changes)
            return
        raise ValueError(f"Unsupported patch_type: {patch_type}")

    def _apply_selector_update(
        self,
        sandbox_project_root: Path,
        skill_root: Path,
        patch: dict[str, Any],
        selector_changes: dict[str, Any],
    ) -> None:
        selectors_path = self._safe_target_path(sandbox_project_root, skill_root, patch, selector_changes["target_file"])
        selectors = yaml.safe_load(selectors_path.read_text(encoding="utf-8")) or {}
        selector_ref = selector_changes["selector_ref"]
        current = selectors.setdefault(selector_ref, {})

        if selector_changes.get("new_primary") is not None:
            current["primary"] = selector_changes["new_primary"]
        if selector_changes.get("new_fallbacks") is not None:
            current["fallbacks"] = selector_changes["new_fallbacks"]

        self._write_yaml_atomic(selectors_path, selectors)

    def _apply_fallback_selector_add(
        self,
        sandbox_project_root: Path,
        skill_root: Path,
        patch: dict[str, Any],
        selector_changes: dict[str, Any],
    ) -> None:
        selectors_path = self._safe_target_path(sandbox_project_root, skill_root, patch, selector_changes["target_file"])
        selectors = yaml.safe_load(selectors_path.read_text(encoding="utf-8")) or {}
        selector_ref = selector_changes["selector_ref"]
        current = selectors.setdefault(selector_ref, {})
        existing = list(current.get("fallbacks", []) or [])
        for candidate in selector_changes.get("add_fallbacks", []):
            if candidate not in existing:
                existing.append(candidate)
        current["fallbacks"] = existing
        self._write_yaml_atomic(selectors_path, selectors)

    def _safe_target_path(
        self,
        sandbox_project_root: Path,
        skill_root: Path,
        patch: dict[str, Any],
        target_file: str,
    ) -> Path:
        return resolve_allowed_selector_target(
            project_root=sandbox_project_root,
            skill_root=skill_root,
            target_file=target_file,
            allowed_files=patch.get("allowed_repair_scope", {}).get("allowed_files", []),
        )

    def _write_yaml_atomic(self, path: Path, data: dict[str, Any]) -> None:
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        os.replace(temp_path, path)

    def _infer_project_root(self, skill: Any) -> Path:
        base_path = skill.base_path.resolve()
        for parent in [base_path, *base_path.parents]:
            if (parent / "rpa_runtime").exists() and (parent / "skill_registry").exists():
                return parent
        return base_path.parent

    def _make_sandbox_parent(self) -> Path:
        if self.sandbox_root:
            self.sandbox_root.mkdir(parents=True, exist_ok=True)
            return Path(tempfile.mkdtemp(prefix="repair_sandbox_", dir=self.sandbox_root))
        return Path(tempfile.mkdtemp(prefix="repair_sandbox_"))

    def _normalize_test_command(self, test_command: list[str], *, sandbox_parent: Path) -> list[str]:
        if not isinstance(test_command, list) or not test_command or not all(
            isinstance(item, str) for item in test_command
        ):
            raise ValueError("repair_request.test_command must be a non-empty list of strings")
        self._reject_shell_metacharacters(test_command)
        if test_command[:3] == ["python", "-m", "pytest"]:
            command = [sys.executable, "-m", "pytest", *test_command[3:]]
            return self._with_pytest_basetemp(command, sandbox_parent=sandbox_parent)
        raise ValueError("repair_request.test_command must start with ['python', '-m', 'pytest']")

    def _with_pytest_basetemp(self, command: list[str], *, sandbox_parent: Path) -> list[str]:
        if self._has_pytest_basetemp(command):
            return command
        basetemp = Path(tempfile.mkdtemp(prefix="pytest_basetemp_", dir=sandbox_parent))
        return [*command, "--basetemp", str(basetemp)]

    def _has_pytest_basetemp(self, command: list[str]) -> bool:
        return any(item == "--basetemp" or item.startswith("--basetemp=") for item in command)

    def _reject_shell_metacharacters(self, test_command: list[str]) -> None:
        blocked = {";", "&", "|", ">", "<", "`", "\n", "\r"}
        for item in test_command:
            if any(char in item for char in blocked):
                raise ValueError("repair_request.test_command must not contain shell metacharacters")

    def _ignore_runtime_artifacts(self, directory: str, names: list[str]) -> set[str]:
        ignored = {
            ".git",
            ".venv",
            ".pytest_cache",
            "__pycache__",
        }
        if Path(directory).name == "storage":
            ignored.update(name for name in names if name != ".gitkeep")
        ignored.update(name for name in names if name.endswith(".pyc"))
        return ignored.intersection(names)
