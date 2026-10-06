"""Entregas 2 e 3 da Sprint 3: cadastro de usuários e login."""
from tests.conftest import CNPJ_VALIDO, SENHA, cabecalho, dados_abrigo, dados_tutor


def test_cadastro_tutor_persiste_e_nao_devolve_senha(client):
    resp = client.post("/auth/cadastro", json=dados_tutor("Maria@Exemplo.com"))
    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["email"] == "maria@exemplo.com"  # normalizado
    assert corpo["tipo_conta"] == "tutor"
    assert corpo["perfil"] == {"telefone": "81999990000", "cidade": "Recife"}
    assert "senha" not in corpo and "senha_hash" not in corpo


def test_cadastro_abrigo_nasce_pendente(client):
    resp = client.post("/auth/cadastro", json=dados_abrigo())
    assert resp.status_code == 201
    assert resp.json()["perfil"]["status_validacao"] == "pendente"


def test_cadastro_apoiador_normaliza_cnpj(client):
    resp = client.post("/auth/cadastro", json={
        "tipo_conta": "apoiador", "nome": "Pet Shop Amigo", "email": "loja@exemplo.com", "senha": SENHA,
        "cnpj": CNPJ_VALIDO, "tipo_estabelecimento": "petshop", "endereco": "Av. Brasil, 1",
    })
    assert resp.status_code == 201
    assert resp.json()["perfil"]["cnpj"] == "11222333000181"


def test_cadastro_apoiador_recusa_cnpj_invalido(client):
    resp = client.post("/auth/cadastro", json={
        "tipo_conta": "apoiador", "nome": "Loja", "email": "loja@exemplo.com", "senha": SENHA,
        "cnpj": "11.111.111/1111-11", "tipo_estabelecimento": "petshop", "endereco": "Av. Brasil, 1",
    })
    assert resp.status_code == 422


def test_cadastro_nao_permite_virar_admin(client):
    resp = client.post("/auth/cadastro", json={**dados_tutor(), "tipo_conta": "admin"})
    assert resp.status_code == 422


def test_cadastro_email_duplicado(client):
    assert client.post("/auth/cadastro", json=dados_tutor()).status_code == 201
    resp = client.post("/auth/cadastro", json=dados_tutor("TUTOR@exemplo.com"))
    assert resp.status_code == 409


def test_cadastro_valida_senha_e_email(client):
    assert client.post("/auth/cadastro", json=dados_tutor(senha="curta")).status_code == 422
    assert client.post("/auth/cadastro", json=dados_tutor(email="isso-nao-e-email")).status_code == 422


def test_cadastro_abrigo_exige_localizacao(client):
    dados = dados_abrigo()
    del dados["latitude"]
    assert client.post("/auth/cadastro", json=dados).status_code == 422


def test_login_devolve_token_que_funciona(client):
    client.post("/auth/cadastro", json=dados_tutor())
    resp = client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": SENHA})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    eu = client.get("/auth/eu", headers=cabecalho(client, "tutor@exemplo.com"))
    assert eu.status_code == 200 and eu.json()["email"] == "tutor@exemplo.com"


def test_login_recusa_senha_errada_e_email_inexistente_com_a_mesma_mensagem(client):
    client.post("/auth/cadastro", json=dados_tutor())
    errada = client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": "errada-errada"})
    inexistente = client.post("/auth/login", data={"username": "ninguem@exemplo.com", "password": SENHA})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()


def test_rota_protegida_exige_token_valido(client):
    assert client.get("/auth/eu").status_code == 401
    assert client.get("/auth/eu", headers={"Authorization": "Bearer lixo"}).status_code == 401
