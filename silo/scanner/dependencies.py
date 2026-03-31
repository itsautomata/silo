from __future__ import annotations

import re
from pathlib import Path

from silo.models import Dependency


DEP_FILES: dict[str, str] = {
    "requirements.txt": "pip",
    "pyproject.toml": "pip",
    "setup.py": "pip",
    "Pipfile": "pip",
    "package.json": "npm",
    "package-lock.json": "npm",
    "go.mod": "go",
    "Cargo.toml": "cargo",
    "Gemfile": "gem",
}


def find_dependency_file(app_path: Path) -> tuple[str | None, str | None]:
    """find the primary dependency file. returns (filename, source)."""
    for filename, source in DEP_FILES.items():
        if (app_path / filename).exists():
            return filename, source
    return None, None


def parse_dependencies(app_path: Path) -> tuple[list[Dependency], str | None]:
    """parse dependencies from the first matching dependency file."""
    dep_file, source = find_dependency_file(app_path)
    if not dep_file or not source:
        return [], None

    path = app_path / dep_file
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return [], dep_file

    if dep_file == "requirements.txt":
        return _parse_requirements_txt(text, source), dep_file
    if dep_file == "pyproject.toml":
        return _parse_pyproject_toml(text, source), dep_file
    if dep_file == "package.json":
        return _parse_package_json(text, source), dep_file

    return [], dep_file


def _parse_requirements_txt(text: str, source: str) -> list[Dependency]:
    deps = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([a-zA-Z0-9_.-]+)\s*(?:[><=!~]+\s*(.+))?", line)
        if match:
            deps.append(Dependency(
                name=match.group(1),
                version=match.group(2),
                source=source,
            ))
    return deps


def _parse_pyproject_toml(text: str, source: str) -> list[Dependency]:
    deps = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "dependencies = [":
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                break
            match = re.match(r'"([a-zA-Z0-9_.-]+)\s*(?:[><=!~]+\s*(.+))?"', stripped.rstrip(","))
            if match:
                deps.append(Dependency(
                    name=match.group(1),
                    version=match.group(2),
                    source=source,
                ))
    return deps


def _parse_package_json(text: str, source: str) -> list[Dependency]:
    import json
    deps = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return deps
    for section in ("dependencies", "devDependencies"):
        for name, version in data.get(section, {}).items():
            deps.append(Dependency(name=name, version=version, source=source))
    return deps
