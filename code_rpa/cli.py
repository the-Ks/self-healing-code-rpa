"""Minimal CLI for the Self-Healing Code RPA framework."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from code_rpa import __version__
from code_rpa.templates import SkillTemplateSystem
from code_rpa.validator import SkillValidator
from repair_agent.patch_validator import PatchValidator
from repair_agent.pipeline import RepairPipeline
from skill_registry.registry import SkillRegistry
from skill_registry.version_manager import VersionManager


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()

    if args.group == "skill":
        return handle_skill(args, project_root)
    if args.group == "repair":
        return handle_repair(args, project_root)
    if args.group == "version":
        return handle_version(args, project_root)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="code_rpa")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--version", action="version", version=f"code_rpa {__version__}")
    subparsers = parser.add_subparsers(dest="group")

    skill_parser = subparsers.add_parser("skill")
    skill_sub = skill_parser.add_subparsers(dest="action")
    skill_sub.add_parser("list")
    skill_create = skill_sub.add_parser("create")
    skill_create.add_argument("skill_id")
    skill_run = skill_sub.add_parser("run")
    skill_run.add_argument("skill_id")
    skill_test = skill_sub.add_parser("test")
    skill_test.add_argument("skill_id")
    skill_show = skill_sub.add_parser("show")
    skill_show.add_argument("skill_id")
    skill_validate = skill_sub.add_parser("validate")
    skill_validate.add_argument("skill_id")

    repair_parser = subparsers.add_parser("repair")
    repair_sub = repair_parser.add_subparsers(dest="action")
    repair_validate = repair_sub.add_parser("validate")
    repair_validate.add_argument("repair_request_path")
    repair_validate.add_argument("patch_path")
    repair_apply = repair_sub.add_parser("apply")
    repair_apply.add_argument("repair_request_path")
    repair_apply.add_argument("patch_path")

    version_parser = subparsers.add_parser("version")
    version_sub = version_parser.add_subparsers(dest="action")
    version_list = version_sub.add_parser("list")
    version_list.add_argument("skill_id")
    version_current = version_sub.add_parser("current")
    version_current.add_argument("skill_id")
    version_show = version_sub.add_parser("show")
    version_show.add_argument("skill_id")
    version_show.add_argument("version_id")
    version_rollback = version_sub.add_parser("rollback")
    version_rollback.add_argument("skill_id")
    version_rollback.add_argument("version_id")

    return parser


def handle_skill(args: argparse.Namespace, project_root: Path) -> int:
    registry = SkillRegistry(project_root / "example_skills")

    if args.action == "list":
        for skill_id in registry.list_skill_ids():
            print(skill_id)
        return 0

    if args.action == "create":
        try:
            created = SkillTemplateSystem(project_root).create_skill(args.skill_id)
        except (FileExistsError, ValueError) as error:
            print("FAIL")
            print(f"- {error}")
            return 1
        print(f"created {created.skill_dir.relative_to(project_root)}")
        print("files:")
        for path in created.files:
            print(f"- {path.relative_to(project_root)}")
        print("next:")
        print(f"- code-rpa --project-root . skill validate {args.skill_id}")
        print(f"- code-rpa --project-root . skill run {args.skill_id}")
        print(f"- code-rpa --project-root . skill test {args.skill_id}")
        return 0

    if args.action == "run":
        result = run_skill(project_root, args.skill_id)
        print(result)
        return 0

    if args.action == "test":
        return test_skill(project_root, args.skill_id)

    if args.action == "show":
        skill = registry.load(args.skill_id)
        print(json.dumps(skill_summary(skill), indent=2, ensure_ascii=False))
        return 0

    if args.action == "validate":
        result = SkillValidator(project_root / "example_skills").validate(args.skill_id)
        if result.is_valid:
            print("PASS")
            return 0
        print("FAIL")
        for error in result.errors:
            print(f"- {error}")
        return 1

    return 1


def handle_repair(args: argparse.Namespace, project_root: Path) -> int:
    if args.action == "apply":
        try:
            result = RepairPipeline(project_root=project_root).apply(
                args.repair_request_path,
                args.patch_path,
            )
        except Exception as error:
            print("repair failed")
            print(f"stage: setup")
            print(f"- {error}")
            return 1

        sandbox_status = "SKIPPED"
        if result.sandbox is not None:
            sandbox_status = "PASS" if result.sandbox.success else "FAIL"
        print(f"validation: {'PASS' if result.validation and result.validation.is_valid else 'FAIL'}")
        print(f"sandbox: {sandbox_status}")
        print(f"apply: {'PASS' if result.success else 'SKIPPED'}")
        if result.original_version_id:
            print(f"source_version_id: {result.original_version_id}")
        if result.new_version_id:
            print(f"new_version_id: {result.new_version_id}")
        if result.success:
            print("repair: PASS")
            return 0

        print(f"repair: FAIL at {result.stage}")
        for error in result.errors:
            print(f"- {error}")
        return 1

    repair_request = read_json(Path(args.repair_request_path))
    skill_id = repair_request["skill_id"]
    skill = SkillRegistry(project_root / "example_skills").load(skill_id)
    validator = PatchValidator()
    result = validator.validate_patch_file(
        args.repair_request_path,
        args.patch_path,
        current_skill=skill,
    )
    if result.is_valid:
        print("valid")
        return 0
    print("invalid")
    for error in result.errors:
        print(error)
    return 1


def handle_version(args: argparse.Namespace, project_root: Path) -> int:
    manager = VersionManager(project_root / "storage" / "versions")

    if args.action == "list":
        for version in manager.list_versions(args.skill_id):
            print(version["version_id"])
        return 0

    if args.action == "current":
        current = manager.get_current_version(args.skill_id)
        if current is None:
            print("No current version")
            return 1
        print(json.dumps(current, indent=2, ensure_ascii=False))
        return 0

    if args.action == "show":
        version = find_version(manager, args.skill_id, args.version_id)
        if version is None:
            print(f"Version not found: {args.version_id}")
            return 1
        print(json.dumps(version, indent=2, ensure_ascii=False))
        return 0

    if args.action == "rollback":
        skill = SkillRegistry(project_root / "example_skills").load(args.skill_id)
        manager.rollback_to_version(skill=skill, version_id=args.version_id)
        print(f"rolled back {args.skill_id} to {args.version_id}")
        return 0

    return 1


def run_skill(project_root: Path, skill_id: str) -> dict[str, Any]:
    module = load_skill_main(project_root, skill_id)
    result = module.run(storage_root=project_root / "storage")
    return result.to_dict()


def test_skill(project_root: Path, skill_id: str) -> int:
    skill_test_dir = project_root / "example_skills" / skill_id / "tests"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(skill_test_dir)],
        cwd=project_root,
        check=False,
    )
    return completed.returncode


def load_skill_main(project_root: Path, skill_id: str) -> Any:
    main_path = project_root / "example_skills" / skill_id / "main.py"
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    spec = importlib.util.spec_from_file_location(f"{skill_id}_main", main_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load Skill entrypoint: {main_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def skill_summary(skill: Any) -> dict[str, Any]:
    return {
        "id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "entrypoint": skill.entrypoint,
        "base_path": str(skill.base_path),
        "steps": len(skill.steps),
        "selectors": len(skill.selectors),
        "repair_policy": str(skill.repair_policy_path),
    }


def find_version(manager: VersionManager, skill_id: str, version_id: str) -> dict[str, Any] | None:
    for version in manager.list_versions(skill_id):
        if version.get("version_id") == version_id:
            return version
    return None


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return data
