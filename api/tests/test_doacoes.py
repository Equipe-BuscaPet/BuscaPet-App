"""Doações e reconhecimento (RF-30 a RF-35): necessidades, doação com confirmação, ranking e perfis públicos."""
import datetime

import pytest

from app.core import pontuacao
from app.models.doacao import Doacao
from app.models.enums import StatusDoacao
from tests.conftest import SENHA, cabecalho, dados_abrigo

CNPJS = ["11222333000181", "11444777000161", "45723174000110"]


def criar_apoiador(client, email="petshop@exemplo.com", nome="Pet Shop Amigo", tipo="petshop", cnpj=CNPJS[0]) -> dict:
    r = client.post("/auth/cadastro", json={
        "tipo_conta": "apoiador", "nome": nome, "email": email, "senha": SENHA,
        "cnpj": cnpj, "tipo_estabelecimento": tipo, "endereco": "Av. Brasil, 1, Recife",
    })
    assert r.status_code == 201, r.text
    return {"headers": cabecalho(client, email), "id": r.json()["id"]}


@pytest.fixture()
def apoiador(client) -> dict:
    return criar_apoiador(client)


@pytest.fixture()
def necessidade(client, abrigo_aprovado) -> dict:
    r = client.post("/necessidades", json={"item": "Ração para cão adulto (15 kg)", "quantidade": 4, "urgencia": "alta"},
                    headers=abrigo_aprovado["headers"])
    assert r.status_code == 201, r.text
    return r.json()


def avisos_de_doacao(client, cabecalho_conta) -> list[dict]:
    return [n for n in client.get("/notificacoes", headers=cabecalho_conta).json() if n["referencia_tipo"] == "doacao"]


def doar(client, apoiador, **dados):
    return client.post("/doacoes", json={"quantidade": 1, **dados}, headers=apoiador["headers"])


# ---------- RF-30: necessidades ----------

def test_abrigo_verificado_publica_e_ela_aparece_no_mural(client, necessidade):
    mural = client.get("/necessidades").json()
    assert [n["id"] for n in mural] == [necessidade["id"]]
    assert mural[0]["nome_abrigo"] == "Abrigo Patinhas" and mural[0]["quantidade_recebida"] == 0


def test_abrigo_sem_selo_nao_publica(client):
    client.post("/auth/cadastro", json=dados_abrigo(email="novo@exemplo.com"))
    r = client.post("/necessidades", json={"item": "Areia", "quantidade": 2}, headers=cabecalho(client, "novo@exemplo.com"))
    assert r.status_code == 403 and "selo Verificado" in r.json()["detail"]


def test_mural_ordena_por_urgencia_e_filtra(client, abrigo_aprovado):
    h = abrigo_aprovado["headers"]
    for item, urgencia in [("Areia", "baixa"), ("Vermífugo", "alta"), ("Sabão", "media")]:
        client.post("/necessidades", json={"item": item, "quantidade": 1, "urgencia": urgencia}, headers=h)
    assert [n["item"] for n in client.get("/necessidades").json()] == ["Vermífugo", "Sabão", "Areia"]
    assert [n["item"] for n in client.get("/necessidades", params={"urgencia": "baixa"}).json()] == ["Areia"]
    assert client.get("/necessidades", params={"raio_km": 5}).status_code == 422


def test_so_o_dono_edita_e_atendida_sai_do_mural(client, necessidade, admin):
    client.post("/auth/cadastro", json=dados_abrigo(email="outro@exemplo.com"))
    outro = cabecalho(client, "outro@exemplo.com")
    assert client.patch(f"/necessidades/{necessidade['id']}", json={"status": "atendida"}, headers=outro).status_code == 404
    dono = cabecalho(client, "abrigo@exemplo.com")
    r = client.patch(f"/necessidades/{necessidade['id']}", json={"status": "atendida", "quantidade": 6}, headers=dono)
    assert r.status_code == 200 and r.json()["quantidade"] == 6
    assert client.get("/necessidades").json() == []
    assert client.get("/necessidades/minhas", headers=dono).json()[0]["status"] == "atendida"


def test_validacao_da_necessidade(client, abrigo_aprovado):
    r = client.post("/necessidades", json={"item": "x", "quantidade": 0, "urgencia": "urgentissima"}, headers=abrigo_aprovado["headers"])
    assert r.status_code == 422
    assert {e["loc"][-1] for e in r.json()["detail"]} == {"item", "quantidade", "urgencia"}


# ---------- RF-31 / RF-32: doação e confirmação ----------

def test_fluxo_completo_doacao_confirmada_pontua_e_completa_a_necessidade(client, apoiador, necessidade, abrigo_aprovado):
    r = doar(client, apoiador, necessidade_id=necessidade["id"], quantidade=4)
    assert r.status_code == 201, r.text
    doacao = r.json()
    assert doacao["status"] == "aguardando_confirmacao" and doacao["item"] == "Ração para cão adulto (15 kg)"

    abrigo = abrigo_aprovado["headers"]
    [aviso] = avisos_de_doacao(client, abrigo)
    assert "vai doar 4 × Ração" in aviso["mensagem"] and aviso["destino"] == "/doacoes"
    recebidas = client.get("/doacoes/recebidas", headers=abrigo).json()
    assert recebidas[0]["contato"] == "petshop@exemplo.com"  # o abrigo vê como falar com o apoiador

    assert client.get("/apoiadores/ranking").json() == []  # ainda não conta: falta a confirmação
    r = client.patch(f"/doacoes/{doacao['id']}", json={"status": "confirmada"}, headers=abrigo)
    assert r.status_code == 200 and r.json()["confirmado_em"]

    [primeiro] = client.get("/apoiadores/ranking", params={"categoria": "petshop"}).json()
    assert primeiro["nome"] == "Pet Shop Amigo" and primeiro["pontos"] == 20  # 10 (1 doação) + 10 (1º mês seguido)
    assert primeiro["selo_ativo"] is True
    assert client.get("/necessidades").json() == []  # 4 de 4 recebidos: atendida, saiu do mural
    [obrigado] = avisos_de_doacao(client, apoiador["headers"])
    assert "confirmou o recebimento" in obrigado["mensagem"] and obrigado["destino"] == "/minhas-doacoes"
    assert client.patch(f"/doacoes/{doacao['id']}", json={"status": "recusada"}, headers=abrigo).status_code == 409


def test_doacao_parcial_mantem_a_necessidade_no_mural_com_o_progresso(client, apoiador, necessidade, abrigo_aprovado):
    d = doar(client, apoiador, necessidade_id=necessidade["id"], quantidade=1).json()
    client.patch(f"/doacoes/{d['id']}", json={"status": "confirmada"}, headers=abrigo_aprovado["headers"])
    [n] = client.get("/necessidades").json()
    assert n["quantidade_recebida"] == 1 and n["status"] == "aberta"


def test_doacao_recusada_nao_pontua(client, apoiador, necessidade, abrigo_aprovado):
    d = doar(client, apoiador, necessidade_id=necessidade["id"]).json()
    client.patch(f"/doacoes/{d['id']}", json={"status": "recusada"}, headers=abrigo_aprovado["headers"])
    assert client.get("/apoiadores/ranking").json() == []
    assert "não recebeu" in avisos_de_doacao(client, apoiador["headers"])[0]["mensagem"]


def test_regras_de_quem_doa_e_para_quem(client, apoiador, necessidade, abrigo_aprovado):
    tutor = client.post("/auth/cadastro", json={"tipo_conta": "tutor", "nome": "Ana", "email": "ana@exemplo.com", "senha": SENHA})
    assert tutor.status_code == 201
    assert doar(client, {"headers": cabecalho(client, "ana@exemplo.com")}, necessidade_id=necessidade["id"]).status_code == 403
    sem_selo = client.post("/auth/cadastro", json=dados_abrigo(email="semselo@exemplo.com")).json()["id"]
    r = doar(client, apoiador, abrigo_id=sem_selo, item="Areia")
    assert r.status_code == 409 and "selo Verificado" in r.json()["detail"]
    assert doar(client, apoiador, quantidade=2).status_code == 422  # sem necessidade nem abrigo
    assert doar(client, apoiador, necessidade_id=999).status_code == 404
    avulsa = doar(client, apoiador, abrigo_id=abrigo_aprovado["id"], item="Cobertores", quantidade=3)
    assert avulsa.status_code == 201 and avulsa.json()["necessidade_id"] is None


def test_apoiador_cancela_so_enquanto_aguarda_e_outro_abrigo_nao_decide(client, apoiador, necessidade, abrigo_aprovado):
    d1 = doar(client, apoiador, necessidade_id=necessidade["id"]).json()
    client.post("/auth/cadastro", json=dados_abrigo(email="outro@exemplo.com"))
    assert client.patch(f"/doacoes/{d1['id']}", json={"status": "confirmada"}, headers=cabecalho(client, "outro@exemplo.com")).status_code == 404
    assert client.delete(f"/doacoes/{d1['id']}", headers=apoiador["headers"]).status_code == 204
    assert client.get("/doacoes/minhas", headers=apoiador["headers"]).json() == []
    d2 = doar(client, apoiador, necessidade_id=necessidade["id"]).json()
    client.patch(f"/doacoes/{d2['id']}", json={"status": "confirmada"}, headers=abrigo_aprovado["headers"])
    assert client.delete(f"/doacoes/{d2['id']}", headers=apoiador["headers"]).status_code == 409


def test_necessidade_com_doacao_nao_e_excluida(client, apoiador, necessidade, abrigo_aprovado):
    doar(client, apoiador, necessidade_id=necessidade["id"])
    r = client.delete(f"/necessidades/{necessidade['id']}", headers=abrigo_aprovado["headers"])
    assert r.status_code == 409 and "Marque-a como atendida" in r.json()["detail"]


# ---------- RF-33: pontuação por volume e regularidade ----------

def _confirmada_em(sessao_factory, apoiador_id, abrigo_id, *datas):
    with sessao_factory() as db:
        for momento in datas:
            db.add(Doacao(apoiador_id=apoiador_id, abrigo_id=abrigo_id, item="Ração", quantidade=1,
                          status=StatusDoacao.CONFIRMADA, confirmado_em=momento))
        db.flush()
        pontuacao.recalcular(db, apoiador_id)
        db.commit()


def test_regularidade_vale_tanto_quanto_volume(client, sessao_factory, abrigo_aprovado):
    hoje = datetime.datetime.now(datetime.UTC).replace(day=10)
    mes_passado = (hoje.replace(day=1) - datetime.timedelta(days=1)).replace(day=10)
    retrasado = (mes_passado.replace(day=1) - datetime.timedelta(days=1)).replace(day=10)
    constante = criar_apoiador(client, "constante@exemplo.com", "Petshop do Bairro", cnpj=CNPJS[1])
    grande = criar_apoiador(client, "grande@exemplo.com", "Petshop Grande", cnpj=CNPJS[2])
    # Constante: 1 doação por mês há 3 meses → neste mês: 10 (volume) + 30 (3º mês seguido) = 40.
    _confirmada_em(sessao_factory, constante["id"], abrigo_aprovado["id"], retrasado, mes_passado, hoje)
    # Grande: 2 doações só neste mês → 20 (volume) + 10 (1º mês) = 30.
    _confirmada_em(sessao_factory, grande["id"], abrigo_aprovado["id"], hoje, hoje)

    mes = client.get("/apoiadores/ranking", params={"categoria": "petshop", "periodo": "mes"}).json()
    assert [(r["nome"], r["pontos"], r["meses_seguidos"]) for r in mes] == [("Petshop do Bairro", 40, 3), ("Petshop Grande", 30, 1)]
    if retrasado.year == hoje.year:  # o acumulado do ano soma os meses (20 + 30 + 40 = 90)
        ano = client.get("/apoiadores/ranking", params={"categoria": "petshop", "periodo": "ano"}).json()
        assert ano[0]["pontos"] == 90 and ano[0]["doacoes_confirmadas"] == 3
    assert client.get("/apoiadores/ranking", params={"categoria": "clinica"}).json() == []
    assert client.get("/apoiadores/ranking", params={"mes": "2026-13"}).status_code == 422


def test_selo_ativo_so_com_doacao_recente():
    assert pontuacao.selo_ativo({(2026, 10)}, datetime.date(2026, 10, 20))
    assert pontuacao.selo_ativo({(2026, 9)}, datetime.date(2026, 10, 20))
    assert not pontuacao.selo_ativo({(2026, 8)}, datetime.date(2026, 10, 20))
    assert pontuacao.selo_ativo({(2025, 12)}, datetime.date(2026, 1, 5))  # virada de ano


# ---------- RF-34 e RF-12: perfis públicos ----------

def test_perfis_publicos_integram_os_modulos(client, apoiador, necessidade, abrigo_aprovado):
    d = doar(client, apoiador, necessidade_id=necessidade["id"], quantidade=2).json()
    client.patch(f"/doacoes/{d['id']}", json={"status": "confirmada"}, headers=abrigo_aprovado["headers"])
    client.post("/animais", json={"nome": "Thor", "especie": "cao", "porte": "medio", "sexo": "macho"}, headers=abrigo_aprovado["headers"])

    abrigo = client.get(f"/abrigos/{abrigo_aprovado['id']}").json()
    assert abrigo["verificado"] is True and abrigo["animais_disponiveis"] == 1
    assert [n["quantidade_recebida"] for n in abrigo["necessidades"]] == [2]
    assert [(a["nome"], a["selo_ativo"]) for a in abrigo["apoiadores"]] == [("Pet Shop Amigo", True)]

    perfil = client.get(f"/apoiadores/{apoiador['id']}").json()
    assert perfil["pontos_mes"] == 20 and perfil["doacoes_confirmadas"] == 1
    assert perfil["abrigos_apoiados"] == [{"id": abrigo_aprovado["id"], "nome_abrigo": "Abrigo Patinhas", "doacoes_confirmadas": 1}]
    assert "cnpj" not in perfil and "email" not in perfil
    assert [a["nome"] for a in client.get("/apoiadores").json()] == ["Pet Shop Amigo"]
    assert client.get("/apoiadores/99999").status_code == 404


def test_abrigo_sem_selo_nao_mostra_chave_nem_necessidades(client):
    r = client.post("/auth/cadastro", json=dados_abrigo(email="semselo@exemplo.com"))
    cab = cabecalho(client, "semselo@exemplo.com")
    client.patch("/usuarios/eu", json={"perfil": {"chave_doacao_financeira": "pix@semselo.org"}}, headers=cab)
    perfil = client.get(f"/abrigos/{r.json()['id']}").json()
    assert perfil["verificado"] is False and perfil["chave_doacao_financeira"] is None and perfil["necessidades"] == []
    assert client.get("/abrigos/99999").status_code == 404
