"""Mapa de abrigos e perfil público do abrigo — consultas públicas (RF-09, RF-12).

Lista os abrigos ativos e não suspensos, com a quantidade de animais disponíveis. Se a pessoa
informar a própria posição (`lat` e `lng`), devolve também a distância e ordena do mais perto
para o mais longe; `raio_km` limita a busca.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import pontuacao
from app.core.geo import distancia_km
from app.db.session import get_db
from app.models.animal import Animal
from app.models.doacao import Doacao, PontuacaoApoiador
from app.models.enums import StatusAnimal, StatusDoacao, StatusValidacao
from app.models.usuario import Abrigo, Apoiador, Usuario
from app.routers.doacoes import _necessidade_out, _recebido, meta_do_mes, necessidades_abertas, ordenar_mural
from app.schemas.abrigo import AbrigoMapaOut
from app.schemas.doacao import AbrigoPerfilOut, ApoiadorResumo

router = APIRouter(prefix="/abrigos", tags=["abrigos"])


@router.get("", response_model=list[AbrigoMapaOut])
def listar(
    lat: float | None = Query(default=None, ge=-90, le=90, description="Latitude de quem consulta"),
    lng: float | None = Query(default=None, ge=-180, le=180, description="Longitude de quem consulta"),
    raio_km: float | None = Query(default=None, gt=0, le=2000, description="Só abrigos até esta distância"),
    db: Session = Depends(get_db),
) -> list[AbrigoMapaOut]:
    """Abrigos ativos para o mapa, com a quantidade de animais disponíveis. Com `lat`/`lng`, ordena por distância; com `raio_km`, filtra."""
    if (lat is None) != (lng is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe latitude e longitude juntas.")
    if raio_km is not None and lat is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Para filtrar por raio, informe a sua posição (latitude e longitude).")

    disponiveis = (
        select(Animal.abrigo_id, func.count(Animal.id).label("total"))
        .where(Animal.status == StatusAnimal.DISPONIVEL, Animal.removido_em.is_(None))
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


@router.get("/{abrigo_id}", response_model=AbrigoPerfilOut)
def perfil(abrigo_id: int, db: Session = Depends(get_db)) -> AbrigoPerfilOut:
    """Perfil público (RF-12): integra os três módulos — animais para adoção, necessidades em aberto e quem apoia.
    A chave de doação e as necessidades só aparecem com o selo Verificado (risco de golpe)."""
    abrigo = db.get(Abrigo, abrigo_id)
    if abrigo is None or not abrigo.usuario.ativo or abrigo.status_validacao == StatusValidacao.REJEITADO:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrigo não encontrado.")
    verificado = abrigo.status_validacao == StatusValidacao.APROVADO
    disponiveis = db.scalar(
        select(func.count(Animal.id)).where(Animal.abrigo_id == abrigo_id, Animal.status == StatusAnimal.DISPONIVEL, Animal.removido_em.is_(None))
    )
    necessidades = []
    if verificado:
        linhas = necessidades_abertas(db, abrigo_id)
        recebido = _recebido(db, [n.id for n, _ in linhas])
        necessidades = ordenar_mural([_necessidade_out(n, a, recebido.get(n.id, 0)) for n, a in linhas])
    apoiadores = []
    for ap, u in db.execute(
        select(Apoiador, Usuario).join(Usuario, Usuario.id == Apoiador.usuario_id)
        .where(Apoiador.usuario_id.in_(
            select(Doacao.apoiador_id).where(Doacao.abrigo_id == abrigo_id, Doacao.status == StatusDoacao.CONFIRMADA)
        ), Usuario.ativo.is_(True))
        .order_by(Usuario.nome)
    ).tuples():
        meses = {pontuacao.mes_de(p.mes_referencia) for p in db.scalars(select(PontuacaoApoiador).where(PontuacaoApoiador.apoiador_id == ap.usuario_id))}
        apoiadores.append(ApoiadorResumo(id=ap.usuario_id, nome=u.nome, tipo_estabelecimento=ap.tipo_estabelecimento, selo_ativo=pontuacao.selo_ativo(meses)))
    return AbrigoPerfilOut(
        id=abrigo.usuario_id, nome_abrigo=abrigo.nome_abrigo, endereco=abrigo.endereco, latitude=abrigo.latitude,
        longitude=abrigo.longitude, telefone=abrigo.telefone, horario_funcionamento=abrigo.horario_funcionamento,
        descricao=abrigo.descricao, verificado=verificado, animais_disponiveis=disponiveis or 0,
        chave_doacao_financeira=abrigo.chave_doacao_financeira if verificado else None,
        meta_mensal=meta_do_mes(db, abrigo) if verificado and abrigo.chave_doacao_financeira else None,
        necessidades=necessidades, apoiadores=apoiadores,
    )
