from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import code_rpa.cli as cli
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


def test_cli_skill_create_outputs_next_steps_and_generates_runnable_skill(tmp_path, capsys):
    project = copy_project(tmp_path)

    exit_code = main(["--project-root", str(project), "skill", "create", "invoice_export"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "created" in captured.out
    assert "skill validate invoice_export" in captured.out
    assert "skill run invoice_export" in captured.out
    assert "skill test invoice_export" in captured.out

    exit_code = main(["--project-root", str(project), "skill", "validate", "invoice_export"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "PASS"

    exit_code = main(["--project-root", str(project), "skill", "run", "invoice_export"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "'status': 'success'" in captured.out

    exit_code = main(["--project-root", str(project), "skill", "test", "invoice_export"])
    assert exit_code == 0


def test_cli_skill_test_uses_unique_pytest_basetemp(tmp_path, monkeypatch):
    project = copy_project(tmp_path)
    main(["--project-root", str(project), "skill", "create", "invoice_export"])
    captured_run = {}
    basetemp = tmp_path / "child_pytest_basetemp"

    class Completed:
        returncode = 0

    def fake_mkdtemp(prefix):
        assert prefix == "code_rpa_skill_test_"
        basetemp.mkdir()
        return str(basetemp)

    def fake_run(command, *, cwd, check, shell):
        captured_run["command"] = command
        captured_run["cwd"] = cwd
        captured_run["check"] = check
        captured_run["shell"] = shell
        return Completed()

    monkeypatch.setattr(cli.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    exit_code = main(["--project-root", str(project), "skill", "test", "invoice_export"])
    command = captured_run["command"]

    assert exit_code == 0
    assert "--basetemp" in command
    captured_basetemp = Path(command[command.index("--basetemp") + 1])
    basetemp_ancestors = [captured_basetemp.resolve(), *captured_basetemp.resolve().parents]
    assert captured_basetemp == basetemp
    assert (project / "storage").resolve() not in basetemp_ancestors
    assert (project / "example_skills").resolve() not in basetemp_ancestors
    assert captured_run["cwd"] == project
    assert captured_run["check"] is False
    assert captured_run["shell"] is False
    assert not basetemp.exists()


def test_project_pytest_collects_multiple_standard_skill_test_modules(tmp_path):
    project = copy_project(tmp_path)
    unique_suffix = uuid.uuid4().hex[:8]
    skill_ids = [f"multi_collect_{unique_suffix}_one", f"multi_collect_{unique_suffix}_two"]

    for skill_id in skill_ids:
        assert main(["--project-root", str(project), "skill", "create", skill_id]) == 0
        assert main(["--project-root", str(project), "skill", "validate", skill_id]) == 0
        assert main(["--project-root", str(project), "skill", "test", skill_id]) == 0

    test_dirs = [project / "example_skills" / "web_report_export" / "tests"]
    test_dirs.extend(project / "example_skills" / skill_id / "tests" for skill_id in skill_ids)

    for test_dir in test_dirs:
        assert (test_dir / "test_skill.py").exists()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *(str(test_dir) for test_dir in test_dirs),
            "--basetemp",
            str(tmp_path / "multi_skill_collection_basetemp"),
        ],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )

    output = completed.stdout + completed.stderr
    assert "import file mismatch" not in output
    assert completed.returncode == 0, output


def test_cli_skill_create_reports_invalid_skill_id(tmp_path, capsys):
    project = copy_project(tmp_path)

    exit_code = main(["--project-root", str(project), "skill", "create", "InvoiceExport"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.out
    assert "skill_id must contain lowercase letters" in captured.out


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
