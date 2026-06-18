from pathlib import Path
import shutil

from code_rpa.cli import main
from skill_registry.loader import SkillLoader
from skill_registry.version_manager import VersionManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def copy_project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(
        PROJECT_ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    return target


def seed_version(project_root: Path, version_root: Path) -> str:
    skill = SkillLoader().load(project_root / "example_skills" / "web_report_export" / "skill.yaml")
    manager = VersionManager(version_root)
    version_dir = manager.snapshot(skill, reason="baseline")
    return version_dir.name


def test_version_cli_lists_current_shows_and_rolls_back(tmp_path, capsys):
    project = copy_project(tmp_path)
    version_root = project / "storage" / "versions"
    version_id = seed_version(project, version_root)

    exit_code = main(["--project-root", str(project), "version", "list", "web_report_export"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert version_id in captured.out

    exit_code = main(["--project-root", str(project), "version", "current", "web_report_export"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert version_id in captured.out

    exit_code = main(
        ["--project-root", str(project), "version", "show", "web_report_export", version_id]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert version_id in captured.out

    exit_code = main(
        ["--project-root", str(project), "version", "rollback", "web_report_export", version_id]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"rolled back web_report_export to {version_id}" in captured.out
