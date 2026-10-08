"""Entregas 4 e 5 da Sprint 3: controle de perfis e CRUD de animais."""

from tests.conftest import cabecalho, dados_abrigo, dados_animal, dados_tutor


# ---------- controle de perfis ----------

def test_visitante_nao_cadastra_animal(client):
    assert client.post("/animais", json=dados_animal()).status_code == 401


def test_tutor_nao_cadastra_animal(client):
    client.post("/auth/cadastro", json=dados_tutor())
    resp = client.post("/animais", json=dados_animal(), headers=cabecalho(client, "tutor@exemplo.com"))
    assert resp.status_code == 403


def test_abrigo_nao_verificado_ja_cadastra_animal_e_o_selo_aparece_depois(client, admin):
    r = client.post("/auth/cadastro", json=dados_abrigo())
    h = cabecalho(client, "abrigo@exemplo.com")
    resp = client.post("/animais", json=dados_animal(), headers=h)
    assert resp.status_code == 201
    animal_id = resp.json()["id"]
    assert resp.json()["abrigo_verificado"] is False
    client.patch(f"/admin/abrigos/{r.json()['id']}/validacao", json={"status": "aprovado"}, headers=admin)
    assert client.get(f"/animais/{animal_id}").json()["abrigo_verificado"] is True


def test_abrigo_suspenso_nao_cadastra_nem_exclui_animal(client, admin):
    r = client.post("/auth/cadastro", json=dados_abrigo())
    h = cabecalho(client, "abrigo@exemplo.com")
    animal_id = client.post("/animais", json=dados_animal(), headers=h).json()["id"]
    client.patch(f"/admin/abrigos/{r.json()['id']}/validacao", json={"status": "rejeitado"}, headers=admin)
    resp = client.post("/animais", json=dados_animal(), headers=h)
    assert resp.status_code == 403 and "suspenso" in resp.json()["detail"]
    assert client.delete(f"/animais/{animal_id}", headers=h).status_code == 403


def test_so_admin_valida_abrigo(client):
    r = client.post("/auth/cadastro", json=dados_abrigo())
    h = cabecalho(client, "abrigo@exemplo.com")
    url = f"/admin/abrigos/{r.json()['id']}/validacao"
    assert client.patch(url, json={"status": "aprovado"}).status_code == 401
    assert client.patch(url, json={"status": "aprovado"}, headers=h).status_code == 403
    assert client.get("/admin/abrigos", headers=h).status_code == 403


def test_admin_lista_fila_e_aprova_ou_rejeita(client, admin):
    r = client.post("/auth/cadastro", json=dados_abrigo())
    fila = client.get("/admin/abrigos", headers=admin).json()
    assert [u["id"] for u in fila] == [r.json()["id"]]
    resp = client.patch(f"/admin/abrigos/{r.json()['id']}/validacao", json={"status": "rejeitado"}, headers=admin)
    assert resp.status_code == 200 and resp.json()["perfil"]["status_validacao"] == "rejeitado"
    assert client.get("/admin/abrigos", headers=admin).json() == []
    # O admin pode tirar o selo (voltar para "não verificado").
    resp = client.patch(f"/admin/abrigos/{r.json()['id']}/validacao", json={"status": "pendente"}, headers=admin)
    assert resp.status_code == 200 and resp.json()["perfil"]["status_validacao"] == "pendente"
    assert client.patch(f"/admin/abrigos/{r.json()['id']}/validacao", json={"status": "qualquer"}, headers=admin).status_code == 422


# ---------- CRUD ----------

def test_crud_completo_do_animal(client, abrigo_aprovado):
    h = abrigo_aprovado["headers"]

    criado = client.post("/animais", json=dados_animal(raca_aproximada="SRD", data_entrada="2026-10-01"), headers=h)
    assert criado.status_code == 201
    animal = criado.json()
    assert animal["nome"] == "Thor" and animal["status"] == "disponivel"
    assert animal["nome_abrigo"] == "Abrigo Patinhas"
    assert animal["abrigo_id"] == abrigo_aprovado["id"]

    lido = client.get(f"/animais/{animal['id']}")
    assert lido.status_code == 200 and lido.json()["raca_aproximada"] == "SRD"

    atualizado = client.patch(f"/animais/{animal['id']}", json={"nome": "Thor II", "vacinado": True, "status": "em_processo"}, headers=h)
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Thor II" and atualizado.json()["vacinado"] is True
    assert client.get(f"/animais/{animal['id']}").json()["status"] == "em_processo"

    assert client.delete(f"/animais/{animal['id']}", headers=h).status_code == 204
    assert client.get(f"/animais/{animal['id']}").status_code == 404
    assert client.delete(f"/animais/{animal['id']}", headers=h).status_code == 404


def test_cadastro_de_animal_valida_dados(client, abrigo_aprovado):
    h = abrigo_aprovado["headers"]
    assert client.post("/animais", json=dados_animal(especie="dragao"), headers=h).status_code == 422
    assert client.post("/animais", json=dados_animal(porte="gigante"), headers=h).status_code == 422
    assert client.post("/animais", json=dados_animal(idade_estimada_meses=-1), headers=h).status_code == 422
    assert client.post("/animais", json={"nome": "Sem espécie"}, headers=h).status_code == 422


def test_atualizar_nao_aceita_trocar_o_dono(client, abrigo_aprovado):
    h = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(), headers=h).json()
    assert client.patch(f"/animais/{animal['id']}", json={"abrigo_id": 999}, headers=h).status_code == 422
    assert client.patch(f"/animais/{animal['id']}", json={"nome": None}, headers=h).status_code == 422


def test_abrigo_so_mexe_nos_proprios_animais(client, abrigo_aprovado, admin):
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    outro = client.post("/auth/cadastro", json=dados_abrigo("outro@exemplo.com", nome_abrigo="Outro Abrigo")).json()
    client.patch(f"/admin/abrigos/{outro['id']}/validacao", json={"status": "aprovado"}, headers=admin)
    h2 = cabecalho(client, "outro@exemplo.com")

    assert client.patch(f"/animais/{animal['id']}", json={"nome": "Roubado"}, headers=h2).status_code == 403
    assert client.delete(f"/animais/{animal['id']}", headers=h2).status_code == 403
    assert client.get(f"/animais/{animal['id']}").json()["nome"] == "Thor"
    # E a lista "meus" só mostra os do próprio abrigo.
    assert client.get("/animais/meus", headers=h2).json() == []
    assert len(client.get("/animais/meus", headers=abrigo_aprovado["headers"]).json()) == 1


def test_admin_pode_excluir_animal_por_moderacao_mas_nao_editar(client, abrigo_aprovado, admin):
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    assert client.patch(f"/animais/{animal['id']}", json={"nome": "X"}, headers=admin).status_code == 403
    assert client.delete(f"/animais/{animal['id']}", headers=admin).status_code == 204


# ---------- visibilidade pública ----------

def test_catalogo_publico_mostra_abrigo_nao_verificado_com_o_selo_correto(client, abrigo_aprovado):
    client.post("/animais", json=dados_animal(nome="Verificado"), headers=abrigo_aprovado["headers"])
    client.post("/auth/cadastro", json=dados_abrigo("novo@exemplo.com", nome_abrigo="Novo"))
    client.post("/animais", json=dados_animal(nome="NaoVerificado"), headers=cabecalho(client, "novo@exemplo.com"))

    selos = {a["nome"]: a["abrigo_verificado"] for a in client.get("/animais").json()}
    assert selos == {"Verificado": True, "NaoVerificado": False}


def test_animal_de_abrigo_rejeitado_some_do_publico_mas_nao_do_dono(client, abrigo_aprovado, admin):
    h = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(), headers=h).json()
    client.patch(f"/admin/abrigos/{abrigo_aprovado['id']}/validacao", json={"status": "rejeitado"}, headers=admin)
    assert client.get("/animais").json() == []
    assert client.get(f"/animais/{animal['id']}").status_code == 404
    assert client.get(f"/animais/{animal['id']}", headers=h).status_code == 200  # o dono ainda enxerga


def test_animal_some_do_publico_quando_o_abrigo_desativa_a_conta(client, abrigo_aprovado):
    client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"])
    client.delete("/usuarios/eu", headers=abrigo_aprovado["headers"])
    assert client.get("/animais").json() == []


def test_listagem_filtros_busca_e_paginacao(client, abrigo_aprovado):
    h = abrigo_aprovado["headers"]
    client.post("/animais", json=dados_animal(nome="Thor", especie="cao", porte="grande"), headers=h)
    client.post("/animais", json=dados_animal(nome="Mia", especie="gato", porte="pequeno", raca_aproximada="Siamês"), headers=h)
    adotado = client.post("/animais", json=dados_animal(nome="Rex", especie="cao"), headers=h).json()
    client.patch(f"/animais/{adotado['id']}", json={"status": "adotado"}, headers=h)

    def nomes(resposta):
        return sorted(a["nome"] for a in resposta.json())

    assert nomes(client.get("/animais")) == ["Mia", "Thor"]  # padrão: só disponíveis
    assert nomes(client.get("/animais?status=adotado")) == ["Rex"]
    assert nomes(client.get("/animais?especie=gato")) == ["Mia"]
    assert nomes(client.get("/animais?porte=grande")) == ["Thor"]
    assert nomes(client.get("/animais?busca=siam")) == ["Mia"]
    assert len(client.get("/animais?limite=1").json()) == 1
    assert client.get("/animais?limite=1&deslocamento=1").json()[0]["nome"] in {"Mia", "Thor"}
    assert client.get("/animais?limite=1000").status_code == 422


def test_rota_meus_nao_e_confundida_com_id(client, abrigo_aprovado):
    assert client.get("/animais/meus", headers=abrigo_aprovado["headers"]).status_code == 200
    assert client.get("/animais/meus").status_code == 401
