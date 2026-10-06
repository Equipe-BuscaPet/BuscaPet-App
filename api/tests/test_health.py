from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck():
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_db_consulta_o_banco(client):
    resp = client.get("/health/db")
    assert resp.status_code == 200
    assert resp.json()["banco"] == "conectado"


def test_health_db_responde_503_sem_vazar_detalhes_quando_o_banco_cai(client):
    from app.db.session import get_db

    class SessaoQuebrada:
        def execute(self, *a, **k):
            raise RuntimeError("postgresql://usuario:senha@host/banco")

    def quebrado():
        yield SessaoQuebrada()

    original = client.app.dependency_overrides[get_db]
    client.app.dependency_overrides[get_db] = quebrado
    try:
        resp = client.get("/health/db")
    finally:
        client.app.dependency_overrides[get_db] = original
    assert resp.status_code == 503
    assert "senha" not in resp.text and "postgresql" not in resp.text
