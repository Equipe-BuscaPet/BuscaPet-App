"""Núcleo OpenCL na administração: estado, benchmark (RF-29) e indexação das fotos sem descritor (RF-21)."""
import io

from PIL import Image

from tests.conftest import cabecalho, dados_tutor


def _perda(client) -> None:
    client.post("/auth/cadastro", json=dados_tutor())
    tutor = cabecalho(client, "tutor@exemplo.com")
    foto = io.BytesIO()
    Image.new("RGB", (32, 32), (180, 120, 60)).save(foto, format="JPEG")
    client.post("/perdidos", headers=tutor, files=[("fotos", ("a.jpg", foto.getvalue(), "image/jpeg"))], data={
        "especie": "cao", "porte": "medio", "cor_predominante": "caramelo", "sexo": "macho",
        "latitude": "-8.05", "longitude": "-34.9", "data_desaparecimento": "2026-10-01",
    })


def test_sem_nucleo_o_painel_mostra_que_esta_fora_e_o_benchmark_responde_503(client, admin):
    _perda(client)
    estado = client.get("/admin/nucleo", headers=admin).json()
    assert estado["no_ar"] is False and estado["fotos"] == 1 and estado["sem_descritor"] == 1
    r = client.get("/admin/nucleo/benchmark?etapa=busca&n=100", headers=admin)
    assert r.status_code == 503 and "não respondeu" in r.json()["detail"]


def test_com_nucleo_indexa_o_que_falta_e_roda_o_benchmark(client, admin, monkeypatch):
    _perda(client)  # foto gravada com o núcleo fora do ar
    from app.core import nucleo
    from tests.conftest import NucleoFalso

    monkeypatch.setattr(nucleo, "_pedir", NucleoFalso().pedir)
    assert client.get("/admin/nucleo", headers=admin).json()["no_ar"] is True
    r = client.post("/admin/nucleo/indexar", headers=admin).json()
    assert (r["indexadas"], r["com_descritor"], r["sem_descritor"]) == (1, 1, 0)
    b = client.get("/admin/nucleo/benchmark?etapa=lote&n=500", headers=admin).json()
    assert b["etapa"] == "lote" and b["speedup"] > 1 and b["resultados_iguais"] is True


def test_benchmark_limita_o_tamanho(client, admin):
    r = client.get("/admin/nucleo/benchmark?etapa=extracao&n=5000", headers=admin)
    assert r.status_code == 422 and "2.000" in r.json()["detail"]
    assert client.get("/admin/nucleo/benchmark?etapa=outra", headers=admin).status_code == 422
