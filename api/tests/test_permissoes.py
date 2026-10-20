"""Matriz de permissões (Sprint 8, controle de permissões): cada rota × cada perfil.

"Permitido" = a API não barra por perfil (pode responder 200, 201, 404 ou 422, conforme os dados enviados);
"barrado" = 401 para quem não entrou e 403 para perfil sem acesso. A mesma tabela está no documento da Sprint 8.
"""
import pytest

from tests.conftest import CNPJ_VALIDO, SENHA, cabecalho, dados_animal, dados_tutor

PERFIS = ["visitante", "tutor", "abrigo", "apoiador", "admin"]
LOGADOS = {"tutor", "abrigo", "apoiador", "admin"}
TODOS = set(PERFIS)

# (método, rota, quem pode, corpo JSON). {animal} é um animal do abrigo do cenário.
MATRIZ = [
    ("GET", "/animais", TODOS, None),
    ("GET", "/abrigos", TODOS, None),
    ("GET", "/perdidos", TODOS, None),
    ("GET", "/necessidades", TODOS, None),
    ("GET", "/apoiadores/ranking", TODOS, None),
    ("GET", "/usuarios/eu", LOGADOS, None),
    ("GET", "/notificacoes", LOGADOS, None),
    ("POST", "/avistamentos", LOGADOS, None),
    ("POST", "/animais", {"abrigo"}, {"nome": "Rex", "especie": "cao", "porte": "medio", "sexo": "macho"}),
    ("GET", "/animais/meus", {"abrigo"}, None),
    ("GET", "/interesses/recebidos", {"abrigo"}, None),
    ("POST", "/necessidades", {"abrigo"}, {"item": "Ração", "quantidade": 1}),
    ("GET", "/doacoes/recebidas", {"abrigo"}, None),
    ("GET", "/relatorios/abrigo", {"abrigo"}, None),
    ("POST", "/animais/{animal}/interesses", {"tutor"}, {}),
    ("GET", "/interesses/meus", {"tutor"}, None),
    ("POST", "/perdidos", {"tutor"}, None),
    ("POST", "/doacoes", {"apoiador"}, {"abrigo_id": 0, "item": "Ração", "quantidade": 1}),
    ("GET", "/doacoes/minhas", {"apoiador"}, None),
    ("POST", "/animais/{animal}/denuncias", {"tutor", "apoiador"}, {"motivo": "Anúncio com cobrança de taxa."}),
    ("GET", "/admin/painel", {"admin"}, None),
    ("GET", "/admin/abrigos", {"admin"}, None),
    ("GET", "/admin/logs", {"admin"}, None),
    ("GET", "/admin/usuarios", {"admin"}, None),
    ("GET", "/admin/denuncias", {"admin"}, None),
]


@pytest.fixture()
def contas(client, admin, abrigo_aprovado) -> dict:
    client.post("/auth/cadastro", json=dados_tutor())
    client.post("/auth/cadastro", json={
        "tipo_conta": "apoiador", "nome": "Loja", "email": "loja@exemplo.com", "senha": SENHA,
        "cnpj": CNPJ_VALIDO, "tipo_estabelecimento": "petshop", "endereco": "Av. Brasil, 1",
    })
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    return {
        "cabecalhos": {
            "visitante": {}, "tutor": cabecalho(client, "tutor@exemplo.com"), "abrigo": abrigo_aprovado["headers"],
            "apoiador": cabecalho(client, "loja@exemplo.com"), "admin": admin,
        },
        "animal": animal["id"],
    }


@pytest.mark.parametrize("metodo, rota, permitidos, corpo", MATRIZ, ids=[f"{m} {r}" for m, r, _, _ in MATRIZ])
def test_matriz_de_permissoes(client, contas, metodo, rota, permitidos, corpo):
    url = rota.format(animal=contas["animal"])
    for perfil in PERFIS:
        r = client.request(metodo, url, json=corpo, headers=contas["cabecalhos"][perfil])
        if perfil in permitidos:
            assert r.status_code not in (401, 403), f"{perfil} deveria poder: {metodo} {url} → {r.status_code} {r.text}"
        else:
            esperado = 401 if perfil == "visitante" else 403
            assert r.status_code == esperado, f"{perfil} deveria ser barrado: {metodo} {url} → {r.status_code}"
