from pathlib import Path

import yaml

from code_rpa.sdk import SkillBuilder
from code_rpa.validator import SkillValidator
from skill_registry.loader import SkillLoader


def test_skill_builder_generates_standard_skill_files(tmp_path):
    skills_root = tmp_path / "example_skills"

    skill_dir = (
        SkillBuilder("invoice_export", skills_root=skills_root)
        .add_step(
            id="open_invoice_page",
            type="navigate",
            goal="Open the invoice export page.",
            url="about:blank",
        )
        .add_step(
            id="click_export",
            type="click",
            goal="Click the invoice export button.",
            selector_ref="export_button",
            target_description="Button that starts invoice export.",
        )
        .add_selector(
            "export_button",
            primary="#export-invoices",
            fallbacks=["button[data-testid='export-invoices']"],
        )
        .save()
    )

    assert skill_dir == skills_root / "invoice_export"
    assert (skill_dir / "skill.yaml").exists()
    assert (skill_dir / "selectors.yaml").exists()
    assert (skill_dir / "repair_policy.yaml").exists()
    assert (skill_dir / "main.py").exists()
    assert (skill_dir / "README.md").exists()
    assert (skill_dir / "tests" / "test_skill.py").exists()

    skill = SkillLoader().load(skill_dir / "skill.yaml")
    selectors = yaml.safe_load((skill_dir / "selectors.yaml").read_text(encoding="utf-8"))
    validation = SkillValidator(skills_root).validate("invoice_export")

    assert skill.id == "invoice_export"
    assert skill.name == "Invoice Export"
    assert [step["id"] for step in skill.steps] == ["open_invoice_page", "click_export"]
    assert selectors["export_button"]["primary"] == "#export-invoices"
    assert validation.is_valid is True
