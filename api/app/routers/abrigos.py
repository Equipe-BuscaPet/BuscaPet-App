"""Mapa de abrigos — consulta pública (RF-09).

Lista os abrigos ativos e não suspensos, com a quantidade de animais disponíveis. Se a pessoa
informar a própria posição (`lat` e `lng`), devolve também a distância e ordena do mais perto
para o mais longe; `raio_km` limita a busca.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.geo import distancia_km
from app.db.session import get_db
from app.models.animal import Animal
from app.models.enums import StatusAnimal, StatusValidacao
from app.models.usuario import Abrigo, Usuario
from app.schemas.abrigo import AbrigoMapaOut

router = APIRouter(prefix="/abrigos", tags=["abrigos"])


@router.get("", response_model=list[AbrigoMapaOut])
def listar(
    lat: float | None = Query(default=None, ge=-90, le=90, description="Latitude de quem consulta"),
    lng: float | None = Query(default=None, ge=-180, le=180, description="Longitude de quem consulta"),
    raio_km: float | None = Query(default=None, gt=0, le=2000, description="Só abrigos até esta distância"),
    db: Session = Depends(get_db),
) -> list[AbrigoMapaOut]:
    if (lat is None) != (lng is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe latitude e longitude juntas.")
    if raio_km is not None and lat is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Para filtrar por raio, informe a sua posição (latitude e longitude).")

    disponiveis = (
        select(Animal.abrigo_id, func.count(Animal.id).label("total"))
        .where(Animal.status == StatusAnimal.DISPONIVEL)
        .group_by(Animal.abrigo_id)
        .subquery()
    )
    linhas = db.execute(
        select(Abrigo, func.coalesce(disponiveis.c.total, 0))
        .join(Usuario, Usuario.id == Abrigo.usuario_id)
        .outerjoin(disponiveis, disponiveis.c.abrigo_id == Abrigo.usuario_id)
        .where(Usuario.ativo.is_(True), Abrigo.status_validacao != StatusValidacao.REJEITADO)
    ).all()

    saida = []
    for abrigo, total in linhas:
        distancia = distancia_km(lat, lng, abrigo.latitude, abrigo.longitude) if lat is not None else None
        if raio_km is not None and distancia > raio_km:
            continue
        saida.append(
            AbrigoMapaOut(
                id=abrigo.usuario_id,
                nome_abrigo=abrigo.nome_abrigo,
                endereco=abrigo.endereco,
                latitude=abrigo.latitude,
                longitude=abrigo.longitude,
                telefone=abrigo.telefone,
                horario_funcionamento=abrigo.horario_funcionamento,
                descricao=abrigo.descricao,
                verificado=abrigo.status_validacao == StatusValidacao.APROVADO,
                animais_disponiveis=total,
                distancia_km=round(distancia, 1) if distancia is not None else None,
            )
        )
    saida.sort(key=lambda a: (a.distancia_km is None, a.distancia_km or 0, a.nome_abrigo.lower()))
    return saida
