"""Animal perdido (RF-19) e avistamento (RF-20): registro com fotos, consulta pública e privacidade."""
import datetime
import io

import pytest
from PIL import Image

from app.core.config import settings
from tests.conftest import cabecalho, dados_tutor

HOJE = datetime.date.today().isoformat()


@pytest.fixture(autouse=True)
def pasta_fotos_temporaria(tmp_path, monkeypatch):
    """As fotos dos testes vão para uma pasta temporária, nunca para api/uploads."""
    monkeypatch.setattr(settings, "pasta_fotos", tmp_path / "fotos")
    return tmp_path / "fotos"


def imagem(formato="JPEG", tamanho=(64, 48), exif_gps=False) -> bytes:
    img = Image.new("RGB", tamanho, (180, 120, 60))
    saida = io.BytesIO()
    if exif_gps:
        exif = Image.Exif()
        exif[0x8825] = {1: "S", 2: (8.0, 3.0, 0.0)}  # bloco GPSInfo, como o de uma foto de celular
        img.save(saida, format=formato, exif=exif)
    else:
        img.save(saida, format=formato)
    return saida.getvalue()


def arquivos(*conteudos: bytes) -> list:
    return [("fotos", (f"foto{i}.jpg", c, "image/jpeg")) for i, c in enumerate(conteudos)]


def campos_perdido(**extra) -> dict:
    return {
        "especie": "cao", "porte": "medio", "cor_predominante": "caramelo", "sexo": "macho",
        "latitude": "-8.047612", "longitude": "-34.877123", "data_desaparecimento": HOJE, **extra,
    }


def campos_avistamento(**extra) -> dict:
    return {
        "especie": "gato", "porte": "pequeno", "cor_predominante": "preto",
        "latitude": "-8.06", "longitude": "-34.88", "data_avistamento": HOJE, **extra,
    }


@pytest.fixture()
def tutor(client) -> dict:
    client.post("/auth/cadastro", json=dados_tutor())
    return cabecalho(client, "tutor@exemplo.com")


@pytest.fixture()
def outro_tutor(client) -> dict:
    client.post("/auth/cadastro", json=dados_tutor(email="outro@exemplo.com"))
    return cabecalho(client, "outro@exemplo.com")


def test_tutor_registra_perdido_com_fotos(client, tutor, pasta_fotos_temporaria):
    r = client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem(), imagem("PNG")), headers=tutor)
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert len(corpo["fotos"]) == 2 and corpo["resolvido"] is False
    assert corpo["latitude"] == -8.047612 and corpo["localizacao_aproximada"] is False  # o autor vê o ponto exato
    assert len(list(pasta_fotos_temporaria.iterdir())) == 2
    foto = client.get(corpo["fotos"][0])
    assert foto.status_code == 200 and foto.headers["content-type"] == "image/jpeg"


def test_visitante_ve_perdido_com_localizacao_aproximada_e_sem_dados_do_tutor(client, tutor):
    criado = client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=tutor).json()
    lista = client.get("/perdidos").json()
    assert [p["id"] for p in lista] == [criado["id"]]
    publico = client.get(f"/perdidos/{criado['id']}").json()
    assert publico["latitude"] == -8.05 and publico["longitude"] == -34.88
    assert publico["localizacao_aproximada"] is True
    assert not {"tutor_id", "email", "telefone", "nome"} & publico.keys()


def test_foto_e_regravada_sem_metadados_gps(client, tutor, pasta_fotos_temporaria):
    original = imagem(exif_gps=True)
    assert Image.open(io.BytesIO(original)).getexif().get(0x8825)  # a foto enviada TEM GPS
    client.post("/perdidos", data=campos_perdido(), files=arquivos(original), headers=tutor)
    gravada = next(pasta_fotos_temporaria.iterdir())
    assert not Image.open(gravada).getexif()  # a guardada não tem nenhum metadado


def test_foto_grande_e_reduzida(client, tutor, pasta_fotos_temporaria):
    client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem(tamanho=(3000, 2000))), headers=tutor)
    assert max(Image.open(next(pasta_fotos_temporaria.iterdir())).size) == 1280


@pytest.mark.parametrize("enviar, trecho", [
    ([], "pelo menos uma foto"),
    ([b"isto nao e uma imagem"], "não é uma imagem válida"),
    ([b"x"] * 6, "no máximo 5 fotos"),
])
def test_fotos_invalidas_sao_recusadas_sem_gravar_nada(client, tutor, pasta_fotos_temporaria, enviar, trecho):
    r = client.post("/perdidos", data=campos_perdido(), files=arquivos(*enviar) or None, headers=tutor)
    assert r.status_code == 422
    assert trecho in str(r.json()["detail"])
    assert client.get("/perdidos").json() == []
    assert not pasta_fotos_temporaria.exists() or not any(pasta_fotos_temporaria.iterdir())


def test_campos_invalidos_viram_erro_de_validacao(client, tutor):
    amanha_e_mais = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    r = client.post("/perdidos", data=campos_perdido(porte="gigante", latitude="200", data_desaparecimento=amanha_e_mais),
                    files=arquivos(imagem()), headers=tutor)
    assert r.status_code == 422
    campos = {e["loc"][-1] for e in r.json()["detail"]}
    assert {"porte", "latitude", "data_desaparecimento"} <= campos


def test_so_tutor_registra_perdido_e_visitante_precisa_logar(client, abrigo_aprovado):
    assert client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem())).status_code == 401
    r = client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=abrigo_aprovado["headers"])
    assert r.status_code == 403


def test_qualquer_conta_logada_registra_avistamento(client, tutor, abrigo_aprovado):
    for headers in (tutor, abrigo_aprovado["headers"]):
        r = client.post("/avistamentos", data=campos_avistamento(), files=arquivos(imagem()), headers=headers)
        assert r.status_code == 201, r.text
    assert client.post("/avistamentos", data=campos_avistamento(), files=arquivos(imagem())).status_code == 401
    publicos = client.get("/avistamentos").json()
    assert len(publicos) == 2 and all(a["localizacao_aproximada"] for a in publicos)


def test_lista_filtra_por_raio_e_ordena_por_distancia(client, tutor):
    perto = campos_avistamento(latitude="-8.05", longitude="-34.90")     # ~0 km da origem
    medio = campos_avistamento(latitude="-8.10", longitude="-34.90")     # ~5,5 km
    longe = campos_avistamento(latitude="-9.00", longitude="-35.50")     # >100 km
    for campos in (longe, perto, medio):
        client.post("/avistamentos", data=campos, files=arquivos(imagem()), headers=tutor)
    r = client.get("/avistamentos", params={"lat": -8.05, "lng": -34.90, "raio_km": 10})
    distancias = [a["distancia_km"] for a in r.json()]
    assert len(distancias) == 2 and distancias == sorted(distancias)
    assert client.get("/avistamentos", params={"raio_km": 10}).status_code == 422


def test_filtro_por_especie(client, tutor):
    client.post("/avistamentos", data=campos_avistamento(especie="gato"), files=arquivos(imagem()), headers=tutor)
    client.post("/avistamentos", data=campos_avistamento(especie="cao", porte="grande"), files=arquivos(imagem()), headers=tutor)
    assert [a["especie"] for a in client.get("/avistamentos", params={"especie": "cao"}).json()] == ["cao"]


def test_meus_registros_e_exclusao_pelo_autor(client, tutor, outro_tutor, pasta_fotos_temporaria):
    criado = client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=tutor).json()
    assert [p["id"] for p in client.get("/perdidos/meus", headers=tutor).json()] == [criado["id"]]
    assert client.get("/perdidos/meus", headers=outro_tutor).json() == []

    assert client.delete(f"/perdidos/{criado['id']}", headers=outro_tutor).status_code == 403
    assert client.delete(f"/perdidos/{criado['id']}", headers=tutor).status_code == 204
    assert client.get(f"/perdidos/{criado['id']}").status_code == 404
    assert not any(pasta_fotos_temporaria.iterdir())  # o arquivo da foto também foi apagado
    assert client.get(criado["fotos"][0]).status_code == 404


def test_admin_pode_excluir_avistamento(client, tutor, admin):
    criado = client.post("/avistamentos", data=campos_avistamento(), files=arquivos(imagem()), headers=tutor).json()
    assert client.delete(f"/avistamentos/{criado['id']}", headers=admin).status_code == 204


def test_rota_de_foto_nao_le_fora_da_pasta(client):
    assert client.get("/fotos/..%2F..%2F.env").status_code == 404
    assert client.get("/fotos/naoexiste.jpg").status_code == 404


# ---------- alerta por proximidade e caso resolvido (RF-25 por distância, RF-28) ----------

ONTEM = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def alertas(client, cabecalho_tutor) -> list[dict]:
    return [n for n in client.get("/notificacoes", headers=cabecalho_tutor).json() if n["referencia_tipo"] == "avistamento"]


def test_avistamento_perto_avisa_o_tutor_da_perda(client, tutor, outro_tutor):
    client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=tutor)  # cão, raio padrão 5 km
    visto = client.post("/avistamentos", data=campos_avistamento(especie="cao"), files=arquivos(imagem()), headers=outro_tutor).json()
    [alerta] = alertas(client, tutor)
    assert alerta["mensagem"] == "Um cão foi avistado a cerca de 1 km de onde o seu animal sumiu. Veja se é ele."
    assert alerta["referencia_id"] == visto["id"]
    assert alerta["destino"] == f"/reencontro/avistamentos/{visto['id']}"
    assert alertas(client, outro_tutor) == []  # quem avistou não recebe nada


@pytest.mark.parametrize("extra", [
    {"especie": "gato"},  # outra espécie
    {"especie": "cao", "latitude": "-8.2", "longitude": "-34.95"},  # ~18 km, fora do raio de 5 km
    {"especie": "cao", "data_avistamento": ONTEM},  # visto antes do dia em que sumiu
], ids=["outra-especie", "fora-do-raio", "antes-de-sumir"])
def test_avistamento_que_nao_combina_nao_gera_alerta(client, tutor, outro_tutor, extra):
    client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=tutor)
    r = client.post("/avistamentos", data=campos_avistamento(**extra), files=arquivos(imagem()), headers=outro_tutor)
    assert r.status_code == 201, r.text
    assert alertas(client, tutor) == []


def test_raio_de_busca_do_tutor_e_respeitado(client, tutor, outro_tutor):
    client.post("/perdidos", data=campos_perdido(raio_busca_km="1"), files=arquivos(imagem()), headers=tutor)
    client.post("/avistamentos", data=campos_avistamento(especie="cao"), files=arquivos(imagem()), headers=outro_tutor)  # ~1,4 km
    assert alertas(client, tutor) == []


def test_tutor_marca_caso_resolvido_e_ele_sai_do_mapa(client, tutor, outro_tutor):
    criado = client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=tutor).json()
    caminho = f"/perdidos/{criado['id']}/resolvido"
    assert client.patch(caminho).status_code == 401
    r = client.patch(caminho, headers=outro_tutor)
    assert r.status_code == 403 and "Só quem registrou" in r.json()["detail"]

    r = client.patch(caminho, headers=tutor)
    assert r.status_code == 200 and r.json()["resolvido"] is True
    assert client.get("/perdidos").json() == []  # sai da lista pública (e, com ela, do mapa)
    assert client.get("/perdidos/meus", headers=tutor).json()[0]["resolvido"] is True  # o tutor continua vendo
    assert client.patch(caminho, headers=tutor).status_code == 409

    client.post("/avistamentos", data=campos_avistamento(especie="cao"), files=arquivos(imagem()), headers=outro_tutor)
    assert alertas(client, tutor) == []  # caso resolvido não gera mais alerta


def test_abrigo_nao_marca_resolvido(client, tutor, abrigo_aprovado):
    criado = client.post("/perdidos", data=campos_perdido(), files=arquivos(imagem()), headers=tutor).json()
    assert client.patch(f"/perdidos/{criado['id']}/resolvido", headers=abrigo_aprovado["headers"]).status_code == 403
    assert client.patch("/perdidos/999/resolvido", headers=tutor).status_code == 404
