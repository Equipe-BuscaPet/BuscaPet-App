"""RF-41: denúncia de anúncio e moderação; e a revisão de regras da Sprint 8 (interesses encerrados)."""
import pytest

from tests.conftest import cabecalho, dados_animal, dados_tutor

MOTIVO = "Estão pedindo dinheiro pela adoção, parece venda."


@pytest.fixture()
def anuncio(client, abrigo_aprovado) -> dict:
    return client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()


def tutor(client, email: str) -> dict:
    client.post("/auth/cadastro", json=dados_tutor(email=email))
    return cabecalho(client, email)


def notificacoes(client, h, tipo) -> list[str]:
    return [n["mensagem"] for n in client.get("/notificacoes", headers=h).json() if n["referencia_tipo"] == tipo]


def test_qualquer_conta_denuncia_uma_vez_e_o_admin_e_avisado(client, anuncio, admin, abrigo_aprovado):
    t = tutor(client, "t1@exemplo.com")
    r = client.post(f"/animais/{anuncio['id']}/denuncias", json={"motivo": MOTIVO}, headers=t)
    assert r.status_code == 201, r.text
    assert client.post(f"/animais/{anuncio['id']}/denuncias", json={"motivo": MOTIVO}, headers=t).status_code == 409
    assert notificacoes(client, admin, "denuncia") == ["Nova denúncia sobre o anúncio de Thor (Abrigo Patinhas)."]
    [fila] = client.get("/admin/denuncias", headers=admin).json()
    assert fila["motivo"] == MOTIVO and fila["denuncias_do_animal"] == 1


def test_quem_nao_pode_denunciar(client, anuncio, admin, abrigo_aprovado):
    url = f"/animais/{anuncio['id']}/denuncias"
    assert client.post(url, json={"motivo": MOTIVO}).status_code == 401
    assert client.post(url, json={"motivo": MOTIVO}, headers=abrigo_aprovado["headers"]).status_code == 403  # o próprio abrigo
    assert client.post(url, json={"motivo": MOTIVO}, headers=admin).status_code == 403
    r = client.post(url, json={"motivo": "ruim"}, headers=tutor(client, "t1@exemplo.com"))
    assert r.status_code == 422  # motivo curto demais
    assert client.post("/animais/999/denuncias", json={"motivo": MOTIVO}, headers=tutor(client, "t2@exemplo.com")).status_code == 404


def _denunciar(client, anuncio, email):
    h = tutor(client, email)
    return client.post(f"/animais/{anuncio['id']}/denuncias", json={"motivo": MOTIVO}, headers=h).json()["id"], h


def test_ignorar_avisa_quem_denunciou_e_o_anuncio_continua(client, anuncio, admin):
    did, h = _denunciar(client, anuncio, "t1@exemplo.com")
    r = client.patch(f"/admin/denuncias/{did}", json={"decisao": "ignorado"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "ignorado"
    assert "não encontrou irregularidade" in notificacoes(client, h, "denuncia")[0]
    assert [a["id"] for a in client.get("/animais").json()] == [anuncio["id"]]
    assert client.patch(f"/admin/denuncias/{did}", json={"decisao": "removido"}, headers=admin).status_code == 409


def test_advertir_avisa_o_abrigo_com_a_observacao(client, anuncio, admin, abrigo_aprovado):
    did, _ = _denunciar(client, anuncio, "t1@exemplo.com")
    client.patch(f"/admin/denuncias/{did}", json={"decisao": "advertido", "observacao": "Não cobre taxa de adoção."}, headers=admin)
    [aviso] = notificacoes(client, abrigo_aprovado["headers"], "animal")
    assert aviso.startswith("Advertência da administração") and aviso.endswith("Observação: Não cobre taxa de adoção.")


def test_remover_tira_do_ar_resolve_todas_e_encerra_interesses(client, anuncio, admin, abrigo_aprovado):
    d1, h1 = _denunciar(client, anuncio, "t1@exemplo.com")
    d2, _ = _denunciar(client, anuncio, "t2@exemplo.com")
    interessado = tutor(client, "t3@exemplo.com")
    client.post(f"/animais/{anuncio['id']}/interesses", json={}, headers=interessado)

    r = client.patch(f"/admin/denuncias/{d1}", json={"decisao": "removido"}, headers=admin)
    assert r.status_code == 200
    assert client.get("/admin/denuncias", headers=admin).json() == []  # a segunda denúncia foi resolvida junto
    assert {d["id"] for d in client.get("/admin/denuncias", params={"status": "removido"}, headers=admin).json()} == {d1, d2}
    assert client.get("/animais").json() == [] and client.get(f"/animais/{anuncio['id']}").status_code == 404
    [meu] = client.get("/animais/meus", headers=abrigo_aprovado["headers"]).json()
    assert meu["removido_em"] is not None  # o abrigo continua vendo, marcado como removido
    [interesse] = client.get("/interesses/meus", headers=interessado).json()
    assert interesse["status"] == "recusado"
    assert "anúncio removido pela administração" in notificacoes(client, interessado, "interesse")[-1]
    assert "anúncio foi removido" in notificacoes(client, h1, "denuncia")[0]


def test_banir_suspende_o_abrigo_e_tira_todos_os_anuncios_do_ar(client, anuncio, admin, abrigo_aprovado):
    client.post("/animais", json=dados_animal(nome="Mel"), headers=abrigo_aprovado["headers"])
    did, _ = _denunciar(client, anuncio, "t1@exemplo.com")
    client.patch(f"/admin/denuncias/{did}", json={"decisao": "banido"}, headers=admin)
    assert client.get("/animais").json() == []  # o abrigo suspenso some do catálogo inteiro
    assert client.get("/admin/abrigos", params={"status": "rejeitado"}, headers=admin).json()[0]["id"] == abrigo_aprovado["id"]
    acoes = [log["acao"] for log in client.get("/admin/logs", headers=admin).json()["itens"]]
    assert "denuncia.banido" in acoes and "abrigo.suspenso" in acoes


def test_so_admin_modera(client, anuncio, abrigo_aprovado):
    did, h = _denunciar(client, anuncio, "t1@exemplo.com")
    assert client.get("/admin/denuncias", headers=h).status_code == 403
    assert client.patch(f"/admin/denuncias/{did}", json={"decisao": "ignorado"}, headers=abrigo_aprovado["headers"]).status_code == 403


# ---------- revisão de regras: animal que sai de vez encerra os interesses abertos ----------

def test_animal_adotado_por_fora_encerra_os_interesses_que_esperavam_resposta(client, anuncio, abrigo_aprovado):
    h_abrigo = abrigo_aprovado["headers"]
    t1, t2 = tutor(client, "t1@exemplo.com"), tutor(client, "t2@exemplo.com")
    i1 = client.post(f"/animais/{anuncio['id']}/interesses", json={}, headers=t1).json()
    client.post(f"/animais/{anuncio['id']}/interesses", json={}, headers=t2)
    client.patch(f"/interesses/{i1['id']}", json={"status": "em_conversa"}, headers=h_abrigo)

    client.patch(f"/animais/{anuncio['id']}", json={"status": "adotado"}, headers=h_abrigo)
    for h in (t1, t2):
        [i] = client.get("/interesses/meus", headers=h).json()
        assert i["status"] == "recusado"
        assert notificacoes(client, h, "interesse")[0] == "Thor não está mais disponível para adoção (foi adotado). Seu interesse foi encerrado."


def test_interesse_aprovado_nao_e_mexido_quando_o_animal_vira_adotado(client, anuncio, abrigo_aprovado):
    h_abrigo = abrigo_aprovado["headers"]
    t1 = tutor(client, "t1@exemplo.com")
    i1 = client.post(f"/animais/{anuncio['id']}/interesses", json={}, headers=t1).json()
    client.patch(f"/interesses/{i1['id']}", json={"status": "aprovado"}, headers=h_abrigo)
    client.patch(f"/animais/{anuncio['id']}", json={"status": "adotado"}, headers=h_abrigo)
    assert client.get("/interesses/meus", headers=t1).json()[0]["status"] == "aprovado"


def test_animal_que_volta_a_ficar_disponivel_desfaz_a_aprovacao(client, anuncio, abrigo_aprovado):
    # Antes: o aprovado continuava "aprovado" e o abrigo conseguia aprovar um segundo interesse.
    h_abrigo = abrigo_aprovado["headers"]
    t1, t2 = tutor(client, "t1@exemplo.com"), tutor(client, "t2@exemplo.com")
    i1 = client.post(f"/animais/{anuncio['id']}/interesses", json={}, headers=t1).json()
    i2 = client.post(f"/animais/{anuncio['id']}/interesses", json={}, headers=t2).json()
    client.patch(f"/interesses/{i1['id']}", json={"status": "aprovado"}, headers=h_abrigo)

    client.patch(f"/animais/{anuncio['id']}", json={"status": "disponivel"}, headers=h_abrigo)  # a adoção não deu certo
    assert client.get("/interesses/meus", headers=t1).json()[0]["status"] == "recusado"
    assert "não foi concluída" in notificacoes(client, t1, "interesse")[0]
    assert client.patch(f"/interesses/{i2['id']}", json={"status": "aprovado"}, headers=h_abrigo).status_code == 200
    aprovados = [i for i in client.get("/interesses/recebidos", headers=h_abrigo).json() if i["status"] == "aprovado"]
    assert len(aprovados) == 1  # nunca dois aprovados para o mesmo animal
