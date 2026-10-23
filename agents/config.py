from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    agent_service_port: int = 8000
    agent_autonomy_limit_usd: float = 1000.0
    cashier_auto_pay_limit_usd: float = 1000.0
    spacetimedb_uri: str = "http://127.0.0.1:3000"
    spacetimedb_db: str = "swarmcfo"
    demo_room: str = "maya-bakery"
    demo_fallback_replay: bool = True


settings = Settings()