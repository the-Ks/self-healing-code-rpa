import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from code_rpa.cli import main
from example_skills.web_report_export.main import prepare_skill
from repair_agent.patch_validator import PatchValidator
from repair_agent.pipeline import RepairPipeline
from repair_agent.sandbox_runner import SandboxRunner
from rpa_runtime.executor import RPAExecutor
from skill_registry.loader import SkillLoader
from skill_registry.version_manager import VersionManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATCH_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "patches" / "web_report_export_v2_fallback_patch.json"


class FakePage:
    def __init__(self, available_selectors=None):
        self.available_selectors = set(available_selectors or [])
        self.url = "about:blank"
        self.html = """
        <html>
          <body>
            <input id="username" />
            <input id="password" />
            <button id="login-submit">Sign in</button>
            <a id="report-page-link">Reports</a>
            <input id="date-start" />
            <input id="date-end" />
            <button data-testid="export-button-v2">Export Report</button>
            <p id="export-success">Export ready</p>
          </body>
        </html>
        """

    def goto(self, url):
        self.url = url

    def click(self, selector):
        if selector not in self.available_selectors:
            raise RuntimeError(f"selector not found: {selector}")

    def fill(self, selector, value):
        if selector not in self.available_selectors:
            raise RuntimeError(f"selector not found: {selector}")

    def wait_for_selector(self, selector):
        if selector not in self.available_selectors:
            raise RuntimeError(f"selector not found: {selector}")

    def screenshot(self, path, full_page=True):
        Path(path).write_bytes(b"fake screenshot")

    def content(self):
        return self.html


def copy_project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(
        PROJECT_ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    return target


def load_skill(project_root: Path):
    skill_path = project_root / "example_skills" / "web_report_export" / "skill.yaml"
    fixture_url = (project_root / "tests" / "fixtures" / "report_demo.html").resolve().as_uri()
    return prepare_skill(SkillLoader().load(skill_path), fixture_url)


def original_selectors() -> set[str]:
    return {
        "#username",
        "#password",
        "#login-submit",
        "#report-page-link",
        "#date-start",
        "#date-end",
        "button[data-testid='export-button']",
        "#export-success",
    }


def changed_dom_selectors() -> set[str]:
    return {
        "#username",
        "#password",
        "#login-submit",
        "#report-page-link",
        "#date-start",
        "#date-end",
        "button[data-testid='export-button-v2']",
        "#export-success",
    }


def run_skill(project_root: Path, storage_root: Path, selectors: set[str]):
    return RPAExecutor(storage_root=storage_root).run(
        load_skill(project_root),
        page=FakePage(available_selectors=selectors),
    )


def read_patch() -> dict:
    return json.loads(PATCH_FIXTURE.read_text(encoding="utf-8"))


def write_patch(tmp_path: Path, patch: dict) -> Path:
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(json.dumps(patch, indent=2), encoding="utf-8")
    return patch_path


def read_export_fallbacks(project_root: Path) -> list[str]:
    selectors_path = project_root / "example_skills" / "web_report_export" / "selectors.yaml"
    selectors = yaml.safe_load(selectors_path.read_text(encoding="utf-8")) or {}
    return list(selectors["export_button"].get("fallbacks", []) or [])


def write_repair_smoke_test(project_root: Path) -> None:
    smoke_test = project_root / "tests" / "test_repair_smoke_runtime.py"
    smoke_test.write_text(
        '''
from pathlib import Path

from example_skills.web_report_export.main import prepare_skill
from rpa_runtime.executor import RPAExecutor
from skill_registry.loader import SkillLoader


class FakePage:
    def __init__(self):
        self.available_selectors = {
            "#username",
            "#password",
            "#login-submit",
            "#report-page-link",
            "#date-start",
            "#date-end",
            "button[data-testid='export-button-v2']",
            "#export-success",
        }
        self.url = "about:blank"

    def goto(self, url):
        self.url = url

    def click(self, selector):
        if selector not in self.available_selectors:
            raise RuntimeError(f"selector not found: {selector}")

    def fill(self, selector, value):
        if selector not in self.available_selectors:
            raise RuntimeError(f"selector not found: {selector}")

    def wait_for_selector(self, selector):
        if selector not in self.available_selectors:
            raise RuntimeError(f"selector not found: {selector}")


def test_repaired_export_selector_runs_changed_dom(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    skill = SkillLoader().load(project_root / "example_skills" / "web_report_export" / "skill.yaml")
    fixture_url = (project_root / "tests" / "fixtures" / "report_demo.html").resolve().as_uri()
    result = RPAExecutor(storage_root=tmp_path).run(
        prepare_skill(skill, fixture_url),
        page=FakePage(),
    )

    assert result.status == "success"
''',
        encoding="utf-8",
    )


def make_failure(project_root: Path, tmp_path: Path):
    skill = load_skill(project_root)
    skill.repair_policy["sandbox"]["command"] = ["python", "-m", "pytest", "tests/test_repair_smoke_runtime.py"]
    result = RPAExecutor(storage_root=tmp_path / "failure_storage").run(
        skill,
        page=FakePage(available_selectors=changed_dom_selectors()),
    )
    repair_request = json.loads(Path(result.repair_request_path).read_text(encoding="utf-8"))
    return result, repair_request


def update_repair_request(path: str | Path, updates: dict) -> None:
    request_path = Path(path)
    repair_request = json.loads(request_path.read_text(encoding="utf-8"))
    repair_request.update(updates)
    request_path.write_text(json.dumps(repair_request, indent=2), encoding="utf-8")


def test_end_to_end_selector_repair_pipeline_and_rollback(tmp_path):
    project_root = copy_project(tmp_path)
    write_repair_smoke_test(project_root)

    original_run = run_skill(project_root, tmp_path / "original_storage", original_selectors())
    assert original_run.status == "success"

    failed_run, repair_request = make_failure(project_root, tmp_path)
    assert failed_run.status == "failed"
    assert failed_run.steps[-1].step_id == "click_export"
    assert Path(failed_run.repair_request_path).exists()
    assert Path(repair_request["screenshot_path"]).exists()
    assert Path(repair_request["dom_snapshot_path"]).exists()
    assert Path(repair_request["run_log_path"]).exists()
    assert "button[data-testid='export-button']" in repair_request["attempted_selectors"]
    assert repair_request["allowed_repair_scope"]["allowed_files"] == [
        "example_skills/web_report_export/selectors.yaml"
    ]
    assert repair_request["allowed_repair_scope"]["allowed_selector_refs"] == ["export_button"]

    patch = read_patch()
    patch_path = write_patch(tmp_path, patch)
    validation = PatchValidator().validate_patch_file(
        failed_run.repair_request_path,
        patch_path,
        current_skill=load_skill(project_root),
    )
    assert validation.is_valid is True

    pipeline_result = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)
    assert pipeline_result.success is True
    assert pipeline_result.validation.is_valid is True
    assert pipeline_result.sandbox.success is True
    assert pipeline_result.original_version_id is not None
    assert pipeline_result.new_version_id is not None

    repaired_run = run_skill(project_root, tmp_path / "repaired_storage", changed_dom_selectors())
    assert repaired_run.status == "success"
    assert "button[data-testid='export-button-v2']" in read_export_fallbacks(project_root)

    version_manager = VersionManager(project_root / "storage" / "versions")
    current = version_manager.get_current_version("web_report_export")
    assert current["version_id"] == pipeline_result.new_version_id
    assert current["patch_id"] == patch["patch_id"]
    assert current["repair_request_path"] == str(Path(failed_run.repair_request_path))
    assert current["source_version"] == "0.2.0"
    assert current["new_version"] == "0.2.1"
    assert current["result"] == "applied"

    version_manager.rollback_to_version(
        skill=load_skill(project_root),
        version_id=pipeline_result.original_version_id,
    )
    rolled_back_fallbacks = read_export_fallbacks(project_root)
    rolled_back_run = run_skill(project_root, tmp_path / "rolled_back_storage", changed_dom_selectors())

    assert "button[data-testid='export-button-v2']" not in rolled_back_fallbacks
    assert version_manager.get_current_version("web_report_export")["version_id"] == pipeline_result.original_version_id
    assert rolled_back_run.status == "failed"


def test_repair_apply_cli_reports_pipeline_stages(tmp_path, capsys):
    project_root = copy_project(tmp_path)
    write_repair_smoke_test(project_root)
    failed_run, _ = make_failure(project_root, tmp_path)
    patch_path = write_patch(tmp_path, read_patch())

    exit_code = main(
        [
            "--project-root",
            str(project_root),
            "repair",
            "apply",
            failed_run.repair_request_path,
            str(patch_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validation: PASS" in captured.out
    assert "sandbox: PASS" in captured.out
    assert "apply: PASS" in captured.out
    assert "repair: PASS" in captured.out


def test_repair_apply_cli_returns_nonzero_on_validation_failure(tmp_path, capsys):
    project_root = copy_project(tmp_path)
    failed_run, _ = make_failure(project_root, tmp_path)
    patch = read_patch()
    patch["selector_changes"]["target_file"] = "example_skills/web_report_export/../web_report_export/selectors.yaml"
    patch_path = write_patch(tmp_path, patch)

    exit_code = main(
        [
            "--project-root",
            str(project_root),
            "repair",
            "apply",
            failed_run.repair_request_path,
            str(patch_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "validation: FAIL" in captured.out or "repair failed" in captured.out


def test_patch_validator_rejects_p3_negative_cases(tmp_path):
    project_root = copy_project(tmp_path)
    _, repair_request = make_failure(project_root, tmp_path)
    skill = load_skill(project_root)

    cases = [
        ("target_file", ("selector_changes", "target_file"), "example_skills/other/selectors.yaml", "target_file"),
        ("selector_ref", ("selector_changes", "selector_ref"), "other_button", "selector_ref"),
        ("failed_step_id", ("target_step_id",), "enter_report_page", "target_step_id"),
        ("skill_id", ("skill_id",), "other_skill", "skill_id"),
        ("code_changes", ("code_changes",), [{"target_file": "main.py"}], "code_changes must be null"),
        ("test_command", ("test_command",), ["python", "-m", "pytest"], "test_command"),
        ("unknown_field", ("unexpected_capability",), True, "unknown fields"),
        (
            "path_traversal",
            ("selector_changes", "target_file"),
            "example_skills/web_report_export/../web_report_export/selectors.yaml",
            "path traversal",
        ),
        ("unknown_patch_type", ("patch_type",), "python_code_update", "unknown patch_type"),
    ]

    for _, path, value, expected_error in cases:
        patch = read_patch()
        target = patch
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

        validation = PatchValidator().validate_patch(repair_request, patch, current_skill=skill)

        assert validation.is_valid is False
        assert any(expected_error in error for error in validation.errors), validation.errors


def test_sandbox_failure_keeps_live_skill_unchanged(tmp_path):
    project_root = copy_project(tmp_path)
    failed_run, _ = make_failure(project_root, tmp_path)
    update_repair_request(
        failed_run.repair_request_path,
        {"test_command": ["python", "-m", "pytest", "tests/does_not_exist.py"]},
    )
    patch = read_patch()
    patch_path = write_patch(tmp_path, patch)
    before = read_export_fallbacks(project_root)

    result = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)
    after = read_export_fallbacks(project_root)

    assert result.success is False
    assert result.stage == "sandbox"
    assert before == after
    assert "button[data-testid='export-button-v2']" not in after
    assert VersionManager(project_root / "storage" / "versions").list_versions("web_report_export") == []


def test_sandbox_rejects_shell_string_or_shell_metacharacter_test_command(tmp_path):
    project_root = copy_project(tmp_path)
    failed_run, _ = make_failure(project_root, tmp_path)
    patch_path = write_patch(tmp_path, read_patch())

    update_repair_request(failed_run.repair_request_path, {"test_command": "python -m pytest"})
    string_result = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)

    update_repair_request(
        failed_run.repair_request_path,
        {"test_command": ["python", "-m", "pytest", "tests/test_repair_smoke_runtime.py; echo unsafe"]},
    )
    metachar_result = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)

    assert string_result.success is False
    assert string_result.stage == "sandbox"
    assert "non-empty list" in string_result.errors[0]
    assert metachar_result.success is False
    assert metachar_result.stage == "sandbox"
    assert "shell metacharacters" in metachar_result.errors[0]


def test_patch_validator_rejects_symlink_escape_from_skill_root(tmp_path):
    project_root = copy_project(tmp_path)
    _, repair_request = make_failure(project_root, tmp_path)
    skill = load_skill(project_root)
    skill_root = project_root / "example_skills" / "web_report_export"
    outside_dir = tmp_path / "outside_skill_dir"
    outside_dir.mkdir()
    (outside_dir / "selectors.yaml").write_text(
        (skill_root / "selectors.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    link_dir = skill_root / "linked_escape"
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link_dir), str(outside_dir)],
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
            if completed.returncode != 0:
                pytest.skip(f"junction creation is unavailable: {completed.stderr or completed.stdout}")
        else:
            os.symlink(outside_dir, link_dir, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"link creation is unavailable on this system: {error}")

    patch = read_patch()
    patch["selector_changes"]["target_file"] = "example_skills/web_report_export/linked_escape/selectors.yaml"
    patch["allowed_repair_scope"]["allowed_files"] = [
        "example_skills/web_report_export/linked_escape/selectors.yaml"
    ]
    repair_request["allowed_repair_scope"]["allowed_files"] = [
        "example_skills/web_report_export/linked_escape/selectors.yaml"
    ]

    validation = PatchValidator().validate_patch(repair_request, patch, current_skill=skill)

    assert validation.is_valid is False
    assert any("escapes the project root" in error or "escapes the Skill root" in error for error in validation.errors)


def test_version_failure_restores_live_skill_and_removes_partial_version(tmp_path, monkeypatch):
    project_root = copy_project(tmp_path)
    write_repair_smoke_test(project_root)
    failed_run, repair_request = make_failure(project_root, tmp_path)
    patch = read_patch()
    skill = load_skill(project_root)
    sandbox = SandboxRunner().run_patch(
        skill=skill,
        patch=patch,
        test_command=repair_request["test_command"],
        project_root=project_root,
    )
    assert sandbox.success is True

    version_manager = VersionManager(project_root / "storage" / "versions")
    original_snapshot = version_manager.snapshot(skill, reason="before_injected_failure")
    before_selectors = (project_root / "example_skills" / "web_report_export" / "selectors.yaml").read_text(
        encoding="utf-8"
    )

    def fail_set_current(skill_id, version_id):
        raise RuntimeError("injected current write failure")

    monkeypatch.setattr(version_manager, "_set_current", fail_set_current)

    with pytest.raises(RuntimeError, match="injected current write failure"):
        version_manager.create_new_version(
            skill=skill,
            patched_skill_path=sandbox.patched_skill_path,
            patch=patch,
            test_result=sandbox,
            repair_request_path=failed_run.repair_request_path,
        )

    after_selectors = (project_root / "example_skills" / "web_report_export" / "selectors.yaml").read_text(
        encoding="utf-8"
    )
    versions = version_manager.list_versions("web_report_export")

    assert after_selectors == before_selectors
    assert [version["version_id"] for version in versions] == [original_snapshot.name]
    assert version_manager.get_current_version("web_report_export")["version_id"] == original_snapshot.name


def test_repeating_same_patch_id_after_success_is_rejected_by_version_match(tmp_path):
    project_root = copy_project(tmp_path)
    write_repair_smoke_test(project_root)
    failed_run, _ = make_failure(project_root, tmp_path)
    patch_path = write_patch(tmp_path, read_patch())

    first = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)
    second = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)

    fallbacks = read_export_fallbacks(project_root)
    assert first.success is True
    assert second.success is False
    assert second.stage == "validation"
    assert any("current skill version" in error for error in second.errors)
    assert fallbacks.count("button[data-testid='export-button-v2']") == 1


def test_negative_pipeline_does_not_touch_repository_skill(tmp_path):
    repo_selectors = PROJECT_ROOT / "example_skills" / "web_report_export" / "selectors.yaml"
    before = repo_selectors.read_text(encoding="utf-8")
    project_root = copy_project(tmp_path)
    failed_run, _ = make_failure(project_root, tmp_path)
    patch = read_patch()
    patch["selector_changes"]["selector_ref"] = "other_button"
    patch_path = write_patch(tmp_path, patch)

    result = RepairPipeline(project_root=project_root).apply(failed_run.repair_request_path, patch_path)

    assert result.success is False
    assert repo_selectors.read_text(encoding="utf-8") == before


def test_fallback_patch_is_idempotent(tmp_path):
    project_root = copy_project(tmp_path)
    patch = read_patch()
    runner = SandboxRunner()

    runner.apply_patch_to_project(project_root, patch)
    runner.apply_patch_to_project(project_root, patch)

    fallbacks = read_export_fallbacks(project_root)
    assert fallbacks.count("button[data-testid='export-button-v2']") == 1
