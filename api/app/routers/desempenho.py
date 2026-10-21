"""Núcleo OpenCL visto pela administração — RF-29 (modo comparativo de desempenho) e RF-21 (indexação).

- `GET /admin/nucleo`: o núcleo está no ar? em que dispositivo? quantas fotos já têm descritor?
- `GET /admin/nucleo/benchmark`: roda no núcleo a mesma etapa nos dois modos (sequencial em C × OpenCL) e devolve
  os tempos por etapa (envio, kernel, retorno), o speedup e se os resultados bateram.
- `POST /admin/nucleo/indexar`: calcula os descritores que faltam (fotos enviadas com o núcleo fora do ar).
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import nucleo
from app.core.deps import exigir_tipo
from app.db.session import get_db
from app.models.animal import Foto
from app.models.enums import TipoConta
from app.models.reencontro import DescritorVisual

router = APIRouter(prefix="/admin/nucleo", tags=["núcleo OpenCL"], dependencies=[Depends(exigir_tipo(TipoConta.ADMIN))])

LIMITES = {"busca": 200_000, "lote": 20_000, "extracao": 2_000}


def _contagem(db: Session) -> dict:
    total = db.scalar(select(func.count(Foto.id))) or 0
    com = db.scalar(select(func.count(DescritorVisual.id)).where(DescritorVisual.versao_algoritmo == nucleo.VERSAO)) or 0
    return {"fotos": total, "com_descritor": com, "sem_descritor": max(total - com, 0)}


@router.get("")
def estado(db: Session = Depends(get_db)) -> dict:
    try:
        saude = nucleo.saude()
    except nucleo.NucleoIndisponivel as erro:
        return {"no_ar": False, "motivo": str(erro), **_contagem(db)}
    return {"no_ar": True, "nucleo": saude, **_contagem(db)}


@router.get("/benchmark")
def benchmark(etapa: Literal["busca", "lote", "extracao"] = "busca", n: int = Query(default=1000, ge=1)) -> dict:
    """`busca`: 1 foto contra n candidatos · `lote`: 100 fotos novas contra n buscas ativas · `extracao`: n fotos."""
    if n > LIMITES[etapa]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Para a etapa {etapa}, n vai até {LIMITES[etapa]:,}.".replace(",", "."))
    try:
        return nucleo.benchmark(etapa, n)
    except nucleo.NucleoIndisponivel as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"O núcleo OpenCL não respondeu ({erro}).")


@router.post("/indexar")
def indexar(limite: int = Query(default=500, ge=1, le=5000), db: Session = Depends(get_db)) -> dict:
    sem = db.scalars(
        select(Foto).outerjoin(DescritorVisual, DescritorVisual.foto_id == Foto.id)
        .where(DescritorVisual.id.is_(None)).order_by(Foto.id).limit(limite)
    )
    try:
        feitas = nucleo.indexar(db, list(sem), repassar_falha=True)
    except nucleo.NucleoIndisponivel as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"O núcleo OpenCL não respondeu ({erro}).")
    return {"indexadas": feitas, **_contagem(db)}
