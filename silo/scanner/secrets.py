from __future__ import annotations

import re
from pathlib import Path

from silo.models import EnvVar, ExposedSecret
from silo.scanner.files import read_file_safe
from silo.scanner.registry import DEFAULT_REGISTRY, Registry

# patterns for env var references
ENV_PATTERNS = [
    # explicit env access
    re.compile(r"""os\.environ\s*\[\s*['"](\w+)['"]\s*\]"""),
    re.compile(r"""os\.environ\.get\s*\(\s*['"](\w+)['"]"""),
    re.compile(r"""os\.getenv\s*\(\s*['"](\w+)['"]"""),
    re.compile(r"""process\.env\.(\w+)"""),
    # dotenv / config helpers
    re.compile(r"""env\s*\(\s*['"](\w+)['"]"""),
    re.compile(r"""config\s*\[\s*['"](\w+)['"]"""),
    re.compile(r"""load_dotenv"""),  # marker only, no capture
    # pydantic BaseSettings field with env
    re.compile(r"""env\s*=\s*['"](\w+)['"]"""),
    # keyring access
    re.compile(r"""keyring\.get_password\s*\(\s*['"](\w+)['"]"""),
    re.compile(r"""keyring\.set_password\s*\(\s*['"](\w+)['"]"""),
]

# string literals that look like env var names (ALL_CAPS_WITH_UNDERSCORES, 3+ chars)
ENV_VAR_LITERAL = re.compile(r"""['"]([A-Z][A-Z0-9_]{2,})['"]""")

# generic cloud/infra env var prefixes (not AI-specific — those come from registry)
INFRA_ENV_PREFIXES = {
    "AZURE_", "AWS_", "GOOGLE_", "GCP_",
    "DATABASE_", "DB_", "REDIS_", "POSTGRES",
    "API_KEY", "SECRET_", "TOKEN_",
}


def _build_env_prefixes(registry: Registry) -> set[str]:
    """build env var prefix set from registry + infra defaults."""
    prefixes = set(INFRA_ENV_PREFIXES)
    for p in registry.providers:
        if p.env:
            # extract prefix: "OPENAI_API_KEY" → "OPENAI_"
            parts = p.env.split("_")
            if len(parts) >= 2:
                prefixes.add(parts[0] + "_")
    return prefixes

# files that legitimately contain env var names (not secrets)
SAFE_FILES = {".env.example", ".env.template", ".env.sample"}

# compiled pattern cache
_compiled_cache: dict[str, re.Pattern] = {}


def _compile_secret_patterns(registry: Registry) -> list[tuple[re.Pattern, str, str]]:
    """compile registry secret patterns into (regex, name, severity) tuples."""
    result = []
    for sp in registry.secret_patterns:
        if sp.pattern not in _compiled_cache:
            try:
                _compiled_cache[sp.pattern] = re.compile(sp.pattern, re.IGNORECASE)
            except re.error:
                continue
        result.append((_compiled_cache[sp.pattern], sp.name, sp.severity))
    return result


def find_env_references(
    files: list[Path],
    app_path: Path,
    registry: Registry | None = None,
) -> list[EnvVar]:
    """find all environment variable references in source files."""
    reg = registry or DEFAULT_REGISTRY
    env_prefixes = _build_env_prefixes(reg)
    known_env_vars = reg.all_env_vars()  # exact matches from registry

    env_map: dict[str, list[str]] = {}

    def _add(var_name: str, rel_path: str) -> None:
        if var_name not in env_map:
            env_map[var_name] = []
        if rel_path not in env_map[var_name]:
            env_map[var_name].append(rel_path)

    for path in files:
        content = read_file_safe(path)
        if not content:
            continue
        rel = str(path.relative_to(app_path))

        # explicit env access patterns
        for pattern in ENV_PATTERNS:
            for match in pattern.finditer(content):
                if match.lastindex and match.lastindex >= 1:
                    _add(match.group(1), rel)

        # string literals that look like env var names
        for match in ENV_VAR_LITERAL.finditer(content):
            var_name = match.group(1)
            # skip bare prefixes
            if var_name.endswith("_") and var_name in env_prefixes:
                continue
            # match exact known vars from registry or prefix match
            if var_name in known_env_vars:
                _add(var_name, rel)
            elif any(var_name.startswith(prefix) for prefix in env_prefixes):
                _add(var_name, rel)

    # also parse .env files for variable names
    for path in files:
        if path.name.startswith(".env"):
            content = read_file_safe(path)
            if not content:
                continue
            rel = str(path.relative_to(app_path))
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    var_name = line.split("=", 1)[0].strip()
                    _add(var_name, rel)

    # also parse YAML config files for env-like keys
    for path in files:
        if path.suffix in (".yaml", ".yml"):
            content = read_file_safe(path)
            if not content:
                continue
            rel = str(path.relative_to(app_path))
            for match in ENV_VAR_LITERAL.finditer(content):
                var_name = match.group(1)
                if any(var_name.startswith(prefix) for prefix in env_prefixes):
                    _add(var_name, rel)

    return [
        EnvVar(name=name, found_in=locations)
        for name, locations in sorted(env_map.items())
    ]


def find_exposed_secrets(
    files: list[Path],
    app_path: Path,
    registry: Registry | None = None,
) -> list[ExposedSecret]:
    """find hardcoded secrets in source files."""
    reg = registry or DEFAULT_REGISTRY
    compiled = _compile_secret_patterns(reg)
    secrets = []

    for path in files:
        if path.name in SAFE_FILES:
            continue
        if path.name.startswith(".env"):
            continue

        content = read_file_safe(path)
        if not content:
            continue

        rel = str(path.relative_to(app_path))
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, secret_name, severity in compiled:
                if pattern.search(line):
                    secrets.append(ExposedSecret(
                        type=secret_name,
                        file=rel,
                        line=line_num,
                        severity=severity,
                    ))

    return secrets
