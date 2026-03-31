"""
single source of truth for all AI ecosystem knowledge.

shipped with everything we know. users extend via silo.toml.
add a provider/vector DB/framework once here — detection works everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderEntry:
    name: str
    deps: list[str]           # exact pypi/npm package names
    imports: list[str]        # python import prefixes
    env: str | None = None    # primary auth env var
    auth_method: str = "api_key"


@dataclass
class VectorDBEntry:
    name: str
    deps: list[str]
    imports: list[str]


@dataclass
class AgentFrameworkEntry:
    name: str
    deps: list[str]
    imports: list[str]


@dataclass
class SecretPattern:
    name: str           # "openai_key", "github_token"
    pattern: str        # regex string (compiled at lookup time)
    severity: str       # critical, high, medium
    description: str = ""


@dataclass
class Registry:
    providers: list[ProviderEntry] = field(default_factory=list)
    vector_dbs: list[VectorDBEntry] = field(default_factory=list)
    agent_frameworks: list[AgentFrameworkEntry] = field(default_factory=list)
    secret_patterns: list[SecretPattern] = field(default_factory=list)

    def provider_by_dep(self, dep: str) -> ProviderEntry | None:
        dep_lower = dep.lower()
        for p in self.providers:
            if dep_lower in p.deps:
                return p
        return None

    def provider_by_import(self, import_line: str) -> ProviderEntry | None:
        for p in self.providers:
            for imp in p.imports:
                if import_line.startswith(f"import {imp}") or import_line.startswith(f"from {imp}"):
                    return p
        return None

    def vector_db_by_dep(self, dep: str) -> VectorDBEntry | None:
        dep_lower = dep.lower()
        for v in self.vector_dbs:
            if dep_lower in v.deps:
                return v
        return None

    def vector_db_by_import(self, import_line: str) -> VectorDBEntry | None:
        for v in self.vector_dbs:
            for imp in v.imports:
                if import_line.startswith(f"import {imp}") or import_line.startswith(f"from {imp}"):
                    return v
        return None

    def framework_by_dep(self, dep: str) -> AgentFrameworkEntry | None:
        dep_lower = dep.lower()
        for f in self.agent_frameworks:
            if dep_lower in f.deps:
                return f
        return None

    def all_env_vars(self) -> set[str]:
        """all known auth env vars from providers."""
        return {p.env for p in self.providers if p.env}


def build_default_registry() -> Registry:
    """everything we know about the AI ecosystem."""

    providers = [
        # openai
        ProviderEntry(
            name="openai",
            deps=["openai"],
            imports=["openai"],
            env="OPENAI_API_KEY",
        ),
        # azure openai
        ProviderEntry(
            name="azure_openai",
            deps=["openai"],  # same package, different client
            imports=["openai"],
            env="AZURE_OPENAI_API_KEY",
        ),
        # anthropic
        ProviderEntry(
            name="anthropic",
            deps=["anthropic"],
            imports=["anthropic"],
            env="ANTHROPIC_API_KEY",
        ),
        # google
        ProviderEntry(
            name="google_gemini",
            deps=["google-generativeai", "google-genai"],
            imports=["google.generativeai", "google.genai"],
            env="GOOGLE_API_KEY",
        ),
        # litellm
        ProviderEntry(
            name="litellm",
            deps=["litellm"],
            imports=["litellm"],
            env="LITELLM_API_KEY",
        ),
        # cohere
        ProviderEntry(
            name="cohere",
            deps=["cohere"],
            imports=["cohere"],
            env="COHERE_API_KEY",
        ),
        # replicate
        ProviderEntry(
            name="replicate",
            deps=["replicate"],
            imports=["replicate"],
            env="REPLICATE_API_TOKEN",
        ),
        # together
        ProviderEntry(
            name="together",
            deps=["together"],
            imports=["together"],
            env="TOGETHER_API_KEY",
        ),
        # groq
        ProviderEntry(
            name="groq",
            deps=["groq"],
            imports=["groq"],
            env="GROQ_API_KEY",
        ),
        # ollama
        ProviderEntry(
            name="ollama",
            deps=["ollama"],
            imports=["ollama"],
            env=None,
            auth_method="none",
        ),
        # mistral
        ProviderEntry(
            name="mistral",
            deps=["mistralai"],
            imports=["mistralai"],
            env="MISTRAL_API_KEY",
        ),
        # fireworks
        ProviderEntry(
            name="fireworks",
            deps=["fireworks-ai"],
            imports=["fireworks"],
            env="FIREWORKS_API_KEY",
        ),
        # huggingface
        ProviderEntry(
            name="huggingface",
            deps=["huggingface-hub", "transformers"],
            imports=["huggingface_hub", "transformers"],
            env="HF_TOKEN",
        ),
        # deepseek
        ProviderEntry(
            name="deepseek",
            deps=["openai"],  # uses openai-compatible API
            imports=["openai"],
            env="DEEPSEEK_API_KEY",
        ),
        # perplexity
        ProviderEntry(
            name="perplexity",
            deps=["openai"],  # uses openai-compatible API
            imports=["openai"],
            env="PERPLEXITY_API_KEY",
        ),
        # aws bedrock
        ProviderEntry(
            name="aws_bedrock",
            deps=["boto3"],
            imports=["boto3"],
            env="AWS_ACCESS_KEY_ID",
            auth_method="aws_credentials",
        ),
    ]

    vector_dbs = [
        VectorDBEntry(name="chromadb", deps=["chromadb"], imports=["chromadb"]),
        VectorDBEntry(name="pinecone", deps=["pinecone", "pinecone-client"], imports=["pinecone"]),
        VectorDBEntry(name="weaviate", deps=["weaviate-client"], imports=["weaviate"]),
        VectorDBEntry(name="qdrant", deps=["qdrant-client"], imports=["qdrant_client"]),
        VectorDBEntry(name="milvus", deps=["pymilvus"], imports=["pymilvus"]),
        VectorDBEntry(name="pgvector", deps=["pgvector"], imports=["pgvector"]),
        VectorDBEntry(name="faiss", deps=["faiss-cpu", "faiss-gpu"], imports=["faiss"]),
        VectorDBEntry(name="lancedb", deps=["lancedb"], imports=["lancedb"]),
        VectorDBEntry(name="marqo", deps=["marqo"], imports=["marqo"]),
        VectorDBEntry(name="elasticsearch", deps=["elasticsearch"], imports=["elasticsearch"]),
        VectorDBEntry(name="opensearch", deps=["opensearch-py"], imports=["opensearchpy"]),
        VectorDBEntry(name="redis_vector", deps=["redis"], imports=["redis"]),
        VectorDBEntry(name="supabase_vector", deps=["supabase"], imports=["supabase"]),
    ]

    agent_frameworks = [
        AgentFrameworkEntry(name="langchain", deps=["langchain", "langchain-core"], imports=["langchain"]),
        AgentFrameworkEntry(name="langgraph", deps=["langgraph"], imports=["langgraph"]),
        AgentFrameworkEntry(name="autogen", deps=["autogen", "pyautogen"], imports=["autogen"]),
        AgentFrameworkEntry(name="crewai", deps=["crewai"], imports=["crewai"]),
        AgentFrameworkEntry(name="llamaindex", deps=["llama-index", "llama-index-core"], imports=["llama_index"]),
        AgentFrameworkEntry(name="semantic_kernel", deps=["semantic-kernel"], imports=["semantic_kernel"]),
        AgentFrameworkEntry(name="smolagents", deps=["smolagents"], imports=["smolagents"]),
        AgentFrameworkEntry(name="pydantic_ai", deps=["pydantic-ai"], imports=["pydantic_ai"]),
        AgentFrameworkEntry(name="agno", deps=["agno"], imports=["agno"]),
        AgentFrameworkEntry(name="openai_agents", deps=["openai-agents"], imports=["agents"]),
    ]

    secret_patterns = [
        # API key formats — exact prefix patterns
        SecretPattern(
            name="openai_key",
            pattern=r"sk-[a-zA-Z0-9]{20,}",
            severity="critical",
            description="OpenAI API key",
        ),
        SecretPattern(
            name="openai_project_key",
            pattern=r"sk-proj-[a-zA-Z0-9\-_]{20,}",
            severity="critical",
            description="OpenAI project API key",
        ),
        SecretPattern(
            name="anthropic_key",
            pattern=r"sk-ant-[a-zA-Z0-9\-]{20,}",
            severity="critical",
            description="Anthropic API key",
        ),
        SecretPattern(
            name="github_pat",
            pattern=r"ghp_[a-zA-Z0-9]{36}",
            severity="critical",
            description="GitHub personal access token",
        ),
        SecretPattern(
            name="github_oauth",
            pattern=r"gho_[a-zA-Z0-9]{36}",
            severity="critical",
            description="GitHub OAuth token",
        ),
        SecretPattern(
            name="github_app",
            pattern=r"(?:ghs|ghr)_[a-zA-Z0-9]{36}",
            severity="critical",
            description="GitHub App token",
        ),
        SecretPattern(
            name="aws_access_key",
            pattern=r"AKIA[0-9A-Z]{16}",
            severity="critical",
            description="AWS access key ID",
        ),
        SecretPattern(
            name="aws_secret_key",
            pattern=r"""(?:aws_secret_access_key|AWS_SECRET)\s*[:=]\s*['"]([a-zA-Z0-9/+=]{40})['"]""",
            severity="critical",
            description="AWS secret access key",
        ),
        SecretPattern(
            name="azure_key",
            pattern=r"[a-f0-9]{32}",  # too broad alone, needs context — see secrets.py
            severity="high",
            description="Azure service key (32-char hex)",
        ),
        SecretPattern(
            name="google_api_key",
            pattern=r"AIza[0-9A-Za-z\-_]{35}",
            severity="critical",
            description="Google API key",
        ),
        SecretPattern(
            name="slack_token",
            pattern=r"xox[bpras]-[0-9a-zA-Z\-]{10,}",
            severity="critical",
            description="Slack token",
        ),
        SecretPattern(
            name="slack_webhook",
            pattern=r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
            severity="high",
            description="Slack webhook URL",
        ),
        SecretPattern(
            name="stripe_key",
            pattern=r"(?:sk|pk)_(?:test|live)_[a-zA-Z0-9]{20,}",
            severity="critical",
            description="Stripe API key",
        ),
        SecretPattern(
            name="twilio_key",
            pattern=r"SK[a-f0-9]{32}",
            severity="critical",
            description="Twilio API key",
        ),
        SecretPattern(
            name="sendgrid_key",
            pattern=r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}",
            severity="critical",
            description="SendGrid API key",
        ),
        SecretPattern(
            name="jwt",
            pattern=r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
            severity="high",
            description="JSON Web Token",
        ),
        SecretPattern(
            name="private_key",
            pattern=r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
            severity="critical",
            description="Private key file",
        ),
        SecretPattern(
            name="pinecone_key",
            pattern=r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            severity="high",
            description="UUID-format API key (Pinecone, etc.)",
        ),
        SecretPattern(
            name="huggingface_token",
            pattern=r"hf_[a-zA-Z0-9]{34}",
            severity="critical",
            description="Hugging Face token",
        ),
        SecretPattern(
            name="groq_key",
            pattern=r"gsk_[a-zA-Z0-9]{20,}",
            severity="critical",
            description="Groq API key",
        ),
        # generic patterns — need context (key=, secret=, password=)
        SecretPattern(
            name="generic_api_key",
            pattern=r"""(?:api[_-]?key|apikey)\s*[:=]\s*['"]([a-zA-Z0-9_\-]{20,})['"]""",
            severity="critical",
            description="Generic API key assignment",
        ),
        SecretPattern(
            name="generic_secret",
            pattern=r"""(?:secret[_-]?key|secretkey)\s*[:=]\s*['"]([a-zA-Z0-9_\-]{20,})['"]""",
            severity="critical",
            description="Generic secret key assignment",
        ),
        SecretPattern(
            name="generic_password",
            pattern=r"""(?:password|passwd|pwd)\s*[:=]\s*['"]([^'"]{8,})['"]""",
            severity="high",
            description="Generic password assignment",
        ),
        SecretPattern(
            name="generic_token",
            pattern=r"""(?:token)\s*[:=]\s*['"]([a-zA-Z0-9_\-]{20,})['"]""",
            severity="critical",
            description="Generic token assignment",
        ),
    ]

    return Registry(
        providers=providers,
        vector_dbs=vector_dbs,
        agent_frameworks=agent_frameworks,
        secret_patterns=secret_patterns,
    )


# singleton — loaded once
DEFAULT_REGISTRY = build_default_registry()


def load_user_registry(toml_path: str | None = None) -> Registry:
    """load user extensions from silo.toml and merge with defaults."""
    registry = build_default_registry()

    if not toml_path:
        return registry

    from pathlib import Path
    path = Path(toml_path)
    if not path.exists():
        return registry

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return registry

    # merge user providers
    for name, entry in data.get("providers", {}).items():
        registry.providers.append(ProviderEntry(
            name=name,
            deps=entry.get("deps", []),
            imports=entry.get("imports", []),
            env=entry.get("env"),
            auth_method=entry.get("auth_method", "api_key"),
        ))

    # merge user vector DBs
    for name, entry in data.get("vector_dbs", {}).items():
        registry.vector_dbs.append(VectorDBEntry(
            name=name,
            deps=entry.get("deps", []),
            imports=entry.get("imports", []),
        ))

    # merge user agent frameworks
    for name, entry in data.get("agent_frameworks", {}).items():
        registry.agent_frameworks.append(AgentFrameworkEntry(
            name=name,
            deps=entry.get("deps", []),
            imports=entry.get("imports", []),
        ))

    # merge user secret patterns
    for name, entry in data.get("secrets", {}).items():
        registry.secret_patterns.append(SecretPattern(
            name=name,
            pattern=entry.get("pattern", ""),
            severity=entry.get("severity", "high"),
            description=entry.get("description", ""),
        ))

    return registry
