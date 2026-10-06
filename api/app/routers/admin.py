"""Validação de abrigos pelo administrador — RF-06."""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import exigir_tipo
from app.db.session import get_db
from app.models.enums import StatusValidacao, TipoConta
from app.models.usuario import Abrigo, Usuario
from app.routers.serializers import usuario_out
from app.schemas.usuario import UsuarioOut, ValidacaoAbrigo

router = APIRouter(prefix="/admin", tags=["administração"])


@router.get("/abrigos", response_model=list[UsuarioOut])
def listar_abrigos(
    status_validacao: StatusValidacao = Query(default=StatusValidacao.PENDENTE, alias="status"),
    _: Usuario = Depends(exigir_tipo(TipoConta.ADMIN)),
    db: Session = Depends(get_db),
) -> list[UsuarioOut]:
    """Fila de validação: por padrão, os abrigos pendentes, do mais antigo ao mais novo."""
    usuarios = db.scalars(
        select(Usuario)
        .join(Abrigo, Abrigo.usuario_id == Usuario.id)
        .where(Abrigo.status_validacao == status_validacao)
        .order_by(Usuario.criado_em, Usuario.id)
    ).all()
    return [usuario_out(u) for u in usuarios]


@router.patch("/abrigos/{usuario_id}/validacao", response_model=UsuarioOut)
def validar_abrigo(
    usuario_id: int,
    dados: ValidacaoAbrigo,
    admin: Usuario = Depends(exigir_tipo(TipoConta.ADMIN)),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    abrigo = db.get(Abrigo, usuario_id)
    if abrigo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrigo não encontrado.")
    abrigo.status_validacao = StatusValidacao(dados.status)
    abrigo.validado_por_id = admin.id
    abrigo.validado_em = datetime.datetime.now(datetime.UTC)
    db.commit()
    db.refresh(abrigo.usuario)
    return usuario_out(abrigo.usuario)
