"""Skill template helpers for developer-facing scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CreatedSkill:
    skill_id: str
    skill_dir: Path
    files: list[Path]


class SkillTemplateSystem:
    """Create runnable Skill scaffolds from repository templates."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.skills_root = project_root / "example_skills"
        self.assets_dir = project_root / ".agents" / "skills" / "self-healing-rpa-engineer" / "assets"

    def create_skill(self, skill_id: str) -> CreatedSkill:
        validate_skill_id(skill_id)
        skill_dir = self.skills_root / skill_id
        if skill_dir.exists():
            raise FileExistsError(f"Skill already exists: {skill_id}")

        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(parents=True)

        skill_name = title_from_skill_id(skill_id)
        files = [
            self._write_template(
                self.assets_dir / "skill.yaml.template",
                skill_dir / "skill.yaml",
                skill_id,
                skill_name,
                fallback=skill_yaml_template(),
            ),
            self._write_template(
                self.assets_dir / "selectors.yaml.template",
                skill_dir / "selectors.yaml",
                skill_id,
                skill_name,
                fallback=selectors_yaml_template(),
            ),
            self._write_template(
                self.assets_dir / "repair_policy.yaml.template",
                skill_dir / "repair_policy.yaml",
                skill_id,
                skill_name,
                fallback=repair_policy_yaml_template(),
            ),
            self._write_text(skill_dir / "main.py", main_py_template(skill_id)),
            self._write_text(skill_dir / "README.md", skill_readme_template(skill_id, skill_name)),
            self._write_text(tests_dir / "test_skill.py", test_skill_template(skill_id)),
        ]
        return CreatedSkill(skill_id=skill_id, skill_dir=skill_dir, files=files)

    def _write_template(
        self,
        template_path: Path,
        target_path: Path,
        skill_id: str,
        skill_name: str,
        *,
        fallback: str,
    ) -> Path:
        template = template_path.read_text(encoding="utf-8") if template_path.exists() else fallback
        rendered = template.format(skill_id=skill_id, skill_name=skill_name)
        return self._write_text(target_path, rendered)

    def _write_text(self, target_path: Path, content: str) -> Path:
        target_path.write_text(content, encoding="utf-8")
        return target_path


def skill_yaml_template() -> str:
    return '''id: "{skill_id}"
name: "{skill_name}"
version: 0.1.0
entrypoint: main.py
selectors: selectors.yaml
repair_policy: repair_policy.yaml
steps:
  - id: open_page
    type: navigate
    goal: Open the starting page for this Skill.
    url: "about:blank"
'''


def selectors_yaml_template() -> str:
    return '''# Add logical selector refs here.
# Example:
# submit_button:
#   primary: "#submit"
#   fallbacks:
#     - "button[data-testid='submit']"
'''


def repair_policy_yaml_template() -> str:
    return '''retry:
  max_attempts: 1
  delay_seconds: 0
allowed_patch_scope:
  - selectors
sandbox:
  required: true
  command:
    - python
    - -m
    - pytest
'''


def main_py_template(skill_id: str) -> str:
    return f'''"""Entrypoint for the {skill_id} Skill."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rpa_runtime.browser import PlaywrightBrowser
from rpa_runtime.executor import RPAExecutor, RunResult
from skill_registry.loader import SkillLoader


def run(page: Any | None = None, storage_root: Path | None = None) -> RunResult:
    skill_path = Path(__file__).with_name("skill.yaml")
    skill = SkillLoader().load(skill_path)
    executor = RPAExecutor(
        storage_root=storage_root or PROJECT_ROOT / "storage",
        browser=PlaywrightBrowser(headless=True),
    )
    return executor.run(skill, page=page)


if __name__ == "__main__":
    print(run().to_dict())
'''


def test_skill_template(skill_id: str) -> str:
    return f'''from pathlib import Path
import importlib.util
import sys


SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SKILL_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
spec = importlib.util.spec_from_file_location("{skill_id}_main", SKILL_DIR / "main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from skill_registry.loader import SkillLoader


class FakePage:
    def __init__(self):
        self.urls = []

    def goto(self, url):
        self.urls.append(url)


def test_skill_loads():
    skill = SkillLoader().load(SKILL_DIR / "skill.yaml")
    assert skill.id == "{skill_id}"
    assert skill.entrypoint == "main.py"


def test_skill_runs_default_navigation(tmp_path):
    page = FakePage()
    result = module.run(page=page, storage_root=tmp_path)

    assert result.status == "success"
    assert page.urls == ["about:blank"]
'''


def skill_readme_template(skill_id: str, skill_name: str) -> str:
    return f"""# {skill_name}

Generated Self-Healing Code RPA Skill.

## Boundary

- Web RPA only.
- Normal execution must not call an LLM.
- Repairs must stay local to the failed selector or failed step.

## Files

- `skill.yaml` defines the workflow.
- `selectors.yaml` defines primary and fallback selectors.
- `repair_policy.yaml` defines retry and sandbox policy.
- `main.py` is the thin executable entrypoint.
- `tests/test_skill.py` verifies the Skill can be loaded and the default scaffold can run.

## Commands

```powershell
python -m code_rpa skill show {skill_id}
python -m code_rpa skill validate {skill_id}
python -m code_rpa skill run {skill_id}
python -m code_rpa skill test {skill_id}
```
"""


def validate_skill_id(skill_id: str) -> None:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-.")
    if not skill_id or any(char not in allowed for char in skill_id):
        raise ValueError("skill_id must contain lowercase letters, digits, '_', '-', or '.'")


def title_from_skill_id(skill_id: str) -> str:
    return " ".join(part.capitalize() for part in skill_id.replace("-", "_").split("_") if part)
