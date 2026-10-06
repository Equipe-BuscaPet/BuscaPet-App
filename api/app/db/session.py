"""Engine e sessão do SQLAlchemy. A URL vem de Settings (variável de ambiente
DATABASE_URL ou api/.env), a mesma fonte usada pelo resto da API.

Local (docker-compose): postgresql+psycopg://buscapet:buscapet@db:5432/buscapet
Supabase (demo/produção): connection string do painel do projeto.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    """Dependency do FastAPI: uma sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
