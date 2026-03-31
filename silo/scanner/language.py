from __future__ import annotations

from pathlib import Path

# map file extensions to languages, ordered by priority
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
}

FRAMEWORK_MARKERS: dict[str, dict[str, str]] = {
    "python": {
        "fastapi": "fastapi",
        "flask": "flask",
        "django": "django",
        "streamlit": "streamlit",
        "typer": "typer",
        "click": "click",
    },
    "typescript": {
        "next": "nextjs",
        "express": "express",
        "fastify": "fastify",
        "hono": "hono",
    },
    "javascript": {
        "next": "nextjs",
        "express": "express",
        "fastify": "fastify",
    },
}

ENTRY_POINT_CANDIDATES: dict[str, list[str]] = {
    "python": ["main.py", "app.py", "server.py", "api.py", "run.py", "cli.py"],
    "typescript": ["index.ts", "main.ts", "app.ts", "server.ts"],
    "javascript": ["index.js", "main.js", "app.js", "server.js"],
    "go": ["main.go", "cmd/main.go"],
    "rust": ["src/main.rs"],
}


def detect_language(files: list[Path]) -> str | None:
    """detect the primary language by file count."""
    counts: dict[str, int] = {}
    for f in files:
        lang = EXTENSION_MAP.get(f.suffix)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def detect_framework(
    language: str | None, dep_names: list[str], app_path: Path | None = None,
) -> str | None:
    """detect framework from dependency names or project name."""

    # check if the project itself IS a framework (e.g. scanning FastAPI's own repo)
    if app_path:
        project_name = _get_project_name(app_path)
        if project_name:
            all_frameworks = {}
            for markers in FRAMEWORK_MARKERS.values():
                all_frameworks.update(markers)
            if project_name in all_frameworks:
                return all_frameworks[project_name]

    if not language or language not in FRAMEWORK_MARKERS:
        return None
    markers = FRAMEWORK_MARKERS[language]
    for dep in dep_names:
        dep_lower = dep.lower()
        for marker, framework in markers.items():
            if marker == dep_lower:  # exact match, not substring
                return framework
    return None


def _get_project_name(app_path: Path) -> str | None:
    """get project name from pyproject.toml or package.json."""
    pyproject = app_path / "pyproject.toml"
    if pyproject.exists():
        import re
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
            match = re.search(r'name\s*=\s*"([^"]+)"', text)
            if match:
                return match.group(1).lower()
        except (OSError, PermissionError):
            pass

    pkg_json = app_path / "package.json"
    if pkg_json.exists():
        import json
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            return data.get("name", "").lower()
        except (json.JSONDecodeError, OSError):
            pass
    return None


def detect_entry_point(language: str | None, files: list[Path], app_path: Path) -> str | None:
    """find the most likely entry point."""

    # 1. check pyproject.toml [project.scripts] first
    pyproject = app_path / "pyproject.toml"
    if pyproject.exists():
        entry = _parse_entry_from_pyproject(pyproject)
        if entry:
            return entry

    # 2. check package.json "main" or "scripts.start"
    pkg_json = app_path / "package.json"
    if pkg_json.exists():
        entry = _parse_entry_from_package_json(pkg_json)
        if entry:
            return entry

    # 3. fall back to file name candidates
    if not language or language not in ENTRY_POINT_CANDIDATES:
        return None
    candidates = ENTRY_POINT_CANDIDATES[language]
    rel_files = {str(f.relative_to(app_path)): f for f in files}

    # check root first
    for candidate in candidates:
        if candidate in rel_files:
            return candidate

    # check one level deep (src/main.py, app/main.py, etc.)
    for candidate in candidates:
        for rel in rel_files:
            if rel.endswith("/" + candidate) and rel.count("/") == 1:
                return rel

    return None


def _parse_entry_from_pyproject(path: Path) -> str | None:
    """extract entry point from [project.scripts] in pyproject.toml."""
    import re
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None

    in_scripts = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[project.scripts]":
            in_scripts = True
            continue
        if in_scripts:
            if stripped.startswith("["):
                break
            # pattern: name = "module.path:function"
            match = re.match(r'\w+\s*=\s*"([^"]+)"', stripped)
            if match:
                module_path = match.group(1).split(":")[0]
                # convert module.path to module/path.py
                file_path = module_path.replace(".", "/") + ".py"
                return file_path
    return None


def _parse_entry_from_package_json(path: Path) -> str | None:
    """extract entry point from package.json."""
    import json
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if "main" in data:
        return data["main"]
    start = data.get("scripts", {}).get("start", "")
    if start:
        # "node index.js" → "index.js", "ts-node src/main.ts" → "src/main.ts"
        parts = start.split()
        for part in reversed(parts):
            if "." in part and not part.startswith("-"):
                return part
    return None
