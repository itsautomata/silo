from __future__ import annotations

import re
from pathlib import Path

from silo.models import (
    AINativeProfile,
    ModelProvider,
    ModelUsage,
    PromptLocation,
    VectorDBInfo,
)
from silo.scanner.files import read_file_safe
from silo.scanner.registry import DEFAULT_REGISTRY, Registry

# azure openai — require actual class usage, not just the string
AZURE_OPENAI_PATTERN = re.compile(r"AzureOpenAI\s*\(|azure_endpoint\s*=")

# model ID pattern — only in contexts that look like LLM calls
MODEL_CALL_PATTERNS = [
    re.compile(r"""\.create\s*\([^)]*model\s*=\s*['"]([a-zA-Z0-9._/-]+)['"]""", re.DOTALL),
    re.compile(r"""completion\s*\([^)]*model\s*=\s*['"]([a-zA-Z0-9._/-]+)['"]""", re.DOTALL),
    re.compile(r"""Chat\w+\s*\([^)]*model(?:_name)?\s*=\s*['"]([a-zA-Z0-9._/-]+)['"]""", re.DOTALL),
]

# known model ID prefixes — for validating model= matches
MODEL_PREFIXES = {
    "gpt-", "o1", "o3", "claude-", "gemini-", "llama", "mistral", "mixtral",
    "command-r", "command-light", "deepseek-",
}

# prompt patterns
SYSTEM_PROMPT_PATTERN = re.compile(
    r"""(?:system_prompt|system_message|SYSTEM_PROMPT)\s*[:=]\s*['\"]{1,3}""",
)
PROMPT_TEMPLATE_PATTERN = re.compile(
    r"""(?:PromptTemplate|ChatPromptTemplate|prompt_template)\s*[\(=]""",
)

# agent loop indicators
AGENT_LOOP_PATTERNS = [
    re.compile(r"(?:agent\.run|agent\.execute|agent\.invoke|agent\.arun)\s*\("),
    re.compile(r"AgentExecutor\s*\("),
    re.compile(r"while.*tool_calls", re.IGNORECASE),
    re.compile(r"for\s+\w+\s+in\s+.*tool_calls"),
]

# embedding patterns
EMBEDDING_PATTERNS = [
    re.compile(r"\.create_embedding\s*\("),
    re.compile(r"\.embed_query\s*\("),
    re.compile(r"\.embed_documents\s*\("),
    re.compile(r"embeddings\.embed\s*\("),
    re.compile(r"OpenAIEmbeddings\s*\("),
    re.compile(r"SentenceTransformer\s*\("),
    re.compile(r"\.embeddings\.create\s*\("),
]


def detect_ai_patterns(
    files: list[Path],
    dep_names: list[str],
    app_path: Path,
    registry: Registry | None = None,
) -> AINativeProfile | None:
    """detect AI-native patterns in the codebase. static analysis only."""

    reg = registry or DEFAULT_REGISTRY

    providers: dict[str, ModelProvider] = {}
    models: list[ModelUsage] = []
    vector_db: VectorDBInfo | None = None
    embedding_files: list[str] = []
    has_agent_loop = False
    agent_framework: str | None = None
    tool_defs: list[str] = []
    prompt_locations: list[PromptLocation] = []

    # check deps against registry
    for dep in dep_names:
        entry = reg.provider_by_dep(dep)
        if entry:
            providers[entry.name] = ModelProvider(
                name=entry.name,
                auth_method=entry.auth_method,
                env_var=entry.env,
            )

        vdb = reg.vector_db_by_dep(dep)
        if vdb:
            vector_db = VectorDBInfo(type=vdb.name, connection_method="local")

        fw = reg.framework_by_dep(dep)
        if fw:
            agent_framework = fw.name

    # scan source files
    for path in files:
        if path.suffix not in (".py", ".ts", ".tsx", ".js", ".jsx"):
            continue

        rel = str(path.relative_to(app_path))
        if _is_test_or_doc(rel):
            continue

        content = read_file_safe(path)
        if not content:
            continue

        # check imports against registry
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith(("import ", "from ")):
                continue

            entry = reg.provider_by_import(stripped)
            if entry:
                providers[entry.name] = ModelProvider(
                    name=entry.name,
                    auth_method=entry.auth_method,
                    env_var=entry.env,
                )

            vdb = reg.vector_db_by_import(stripped)
            if vdb:
                vector_db = VectorDBInfo(type=vdb.name, connection_method="local")

        # azure openai — class instantiation (separate from import, same openai package)
        if AZURE_OPENAI_PATTERN.search(content):
            providers["azure_openai"] = ModelProvider(
                name="azure_openai",
                auth_method="api_key",
                env_var="AZURE_OPENAI_API_KEY",
            )

        # model IDs — only in LLM call contexts
        for pattern in MODEL_CALL_PATTERNS:
            for match in pattern.finditer(content):
                model_id = match.group(1)
                if _is_known_model(model_id):
                    provider = _guess_provider(model_id, list(providers.keys()))
                    models.append(ModelUsage(
                        provider=provider,
                        model_id=model_id,
                        file=rel,
                    ))

        # agent loops
        for pattern in AGENT_LOOP_PATTERNS:
            if pattern.search(content):
                has_agent_loop = True
                break

        # tool definitions
        if re.search(r"""["']type["']\s*:\s*["']function["']""", content):
            tool_defs.append(rel)

        # embeddings
        for pattern in EMBEDDING_PATTERNS:
            if pattern.search(content):
                if rel not in embedding_files:
                    embedding_files.append(rel)
                break

        # prompts
        for line_num, line in enumerate(content.splitlines(), 1):
            if SYSTEM_PROMPT_PATTERN.search(line):
                prompt_locations.append(PromptLocation(
                    file=rel, type="system_prompt", line=line_num,
                ))
            elif PROMPT_TEMPLATE_PATTERN.search(line):
                prompt_locations.append(PromptLocation(
                    file=rel, type="template", line=line_num,
                ))

    # nothing AI-related found
    if not providers and not models and not vector_db and not agent_framework:
        return None

    # determine if AI-native vs AI-enhanced
    is_ai_native = (
        has_agent_loop
        or agent_framework is not None
        or (vector_db is not None and len(embedding_files) > 0)
        or len(providers) >= 2
    )

    return AINativeProfile(
        is_ai_native=is_ai_native,
        providers=list(providers.values()),
        models=models,
        vector_db=vector_db,
        embedding_calls=embedding_files,
        has_agent_loop=has_agent_loop,
        tool_definitions=tool_defs,
        agent_framework=agent_framework,
        prompt_locations=prompt_locations,
    )


def _is_test_or_doc(rel_path: str) -> bool:
    parts = rel_path.lower().split("/")
    skip_dirs = {"test", "tests", "docs", "doc", "examples", "example", "docs_src"}
    if any(part in skip_dirs for part in parts):
        return True
    name = parts[-1] if parts else ""
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return False


def _is_known_model(model_id: str) -> bool:
    model_lower = model_id.lower()
    return any(model_lower.startswith(prefix) for prefix in MODEL_PREFIXES)


def _guess_provider(model_id: str, known_providers: list[str]) -> str:
    model_lower = model_id.lower()
    if "gpt" in model_lower or model_lower.startswith("o1") or model_lower.startswith("o3"):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower:
        return "google_gemini"
    if "llama" in model_lower or "mixtral" in model_lower or "mistral" in model_lower:
        return "ollama"
    if "command" in model_lower:
        return "cohere"
    if "deepseek" in model_lower:
        return "deepseek"
    if known_providers:
        return known_providers[0]
    return "unknown"
