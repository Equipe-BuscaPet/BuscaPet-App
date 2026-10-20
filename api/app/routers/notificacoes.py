"""Notificações da própria conta — RF-36.

As notificações já eram gravadas pelos fluxos (interesse de adoção, verificação do abrigo); aqui elas passam a
ser lidas. Cada pessoa só vê e mexe nas suas: a notificação de outra conta responde 404 (e não 403), para não
revelar que ela existe.

O sino da interface consulta só `GET /notificacoes/contagem`, que é leve, e busca a lista quando é aberto.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.db.session import get_db
from app.models.enums import TipoConta
from app.models.transversais import Notificacao
from app.models.usuario import Usuario
from app.schemas.notificacao import ContagemNotificacoes, NotificacaoOut

router = APIRouter(prefix="/notificacoes", tags=["notificações"])


def _destino(n: Notificacao, usuario: Usuario) -> str | None:
    """Para onde o clique leva. Depende do tipo de conta: o mesmo interesse abre telas diferentes."""
    if n.referencia_tipo == "interesse":
        return "/interessados" if usuario.tipo_conta == TipoConta.ABRIGO else "/interesses"
    if n.referencia_tipo == "abrigo":
        return "/painel"
    if n.referencia_tipo == "doacao":
        return "/doacoes" if usuario.tipo_conta == TipoConta.ABRIGO else "/minhas-doacoes"
    if n.referencia_tipo == "avistamento":
        return f"/reencontro/avistamentos/{n.referencia_id}"
    return None


def _saida(n: Notificacao, usuario: Usuario) -> NotificacaoOut:
    return NotificacaoOut(
        id=n.id, mensagem=n.mensagem, referencia_tipo=n.referencia_tipo, referencia_id=n.referencia_id,
        lida=n.lida, criado_em=n.criado_em, destino=_destino(n, usuario),
    )


@router.get("", response_model=list[NotificacaoOut])
def listar(
    somente_nao_lidas: bool = False,
    limite: int = Query(default=20, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> list[NotificacaoOut]:
    """As notificações de quem está logado, das mais novas para as mais antigas."""
    consulta = select(Notificacao).where(Notificacao.usuario_id == usuario.id)
    if somente_nao_lidas:
        consulta = consulta.where(Notificacao.lida.is_(False))
    consulta = consulta.order_by(Notificacao.criado_em.desc(), Notificacao.id.desc()).offset(deslocamento).limit(limite)
    return [_saida(n, usuario) for n in db.scalars(consulta)]


@router.get("/contagem", response_model=ContagemNotificacoes)
def contar(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)) -> ContagemNotificacoes:
    total = db.scalar(
        select(func.count()).select_from(Notificacao).where(Notificacao.usuario_id == usuario.id, Notificacao.lida.is_(False))
    )
    return ContagemNotificacoes(nao_lidas=total or 0)


@router.patch("/{notificacao_id}/lida", response_model=NotificacaoOut)
def marcar_lida(
    notificacao_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> NotificacaoOut:
    n = db.get(Notificacao, notificacao_id)
    if n is None or n.usuario_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificação não encontrada.")
    n.lida = True
    db.commit()
    db.refresh(n)
    return _saida(n, usuario)


@router.post("/marcar-todas-lidas", status_code=status.HTTP_204_NO_CONTENT)
def marcar_todas(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)) -> Response:
    db.execute(
        update(Notificacao).where(Notificacao.usuario_id == usuario.id, Notificacao.lida.is_(False)).values(lida=True)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
