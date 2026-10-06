"""CRUD de contas: consultar, atualizar, trocar senha e excluir (desativar)."""
from tests.conftest import SENHA, cabecalho, dados_abrigo, dados_tutor


def test_atualizar_perfil_do_tutor(client):
    client.post("/auth/cadastro", json=dados_tutor())
    h = cabecalho(client, "tutor@exemplo.com")
    resp = client.patch("/usuarios/eu", json={"cidade": "Olinda", "nome": "Maria da Silva"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["perfil"]["cidade"] == "Olinda"
    assert client.get("/usuarios/eu", headers=h).json()["nome"] == "Maria da Silva"


def test_atualizar_recusa_campo_de_outro_tipo_de_conta(client):
    client.post("/auth/cadastro", json=dados_tutor())
    h = cabecalho(client, "tutor@exemplo.com")
    resp = client.patch("/usuarios/eu", json={"nome_abrigo": "Meu abrigo"}, headers=h)
    assert resp.status_code == 422


def test_atualizar_nao_deixa_limpar_campo_obrigatorio(client):
    client.post("/auth/cadastro", json=dados_abrigo())
    h = cabecalho(client, "abrigo@exemplo.com")
    assert client.patch("/usuarios/eu", json={"nome_abrigo": None}, headers=h).status_code == 422


def test_abrigo_nao_consegue_se_aprovar_sozinho(client):
    client.post("/auth/cadastro", json=dados_abrigo())
    h = cabecalho(client, "abrigo@exemplo.com")
    resp = client.patch("/usuarios/eu", json={"status_validacao": "aprovado"}, headers=h)
    assert resp.status_code == 422  # campo nem existe no schema de atualização


def test_trocar_senha(client):
    client.post("/auth/cadastro", json=dados_tutor())
    h = cabecalho(client, "tutor@exemplo.com")
    assert client.post("/usuarios/eu/senha", json={"senha_atual": "errada-errada", "senha_nova": "nova-senha-123"}, headers=h).status_code == 400
    assert client.post("/usuarios/eu/senha", json={"senha_atual": SENHA, "senha_nova": "nova-senha-123"}, headers=h).status_code == 204
    assert client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": SENHA}).status_code == 401
    assert client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": "nova-senha-123"}).status_code == 200


def test_excluir_conta_desativa_e_bloqueia_login_e_token(client):
    client.post("/auth/cadastro", json=dados_tutor())
    h = cabecalho(client, "tutor@exemplo.com")
    assert client.delete("/usuarios/eu", headers=h).status_code == 204
    assert client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": SENHA}).status_code == 401
    assert client.get("/usuarios/eu", headers=h).status_code == 401  # token antigo deixa de valer


def test_email_de_conta_desativada_continua_ocupado(client):
    client.post("/auth/cadastro", json=dados_tutor())
    client.delete("/usuarios/eu", headers=cabecalho(client, "tutor@exemplo.com"))
    assert client.post("/auth/cadastro", json=dados_tutor()).status_code == 409


def test_admin_nao_pode_ser_excluido_pela_api(client, admin):
    assert client.delete("/usuarios/eu", headers=admin).status_code == 403
