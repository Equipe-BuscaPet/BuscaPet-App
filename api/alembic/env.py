import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base  # noqa: E402
from app.models import *  # noqa: E402,F401,F403 — garante que todo model é registrado

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def normalizar_url_banco(url: str) -> str:
    """Igual a app.core.config.normalizar_url_banco (não importado: criar Settings exigiria JWT_SECRET)."""
    url = url.strip()
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


config.set_main_option(
    "sqlalchemy.url",
    # "%%": o configparser do Alembic trata "%" como interpolação, e senhas de banco podem ter "%".
    normalizar_url_banco(os.environ.get("DATABASE_URL", "postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet")).replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
