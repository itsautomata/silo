from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from silo.models import ScanError, ScanResult
from silo.scanner.ai_detect import detect_ai_patterns
from silo.scanner.dependencies import parse_dependencies
from silo.scanner.files import collect_files
from silo.scanner.language import detect_entry_point, detect_framework, detect_language
from silo.scanner.secrets import find_env_references, find_exposed_secrets


def scan(
    app_path: Path,
    exclude: set[str] | None = None,
    include_only: set[str] | None = None,
) -> ScanResult:
    """read a codebase. detect everything. decide nothing.

    never crashes. collects errors and returns partial results.
    """

    app_path = app_path.resolve()
    if not app_path.is_dir():
        raise ValueError(f"not a directory: {app_path}")

    errors: list[ScanError] = []

    # phase 1: collect files
    try:
        files = collect_files(app_path, exclude=exclude, include_only=include_only)
    except Exception as e:
        errors.append(ScanError(phase="collect_files", error=str(e)))
        files = []

    # phase 2: language and framework
    language = None
    framework = None
    entry_point = None
    deps = []
    dep_file = None
    dep_names = []

    try:
        language = detect_language(files)
    except Exception as e:
        errors.append(ScanError(phase="detect_language", error=str(e)))

    try:
        deps, dep_file = parse_dependencies(app_path)
        dep_names = [d.name for d in deps]
    except Exception as e:
        errors.append(ScanError(
            phase="parse_dependencies",
            file=str(app_path / "pyproject.toml"),
            error=str(e),
        ))

    try:
        framework = detect_framework(language, dep_names, app_path)
    except Exception as e:
        errors.append(ScanError(phase="detect_framework", error=str(e)))

    try:
        entry_point = detect_entry_point(language, files, app_path)
    except Exception as e:
        errors.append(ScanError(phase="detect_entry_point", error=str(e)))

    # phase 3: secrets and env vars
    env_vars = []
    exposed_secrets = []

    try:
        env_vars = find_env_references(files, app_path)
    except Exception as e:
        errors.append(ScanError(phase="find_env_references", error=str(e)))

    try:
        exposed_secrets = find_exposed_secrets(files, app_path)
    except Exception as e:
        errors.append(ScanError(phase="find_exposed_secrets", error=str(e)))

    # phase 4: AI-native detection
    ai = None
    try:
        ai = detect_ai_patterns(files, dep_names, app_path)
    except Exception as e:
        errors.append(ScanError(phase="detect_ai_patterns", error=str(e)))

    return ScanResult(
        app_path=app_path,
        app_name=app_path.name,
        scanned_at=datetime.now(timezone.utc),
        language=language,
        framework=framework,
        entry_point=entry_point,
        dependencies=deps,
        dependency_file=dep_file,
        env_vars=env_vars,
        exposed_secrets=exposed_secrets,
        ai=ai,
        errors=errors,
    )
