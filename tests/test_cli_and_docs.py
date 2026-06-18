from pathlib import Path
import shutil

import pytest
from code_rpa.cli import main
import yaml
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def copy_project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(
        PROJECT_ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    return target


def test_cli_skill_list_shows_web_report_export(capsys):
    exit_code = main(["--project-root", str(PROJECT_ROOT), "skill", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "web_report_export" in captured.out


def test_cli_skill_create_generates_standard_skill_files(tmp_path):
    project = copy_project(tmp_path)

    exit_code = main(["--project-root", str(project), "skill", "create", "invoice_export"])

    skill_dir = project / "example_skills" / "invoice_export"
    assert exit_code == 0
    assert (skill_dir / "skill.yaml").exists()
    assert (skill_dir / "selectors.yaml").exists()
    assert (skill_dir / "repair_policy.yaml").exists()
    assert (skill_dir / "main.py").exists()
    assert (skill_dir / "README.md").exists()
    assert (skill_dir / "tests" / "test_skill.py").exists()
    assert 'id: "invoice_export"' in (skill_dir / "skill.yaml").read_text(encoding="utf-8")
    assert "python" in (skill_dir / "repair_policy.yaml").read_text(encoding="utf-8")
    assert "Generated Self-Healing Code RPA Skill." in (skill_dir / "README.md").read_text(encoding="utf-8")


def test_cli_skill_show_prints_skill_summary(capsys):
    exit_code = main(["--project-root", str(PROJECT_ROOT), "skill", "show", "web_report_export"])

    captured = capsys.readouterr()
    summary = yaml.safe_load(captured.out)

    assert exit_code == 0
    assert summary["id"] == "web_report_export"
    assert summary["version"] == "0.2.0"
    assert summary["steps"] == 6
    assert summary["selectors"] == 8


def test_cli_version_flag_prints_package_version(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--project-root", str(PROJECT_ROOT), "--version"])

    captured = capsys.readouterr()

    assert error.value.code == 0
    assert "code_rpa 0.1.0" in captured.out


def test_pyproject_exposes_console_scripts():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["requires-python"] == ">=3.11"
    assert pyproject["project"]["scripts"]["code-rpa"] == "code_rpa.cli:main"
    assert pyproject["project"]["scripts"]["code_rpa"] == "code_rpa.cli:main"


def test_repo_skill_files_exist():
    skill_root = PROJECT_ROOT / ".agents" / "skills" / "self-healing-rpa-engineer"

    assert (skill_root / "SKILL.md").exists()
    assert (skill_root / "references" / "architecture.md").exists()
    assert (skill_root / "references" / "rpa-skill-spec.md").exists()
    assert (skill_root / "references" / "patch-json-spec.md").exists()
    assert (skill_root / "references" / "repair-pipeline.md").exists()
    assert (skill_root / "assets" / "skill.yaml.template").exists()
    assert (skill_root / "assets" / "selectors.yaml.template").exists()
    assert (skill_root / "assets" / "repair_policy.yaml.template").exists()
    assert "Phase 3 Engineering Gate" in (skill_root / "SKILL.md").read_text(encoding="utf-8")


def test_readme_contains_key_sections():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    required_phrases = [
        "Self-Healing Code RPA Framework",
        "What This Is Not",
        "Architecture",
        "MVP Scope",
        "Install",
        "Run Demo",
        "Run Tests",
        "repair_request.json",
        "patch.json",
        "Sandbox Testing",
        "Versions And Rollback",
        "Create A New RPA Skill",
        "Codex Development Contract",
        "Current Capability Boundary",
        "Safety Boundaries",
    ]
    for phrase in required_phrases:
        assert phrase in readme
