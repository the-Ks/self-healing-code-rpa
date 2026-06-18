"""End-to-end selector repair pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from repair_agent.patch_validator import PatchValidationResult, PatchValidator
from repair_agent.sandbox_runner import SandboxResult, SandboxRunner
from skill_registry.registry import SkillRegistry
from skill_registry.version_manager import VersionManager


@dataclass(frozen=True)
class RepairPipelineResult:
    success: bool
    stage: str
    errors: list[str] = field(default_factory=list)
    validation: PatchValidationResult | None = None
    sandbox: SandboxResult | None = None
    original_version_id: str | None = None
    new_version_id: str | None = None


class RepairPipeline:
    """Validate, sandbox, and version a selector-only repair patch."""

    def __init__(
        self,
        *,
        project_root: Path,
        sandbox_runner: SandboxRunner | None = None,
        patch_validator: PatchValidator | None = None,
    ):
        self.project_root = project_root.resolve()
        self.sandbox_runner = sandbox_runner or SandboxRunner()
        self.patch_validator = patch_validator or PatchValidator()

    def apply(self, repair_request_path: str | Path, patch_path: str | Path) -> RepairPipelineResult:
        repair_request_path = Path(repair_request_path)
        patch_path = Path(patch_path)
        repair_request = self._read_json(repair_request_path)
        patch = self._read_json(patch_path)

        skill_id = repair_request.get("skill_id")
        skill = SkillRegistry(self.project_root / "example_skills").load(str(skill_id))
        validation = self.patch_validator.validate_patch(repair_request, patch, current_skill=skill)
        if not validation.is_valid:
            return RepairPipelineResult(
                success=False,
                stage="validation",
                errors=validation.errors,
                validation=validation,
            )

        try:
            sandbox = self.sandbox_runner.run_patch(
                skill=skill,
                patch=patch,
                test_command=repair_request.get("test_command", []),
                project_root=self.project_root,
            )
        except Exception as error:
            return RepairPipelineResult(
                success=False,
                stage="sandbox",
                errors=[str(error)],
                validation=validation,
            )
        if not sandbox.success:
            return RepairPipelineResult(
                success=False,
                stage="sandbox",
                errors=[sandbox.stderr or "Sandbox verification failed"],
                validation=validation,
                sandbox=sandbox,
            )

        version_manager = VersionManager(self.project_root / "storage" / "versions")
        original_version = version_manager.snapshot(
            skill,
            reason=f"before_{patch.get('patch_id', 'repair')}",
        )
        try:
            new_version = version_manager.create_new_version(
                skill=skill,
                patched_skill_path=sandbox.patched_skill_path,
                patch=patch,
                test_result=sandbox,
                repair_request_path=repair_request_path,
            )
        except Exception as error:
            return RepairPipelineResult(
                success=False,
                stage="apply",
                errors=[str(error)],
                validation=validation,
                sandbox=sandbox,
                original_version_id=original_version.name,
            )

        return RepairPipelineResult(
            success=True,
            stage="complete",
            validation=validation,
            sandbox=sandbox,
            original_version_id=original_version.name,
            new_version_id=new_version.name,
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be an object: {path}")
        return data
