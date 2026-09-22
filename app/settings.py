"""Configuration for the local-only proof of concept."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    model: str = os.getenv("OLLAMA_MODEL", "ministral-3:3b")
    timeout: float = float(os.getenv("OLLAMA_TIMEOUT", "180"))
    context_size: int = int(os.getenv("OLLAMA_CONTEXT_SIZE", "8192"))
    session_ttl: int = 7200
    max_sessions: int = 100
    max_steps: int = 60
    max_messages: int = 80
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:4200",
        "http://localhost:4200",
        "http://localhost:4300",
        "http://127.0.0.1:4300",
    )


settings = Settings()
