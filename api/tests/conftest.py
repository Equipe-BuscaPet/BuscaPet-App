"""Fixtures dos testes. Cada teste roda num SQLite em memória, criado do zero a
partir dos models: os testes nunca tocam no banco real (Supabase)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registra todas as tabelas em Base.metadata
from app.core.seguranca import hash_senha
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import TipoConta
from app.models.usuario import Usuario

SENHA = "senha-segura-123"
CNPJ_VALIDO = "11.222.333/0001-81"


@pytest.fixture()
def sessao_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(sessao_factory):
    def _get_db():
        db = sessao_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def cabecalho(client: TestClient, email: str, senha: str = SENHA) -> dict:
    resp = client.post("/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def dados_tutor(email="tutor@exemplo.com", **extra) -> dict:
    return {
        "tipo_conta": "tutor", "nome": "Maria Tutora", "email": email, "senha": SENHA,
        "telefone": "81999990000", "cidade": "Recife", **extra,
    }


def dados_abrigo(email="abrigo@exemplo.com", **extra) -> dict:
    return {
        "tipo_conta": "abrigo", "nome": "Joana Protetora", "email": email, "senha": SENHA,
        "nome_abrigo": "Abrigo Patinhas", "endereco": "Rua das Flores, 10, Recife",
        "latitude": -8.05, "longitude": -34.9, **extra,
    }


def dados_animal(**extra) -> dict:
    return {"nome": "Thor", "especie": "cao", "porte": "medio", "sexo": "macho", **extra}


@pytest.fixture()
def admin(client, sessao_factory) -> dict:
    """Cria um administrador direto no banco (não existe cadastro público de admin)."""
    with sessao_factory() as db:
        db.add(Usuario(nome="Admin", email="admin@exemplo.com", senha_hash=hash_senha(SENHA), tipo_conta=TipoConta.ADMIN))
        db.commit()
    return cabecalho(client, "admin@exemplo.com")


@pytest.fixture()
def abrigo_aprovado(client, admin) -> dict:
    """Abrigo cadastrado e já aprovado pelo admin; devolve cabeçalho e id."""
    resp = client.post("/auth/cadastro", json=dados_abrigo())
    assert resp.status_code == 201, resp.text
    usuario_id = resp.json()["id"]
    ok = client.patch(f"/admin/abrigos/{usuario_id}/validacao", json={"status": "aprovado"}, headers=admin)
    assert ok.status_code == 200, ok.text
    return {"headers": cabecalho(client, "abrigo@exemplo.com"), "id": usuario_id}
