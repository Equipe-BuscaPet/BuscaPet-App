"""Dados de demonstração: criam o mesmo cenário para todo o time e podem ser repetidos sem duplicar."""
from sqlalchemy import func, select

from app.models.animal import Animal
from app.models.usuario import Abrigo, Usuario
from app.scripts.popular_demo import SENHA_DEMO, popular
from tests.conftest import cabecalho


def test_popula_o_cenario_completo(client, sessao_factory):
    with sessao_factory() as db:
        criados = popular(db)
        assert criados == {"contas": 11, "animais": 10}
        assert db.scalar(select(func.count()).select_from(Usuario)) == 11
        assert db.scalar(select(func.count()).select_from(Animal)) == 10
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
        assert db.scalar(select(func.count()).select_from(Usuario)) == 11
        assert db.scalar(select(func.count()).select_from(Animal)) == 10


def test_o_fluxo_de_adocao_funciona_com_os_dados_de_demonstracao(client, sessao_factory):
    with sessao_factory() as db:
        popular(db)
    luna = next(a["id"] for a in client.get("/animais?limite=50").json() if a["nome"] == "Luna")
    resp = client.post(f"/animais/{luna}/interesses", json={}, headers=cabecalho(client, "maria@exemplo.com", SENHA_DEMO))
    assert resp.status_code == 201 and resp.json()["abrigo_telefone"] == "81988880002"


def test_demonstracao_traz_mural_ranking_e_doacao_para_confirmar(client, sessao_factory):
    with sessao_factory() as db:
        popular(db)
    assert len(client.get("/necessidades").json()) == 4
    ranking = client.get("/apoiadores/ranking", params={"categoria": "petshop"}).json()
    assert [r["nome"] for r in ranking] == ["Pet Shop Amigo Fiel", "Pet Center Graças"]  # a constância vence
    patinhas = cabecalho(client, "patinhas@exemplo.com", SENHA_DEMO)
    pendentes = client.get("/doacoes/recebidas", params={"status": "aguardando_confirmacao"}, headers=patinhas).json()
    assert [d["nome_apoiador"] for d in pendentes] == ["Pet Shop Amigo Fiel"]


def test_demonstracao_traz_historico_para_o_relatorio_do_abrigo(client, sessao_factory):
    with sessao_factory() as db:
        popular(db)
    patinhas = cabecalho(client, "patinhas@exemplo.com", SENHA_DEMO)
    r = client.get("/relatorios/abrigo", headers=patinhas).json()
    assert r["adocoes_aprovadas"] == 2 and r["tempo_medio_adocao_dias"] == 20.5  # Pingo 50-28=22 dias, Nina 25-6=19


def test_demonstracao_poe_capa_nos_animais(client, sessao_factory):
    with sessao_factory() as db:
        popular(db)
        popular(db)  # rodar de novo não duplica as fotos
    animais = client.get("/animais?limite=50").json()
    assert animais and all(len(a["fotos"]) == 1 for a in animais)


def test_demonstracao_traz_meta_do_mes_e_pessoas_fisicas_no_ranking(client, sessao_factory):
    with sessao_factory() as db:
        popular(db)
    patinhas = next(a for a in client.get("/abrigos").json() if a["nome_abrigo"] == "Abrigo Patinhas Felizes")
    meta = client.get(f"/abrigos/{patinhas['id']}").json()["meta_mensal"]
    assert meta["valor_centavos"] == 300000 and meta["arrecadado_centavos"] == 11000  # Maria R$ 80 + João R$ 30
    pf = client.get("/apoiadores/ranking", params={"categoria": "pessoa_fisica"}).json()
    assert [r["nome"] for r in pf] == ["Maria S.", "João P."]  # Maria doa há 2 meses seguidos
