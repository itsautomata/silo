from __future__ import annotations

from pathlib import Path

DEFAULT_IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build",
    ".egg-info", ".eggs", ".claude", ".next", ".nuxt",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2",
    ".exe", ".bin",
}

TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".rb",
    ".java", ".kt", ".c", ".cpp", ".h", ".hpp", ".cs",
    ".toml", ".yaml", ".yml", ".json", ".xml",
    ".md", ".txt", ".rst", ".cfg", ".ini", ".conf",
    ".sh", ".bash", ".zsh", ".fish",
    ".html", ".css", ".scss", ".less",
    ".sql", ".graphql",
    ".env", ".env.example", ".env.local",
    ".dockerfile", ".dockerignore",
    ".gitignore",
}


def collect_files(
    app_path: Path,
    exclude: set[str] | None = None,
    include_only: set[str] | None = None,
) -> list[Path]:
    """collect all readable source files in the app directory.

    exclude: additional directory names to skip (e.g. {"tmp", "vendor"})
    include_only: if set, only scan these directories (e.g. {"src", "lib"})
    """
    ignore = DEFAULT_IGNORE_DIRS | (exclude or set())
    files: list[Path] = []
    for path in app_path.rglob("*"):
        rel_parts = path.relative_to(app_path).parts
        if any(part in ignore for part in rel_parts):
            continue
        if include_only and rel_parts and rel_parts[0] not in include_only:
            continue
        if not path.is_file():
            continue
        if path.suffix in IGNORE_EXTENSIONS:
            continue
        if path.suffix in TEXT_EXTENSIONS or path.suffix == "":
            files.append(path)
    return sorted(files)


def read_file_safe(path: Path) -> str | None:
    """read a file, return None if it can't be read."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None
