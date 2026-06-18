"""Command package for Self-Healing Code RPA."""

from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path
import tomllib


PACKAGE_NAME = "self-healing-code-rpa"


def _read_version() -> str:
    try:
        return metadata_version(PACKAGE_NAME)
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        if pyproject_path.exists():
            pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            return str(pyproject["project"]["version"])
        raise


__version__ = _read_version()
