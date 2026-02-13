from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    development: bool

    server_public_host: str
    server_display_name: str = "AmneziaWG Server"

    admin_api_key: str | None = None

    cluster_id: str = "default"
    central_api_url: str | None = None
    central_cluster_api_key: str | None = None
    central_admin_bearer_token: str | None = None
    sync_interval_seconds: int = 60
    protocol_config_path: str = "src/management/protocols.yaml"
    persistent_keepalive_seconds: int = 25
    peer_online_threshold_seconds: int = 180
    
    model_config = SettingsConfigDict(
        env_file = ".env",
        extra="ignore"
    )

@lru_cache
def get_settings():
    return Settings()
