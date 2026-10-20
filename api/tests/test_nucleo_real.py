"""Integração com o núcleo OpenCL DE VERDADE (serviço em C rodando no Docker), com fotos reais.

Opcional: só roda com a variável NUCLEO_REAL_URL apontando para o núcleo no ar, por exemplo
    docker compose up -d nucleo-opencl
    NUCLEO_REAL_URL=http://127.0.0.1:8001 pytest tests/test_nucleo_real.py
Sem ela, o teste é pulado (a CI da API não sobe o núcleo; o núcleo tem os próprios testes no `make teste`).
"""
import io
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageEnhance, ImageOps

from app.core import nucleo
from app.core.config import settings
from tests.conftest import cabecalho, dados_tutor

URL = os.environ.get("NUCLEO_REAL_URL")
FIXTURES = Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "fixtures"

pytestmark = pytest.mark.skipif(not URL, reason="defina NUCLEO_REAL_URL para testar contra o núcleo de verdade")


@pytest.fixture(autouse=True)
def nucleo_de_verdade(monkeypatch, nucleo_desligado):
    monkeypatch.setattr(settings, "nucleo_opencl_url", URL)
    monkeypatch.setattr(nucleo, "_pedir", _pedir_real)


def _pedir_real(metodo, caminho, timeout, **kwargs):
    try:
        r = httpx.request(metodo, settings.nucleo_opencl_url.rstrip("/") + caminho, timeout=timeout, **kwargs)
    except httpx.HTTPError as erro:
        raise nucleo.NucleoIndisponivel(str(erro)) from erro
    assert r.status_code == 200, r.text
    return r.json()


def jpeg(img: Image.Image) -> bytes:
    saida = io.BytesIO()
    img.convert("RGB").save(saida, format="JPEG", quality=90)
    return saida.getvalue()


def test_foto_real_do_mesmo_cao_e_alta_e_o_gato_e_baixa(client):
    cao = Image.open(FIXTURES / "cachorro-caramelo.jpg")
    gato = Image.open(FIXTURES / "gato-cinza.jpg")
    client.post("/auth/cadastro", json=dados_tutor(email="maria@exemplo.com"))
    client.post("/auth/cadastro", json=dados_tutor(email="vizinho@exemplo.com"))
    maria, vizinho = cabecalho(client, "maria@exemplo.com"), cabecalho(client, "vizinho@exemplo.com")

    base = {"especie": "cao", "porte": "medio", "cor_predominante": "caramelo", "latitude": "-8.0476", "longitude": "-34.8771"}
    perdido = client.post("/perdidos", data={**base, "sexo": "macho", "data_desaparecimento": "2026-10-01"},
                          files=[("fotos", ("cao.jpg", jpeg(cao), "image/jpeg"))], headers=maria).json()
    # o mesmo cão em outra foto: espelhada, mais escura e recortada (como seria uma foto tirada na rua)
    w, h = cao.size
    na_rua = ImageEnhance.Brightness(ImageOps.mirror(cao).crop((int(w * .08), 0, w, int(h * .92)))).enhance(0.7)
    visto = client.post("/avistamentos", data={**base, "data_avistamento": "2026-10-05"},
                        files=[("fotos", ("visto.jpg", jpeg(na_rua), "image/jpeg"))], headers=vizinho).json()
    outro = client.post("/avistamentos", data={**base, "data_avistamento": "2026-10-05"},
                        files=[("fotos", ("gato.jpg", jpeg(gato), "image/jpeg"))], headers=vizinho).json()

    r = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}").json()
    assert r["comparacao_por_foto"] is True and r["modo"] == "opencl"
    graus = {c["id"]: c["grau"] for c in r["candidatos"]}
    assert graus[visto["id"]] == "alta", r
    assert graus[outro["id"]] == "baixa", r
    assert [c["id"] for c in r["candidatos"]][0] == visto["id"]

    sequencial = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}&modo=sequencial").json()
    assert [c["id"] for c in sequencial["candidatos"]] == [c["id"] for c in r["candidatos"]]  # mesmo ranking (RF-29)
