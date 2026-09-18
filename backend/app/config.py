"""Centralized application configuration.

Every environment variable the backend understands is declared here exactly
once (spec: "Make all configuration centralized"). Nothing else in the
codebase reads ``os.environ`` directly.

WHY pydantic-settings?
  WHAT: parses environment variables + an optional .env file into a typed
        object at process start.
  WHY: a typo in an env var name fails fast at boot, not at midnight.
  TRADEOFF: one extra dependency vs. hand-rolled os.getenv parsing.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents: [0]=app, [1]=backend, [2]=repo root.
# Used so the SQLite default path works no matter where the process starts.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH: Path = REPO_ROOT / "data" / "autom8r.db"


class Settings(BaseSettings):
    """Typed view over the process environment.

    pydantic-settings reads matching environment variables (case-insensitive)
    and falls back to the defaults below, so the app boots with no .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- runtime ---
    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_port: int = 5173

    # --- database ---
    # Empty string -> replaced by the repo-root default in model_post_init.
    database_url: str = ""

    # --- MCP ---
    mcp_server_url: str = "http://127.0.0.1:8001/mcp"

    # --- LLM ---
    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    # --- demo auth secrets ---
    admin_token: str = "change-me"
    webhook_secret: str = "change-me"

    # --- optional Google Sheets adapter ---
    google_sheets_enabled: bool = False
    google_service_account_json: str = ""
    google_sheet_id: str = ""

    # --- CORS: comma-separated browser origins ---
    cors_origins: str = "http://localhost:5173"

    def model_post_init(self, __context: object, /) -> None:
        """Fill derived defaults after env parsing."""
        if not self.database_url:
            # as_posix() keeps forward slashes so the URL is valid on Windows.
            self.database_url = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS as a list ('http://a,http://b' -> ['http://a', 'http://b'])."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_mode(self) -> str:
        """'live' only when enabled AND a key exists; otherwise 'mock'."""
        return "live" if (self.llm_enabled and self.llm_api_key) else "mock"


settings = Settings()
