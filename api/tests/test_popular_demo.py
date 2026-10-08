"""Dados de demonstração: criam o mesmo cenário para todo o time e podem ser repetidos sem duplicar."""
from sqlalchemy import func, select

from app.models.animal import Animal
from app.models.usuario import Abrigo, Usuario
from app.scripts.popular_demo import SENHA_DEMO, popular
from tests.conftest import cabecalho


def test_popula_o_cenario_completo(client, sessao_factory):
    with sessao_factory() as db:
        criados = popular(db)
        assert criados == {"contas": 7, "animais": 8}
        assert db.scalar(select(func.count()).select_from(Usuario)) == 7
        assert db.scalar(select(func.count()).select_from(Animal)) == 8
        assert db.scalar(select(func.count()).select_from(Abrigo)) == 4

    # As contas funcionam de verdade e o selo está onde deveria.
    maria = cabecalho(client, "maria@exemplo.com", SENHA_DEMO)
    assert client.get("/auth/eu", headers=maria).json()["tipo_conta"] == "tutor"
    abrigos = {a["nome_abrigo"]: a["verificado"] for a in client.get("/abrigos").json()}
    assert abrigos == {
        "Abrigo Patinhas Felizes": True, "Casa dos Gatinhos": False,
        "Protetores do Cordeiro": False, "Amigos de Quatro Patas": False,
    }
    assert len(client.get("/animais?limite=50").json()) == 8


def test_rodar_de_novo_nao_duplica_nada(sessao_factory):
    with sessao_factory() as db:
        popular(db)
    with sessao_factory() as db:
        assert popular(db) == {"contas": 0, "animais": 0}
        assert db.scalar(select(func.count()).select_from(Usuario)) == 7
        assert db.scalar(select(func.count()).select_from(Animal)) == 8


def test_o_fluxo_de_adocao_funciona_com_os_dados_de_demonstracao(client, sessao_factory):
    with sessao_factory() as db:
        popular(db)
    luna = next(a["id"] for a in client.get("/animais?limite=50").json() if a["nome"] == "Luna")
    resp = client.post(f"/animais/{luna}/interesses", json={}, headers=cabecalho(client, "maria@exemplo.com", SENHA_DEMO))
    assert resp.status_code == 201 and resp.json()["abrigo_telefone"] == "81988880002"
