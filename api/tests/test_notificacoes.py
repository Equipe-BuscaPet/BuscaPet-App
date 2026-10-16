"""RF-36 — notificações da própria conta: listar, contar, marcar como lida; cada um só vê as suas."""
from tests.conftest import cabecalho, dados_abrigo, dados_animal, dados_tutor


def _cenario(client):
    """Abrigo com um animal e um tutor que registra interesse (gera uma notificação para o abrigo)."""
    client.post("/auth/cadastro", json=dados_abrigo())
    h_abrigo = cabecalho(client, "abrigo@exemplo.com")
    animal = client.post("/animais", json=dados_animal(nome="Thor"), headers=h_abrigo).json()
    client.post("/auth/cadastro", json=dados_tutor("ana@exemplo.com", nome="Ana"))
    h_tutor = cabecalho(client, "ana@exemplo.com")
    interesse = client.post(f"/animais/{animal['id']}/interesses", json={}, headers=h_tutor).json()
    return {"abrigo": h_abrigo, "tutor": h_tutor, "interesse_id": interesse["id"]}


def test_notificacoes_exigem_login(client):
    assert client.get("/notificacoes").status_code == 401
    assert client.get("/notificacoes/contagem").status_code == 401


def test_abrigo_recebe_aviso_de_interesse_com_destino_para_os_interessados(client):
    c = _cenario(client)
    assert client.get("/notificacoes/contagem", headers=c["abrigo"]).json() == {"nao_lidas": 1}
    [n] = client.get("/notificacoes", headers=c["abrigo"]).json()
    assert n["mensagem"] == "Ana tem interesse em adotar Thor."
    assert n["lida"] is False
    assert n["referencia_tipo"] == "interesse" and n["referencia_id"] == c["interesse_id"]
    assert n["destino"] == "/interessados"
    # O tutor não recebeu nada (quem agiu foi ele).
    assert client.get("/notificacoes", headers=c["tutor"]).json() == []


def test_tutor_recebe_a_resposta_do_abrigo_com_destino_para_meus_interesses(client):
    c = _cenario(client)
    client.patch(f"/interesses/{c['interesse_id']}", json={"status": "em_conversa"}, headers=c["abrigo"])
    [n] = client.get("/notificacoes", headers=c["tutor"]).json()
    assert n["destino"] == "/interesses"


def test_marcar_uma_e_todas_como_lidas(client):
    c = _cenario(client)
    client.post("/auth/cadastro", json=dados_tutor("bia@exemplo.com", nome="Bia"))
    animal_id = client.get("/animais/meus", headers=c["abrigo"]).json()[0]["id"]
    client.post(f"/animais/{animal_id}/interesses", json={}, headers=cabecalho(client, "bia@exemplo.com"))

    lista = client.get("/notificacoes", headers=c["abrigo"]).json()
    assert [n["mensagem"] for n in lista] == ["Bia tem interesse em adotar Thor.", "Ana tem interesse em adotar Thor."]  # mais nova primeiro

    resp = client.patch(f"/notificacoes/{lista[0]['id']}/lida", headers=c["abrigo"])
    assert resp.status_code == 200 and resp.json()["lida"] is True
    assert client.get("/notificacoes/contagem", headers=c["abrigo"]).json() == {"nao_lidas": 1}
    assert len(client.get("/notificacoes?somente_nao_lidas=true", headers=c["abrigo"]).json()) == 1

    assert client.post("/notificacoes/marcar-todas-lidas", headers=c["abrigo"]).status_code == 204
    assert client.get("/notificacoes/contagem", headers=c["abrigo"]).json() == {"nao_lidas": 0}


def test_ninguem_mexe_na_notificacao_de_outra_conta(client):
    c = _cenario(client)
    [n] = client.get("/notificacoes", headers=c["abrigo"]).json()
    resp = client.patch(f"/notificacoes/{n['id']}/lida", headers=c["tutor"])
    assert resp.status_code == 404  # 404, e não 403: não revela que a notificação existe
    client.post("/notificacoes/marcar-todas-lidas", headers=c["tutor"])  # só afeta as do tutor
    assert client.get("/notificacoes/contagem", headers=c["abrigo"]).json() == {"nao_lidas": 1}


def test_abrigo_e_avisado_quando_ganha_ou_perde_o_selo(client, admin):
    client.post("/auth/cadastro", json=dados_abrigo())
    h_abrigo = cabecalho(client, "abrigo@exemplo.com")
    abrigo_id = client.get("/auth/eu", headers=h_abrigo).json()["id"]

    client.patch(f"/admin/abrigos/{abrigo_id}/validacao", json={"status": "aprovado"}, headers=admin)
    client.patch(f"/admin/abrigos/{abrigo_id}/validacao", json={"status": "aprovado"}, headers=admin)  # sem mudança: sem aviso
    [n] = client.get("/notificacoes", headers=h_abrigo).json()
    assert "selo Verificado" in n["mensagem"] and n["destino"] == "/painel"

    client.patch(f"/admin/abrigos/{abrigo_id}/validacao", json={"status": "rejeitado"}, headers=admin)
    assert "suspenso" in client.get("/notificacoes", headers=h_abrigo).json()[0]["mensagem"]


def test_paginacao(client):
    c = _cenario(client)
    assert len(client.get("/notificacoes?limite=1&deslocamento=1", headers=c["abrigo"]).json()) == 0
    assert client.get("/notificacoes?limite=0", headers=c["abrigo"]).status_code == 422
