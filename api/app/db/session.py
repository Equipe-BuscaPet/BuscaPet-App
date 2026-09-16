"""Engine e sessão do SQLAlchemy, lidas da variável de ambiente DATABASE_URL.

Local (docker-compose): postgresql+psycopg://buscapet:buscapet@db:5432/buscapet
Supabase (produção/demo): connection string fornecida pelo painel do projeto.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    """Dependency do FastAPI: uma sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
