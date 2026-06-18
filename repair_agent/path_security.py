"""Path safety helpers for selector-only repair patches."""

from __future__ import annotations

from pathlib import Path


def resolve_allowed_selector_target(
    *,
    project_root: Path,
    skill_root: Path,
    target_file: str,
    allowed_files: list[str] | set[str],
) -> Path:
    """Resolve a patch target and prove it stays within the allowed Skill root."""

    project_root = project_root.resolve()
    skill_root = skill_root.resolve()
    _require_inside(skill_root, project_root, "Skill root must stay inside the project root")

    target_path = _safe_relative_path(target_file, "selector_changes.target_file")
    target_resolved = (project_root / target_path).resolve()
    _require_inside(target_resolved, project_root, "selector_changes.target_file escapes the project root")
    _require_inside(target_resolved, skill_root, "selector_changes.target_file escapes the Skill root")

    allowed_resolved = {
        _resolve_allowed_file(project_root, skill_root, allowed_file)
        for allowed_file in allowed_files
    }
    if target_resolved not in allowed_resolved:
        raise ValueError("selector_changes.target_file must resolve to an allowed file")
    return target_resolved


def normalize_relative_path(path_value: str, label: str) -> str:
    return _safe_relative_path(path_value, label).as_posix()


def _resolve_allowed_file(project_root: Path, skill_root: Path, allowed_file: str) -> Path:
    allowed_path = _safe_relative_path(allowed_file, "allowed_repair_scope.allowed_files")
    allowed_resolved = (project_root / allowed_path).resolve()
    _require_inside(allowed_resolved, project_root, "allowed file escapes the project root")
    _require_inside(allowed_resolved, skill_root, "allowed file escapes the Skill root")
    return allowed_resolved


def _safe_relative_path(path_value: str, label: str) -> Path:
    if not isinstance(path_value, str) or not path_value:
        raise ValueError(f"{label} must be a non-empty string")
    normalized = path_value.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute():
        raise ValueError(f"{label} must be a repository-relative path")
    if ".." in path.parts:
        raise ValueError(f"{label} must not contain '..' path traversal")
    return path


def _require_inside(path: Path, root: Path, message: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(message) from error
