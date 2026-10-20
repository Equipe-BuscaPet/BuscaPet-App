"""Cliente do núcleo OpenCL (serviço em C, `nucleo-opencl/`) — RF-21, RF-22, RF-25, RF-29.

A API nunca executa OpenCL: ela abre a foto (Pillow), manda os pixels para o núcleo e guarda o descritor que
volta. Na hora da busca, manda os descritores e recebe as notas de semelhança já ordenadas.

Se o núcleo estiver fora do ar, nada quebra: a foto fica sem descritor (é calculado depois, na primeira busca
ou pelo script `python -m app.scripts.indexar_fotos`) e a busca avisa que a comparação por foto está indisponível.
"""
import base64
import json
import logging
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import fotos as armazenamento
from app.core.config import settings
from app.models.animal import Foto
from app.models.reencontro import DescritorVisual

log = logging.getLogger(__name__)

VERSAO = "v1"
DIM = 224
COR, TEXTURA = slice(0, 208), slice(208, 218)
PROPORCOES = slice(218, DIM)
LADO_ENVIO = 512  # o núcleo reduz para 128×128; mandar mais que isso só pesa na rede


class NucleoIndisponivel(Exception):
    """O núcleo não respondeu (fora do ar, tempo esgotado ou resposta inválida)."""


def _url(caminho: str) -> str:
    return settings.nucleo_opencl_url.rstrip("/") + caminho


def _pedir(metodo: str, caminho: str, timeout: float, **kwargs) -> dict:
    try:
        resposta = httpx.request(metodo, _url(caminho), timeout=timeout, **kwargs)
    except httpx.HTTPError as erro:
        raise NucleoIndisponivel(f"núcleo fora do ar ({erro.__class__.__name__})") from erro
    if resposta.status_code != 200:
        raise NucleoIndisponivel(f"núcleo respondeu {resposta.status_code}: {resposta.text[:200]}")
    return resposta.json()


def saude() -> dict:
    return _pedir("GET", "/saude", timeout=3)


def extrair(arquivo: Path) -> list[float]:
    """Descritor (224 números) de uma foto gravada em disco."""
    with Image.open(arquivo) as img:
        img = img.convert("RGB")
        img.thumbnail((LADO_ENVIO, LADO_ENVIO))
        corpo = {"largura": img.width, "altura": img.height, "pixels": base64.b64encode(img.tobytes()).decode()}
    return _pedir("POST", "/extrair-descritor", timeout=15, json=corpo)["descritor"]


def comparar(consultas: list[list[float]], candidatos: list[tuple[int, list[float]]], modo: str = "opencl") -> dict:
    """Notas de cada consulta contra cada candidato. Resposta: {"resultados": [[{id, nota, grau}, ...] por consulta],
    "tempos": {...}, "modo": ...}, cada lista já em ordem do mais parecido para o menos."""
    corpo = {"consultas": consultas, "candidatos": [{"id": i, "descritor": d} for i, d in candidatos], "modo": modo}
    return _pedir("POST", "/comparar", timeout=60, json=corpo)


def benchmark(etapa: str, n: int) -> dict:
    return _pedir("GET", "/benchmark", timeout=300, params={"etapa": etapa, "n": n})


# ---------- descritores guardados no banco ----------

def vetor(d: DescritorVisual) -> list[float]:
    return json.loads(d.histograma_cor) + json.loads(d.textura) + json.loads(d.proporcoes)


def indexar(db: Session, fotos: list[Foto], repassar_falha: bool = False) -> int:
    """Calcula e grava o descritor das fotos que ainda não têm (RF-21). Devolve quantas foram indexadas.

    Foto sem arquivo é pulada. Se o núcleo cair, para (e, com `repassar_falha`, levanta NucleoIndisponivel —
    a busca precisa saber; o cadastro não). Faz commit próprio do que conseguiu.
    """
    if not fotos:
        return 0
    ja_tem = set(db.scalars(select(DescritorVisual.foto_id).where(DescritorVisual.foto_id.in_([f.id for f in fotos]))))
    feitas = 0
    for foto in fotos:
        if foto.id in ja_tem:
            continue
        arquivo = armazenamento.caminho(armazenamento.nome_da_url(foto.url))
        if arquivo is None or not arquivo.exists():
            continue
        try:
            d = extrair(arquivo)
        except NucleoIndisponivel as erro:
            log.warning("Descritor da foto %s não calculado: %s", foto.id, erro)
            if feitas:
                db.commit()
            if repassar_falha:
                raise
            return feitas  # se o núcleo caiu, não adianta tentar as próximas agora
        db.add(DescritorVisual(
            foto_id=foto.id, histograma_cor=json.dumps(d[COR]), textura=json.dumps(d[TEXTURA]),
            proporcoes=json.dumps(d[PROPORCOES]), versao_algoritmo=VERSAO,
        ))
        feitas += 1
    if feitas:
        db.commit()
    return feitas


def descritores(db: Session, fotos: list[Foto]) -> dict[int, list[float]]:
    """foto.id → descritor; calcula antes os que faltarem (NucleoIndisponivel se o núcleo estiver fora)."""
    indexar(db, fotos, repassar_falha=True)
    linhas = db.scalars(select(DescritorVisual).where(DescritorVisual.foto_id.in_([f.id for f in fotos])))
    return {d.foto_id: vetor(d) for d in linhas if d.versao_algoritmo == VERSAO}
