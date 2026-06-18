"""Python SDK helpers for constructing Skill directories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SkillBuilder:
    """Build standard Skill files without touching runtime execution."""

    def __init__(
        self,
        skill_id: str,
        *,
        name: str | None = None,
        version: str = "0.1.0",
        skills_root: str | Path = "example_skills",
    ):
        self.skill_id = self._validate_skill_id(skill_id)
        self.name = name or self._title_from_skill_id(skill_id)
        self.version = version
        self.skills_root = Path(skills_root)
        self.steps: list[dict[str, Any]] = []
        self.selectors: dict[str, dict[str, Any]] = {}
        self.repair_policy: dict[str, Any] = self._default_repair_policy()

    def add_step(self, step: dict[str, Any] | None = None, **fields: Any) -> "SkillBuilder":
        payload = dict(step or {})
        payload.update(fields)
        if "id" not in payload:
            raise ValueError("step id is required")
        if "type" not in payload:
            raise ValueError("step type is required")
        if "goal" not in payload:
            raise ValueError("step goal is required")
        self.steps.append(payload)
        return self

    def add_selector(
        self,
        selector_ref: str,
        *,
        primary: str,
        fallbacks: list[str] | None = None,
    ) -> "SkillBuilder":
        if not selector_ref:
            raise ValueError("selector_ref is required")
        if not primary:
            raise ValueError("primary selector is required")
        self.selectors[selector_ref] = {
            "primary": primary,
            "fallbacks": list(fallbacks or []),
        }
        return self

    def set_repair_policy(self, repair_policy: dict[str, Any]) -> "SkillBuilder":
        if not isinstance(repair_policy, dict):
            raise ValueError("repair_policy must be a mapping")
        self.repair_policy = repair_policy
        return self

    def save(self, skills_root: str | Path | None = None) -> Path:
        root = Path(skills_root) if skills_root is not None else self.skills_root
        skill_dir = root / self.skill_id
        if skill_dir.exists():
            raise FileExistsError(f"Skill already exists: {skill_dir}")

        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(parents=True)

        self._write_yaml(skill_dir / "skill.yaml", self._skill_yaml())
        self._write_yaml(skill_dir / "selectors.yaml", self.selectors)
        self._write_yaml(skill_dir / "repair_policy.yaml", self.repair_policy)
        (skill_dir / "main.py").write_text(self._main_py(), encoding="utf-8")
        (skill_dir / "README.md").write_text(self._readme(), encoding="utf-8")
        (tests_dir / "test_skill.py").write_text(self._test_skill(), encoding="utf-8")
        return skill_dir

    def _skill_yaml(self) -> dict[str, Any]:
        steps = self.steps or [
            {
                "id": "open_page",
                "type": "navigate",
                "goal": "Open the starting page for this Skill.",
                "url": "about:blank",
            }
        ]
        return {
            "id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "entrypoint": "main.py",
            "selectors": "selectors.yaml",
            "repair_policy": "repair_policy.yaml",
            "steps": steps,
        }

    def _main_py(self) -> str:
        return f'''"""Entrypoint for the {self.skill_id} Skill."""

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

    def _readme(self) -> str:
        return f"""# {self.name}

Generated Self-Healing Code RPA Skill.

## Boundary

- Web RPA only.
- Normal execution must not call an LLM.
- Repairs must stay local to the failed selector or failed step.

## Commands

```powershell
python -m code_rpa skill show {self.skill_id}
python -m code_rpa skill validate {self.skill_id}
python -m code_rpa skill test {self.skill_id}
```
"""

    def _test_skill(self) -> str:
        return f'''from pathlib import Path
import importlib.util
import sys


SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SKILL_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
spec = importlib.util.spec_from_file_location("{self.skill_id}_main", SKILL_DIR / "main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from skill_registry.loader import SkillLoader


def test_skill_loads(tmp_path):
    skill = SkillLoader().load(SKILL_DIR / "skill.yaml")
    assert skill.id == "{self.skill_id}"
    assert skill.entrypoint == "main.py"
'''

    def _default_repair_policy(self) -> dict[str, Any]:
        return {
            "retry": {
                "max_attempts": 1,
                "delay_seconds": 0,
            },
            "allowed_patch_scope": ["selectors"],
            "sandbox": {
                "required": True,
                "command": ["python", "-m", "pytest"],
            },
        }

    def _write_yaml(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _validate_skill_id(self, skill_id: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-.")
        if not skill_id or any(char not in allowed for char in skill_id):
            raise ValueError("skill_id must contain lowercase letters, digits, '_', '-', or '.'")
        return skill_id

    def _title_from_skill_id(self, skill_id: str) -> str:
        return " ".join(part.capitalize() for part in skill_id.replace("-", "_").split("_") if part)
