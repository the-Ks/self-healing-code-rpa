from pathlib import Path
import shutil

import yaml

from code_rpa.cli import main
from code_rpa.validator import SkillValidator


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def copy_project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(
        PROJECT_ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    return target


def test_skill_validator_accepts_web_report_export():
    result = SkillValidator(PROJECT_ROOT / "example_skills").validate("web_report_export")

    assert result.is_valid is True
    assert result.errors == []


def test_cli_skill_validate_prints_pass(capsys):
    exit_code = main(["--project-root", str(PROJECT_ROOT), "skill", "validate", "web_report_export"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "PASS"


def test_cli_skill_validate_reports_missing_files_and_duplicate_steps(tmp_path, capsys):
    project = copy_project(tmp_path)
    skill_dir = project / "example_skills" / "web_report_export"
    (skill_dir / "selectors.yaml").unlink()

    skill_path = skill_dir / "skill.yaml"
    skill = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
    skill["steps"][1]["id"] = "click_export"
    skill_path.write_text(yaml.safe_dump(skill, sort_keys=False), encoding="utf-8")

    exit_code = main(["--project-root", str(project), "skill", "validate", "web_report_export"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "FAIL" in captured.out
    assert "- Missing selectors.yaml" in captured.out
    assert "- Duplicate step_id: click_export" in captured.out
