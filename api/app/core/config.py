from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet"
    jwt_secret: str = "troque-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 60 * 24
    nucleo_opencl_url: str = "http://nucleo-opencl:8001"
    redis_url: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
