"""Doação de tutor (pessoa física, com ranking próprio) e meta mensal em dinheiro do abrigo (PIX fora da plataforma)."""
import datetime

from app.models.usuario import Abrigo
from app.routers.apoiadores import nome_publico
from app.routers.doacoes import meta_do_mes, reais
from tests.conftest import SENHA, cabecalho, dados_abrigo
from tests.test_doacoes import avisos_de_doacao, criar_apoiador, doar

PIX = "pix@patinhas.org"


def criar_tutor(client, nome="Maria da Silva", email="maria@exemplo.com") -> dict:
    r = client.post("/auth/cadastro", json={"tipo_conta": "tutor", "nome": nome, "email": email, "senha": SENHA})
    assert r.status_code == 201, r.text
    return {"headers": cabecalho(client, email), "id": r.json()["id"]}


def definir_meta(client, abrigo, centavos=300000, descricao="Ração R$ 1.800, veterinário R$ 900, contas R$ 300", pix=PIX):
    r = client.patch("/usuarios/eu", json={"chave_doacao_financeira": pix, "meta_mensal_centavos": centavos,
                                            "meta_mensal_descricao": descricao}, headers=abrigo["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def confirmar(client, abrigo, doacao_id):
    r = client.patch(f"/doacoes/{doacao_id}", json={"status": "confirmada"}, headers=abrigo["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def test_valores_em_reais_e_nome_publico():
    assert reais(5000) == "R$ 50,00" and reais(123456) == "R$ 1.234,56" and reais(100) == "R$ 1,00"
    assert nome_publico("Maria da Silva Souza") == "Maria S." and nome_publico("Ana") == "Ana"


def test_tutor_doa_itens_do_mural_e_acompanha(client, abrigo_aprovado):
    n = client.post("/necessidades", json={"item": "Areia sanitária", "quantidade": 2}, headers=abrigo_aprovado["headers"]).json()
    tutor = criar_tutor(client)
    d = doar(client, tutor, necessidade_id=n["id"], quantidade=2)
    assert d.status_code == 201 and d.json()["valor_centavos"] is None and d.json()["perfil_publico_doador"] is False
    assert [x["id"] for x in client.get("/doacoes/minhas", headers=tutor["headers"]).json()] == [d.json()["id"]]
    confirmar(client, abrigo_aprovado, d.json()["id"])
    assert client.get("/necessidades").json() == []  # a doação do tutor completou o pedido
    assert "confirmou o recebimento de 2 × Areia sanitária" in avisos_de_doacao(client, tutor["headers"])[0]["mensagem"]


def test_doacao_em_dinheiro_avanca_a_meta_so_depois_da_confirmacao(client, abrigo_aprovado):
    definir_meta(client, abrigo_aprovado)
    tutor = criar_tutor(client)
    r = doar(client, tutor, abrigo_id=abrigo_aprovado["id"], valor_centavos=5000)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["item"] == "Doação em dinheiro (PIX)" and d["valor_centavos"] == 5000 and d["status"] == "aguardando_confirmacao"
    assert "PIX de R$ 50,00" in avisos_de_doacao(client, abrigo_aprovado["headers"])[0]["mensagem"]

    meta = client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"]
    assert meta["valor_centavos"] == 300000 and meta["arrecadado_centavos"] == 0 and meta["descricao"].startswith("Ração")
    confirmar(client, abrigo_aprovado, d["id"])
    meta = client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"]
    assert meta["arrecadado_centavos"] == 5000 and meta["doacoes_confirmadas"] == 1
    assert "R$ 50,00 via PIX" in avisos_de_doacao(client, tutor["headers"])[0]["mensagem"]


def test_doacao_recusada_nao_conta_na_meta(client, abrigo_aprovado):
    definir_meta(client, abrigo_aprovado)
    apoiador = criar_apoiador(client)
    d = doar(client, apoiador, abrigo_id=abrigo_aprovado["id"], valor_centavos=20000).json()
    client.patch(f"/doacoes/{d['id']}", json={"status": "recusada"}, headers=abrigo_aprovado["headers"])
    assert client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"]["arrecadado_centavos"] == 0


def test_regras_da_doacao_em_dinheiro(client, abrigo_aprovado):
    tutor = criar_tutor(client)
    sem_pix = doar(client, tutor, abrigo_id=abrigo_aprovado["id"], valor_centavos=5000)
    assert sem_pix.status_code == 409 and "chave PIX" in sem_pix.json()["detail"]
    definir_meta(client, abrigo_aprovado)
    assert doar(client, tutor, abrigo_id=abrigo_aprovado["id"], valor_centavos=50).status_code == 422  # mínimo R$ 1,00
    assert doar(client, tutor, valor_centavos=5000).status_code == 422  # sem abrigo
    assert doar(client, tutor, abrigo_id=abrigo_aprovado["id"], item="Ração", valor_centavos=5000).status_code == 422  # item e valor
    sem_selo = client.post("/auth/cadastro", json=dados_abrigo(email="semselo@exemplo.com", chave_doacao_financeira=PIX)).json()["id"]
    r = doar(client, tutor, abrigo_id=sem_selo, valor_centavos=5000)
    assert r.status_code == 409 and "selo Verificado" in r.json()["detail"]


def test_meta_so_aparece_com_selo_e_chave_e_pode_ser_retirada(client, abrigo_aprovado, admin):
    assert client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"] is None  # sem meta definida
    eu = definir_meta(client, abrigo_aprovado)
    assert eu["perfil"]["meta_mensal_centavos"] == 300000
    client.patch(f"/admin/abrigos/{abrigo_aprovado['id']}/validacao", json={"status": "pendente"}, headers=admin)
    assert client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"] is None  # perdeu o selo
    client.patch(f"/admin/abrigos/{abrigo_aprovado['id']}/validacao", json={"status": "aprovado"}, headers=admin)
    assert client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"] is not None
    client.patch("/usuarios/eu", json={"meta_mensal_centavos": None}, headers=abrigo_aprovado["headers"])
    assert client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["meta_mensal"] is None
    assert client.patch("/usuarios/eu", json={"meta_mensal_centavos": 10}, headers=abrigo_aprovado["headers"]).status_code == 422
    tutor = criar_tutor(client)
    assert client.patch("/usuarios/eu", json={"meta_mensal_centavos": 5000}, headers=tutor["headers"]).status_code == 422


def test_meta_conta_so_o_mes_corrente_no_fuso_de_recife(client, abrigo_aprovado, sessao_factory):
    definir_meta(client, abrigo_aprovado)
    tutor = criar_tutor(client)
    d = doar(client, tutor, abrigo_id=abrigo_aprovado["id"], valor_centavos=7000).json()
    confirmar(client, abrigo_aprovado, d["id"])
    with sessao_factory() as db:
        abrigo = db.get(Abrigo, abrigo_aprovado["id"])
        hoje = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date()
        assert meta_do_mes(db, abrigo, hoje).arrecadado_centavos == 7000
        mes_que_vem = (hoje.replace(day=28) + datetime.timedelta(days=5)).replace(day=1)
        assert meta_do_mes(db, abrigo, mes_que_vem).arrecadado_centavos == 0


def test_tutor_entra_no_ranking_de_pessoa_fisica_com_nome_resumido(client, abrigo_aprovado):
    definir_meta(client, abrigo_aprovado)
    tutor = criar_tutor(client, nome="Maria da Silva")
    criar_tutor(client, nome="João Sem Doação", email="joao@exemplo.com")
    apoiador = criar_apoiador(client)
    for conta in (tutor, apoiador):
        d = doar(client, conta, abrigo_id=abrigo_aprovado["id"], valor_centavos=3000).json()
        confirmar(client, abrigo_aprovado, d["id"])

    [pf] = client.get("/apoiadores/ranking", params={"categoria": "pessoa_fisica"}).json()
    assert pf["nome"] == "Maria S." and pf["tipo_estabelecimento"] == "pessoa_fisica" and pf["perfil_publico"] is False
    assert pf["doacoes_confirmadas"] == 1 and pf["pontos"] == 20
    assert [r["nome"] for r in client.get("/apoiadores/ranking", params={"categoria": "petshop"}).json()] == ["Pet Shop Amigo"]
    assert {r["nome"] for r in client.get("/apoiadores/ranking").json()} == {"Maria S.", "Pet Shop Amigo"}  # destaques
    # pessoa física não tem perfil público nem aparece no mapa, nem na lista de apoiadores do abrigo
    assert client.get(f"/apoiadores/{tutor['id']}").status_code == 404
    assert [a["nome"] for a in client.get("/apoiadores").json()] == ["Pet Shop Amigo"]
    assert [a["nome"] for a in client.get(f"/abrigos/{abrigo_aprovado['id']}").json()["apoiadores"]] == ["Pet Shop Amigo"]


def test_tutor_desativado_sai_do_ranking(client, abrigo_aprovado):
    definir_meta(client, abrigo_aprovado)
    tutor = criar_tutor(client)
    d = doar(client, tutor, abrigo_id=abrigo_aprovado["id"], valor_centavos=3000).json()
    confirmar(client, abrigo_aprovado, d["id"])
    client.delete("/usuarios/eu", headers=tutor["headers"])
    assert client.get("/apoiadores/ranking", params={"categoria": "pessoa_fisica"}).json() == []


def test_conta_de_apoiador_nao_pode_ser_pessoa_fisica(client):
    r = client.post("/auth/cadastro", json={
        "tipo_conta": "apoiador", "nome": "Fulano", "email": "fulano@exemplo.com", "senha": SENHA,
        "cnpj": "11222333000181", "tipo_estabelecimento": "pessoa_fisica", "endereco": "Rua A, 1, Recife",
    })
    assert r.status_code == 422 and "conta de tutor" in r.text
    apoiador = criar_apoiador(client)
    assert client.patch("/usuarios/eu", json={"tipo_estabelecimento": "pessoa_fisica"}, headers=apoiador["headers"]).status_code == 422


def test_csv_de_doacoes_traz_pessoa_fisica_e_valor(client, abrigo_aprovado):
    definir_meta(client, abrigo_aprovado)
    tutor = criar_tutor(client)
    doar(client, tutor, abrigo_id=abrigo_aprovado["id"], valor_centavos=12345)
    csv = client.get("/relatorios/abrigo/doacoes.csv", headers=abrigo_aprovado["headers"]).content.decode("utf-8-sig")
    cabecalho_csv, linha = csv.strip().splitlines()
    assert "Valor (R$)" in cabecalho_csv
    assert "Maria da Silva;pessoa_fisica;Doação em dinheiro (PIX);1;123,45;" in linha
