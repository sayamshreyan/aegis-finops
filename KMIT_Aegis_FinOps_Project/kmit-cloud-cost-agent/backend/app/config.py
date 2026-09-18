from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("AGENT_PROVIDER", "mock").lower()
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6")
    max_observation_age_seconds: int = int(os.getenv("MAX_OBSERVATION_AGE_SECONDS", "900"))
    database_path: str = os.getenv("DATABASE_PATH", "./data/aegis_finops.db")

settings = Settings()
