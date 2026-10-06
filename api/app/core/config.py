from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env fica em api/.env — caminho absoluto para funcionar rodando de qualquer pasta.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = "postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet"
    jwt_secret: str = "troque-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 60 * 24
    nucleo_opencl_url: str = "http://nucleo-opencl:8001"
    redis_url: str = "redis://redis:6379/0"
    cors_origens: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
