"""Sprint 4 — mapa público de abrigos."""
from app.core.geo import distancia_km
from tests.conftest import cabecalho, dados_abrigo, dados_animal, dados_tutor

# Pontos reais do Recife, para as distâncias fazerem sentido.
BOA_VIAGEM = {"latitude": -8.1180, "longitude": -34.9000}
CENTRO = {"latitude": -8.0630, "longitude": -34.8710}
OLINDA = {"latitude": -8.0089, "longitude": -34.8553}


def _abrigo(client, email, nome, ponto, **extra):
    resp = client.post("/auth/cadastro", json=dados_abrigo(email, nome_abrigo=nome, **ponto, **extra))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_distancia_conhecida_entre_dois_pontos():
    # Praça do Marco Zero (Recife) a Olinda (Alto da Sé): cerca de 7 km em linha reta.
    d = distancia_km(-8.0631, -34.8711, -8.0089, -34.8553)
    assert 5.5 < d < 7.5
    assert distancia_km(-8.0, -34.0, -8.0, -34.0) == 0


def test_mapa_e_publico_e_lista_abrigos_sem_dados_de_conta(client):
    _abrigo(client, "a@exemplo.com", "Abrigo A", CENTRO, telefone="81911112222")
    resp = client.get("/abrigos")
    assert resp.status_code == 200
    abrigo = resp.json()[0]
    assert abrigo["nome_abrigo"] == "Abrigo A" and abrigo["telefone"] == "81911112222"
    assert abrigo["verificado"] is False and abrigo["animais_disponiveis"] == 0 and abrigo["distancia_km"] is None
    assert "email" not in abrigo and "senha_hash" not in abrigo


def test_conta_so_de_abrigos_aparece_no_mapa(client):
    client.post("/auth/cadastro", json=dados_tutor())
    assert client.get("/abrigos").json() == []


def test_conta_quantos_animais_disponiveis_cada_abrigo_tem(client):
    _abrigo(client, "a@exemplo.com", "Abrigo A", CENTRO)
    h = cabecalho(client, "a@exemplo.com")
    client.post("/animais", json=dados_animal(nome="Um"), headers=h)
    client.post("/animais", json=dados_animal(nome="Dois"), headers=h)
    adotado = client.post("/animais", json=dados_animal(nome="Tres"), headers=h).json()
    client.patch(f"/animais/{adotado['id']}", json={"status": "adotado"}, headers=h)
    assert client.get("/abrigos").json()[0]["animais_disponiveis"] == 2


def test_ordena_por_distancia_e_aplica_o_raio(client):
    _abrigo(client, "olinda@exemplo.com", "Olinda", OLINDA)
    _abrigo(client, "centro@exemplo.com", "Centro", CENTRO)
    _abrigo(client, "boa@exemplo.com", "Boa Viagem", BOA_VIAGEM)

    # Quem está no Marco Zero (centro do Recife):
    perto = client.get("/abrigos", params={"lat": -8.0631, "lng": -34.8711}).json()
    assert [a["nome_abrigo"] for a in perto] == ["Centro", "Olinda", "Boa Viagem"]
    assert perto[0]["distancia_km"] < 1

    # Distâncias reais: Centro 0,0 km, Olinda 6,3 km, Boa Viagem 6,9 km.
    assert [a["nome_abrigo"] for a in client.get("/abrigos", params={"lat": -8.0631, "lng": -34.8711, "raio_km": 1}).json()] == ["Centro"]
    limitado = client.get("/abrigos", params={"lat": -8.0631, "lng": -34.8711, "raio_km": 6.6}).json()
    assert [a["nome_abrigo"] for a in limitado] == ["Centro", "Olinda"]


def test_valida_os_parametros_com_mensagens_claras(client):
    assert client.get("/abrigos", params={"lat": -8.0}).status_code == 422
    resp = client.get("/abrigos", params={"raio_km": 5})
    assert resp.status_code == 422 and "posição" in resp.json()["detail"]
    assert client.get("/abrigos", params={"lat": 95, "lng": 0}).status_code == 422
    assert client.get("/abrigos", params={"lat": 0, "lng": 0, "raio_km": 0}).status_code == 422


def test_abrigo_suspenso_ou_desativado_some_do_mapa_e_o_selo_aparece(client, admin):
    suspenso = _abrigo(client, "s@exemplo.com", "Suspenso", CENTRO)
    verificado = _abrigo(client, "v@exemplo.com", "Verificado", OLINDA)
    desativado = _abrigo(client, "d@exemplo.com", "Desativado", BOA_VIAGEM)
    client.patch(f"/admin/abrigos/{suspenso}/validacao", json={"status": "rejeitado"}, headers=admin)
    client.patch(f"/admin/abrigos/{verificado}/validacao", json={"status": "aprovado"}, headers=admin)
    client.delete("/usuarios/eu", headers=cabecalho(client, "d@exemplo.com"))
    assert desativado  # só para deixar claro de quem é a conta desativada

    lista = client.get("/abrigos").json()
    assert [(a["nome_abrigo"], a["verificado"]) for a in lista] == [("Verificado", True)]
