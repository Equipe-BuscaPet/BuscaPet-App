"""ARMAZENAMENTO_FOTOS=banco: o JPEG vive na tabela fotos_arquivos (hospedagem gratuita, sem disco permanente)."""
import pytest
from sqlalchemy import func, select

from app.core import fotos as armazenamento
from app.core.config import settings
from app.models.animal import FotoArquivo
from tests.conftest import dados_animal
from tests.test_fotos_animal import arquivos


@pytest.fixture(autouse=True)
def modo_banco(monkeypatch, sessao_factory, tmp_path):
    monkeypatch.setattr(settings, "armazenamento_fotos", "banco")
    monkeypatch.setattr(armazenamento, "SessionLocal", sessao_factory)
    return tmp_path / "fotos-teste"


def _total(sessao_factory) -> int:
    with sessao_factory() as db:
        return db.scalar(select(func.count()).select_from(FotoArquivo))


def test_foto_enviada_e_servida_sem_tocar_no_disco(client, abrigo_aprovado, sessao_factory, modo_banco):
    h = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(), headers=h).json()
    r = client.post(f"/animais/{animal['id']}/fotos", files=arquivos(2), headers=h)
    assert r.status_code == 201, r.text
    url = r.json()["fotos"][0]["url"]
    assert _total(sessao_factory) == 2 and not modo_banco.exists()
    servida = client.get(url)
    assert servida.status_code == 200 and servida.headers["content-type"] == "image/jpeg"
    assert servida.content[:2] == b"\xff\xd8"  # começa como JPEG


def test_apagar_a_foto_remove_o_arquivo_do_banco(client, abrigo_aprovado, sessao_factory):
    h = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(), headers=h).json()
    fotos = client.post(f"/animais/{animal['id']}/fotos", files=arquivos(1), headers=h).json()["fotos"]
    assert client.delete(f"/animais/{animal['id']}/fotos/{fotos[0]['id']}", headers=h).status_code in (200, 204)
    assert _total(sessao_factory) == 0
    assert client.get(fotos[0]["url"]).status_code == 404


def test_nome_invalido_ou_inexistente_da_404(client):
    assert client.get("/fotos/" + "0" * 32 + ".jpg").status_code == 404
    assert armazenamento.ler("../../etc/passwd") is None
