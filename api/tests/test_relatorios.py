"""Sprint 7: histórico de operações (RF-39), painel da administração (RF-38), relatórios do abrigo (RF-40),
pesquisa, filtros e exportação CSV."""
import datetime

import pytest

from tests.conftest import SENHA, cabecalho, dados_abrigo, dados_animal, dados_tutor
from tests.test_doacoes import criar_apoiador

# "Hoje" no fuso de Recife, como a API: na CI (em UTC), entre 21h e meia-noite de Recife as datas diferem.
HOJE = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date()


@pytest.fixture()
def cenario(client, admin, abrigo_aprovado):
    """Abrigo verificado com um animal que entrou há 10 dias, um interesse aprovado e uma doação confirmada."""
    abrigo = abrigo_aprovado["headers"]
    entrada = (HOJE - datetime.timedelta(days=10)).isoformat()
    animal = client.post("/animais", json=dados_animal(nome="Thor", data_entrada=entrada), headers=abrigo).json()
    client.post("/auth/cadastro", json=dados_tutor(cidade="Olinda"))
    tutor = cabecalho(client, "tutor@exemplo.com")
    interesse = client.post(f"/animais/{animal['id']}/interesses", json={}, headers=tutor).json()
    client.patch(f"/interesses/{interesse['id']}", json={"status": "aprovado"}, headers=abrigo)

    apoiador = criar_apoiador(client)
    n = client.post("/necessidades", json={"item": "Ração", "quantidade": 5}, headers=abrigo).json()
    d = client.post("/doacoes", json={"necessidade_id": n["id"], "quantidade": 3}, headers=apoiador["headers"]).json()
    client.patch(f"/doacoes/{d['id']}", json={"status": "confirmada"}, headers=abrigo)
    return {"admin": admin, "abrigo": abrigo, "abrigo_id": abrigo_aprovado["id"], "tutor": tutor, "animal": animal}


# ---------- histórico (RF-39) ----------

def test_acoes_sensiveis_ficam_no_historico_com_quem_fez(client, cenario):
    itens = client.get("/admin/logs", headers=cenario["admin"]).json()["itens"]
    acoes = [i["acao"] for i in itens]
    for esperada in ["abrigo.verificado", "animal.cadastrado", "interesse.registrado", "interesse.aprovado",
                     "necessidade.publicada", "doacao.registrada", "doacao.confirmada", "conta.criada"]:
        assert esperada in acoes, esperada
    aprovacao = next(i for i in itens if i["acao"] == "interesse.aprovado")
    assert aprovacao["usuario_email"] == "abrigo@exemplo.com" and aprovacao["rotulo"] == "Adoção aprovada"
    assert aprovacao["detalhes"]["animal"] == "Thor"


def test_historico_filtra_por_acao_pesquisa_e_periodo(client, cenario):
    h = cenario["admin"]
    so_doacoes = client.get("/admin/logs", params={"acao": "doacao.confirmada"}, headers=h).json()
    assert so_doacoes["total"] == 1 and so_doacoes["itens"][0]["detalhes"]["item"] == "Ração"
    por_pessoa = client.get("/admin/logs", params={"q": "petshop@"}, headers=h).json()["itens"]
    assert por_pessoa and {i["usuario_email"] for i in por_pessoa} == {"petshop@exemplo.com"}
    assert client.get("/admin/logs", params={"q": "Thor"}, headers=h).json()["total"] >= 2  # pesquisa também nos detalhes
    ontem = (HOJE - datetime.timedelta(days=2)).isoformat()
    assert client.get("/admin/logs", params={"de": ontem, "ate": ontem}, headers=h).json()["total"] == 0
    assert client.get("/admin/logs", params={"de": HOJE.isoformat(), "ate": ontem}, headers=h).status_code == 422


def test_falha_na_acao_nao_deixa_log(client, cenario):
    antes = client.get("/admin/logs", headers=cenario["admin"]).json()["total"]
    animal = cenario["animal"]
    r = client.patch(f"/interesses/{999}", json={"status": "aprovado"}, headers=cenario["abrigo"])
    assert r.status_code == 404
    r = client.post(f"/animais/{animal['id']}/interesses", json={}, headers=cenario["tutor"])
    assert r.status_code == 409  # animal já em processo
    assert client.get("/admin/logs", headers=cenario["admin"]).json()["total"] == antes


def test_historico_e_exportacoes_da_administracao_sao_so_do_admin(client, cenario):
    for rota in ["/admin/logs", "/admin/logs.csv", "/admin/painel", "/admin/usuarios", "/admin/relatorios/abrigos.csv"]:
        assert client.get(rota, headers=cenario["abrigo"]).status_code == 403, rota
        assert client.get(rota).status_code == 401, rota


def test_historico_em_csv(client, cenario):
    r = client.get("/admin/logs.csv", params={"acao": "interesse.aprovado"}, headers=cenario["admin"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    texto = r.content.decode("utf-8")
    assert texto.startswith("﻿Data;Quem;E-mail;")  # BOM: o Excel abre com acentos
    linhas = texto.strip().splitlines()
    assert len(linhas) == 2 and "Adoção aprovada" in linhas[1]
    assert linhas[1].endswith(";Animal: Thor")  # detalhes legíveis, sem id interno e sem ";" dentro do campo


# ---------- painel da administração (RF-38) ----------

def test_painel_da_administracao_resume_os_tres_modulos(client, cenario):
    p = client.get("/admin/painel", headers=cenario["admin"]).json()
    contas = {c["chave"]: c["total"] for c in p["contas"]}
    assert contas == {"admin": 1, "abrigo": 1, "tutor": 1, "apoiador": 1}
    assert p["no_periodo"]["adocoes_aprovadas"] == 1 and p["no_periodo"]["doacoes_confirmadas"] == 1
    assert p["no_periodo"]["interesses"] == 1 and p["agora"]["necessidades_abertas"] == 1
    assert {a["chave"]: a["total"] for a in p["animais"]} == {"em_processo": 1}
    assert len(p["serie_mensal"]) == 6 and p["serie_mensal"][-1]["mes"] == HOJE.strftime("%Y-%m")
    assert p["serie_mensal"][-1]["interesses"] == 1 and p["serie_mensal"][-1]["doacoes_confirmadas"] == 1
    assert p["ultimas_acoes"][0]["acao"] == "doacao.confirmada"


def test_csv_de_abrigos_com_o_movimento_do_periodo(client, cenario):
    texto = client.get("/admin/relatorios/abrigos.csv", headers=cenario["admin"]).content.decode("utf-8")
    [cabecalho_csv, linha] = texto.strip().splitlines()
    assert "Adoções aprovadas no período" in cabecalho_csv
    assert linha.split(";")[:8] == ["Abrigo Patinhas", "Joana Protetora", "abrigo@exemplo.com", "Verificado", "0", "1", "1", "1"]  # 3 de 5: a necessidade segue aberta


# ---------- pesquisa de contas ----------

def test_pesquisa_de_contas_por_nome_email_abrigo_e_tipo(client, cenario):
    h = cenario["admin"]
    assert [u["email"] for u in client.get("/admin/usuarios", params={"q": "patinhas"}, headers=h).json()] == ["abrigo@exemplo.com"]
    assert client.get("/admin/usuarios", params={"q": "patinhas"}, headers=h).json()[0]["detalhe"] == "Abrigo Patinhas (verificado)"
    assert [u["tipo_conta"] for u in client.get("/admin/usuarios", params={"tipo": "apoiador"}, headers=h).json()] == ["apoiador"]
    assert client.get("/admin/usuarios", params={"q": "ninguém-com-esse-nome"}, headers=h).json() == []


# ---------- relatório do abrigo (RF-40) ----------

def test_relatorio_do_abrigo(client, cenario):
    r = client.get("/relatorios/abrigo", headers=cenario["abrigo"]).json()
    assert r["adocoes_aprovadas"] == 1
    assert r["tempo_medio_adocao_dias"] == 10  # entrou há 10 dias (calendário) e foi aprovado hoje
    assert r["origem_interessados"] == [{"chave": "Olinda", "total": 1}]
    assert {c["chave"]: c["total"] for c in r["interesses"]} == {"aprovado": 1}
    assert r["por_apoiador"] == [{"nome": "Pet Shop Amigo", "doacoes": 1, "quantidade": 3}]
    assert r["por_item"] == [{"chave": "Ração", "total": 3}]
    assert {c["chave"]: c["total"] for c in r["necessidades"]} == {"aberta": 1}


def test_cada_abrigo_ve_so_o_seu_relatorio(client, cenario):
    client.post("/auth/cadastro", json=dados_abrigo(email="outro@exemplo.com"))
    outro = cabecalho(client, "outro@exemplo.com")
    r = client.get("/relatorios/abrigo", headers=outro).json()
    assert r["adocoes_aprovadas"] == 0 and r["interesses"] == [] and r["por_apoiador"] == []
    assert client.get("/relatorios/abrigo", headers=cenario["tutor"]).status_code == 403
    historico = client.get("/relatorios/abrigo/historico", headers=outro).json()["itens"]
    assert {i["usuario_email"] for i in historico} == {"outro@exemplo.com"}


def test_exportacoes_do_abrigo(client, cenario):
    h = cenario["abrigo"]
    interesses = client.get("/relatorios/abrigo/interesses.csv", headers=h).content.decode("utf-8").strip().splitlines()
    assert interesses[0].endswith("Cidade;Situação") and "Thor;Maria Tutora;tutor@exemplo.com" in interesses[1] and interesses[1].endswith("Olinda;Aprovado")
    doacoes = client.get("/relatorios/abrigo/doacoes.csv", headers=h).content.decode("utf-8").strip().splitlines()
    assert "Pet Shop Amigo;petshop;Ração;3;Confirmada" in doacoes[1]
    animais = client.get("/relatorios/abrigo/animais.csv", headers=h).content.decode("utf-8").strip().splitlines()
    entrada = (HOJE - datetime.timedelta(days=10)).strftime("%d/%m/%Y")
    assert animais[1].startswith("Thor;cao;medio;macho;;em_processo;" + entrada)  # a data do dia não volta um dia


def test_troca_de_senha_e_conta_ficam_no_historico_sem_dados_sensiveis(client, cenario):
    client.post("/usuarios/eu/senha", json={"senha_atual": SENHA, "senha_nova": "OutraSenha123!"}, headers=cenario["tutor"])
    [log] = client.get("/admin/logs", params={"acao": "conta.senha_trocada"}, headers=cenario["admin"]).json()["itens"]
    assert log["detalhes"] == {} and "Senha" not in str(log["detalhes"])


def test_navegador_consegue_ler_o_nome_do_arquivo_csv(client, cenario):
    # A interface roda em outra origem: o CORS precisa expor o Content-Disposition (achado no teste E2E).
    r = client.get("/admin/logs.csv", headers={**cenario["admin"], "Origin": "http://localhost:5173"})
    assert "content-disposition" in r.headers.get("access-control-expose-headers", "").lower()


def test_listas_longas_vem_resumidas_e_completas_sob_demanda(client, cenario):
    # Situação real: muitos itens doados. O relatório traz só os 5 primeiros e o total; o resto vem em páginas.
    apoiador = cabecalho(client, "petshop@exemplo.com")
    for i in range(6):
        d = client.post("/doacoes", json={"abrigo_id": cenario["abrigo_id"], "item": f"Item {i}", "quantidade": 10 - i}, headers=apoiador).json()
        client.patch(f"/doacoes/{d['id']}", json={"status": "confirmada"}, headers=cenario["abrigo"])
    r = client.get("/relatorios/abrigo", headers=cenario["abrigo"]).json()
    assert len(r["por_item"]) == 5 and r["totais_listas"]["itens"] == 7  # 6 novos + a Ração
    assert r["por_item"][0] == {"chave": "Item 0", "total": 10}

    pagina = client.get("/relatorios/abrigo/lista/itens", params={"limite": 4, "deslocamento": 4}, headers=cenario["abrigo"]).json()
    assert pagina["total"] == 7 and pagina["colunas"] == ["Item", "Quantidade"]
    assert [linha["rotulo"] for linha in pagina["itens"]] == ["Item 4", "Item 5", "Ração"]  # 6, 5 e 3 unidades
    apoiadores = client.get("/relatorios/abrigo/lista/apoiadores", headers=cenario["abrigo"]).json()
    assert apoiadores["itens"] == [{"rotulo": "Pet Shop Amigo", "valores": [7, 48]}]
    assert client.get("/relatorios/abrigo/lista/outra", headers=cenario["abrigo"]).status_code == 422
    assert client.get("/relatorios/abrigo/lista/itens", headers=cenario["tutor"]).status_code == 403
