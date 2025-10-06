import os
from dataclasses import dataclass, field


def _split_env_list(name: str, default: list[str]) -> list[str]:
    val = os.getenv(name)
    if not val:
        return default
    # Split by comma and trim spaces
    return [item.strip() for item in val.split(",") if item.strip()]


@dataclass
class Settings:
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8001"))
    ssl_keyfile: str | None = os.getenv("SSL_KEYFILE")
    ssl_certfile: str | None = os.getenv("SSL_CERTFILE")

    # AI / Models
    default_model: str = os.getenv("DEFAULT_MODEL", "gemma3:12b")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")

    # CORS (use default_factory to avoid mutable default issues)
    cors_allow_origins: list[str] = field(default_factory=lambda: _split_env_list("CORS_ALLOW_ORIGINS", ["*"]))
    cors_allow_credentials: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    cors_allow_methods: list[str] = field(default_factory=lambda: _split_env_list("CORS_ALLOW_METHODS", ["*"]))
    cors_allow_headers: list[str] = field(default_factory=lambda: _split_env_list("CORS_ALLOW_HEADERS", ["*"]))


settings = Settings()
