"""NexusOS configuration management via environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Local LLM (Ollama)
    llm_provider: str = "openai"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Voice
    wake_word: str = "nexus"
    voice_language: str = "en-US"
    whisper_model: str = "base"
    tts_rate: int = 175
    tts_volume: float = 1.0

    # Database
    database_url: str = "sqlite:///./data/nexus.db"
    redis_url: str = "redis://localhost:6379"
    memory_db_path: str = "./data/memory.db"

    # MQTT
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883

    # Server
    cors_origins: str = "http://localhost:3002,http://localhost:5173"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Sandbox
    allowed_commands: str = "ls,pwd,echo,python,node,npm"
    sandbox_timeout: int = 30

    # Memory
    max_memory_entries: int = 1000

    # Workflow
    workflow_timeout: int = 300

    # Browser
    browser_headless: bool = True

    # Plugins
    plugin_dir: str = "./plugins"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def allowed_commands_list(self) -> List[str]:
        return [c.strip() for c in self.allowed_commands.split(",")]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
