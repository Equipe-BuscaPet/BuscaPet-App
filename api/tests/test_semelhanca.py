"""Reencontro por semelhança visual (RF-21 a RF-27) com o núcleo OpenCL imitado por `nucleo_falso`.

Cores das fotos: CARAMELO e CARAMELO_ESCURO caem no mesmo tom do descritor falso (semelhança alta); CINZA cai
em outro (baixa). O descritor de verdade (e a equivalência sequencial × OpenCL) é testado no próprio núcleo.
"""
import datetime
import io

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.reencontro import BuscaSalva, Correspondencia, DescritorVisual
from tests.conftest import cabecalho, dados_animal, dados_tutor

HOJE = datetime.date.today()
CARAMELO, CARAMELO_ESCURO, CINZA = (180, 120, 60), (170, 110, 50), (128, 128, 128)
PERTO = ("-8.0480", "-34.8775")  # ~50 m do ponto da perda
LONGE = ("-8.20", "-34.95")  # ~18 km


def foto(cor) -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", (64, 48), cor).save(saida, format="JPEG")
    return saida.getvalue()


def enviar(*cores) -> list:
    return [("fotos", (f"f{i}.jpg", foto(c), "image/jpeg")) for i, c in enumerate(cores)]


def dia(delta: int) -> str:
    return (HOJE + datetime.timedelta(days=delta)).isoformat()


@pytest.fixture()
def tutora(client):
    client.post("/auth/cadastro", json=dados_tutor(email="maria@exemplo.com"))
    return cabecalho(client, "maria@exemplo.com")


@pytest.fixture()
def vizinho(client):
    client.post("/auth/cadastro", json=dados_tutor(email="vizinho@exemplo.com", nome="Vizinho"))
    return cabecalho(client, "vizinho@exemplo.com")


def registrar_perda(client, tutora, cor=CARAMELO, **extra) -> dict:
    campos = {"especie": "cao", "porte": "medio", "cor_predominante": "caramelo", "sexo": "macho",
              "latitude": "-8.047612", "longitude": "-34.877123", "data_desaparecimento": dia(-3), **extra}
    r = client.post("/perdidos", data=campos, files=enviar(cor), headers=tutora)
    assert r.status_code == 201, r.text
    return r.json()


def registrar_avistamento(client, quem, cor, lugar=PERTO, especie="cao", quando=0, porte="medio", cor_texto="caramelo") -> dict:
    campos = {"especie": especie, "porte": porte, "cor_predominante": cor_texto, "latitude": lugar[0],
              "longitude": lugar[1], "data_avistamento": dia(quando)}
    r = client.post("/avistamentos", data=campos, files=enviar(cor), headers=quem)
    assert r.status_code == 201, r.text
    return r.json()


def notificacoes(client, quem) -> list:
    return client.get("/notificacoes", headers=quem).json()


# ---------- RF-21 e RF-24: descritor na hora e busca salva ----------

def test_perda_nasce_monitorada_e_cada_foto_ganha_descritor(client, tutora, nucleo_falso, sessao_factory):
    perdido = registrar_perda(client, tutora)
    with sessao_factory() as db:
        busca = db.scalar(select(BuscaSalva).where(BuscaSalva.animal_perdido_id == perdido["id"]))
        assert busca is not None and busca.status.value == "monitorando"
        assert len(list(db.scalars(select(DescritorVisual)))) == 1
    assert nucleo_falso.extracoes == 1


def test_sem_nucleo_a_foto_e_gravada_e_o_descritor_vem_depois_na_busca(client, tutora, vizinho, sessao_factory, monkeypatch):
    perdido = registrar_perda(client, tutora)  # núcleo desligado (padrão dos testes)
    with sessao_factory() as db:
        assert list(db.scalars(select(DescritorVisual))) == []
    registrar_avistamento(client, vizinho, CARAMELO)

    from app.core import nucleo
    from tests.conftest import NucleoFalso

    monkeypatch.setattr(nucleo, "_pedir", NucleoFalso().pedir)  # o núcleo voltou
    r = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}").json()
    assert r["comparacao_por_foto"] is True and r["candidatos"][0]["grau"] == "alta"
    with sessao_factory() as db:
        assert len(list(db.scalars(select(DescritorVisual)))) == 2  # calculados na primeira busca


# ---------- RF-22, RF-23: busca de quem perdeu ----------

def test_busca_ordena_por_semelhanca_e_aplica_os_filtros_previos(client, tutora, vizinho, abrigo_aprovado, nucleo_falso):
    perdido = registrar_perda(client, tutora)
    parecido = registrar_avistamento(client, vizinho, CARAMELO_ESCURO)
    diferente = registrar_avistamento(client, vizinho, CINZA)
    registrar_avistamento(client, vizinho, CARAMELO, lugar=LONGE)  # fora do raio de 5 km
    registrar_avistamento(client, vizinho, CARAMELO, quando=-10)  # visto antes de sumir
    registrar_avistamento(client, vizinho, CARAMELO, especie="gato")  # outra espécie
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    client.post(f"/animais/{animal['id']}/fotos", files=enviar(CARAMELO), headers=abrigo_aprovado["headers"])

    r = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["comparacao_por_foto"] is True and corpo["registros_comparados"] == 3
    vistos = [(c["tipo"], c["id"], c["grau"]) for c in corpo["candidatos"]]
    assert set(vistos[:2]) == {("avistamento", parecido["id"], "alta"), ("animal", animal["id"], "alta")}
    assert vistos[2] == ("avistamento", diferente["id"], "baixa")
    animal_out = next(c for c in corpo["candidatos"] if c["tipo"] == "animal")
    assert animal_out["caminho"] == f"/animais/{animal['id']}" and "Abrigo Patinhas" in animal_out["rotulo"]
    assert all(c["distancia_km"] <= 5 for c in corpo["candidatos"])

    # ampliando o raio, o avistamento distante entra
    longe = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}&raio_km=30").json()
    assert longe["registros_comparados"] == 4


def test_filtros_opcionais_de_porte_e_cor(client, tutora, vizinho, nucleo_falso):
    perdido = registrar_perda(client, tutora)
    registrar_avistamento(client, vizinho, CARAMELO, porte="grande")
    registrar_avistamento(client, vizinho, CARAMELO, cor_texto="preto")
    base = f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}"
    assert client.get(base).json()["registros_comparados"] == 2
    assert client.get(base + "&mesmo_porte=true").json()["registros_comparados"] == 1
    assert client.get(base + "&mesma_cor=true").json()["registros_comparados"] == 1
    assert client.get(base + "&mesmo_porte=true&mesma_cor=true").json()["registros_comparados"] == 0


def test_modo_sequencial_vai_para_o_nucleo(client, tutora, vizinho, nucleo_falso):
    perdido = registrar_perda(client, tutora)
    registrar_avistamento(client, vizinho, CARAMELO)
    r = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}&modo=sequencial").json()
    assert r["modo"] == "sequencial"


def test_sem_nucleo_a_busca_avisa_e_lista_por_distancia(client, tutora, vizinho):
    perdido = registrar_perda(client, tutora)
    registrar_avistamento(client, vizinho, CINZA)
    r = client.get(f"/reencontro/semelhantes?origem=perdido&id={perdido['id']}").json()
    assert r["comparacao_por_foto"] is False and "indisponível" in r["motivo"]
    assert [c["grau"] for c in r["candidatos"]] == [None]


def test_registro_inexistente(client):
    assert client.get("/reencontro/semelhantes?origem=perdido&id=999").status_code == 404
    assert client.get("/reencontro/semelhantes?origem=outro&id=1").status_code == 422


# ---------- RF-27: busca inversa ----------

def test_quem_encontrou_compara_contra_os_perdidos(client, tutora, vizinho, nucleo_falso):
    parecida = registrar_perda(client, tutora)
    client.post("/auth/cadastro", json=dados_tutor(email="joao@exemplo.com", nome="João"))
    joao = cabecalho(client, "joao@exemplo.com")
    diferente = registrar_perda(client, joao, cor=CINZA)
    registrar_perda(client, joao, cor=CARAMELO, data_desaparecimento=dia(0), latitude="-8.30")  # longe
    achado = registrar_avistamento(client, vizinho, CARAMELO, quando=-1)

    r = client.get(f"/reencontro/semelhantes?origem=avistamento&id={achado['id']}").json()
    assert [(c["id"], c["grau"]) for c in r["candidatos"]] == [(parecida["id"], "alta"), (diferente["id"], "baixa")]
    assert r["candidatos"][0]["caminho"] == f"/reencontro/perdidos/{parecida['id']}"


# ---------- RF-25: monitoramento contínuo ----------

def test_avistamento_parecido_avisa_o_tutor_com_o_grau_e_fica_registrado(client, tutora, vizinho, nucleo_falso, sessao_factory):
    perdido = registrar_perda(client, tutora)
    av = registrar_avistamento(client, vizinho, CARAMELO_ESCURO)
    [aviso] = notificacoes(client, tutora)
    assert "semelhança alta" in aviso["mensagem"] and aviso["destino"] == f"/reencontro/avistamentos/{av['id']}"
    with sessao_factory() as db:
        [c] = list(db.scalars(select(Correspondencia)))
        assert (c.animal_perdido_id, c.avistamento_id, c.grau_semelhanca.value) == (perdido["id"], av["id"], "alta")


def test_avistamento_perto_mas_diferente_nao_incomoda_o_tutor(client, tutora, vizinho, nucleo_falso):
    registrar_perda(client, tutora)
    registrar_avistamento(client, vizinho, CINZA)
    assert notificacoes(client, tutora) == []


def test_sem_nucleo_o_alerta_volta_a_ser_por_distancia(client, tutora, vizinho):
    registrar_perda(client, tutora)
    registrar_avistamento(client, vizinho, CINZA)
    [aviso] = notificacoes(client, tutora)
    assert "semelhança" not in aviso["mensagem"] and "avistado a menos de 1 km" in aviso["mensagem"]


# ---------- RF-26: alerta ao abrigo ----------

def test_abrigo_cadastra_animal_parecido_e_tutor_e_abrigo_sao_avisados_uma_vez(client, tutora, abrigo_aprovado, nucleo_falso):
    perdido = registrar_perda(client, tutora)
    cab = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(nome="Caramelo"), headers=cab).json()
    client.post(f"/animais/{animal['id']}/fotos", files=enviar(CARAMELO), headers=cab)

    [aviso_tutor] = notificacoes(client, tutora)
    assert "Abrigo Patinhas" in aviso_tutor["mensagem"] and aviso_tutor["destino"] == f"/animais/{animal['id']}"
    [aviso_abrigo] = [n for n in notificacoes(client, cab) if n["referencia_tipo"] == "perdido_semelhante"]
    assert "Caramelo" in aviso_abrigo["mensagem"] and aviso_abrigo["destino"] == f"/reencontro/perdidos/{perdido['id']}"

    client.post(f"/animais/{animal['id']}/fotos", files=enviar(CARAMELO_ESCURO), headers=cab)  # mais uma foto
    assert len(notificacoes(client, tutora)) == 1


def test_animal_diferente_no_abrigo_nao_avisa_ninguem(client, tutora, abrigo_aprovado, nucleo_falso):
    registrar_perda(client, tutora)
    cab = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(), headers=cab).json()
    client.post(f"/animais/{animal['id']}/fotos", files=enviar(CINZA), headers=cab)
    assert notificacoes(client, tutora) == []


# ---------- exclusão com correspondências ----------

def test_registros_com_correspondencia_continuam_podendo_ser_excluidos(client, tutora, vizinho, abrigo_aprovado, nucleo_falso, sessao_factory):
    perdido = registrar_perda(client, tutora)
    av = registrar_avistamento(client, vizinho, CARAMELO)
    cab = abrigo_aprovado["headers"]
    animal = client.post("/animais", json=dados_animal(), headers=cab).json()
    client.post(f"/animais/{animal['id']}/fotos", files=enviar(CARAMELO), headers=cab)
    with sessao_factory() as db:
        assert len(list(db.scalars(select(Correspondencia)))) == 2
    assert client.delete(f"/avistamentos/{av['id']}", headers=vizinho).status_code == 204
    assert client.delete(f"/animais/{animal['id']}", headers=cab).status_code == 204
    assert client.delete(f"/perdidos/{perdido['id']}", headers=tutora).status_code == 204
    with sessao_factory() as db:
        assert list(db.scalars(select(Correspondencia))) == []
