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


def test_skill_validator_reports_required_fields_and_shape_errors(tmp_path):
    project = copy_project(tmp_path)
    skill_dir = project / "example_skills" / "web_report_export"

    skill_path = skill_dir / "skill.yaml"
    skill = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
    del skill["entrypoint"]
    skill["steps"][0]["type"] = "drag"
    skill_path.write_text(yaml.safe_dump(skill, sort_keys=False), encoding="utf-8")

    selectors_path = skill_dir / "selectors.yaml"
    selectors = yaml.safe_load(selectors_path.read_text(encoding="utf-8"))
    selectors["export_button"]["fallbacks"] = "button.export"
    selectors["broken_selector"] = {"fallbacks": []}
    selectors_path.write_text(yaml.safe_dump(selectors, sort_keys=False), encoding="utf-8")

    repair_policy_path = skill_dir / "repair_policy.yaml"
    repair_policy = yaml.safe_load(repair_policy_path.read_text(encoding="utf-8"))
    del repair_policy["sandbox"]["required"]
    repair_policy_path.write_text(yaml.safe_dump(repair_policy, sort_keys=False), encoding="utf-8")

    result = SkillValidator(project / "example_skills").validate("web_report_export")

    assert result.is_valid is False
    assert "Missing required skill.yaml field: entrypoint" in result.errors
    assert "Unsupported step type in step open_login_page: drag" in result.errors
    assert "Selector 'export_button' fallbacks must be a list of strings" in result.errors
    assert "Selector 'broken_selector' primary must be a non-empty string" in result.errors
    assert "repair_policy.sandbox.required must be a boolean" in result.errors


def test_skill_validator_reports_invalid_yaml(tmp_path):
    project = copy_project(tmp_path)
    skill_dir = project / "example_skills" / "web_report_export"
    (skill_dir / "selectors.yaml").write_text("export_button: [", encoding="utf-8")

    result = SkillValidator(project / "example_skills").validate("web_report_export")

    assert result.is_valid is False
    assert any(error.startswith("Invalid YAML in selectors.yaml") for error in result.errors)
