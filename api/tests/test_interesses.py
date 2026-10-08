"""Sprint 4 — módulo Adoção: interesse do tutor, resposta do abrigo, mudança de situação do animal."""
from sqlalchemy import select

from app.models.transversais import Notificacao
from tests.conftest import cabecalho, dados_abrigo, dados_animal, dados_tutor


def _cenario(client):
    """Abrigo (não verificado, com telefone) com um animal, e dois tutores."""
    client.post("/auth/cadastro", json=dados_abrigo(telefone="81988887777"))
    h_abrigo = cabecalho(client, "abrigo@exemplo.com")
    animal = client.post("/animais", json=dados_animal(nome="Thor"), headers=h_abrigo).json()
    client.post("/auth/cadastro", json=dados_tutor("ana@exemplo.com", nome="Ana"))
    client.post("/auth/cadastro", json=dados_tutor("bia@exemplo.com", nome="Bia"))
    return {
        "abrigo": h_abrigo,
        "ana": cabecalho(client, "ana@exemplo.com"),
        "bia": cabecalho(client, "bia@exemplo.com"),
        "animal_id": animal["id"],
    }


def _registrar(client, c, quem="ana", **corpo):
    return client.post(f"/animais/{c['animal_id']}/interesses", json=corpo, headers=c[quem])


# ---------- registrar ----------

def test_so_tutor_registra_interesse(client):
    c = _cenario(client)
    url = f"/animais/{c['animal_id']}/interesses"
    assert client.post(url, json={}).status_code == 401
    assert client.post(url, json={}, headers=c["abrigo"]).status_code == 403


def test_tutor_registra_interesse_e_so_entao_recebe_o_contato_do_abrigo(client):
    c = _cenario(client)
    resp = _registrar(client, c, mensagem="  Tenho quintal e já criei cães.  ")
    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["status"] == "aguardando"
    assert corpo["mensagem"] == "Tenho quintal e já criei cães."
    assert corpo["abrigo_telefone"] == "81988887777"
    assert corpo["animal_nome"] == "Thor"
    # A ficha pública do animal não traz o telefone do abrigo.
    assert "abrigo_telefone" not in client.get(f"/animais/{c['animal_id']}").json()


def test_interesse_repetido_e_recusado_com_mensagem_clara(client):
    c = _cenario(client)
    assert _registrar(client, c).status_code == 201
    resp = _registrar(client, c)
    assert resp.status_code == 409
    assert "já registrou interesse" in resp.json()["detail"]


def test_interesse_valida_animal_e_tamanho_da_mensagem(client):
    c = _cenario(client)
    assert client.post("/animais/9999/interesses", json={}, headers=c["ana"]).status_code == 404
    assert _registrar(client, c, mensagem="x" * 501).status_code == 422


def test_nao_ha_interesse_em_animal_que_nao_esta_disponivel(client):
    c = _cenario(client)
    client.patch(f"/animais/{c['animal_id']}", json={"status": "adotado"}, headers=c["abrigo"])
    resp = _registrar(client, c)
    assert resp.status_code == 409 and "não está mais disponível" in resp.json()["detail"]


def test_nao_ha_interesse_em_animal_de_abrigo_suspenso(client, admin):
    c = _cenario(client)
    abrigo_id = client.get(f"/animais/{c['animal_id']}").json()["abrigo_id"]
    client.patch(f"/admin/abrigos/{abrigo_id}/validacao", json={"status": "rejeitado"}, headers=admin)
    assert _registrar(client, c).status_code == 404


# ---------- listas ----------

def test_tutor_ve_so_os_seus_interesses_e_abrigo_ve_os_recebidos_com_contato(client):
    c = _cenario(client)
    _registrar(client, c, "ana", mensagem="Sou a Ana")
    _registrar(client, c, "bia")

    meus = client.get("/interesses/meus", headers=c["ana"]).json()
    assert [i["mensagem"] for i in meus] == ["Sou a Ana"]

    recebidos = client.get("/interesses/recebidos", headers=c["abrigo"]).json()
    assert {i["tutor_nome"] for i in recebidos} == {"Ana", "Bia"}
    ana = next(i for i in recebidos if i["tutor_nome"] == "Ana")
    assert ana["tutor_email"] == "ana@exemplo.com" and ana["tutor_telefone"] == "81999990000" and ana["tutor_cidade"] == "Recife"

    assert client.get("/interesses/recebidos?status=aprovado", headers=c["abrigo"]).json() == []
    assert client.get("/interesses/recebidos", headers=c["ana"]).status_code == 403
    assert client.get("/interesses/meus", headers=c["abrigo"]).status_code == 403


def test_abrigo_so_ve_interesses_dos_proprios_animais(client):
    c = _cenario(client)
    _registrar(client, c)
    client.post("/auth/cadastro", json=dados_abrigo("outro@exemplo.com", nome_abrigo="Outro"))
    assert client.get("/interesses/recebidos", headers=cabecalho(client, "outro@exemplo.com")).json() == []


# ---------- decisão do abrigo ----------

def test_abrigo_conversa_e_aprova_e_o_animal_entra_em_processo(client, sessao_factory):
    c = _cenario(client)
    interesse_id = _registrar(client, c).json()["id"]
    url = f"/interesses/{interesse_id}"

    resp = client.patch(url, json={"status": "em_conversa"}, headers=c["abrigo"])
    assert resp.status_code == 200 and resp.json()["status"] == "em_conversa"

    resp = client.patch(url, json={"status": "aprovado"}, headers=c["abrigo"])
    assert resp.status_code == 200 and resp.json()["status"] == "aprovado"
    assert client.get(f"/animais/{c['animal_id']}").json()["status"] == "em_processo"
    assert client.get("/animais").json() == []  # sai do catálogo de disponíveis

    with sessao_factory() as db:
        textos = list(db.scalars(select(Notificacao.mensagem)))
    assert any("tem interesse em adotar Thor" in t for t in textos)  # abrigo avisado
    assert any("aprovou seu interesse" in t for t in textos)  # tutora avisada


def test_so_um_interesse_pode_ser_aprovado_por_animal(client):
    c = _cenario(client)
    ana = _registrar(client, c, "ana").json()["id"]
    bia = _registrar(client, c, "bia").json()["id"]
    assert client.patch(f"/interesses/{ana}", json={"status": "aprovado"}, headers=c["abrigo"]).status_code == 200
    resp = client.patch(f"/interesses/{bia}", json={"status": "aprovado"}, headers=c["abrigo"])
    assert resp.status_code == 409 and "não está disponível" in resp.json()["detail"]
    # Recusar o outro continua possível.
    assert client.patch(f"/interesses/{bia}", json={"status": "recusado"}, headers=c["abrigo"]).status_code == 200


def test_interesse_encerrado_nao_muda_mais_e_status_invalido_e_recusado(client):
    c = _cenario(client)
    interesse_id = _registrar(client, c).json()["id"]
    url = f"/interesses/{interesse_id}"
    assert client.patch(url, json={"status": "aguardando"}, headers=c["abrigo"]).status_code == 422
    assert client.patch(url, json={"status": "recusado"}, headers=c["abrigo"]).status_code == 200
    assert client.patch(url, json={"status": "em_conversa"}, headers=c["abrigo"]).status_code == 409


def test_so_o_abrigo_dono_decide(client):
    c = _cenario(client)
    interesse_id = _registrar(client, c).json()["id"]
    url = f"/interesses/{interesse_id}"
    assert client.patch(url, json={"status": "recusado"}, headers=c["ana"]).status_code == 403
    client.post("/auth/cadastro", json=dados_abrigo("outro@exemplo.com", nome_abrigo="Outro"))
    assert client.patch(url, json={"status": "recusado"}, headers=cabecalho(client, "outro@exemplo.com")).status_code == 404


# ---------- desistência ----------

def test_tutor_pode_desistir_enquanto_nao_for_encerrado(client):
    c = _cenario(client)
    interesse_id = _registrar(client, c).json()["id"]
    assert client.delete(f"/interesses/{interesse_id}", headers=c["bia"]).status_code == 404  # não é dela
    assert client.delete(f"/interesses/{interesse_id}", headers=c["ana"]).status_code == 204
    assert client.get("/interesses/meus", headers=c["ana"]).json() == []
    assert _registrar(client, c).status_code == 201  # pode registrar de novo

    novo_id = client.get("/interesses/meus", headers=c["ana"]).json()[0]["id"]
    client.patch(f"/interesses/{novo_id}", json={"status": "aprovado"}, headers=c["abrigo"])
    assert client.delete(f"/interesses/{novo_id}", headers=c["ana"]).status_code == 409


def test_excluir_animal_leva_os_interesses_junto(client):
    c = _cenario(client)
    _registrar(client, c)
    assert client.delete(f"/animais/{c['animal_id']}", headers=c["abrigo"]).status_code == 204
    assert client.get("/interesses/meus", headers=c["ana"]).json() == []
