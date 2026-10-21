from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

# Valor de exemplo da chave que assina os logins: serve só para desenvolvimento (ver _segredo_de_verdade).
SEGREDO_PADRAO = "troque-em-producao"
HOSTS_LOCAIS = {None, "", "localhost", "127.0.0.1", "db"}  # db = o Postgres do docker-compose

# .env fica em api/.env — caminho absoluto para funcionar rodando de qualquer pasta.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = "postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet"
    jwt_secret: str = SEGREDO_PADRAO
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 60 * 24
    nucleo_opencl_url: str = "http://nucleo-opencl:8001"
    cors_origens: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    # Fotos do reencontro (RF-19/RF-20). Pasta fora do Git; ver app/core/fotos.py.
    pasta_fotos: Path = ENV_FILE.parent / "uploads" / "fotos"
    foto_tamanho_max_mb: int = 8
    # E-mail (RF-05, RF-36). Sem SMTP_HOST, os e-mails vão para a caixa de saída (arquivos .eml); ver app/core/email.py.
    smtp_host: str | None = None
    smtp_porta: int = 587
    smtp_usuario: str | None = None
    smtp_senha: str | None = None
    email_remetente: str = "BuscaPet <nao-responda@buscapet.dev>"
    pasta_caixa_saida: Path = ENV_FILE.parent / "caixa-de-saida"
    # Endereço da interface, usado nos links dos e-mails (ex.: redefinir senha).
    url_interface: str = "http://localhost:5173"
    redefinir_senha_minutos: int = 30

    @model_validator(mode="after")
    def _segredo_de_verdade(self):
        """Com o segredo de exemplo, qualquer pessoa forjaria um login. Fora de um banco local, a API não sobe."""
        if self.jwt_secret == SEGREDO_PADRAO and make_url(self.database_url).host not in HOSTS_LOCAIS:
            raise ValueError("Defina JWT_SECRET com um valor aleatório longo antes de usar um banco que não é local "
                             "(ex.: python -c \"import secrets; print(secrets.token_urlsafe(48))\").")
        return self


settings = Settings()
