"""RF-17: fotos dos animais para adoção (enviar, limite, capa, excluir) e a capa no catálogo."""
import pytest

from app.core.config import settings
from tests.conftest import cabecalho, dados_abrigo, dados_animal, dados_tutor
from tests.test_reencontro import imagem


@pytest.fixture(autouse=True)
def pasta_fotos_temporaria(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "pasta_fotos", tmp_path / "fotos")
    return tmp_path / "fotos"


def arquivos(n: int, formato="JPEG") -> list:
    return [("fotos", (f"foto{i}.jpg", imagem(formato), "image/jpeg")) for i in range(n)]


@pytest.fixture()
def animal(client, abrigo_aprovado) -> dict:
    r = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"])
    assert r.status_code == 201
    return r.json()


def test_abrigo_envia_fotos_e_a_primeira_vira_capa_no_catalogo(client, abrigo_aprovado, animal, pasta_fotos_temporaria):
    r = client.post(f"/animais/{animal['id']}/fotos", files=arquivos(2), headers=abrigo_aprovado["headers"])
    assert r.status_code == 201, r.text
    fotos = r.json()["fotos"]
    assert len(fotos) == 2 and len(list(pasta_fotos_temporaria.iterdir())) == 2
    [no_catalogo] = client.get("/animais").json()
    assert no_catalogo["fotos"][0]["url"] == fotos[0]["url"]
    assert client.get(fotos[0]["url"]).headers["content-type"] == "image/jpeg"


def test_no_maximo_cinco_fotos_por_animal_e_nada_e_gravado_se_passar(client, abrigo_aprovado, animal, pasta_fotos_temporaria):
    h = abrigo_aprovado["headers"]
    assert client.post(f"/animais/{animal['id']}/fotos", files=arquivos(4), headers=h).status_code == 201
    r = client.post(f"/animais/{animal['id']}/fotos", files=arquivos(2), headers=h)
    assert r.status_code == 422 and "no máximo 5 fotos (este já tem 4)" in r.json()["detail"]
    assert len(list(pasta_fotos_temporaria.iterdir())) == 4


def test_arquivo_invalido_nao_grava_nenhuma_foto(client, abrigo_aprovado, animal, pasta_fotos_temporaria):
    files = arquivos(1) + [("fotos", ("texto.jpg", b"isto nao e imagem", "image/jpeg"))]
    r = client.post(f"/animais/{animal['id']}/fotos", files=files, headers=abrigo_aprovado["headers"])
    assert r.status_code == 422 and r.json()["detail"].startswith("Foto 2:")
    assert not pasta_fotos_temporaria.exists() or not any(pasta_fotos_temporaria.iterdir())


def test_so_o_abrigo_dono_mexe_nas_fotos(client, animal, abrigo_aprovado):
    client.post("/auth/cadastro", json=dados_abrigo(email="outro@exemplo.com"))
    assert client.post(f"/animais/{animal['id']}/fotos", files=arquivos(1), headers=cabecalho(client, "outro@exemplo.com")).status_code == 403
    client.post("/auth/cadastro", json=dados_tutor())
    assert client.post(f"/animais/{animal['id']}/fotos", files=arquivos(1), headers=cabecalho(client, "tutor@exemplo.com")).status_code == 403
    assert client.post(f"/animais/{animal['id']}/fotos", files=arquivos(1)).status_code == 401


def test_escolher_capa_e_excluir_foto(client, abrigo_aprovado, animal, pasta_fotos_temporaria):
    h = abrigo_aprovado["headers"]
    a, b, c = client.post(f"/animais/{animal['id']}/fotos", files=arquivos(3), headers=h).json()["fotos"]
    r = client.patch(f"/animais/{animal['id']}/fotos/{c['id']}/capa", headers=h)
    assert [f["id"] for f in r.json()["fotos"]] == [c["id"], a["id"], b["id"]]
    r = client.delete(f"/animais/{animal['id']}/fotos/{a['id']}", headers=h)
    assert [f["id"] for f in r.json()["fotos"]] == [c["id"], b["id"]]
    assert len(list(pasta_fotos_temporaria.iterdir())) == 2  # o arquivo também saiu
    assert client.delete(f"/animais/{animal['id']}/fotos/{a['id']}", headers=h).status_code == 404


def test_excluir_o_animal_apaga_os_arquivos_das_fotos(client, abrigo_aprovado, animal, pasta_fotos_temporaria):
    h = abrigo_aprovado["headers"]
    client.post(f"/animais/{animal['id']}/fotos", files=arquivos(2), headers=h)
    assert client.delete(f"/animais/{animal['id']}", headers=h).status_code == 204
    assert not any(pasta_fotos_temporaria.iterdir())
