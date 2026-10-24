from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent
_ENV_FILES = (
    str(_ROOT / ".env"),
    str(_ROOT.parent / ".env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    anthropic_api_key: str = ""
    # 8000 is often taken on hackathon machines — default to 8765
    agent_service_port: int = 8765
    agent_autonomy_limit_usd: float = 1000.0
    cashier_auto_pay_limit_usd: float = 1000.0
    spacetimedb_uri: str = "http://127.0.0.1:3000"
    spacetimedb_db: str = "swarmcfo"
    demo_room: str = "maya-bakery"
    demo_fallback_replay: bool = True

    # Capital One Nessie (https://api.nessieisreal.com) — set in .env, never commit
    nessie_api_key: str = ""
    nessie_base_url: str = "https://api.nessieisreal.com"

    # Claude model for agent tool-use (override via CLAUDE_MODEL)
    claude_model: str = "claude-sonnet-4-5"

    # Mission Margin Controller — default demo economics
    mission_default_quote_cents: int = 25_000  # $250
    mission_default_max_spend_cents: int = 800  # $8


settings = Settings()