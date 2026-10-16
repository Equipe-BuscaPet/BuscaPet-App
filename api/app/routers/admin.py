"""Verificação de abrigos pelo administrador — RF-06.

Aprovado = abrigo verificado (selo). Pendente = ainda não verificado, mas opera.
Rejeitado = suspenso: some do catálogo público e não publica."""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import exigir_tipo
from app.db.session import get_db
from app.models.enums import StatusValidacao, TipoConta
from app.models.transversais import Notificacao
from app.models.usuario import Abrigo, Usuario
from app.routers.serializers import usuario_out
from app.schemas.usuario import UsuarioOut, ValidacaoAbrigo

router = APIRouter(prefix="/admin", tags=["administração"])

# Aviso ao abrigo quando a situação dele muda (RF-36).
_AVISO = {
    StatusValidacao.APROVADO: "Seu abrigo recebeu o selo Verificado. Ele aparece em destaque no catálogo e no mapa.",
    StatusValidacao.PENDENTE: "O selo Verificado do seu abrigo foi retirado. Você continua podendo publicar animais.",
    StatusValidacao.REJEITADO: "Seu abrigo foi suspenso pela administração e saiu do catálogo. Fale com a equipe do BuscaPet.",
}


@router.get("/abrigos", response_model=list[UsuarioOut])
def listar_abrigos(
    status_validacao: StatusValidacao = Query(default=StatusValidacao.PENDENTE, alias="status"),
    _: Usuario = Depends(exigir_tipo(TipoConta.ADMIN)),
    db: Session = Depends(get_db),
) -> list[UsuarioOut]:
    """Fila de verificação: por padrão, os abrigos ainda não verificados, do mais antigo ao mais novo."""
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
    novo = StatusValidacao(dados.status)
    if novo != abrigo.status_validacao:
        db.add(Notificacao(usuario_id=abrigo.usuario_id, mensagem=_AVISO[novo], referencia_tipo="abrigo", referencia_id=abrigo.usuario_id))
    abrigo.status_validacao = novo
    abrigo.validado_por_id = admin.id
    abrigo.validado_em = datetime.datetime.now(datetime.UTC)
    db.commit()
    db.refresh(abrigo.usuario)
    return usuario_out(abrigo.usuario)
