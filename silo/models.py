from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class Dependency(BaseModel):
    name: str
    version: str | None = None
    source: str  # pip, npm, cargo, go


class EnvVar(BaseModel):
    name: str
    found_in: list[str]  # file paths where referenced
    has_default: bool = False


class ExposedSecret(BaseModel):
    type: str  # api_key, token, password
    file: str
    line: int
    severity: str  # critical, high, medium


class ExternalService(BaseModel):
    host: str
    purpose: str | None = None


class Vulnerability(BaseModel):
    source: str  # dependency name or file
    description: str
    severity: str  # critical, high, medium, low
    cve: str | None = None


class DatabaseConnection(BaseModel):
    type: str  # postgres, sqlite, redis, mongo
    connection_pattern: str  # env_var, hardcoded, config_file


class ModelProvider(BaseModel):
    name: str  # openai, anthropic, azure_openai, ollama
    auth_method: str  # api_key, oauth, managed_identity, none
    env_var: str | None = None


class ModelUsage(BaseModel):
    provider: str
    model_id: str | None = None
    file: str
    purpose: str | None = None  # chat, embedding, classification


class VectorDBInfo(BaseModel):
    type: str  # chromadb, pinecone, weaviate, pgvector
    connection_method: str  # local, cloud, env_var


class PromptLocation(BaseModel):
    file: str
    type: str  # inline, template_file, dynamic, system_prompt
    line: int | None = None


class AINativeProfile(BaseModel):
    is_ai_native: bool = False

    # model usage
    providers: list[ModelProvider] = []
    models: list[ModelUsage] = []

    # RAG
    vector_db: VectorDBInfo | None = None
    embedding_calls: list[str] = []
    retrieval_pattern: str | None = None

    # agents
    has_agent_loop: bool = False
    tool_definitions: list[str] = []
    agent_framework: str | None = None

    # prompts
    prompt_locations: list[PromptLocation] = []


class ScanError(BaseModel):
    phase: str       # which scan phase failed
    file: str | None = None  # which file caused it, if known
    error: str       # what went wrong


class ScanResult(BaseModel):
    # identity
    app_path: Path
    app_name: str
    scanned_at: datetime

    # runtime
    language: str | None = None
    framework: str | None = None
    runtime_version: str | None = None
    entry_point: str | None = None

    # dependencies
    dependencies: list[Dependency] = []
    dependency_file: str | None = None

    # network
    ports: list[int] = []
    external_services: list[ExternalService] = []

    # secrets
    env_vars: list[EnvVar] = []
    exposed_secrets: list[ExposedSecret] = []

    # security
    vulnerabilities: list[Vulnerability] = []

    # storage
    databases: list[DatabaseConnection] = []
    file_storage: list[str] = []

    # AI-native (None if not an AI app)
    ai: AINativeProfile | None = None

    # errors encountered during scan (empty = clean scan)
    errors: list[ScanError] = []
