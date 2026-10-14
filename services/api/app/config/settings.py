from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/finops_ai"
    test_database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/finops_ai_test"

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    upload_max_bytes: int = 200 * 1024 * 1024
    upload_allowed_extensions: str = ".csv,.parquet,.csv.gz"
    upload_decompression_max_ratio: int = 10
    upload_decompression_max_bytes: int = 2 * 1024 * 1024 * 1024
    upload_staging_dir: str = "./data/incoming"

    worker_heartbeat_seconds: int = 5
    worker_orphan_timeout_seconds: int = 30
    worker_max_attempts: int = 3
    worker_reaper_poll_seconds: int = 5
    worker_poll_seconds: int = 1

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip() for e in self.upload_allowed_extensions.split(",") if e.strip()]


settings = Settings()
