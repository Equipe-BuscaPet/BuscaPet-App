"""Base declarativa do SQLAlchemy, compartilhada por todos os models."""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convenção de nomes para constraints — deixa os nomes previsíveis nas migrations
# do Alembic (evita nomes autogerados tipo "sa_fk_xxxxx" ilegíveis no schema.sql).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
