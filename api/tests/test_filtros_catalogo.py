"""RF-14: filtros combinados do catálogo (sexo, idade, castrado, vacinado, convivência)."""
from tests.conftest import dados_animal


def nomes(client, **filtros) -> set[str]:
    return {a["nome"] for a in client.get("/animais", params=filtros).json()}


def test_filtros_combinados(client, abrigo_aprovado):
    h = abrigo_aprovado["headers"]
    for nome, extra in [
        ("Filhote", {"sexo": "femea", "idade_estimada_meses": 4, "vacinado": True, "convivencia_criancas": True}),
        ("Adulto", {"sexo": "macho", "idade_estimada_meses": 36, "castrado": True, "vacinado": True, "convivencia_outros_animais": True}),
        ("Idoso", {"sexo": "macho", "idade_estimada_meses": 120, "castrado": True, "convivencia_criancas": False}),
        ("SemIdade", {"sexo": "femea"}),
    ]:
        assert client.post("/animais", json=dados_animal(nome=nome, **extra), headers=h).status_code == 201

    assert nomes(client, sexo="femea") == {"Filhote", "SemIdade"}
    assert nomes(client, idade="filhote") == {"Filhote"}
    assert nomes(client, idade="adulto") == {"Adulto"}
    assert nomes(client, idade="idoso") == {"Idoso"}
    assert nomes(client, castrado="true") == {"Adulto", "Idoso"}
    assert nomes(client, convive_criancas="true") == {"Filhote"}  # "Não informado" não entra
    assert nomes(client, convive_animais="true") == {"Adulto"}
    # Combinados: todos valem ao mesmo tempo.
    assert nomes(client, sexo="macho", castrado="true", vacinado="true") == {"Adulto"}
    assert nomes(client, sexo="femea", idade="adulto") == set()
    assert client.get("/animais", params={"idade": "bebe"}).status_code == 422
