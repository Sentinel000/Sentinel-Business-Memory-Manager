"""Application settings, loaded from the environment.

Secrets never appear in code. See docs/rules/security.md.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env lives at the repo root, one level above backend/.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment configuration. Every field is documented in backend/.env.example."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_connection_string: str

    # Auth — the JWT secret is the tenancy boundary, since company_id is a signed claim.
    jwt_secret_key: str = "change-me-generate-a-real-random-value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    # Agent & LLM (Qwen API via OpenAI-compatible endpoint).
    # No default: a key belongs in .env, never in the repo. See docs/rules/security.md.
    qwen_api_key: str = ""
    qwen_api_base: str = "https://ws-pqnqfaz25ftwogus.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    agent_model: str = "qwen3.6-plus"
    auto_approve_threshold_default: float = 1.0

    # Knowledge memory (HydraDB). Empty disables knowledge tools rather than failing
    # startup — the system runs without them, just with thinner chat answers.
    hydra_db_api_key: str = ""
    hydra_timeout_seconds: float = 30.0

    # Email (SMTP). An empty host disables delivery without failing anything:
    # reminders still land on the employee's task view, they are just not emailed.
    # Any SMTP provider works - Alibaba Cloud DirectMail, Resend, Gmail with an app
    # password. smtp_use_ssl means implicit TLS (usually port 465); otherwise STARTTLS.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True
    email_from: str = ""
    smtp_timeout_seconds: float = 15.0

    # Where the web app is served, for links inside emails.
    app_base_url: str = "http://localhost:3000"
    #: How long an emailed one-tap status link stays valid.
    action_link_ttl_hours: int = 168

    @property
    def sqlalchemy_url(self) -> str:
        """The connection string with a psycopg 3 driver prefix.

        Neon hands out plain ``postgresql://`` URLs. SQLAlchemy reads that as psycopg2,
        which we do not install, so the prefix is normalised here rather than relying on
        whoever pastes the URL to remember.
        """
        url = self.database_connection_string.strip().strip('"').strip("'")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def is_pooled_connection(self) -> bool:
        """Neon's ``-pooler`` endpoint is pgbouncer in transaction mode.

        Server-side prepared statements do not survive it, so psycopg's prepare
        threshold has to be disabled when we are pointed at one.
        """
        return "-pooler." in self.database_connection_string

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS is comma-separated in the environment."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.email_from)

    @property
    def uses_weak_jwt_secret(self) -> bool:
        """The shipped placeholder, or anything too short to be a real key.

        This key signs session tokens *and* emailed action links, and company_id
        rides inside those tokens - so a guessable key is a cross-tenant problem.
        """
        return self.jwt_secret_key.startswith("change-me") or len(self.jwt_secret_key) < 32


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env is read once per process."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
