"""Necessidades do abrigo (RF-30) e doações do apoiador com confirmação do abrigo (RF-31, RF-32).

Fluxo: o abrigo publica o que precisa → o apoiador registra a doação (do mural ou avulsa) → o abrigo
confirma quando recebe (ou recusa) → só então a doação pontua no ranking (escopo 5.4).

O selo Verificado passa a ser exigido aqui, onde há risco de golpe (decisão da Sprint 4):
só abrigo verificado publica no mural e recebe doação pela plataforma.
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import auditoria
from app.core import pontuacao
from app.core.deps import exigir_tipo, get_abrigo_operante
from app.core.geo import distancia_km
from app.db.session import get_db
from app.models.doacao import Doacao, Necessidade
from app.models.enums import StatusDoacao, StatusNecessidade, StatusValidacao, TipoConta, UrgenciaNecessidade
from app.models.transversais import Notificacao
from app.models.usuario import Abrigo, Usuario
from app.schemas.doacao import DecisaoDoacao, DoacaoIn, DoacaoOut, NecessidadeEdicao, NecessidadeIn, NecessidadeOut

router = APIRouter(tags=["doações"])

ORDEM_URGENCIA = {UrgenciaNecessidade.ALTA: 0, UrgenciaNecessidade.MEDIA: 1, UrgenciaNecessidade.BAIXA: 2}
SEM_SELO = "Seu abrigo precisa do selo Verificado para publicar necessidades no mural. A administração concede o selo depois de conferir o abrigo."


# ---------- apoio ----------

def _recebido(db: Session, ids: list[int]) -> dict[int, int]:
    """Soma das quantidades confirmadas por necessidade."""
    if not ids:
        return {}
    linhas = db.execute(
        select(Doacao.necessidade_id, func.sum(Doacao.quantidade))
        .where(Doacao.necessidade_id.in_(ids), Doacao.status == StatusDoacao.CONFIRMADA)
        .group_by(Doacao.necessidade_id)
    )
    return {nid: int(total) for nid, total in linhas}


def _necessidade_out(n: Necessidade, abrigo: Abrigo, recebido: int, origem=None) -> NecessidadeOut:
    distancia = round(distancia_km(origem[0], origem[1], abrigo.latitude, abrigo.longitude), 1) if origem else None
    return NecessidadeOut(
        id=n.id, abrigo_id=n.abrigo_id, nome_abrigo=abrigo.nome_abrigo, item=n.item, quantidade=n.quantidade,
        quantidade_recebida=recebido, urgencia=n.urgencia, status=n.status, criado_em=n.criado_em, distancia_km=distancia,
    )


def necessidades_abertas(db: Session, abrigo_id: int | None = None) -> list[tuple[Necessidade, Abrigo]]:
    """Mural: necessidades abertas de abrigos verificados e ativos (também usado no perfil público do abrigo)."""
    consulta = (
        select(Necessidade, Abrigo)
        .join(Abrigo, Abrigo.usuario_id == Necessidade.abrigo_id)
        .join(Usuario, Usuario.id == Abrigo.usuario_id)
        .where(Necessidade.status == StatusNecessidade.ABERTA, Abrigo.status_validacao == StatusValidacao.APROVADO, Usuario.ativo.is_(True))
    )
    if abrigo_id is not None:
        consulta = consulta.where(Necessidade.abrigo_id == abrigo_id)
    return list(db.execute(consulta).tuples())


def ordenar_mural(itens: list[NecessidadeOut]) -> list[NecessidadeOut]:
    """Mais urgente primeiro; dentro da mesma urgência, mais perto (se houver posição) ou mais recente."""
    return sorted(itens, key=lambda n: (
        ORDEM_URGENCIA[n.urgencia], n.distancia_km if n.distancia_km is not None else 0, -n.criado_em.timestamp(),
    ))


def _doacao_out(d: Doacao, apoiador: Usuario, abrigo: Abrigo, ver_contato_de: str | None = None) -> DoacaoOut:
    contato = None
    if ver_contato_de == "apoiador":
        contato = apoiador.email
    elif ver_contato_de == "abrigo":
        contato = " · ".join(filter(None, [abrigo.telefone, abrigo.endereco]))
    return DoacaoOut(
        id=d.id, apoiador_id=d.apoiador_id, nome_apoiador=apoiador.nome, abrigo_id=d.abrigo_id, nome_abrigo=abrigo.nome_abrigo,
        necessidade_id=d.necessidade_id, item=d.item, quantidade=d.quantidade, status=d.status,
        registrado_em=d.registrado_em, confirmado_em=d.confirmado_em, contato=contato,
    )


def _notificar(db: Session, usuario_id: int, mensagem: str, doacao_id: int) -> None:
    db.add(Notificacao(usuario_id=usuario_id, mensagem=mensagem, referencia_tipo="doacao", referencia_id=doacao_id))


def _minha_necessidade(db: Session, necessidade_id: int, abrigo: Abrigo) -> Necessidade:
    n = db.get(Necessidade, necessidade_id)
    if n is None or n.abrigo_id != abrigo.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Necessidade não encontrada.")
    return n


# ---------- RF-30: necessidades ----------

@router.post("/necessidades", response_model=NecessidadeOut, status_code=status.HTTP_201_CREATED)
def publicar_necessidade(dados: NecessidadeIn, abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> NecessidadeOut:
    if abrigo.status_validacao != StatusValidacao.APROVADO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, SEM_SELO)
    n = Necessidade(abrigo_id=abrigo.usuario_id, **dados.model_dump())
    db.add(n)
    db.flush()
    auditoria.registrar(db, abrigo.usuario_id, "necessidade.publicada", "necessidade", n.id, item=n.item, quantidade=n.quantidade)
    db.commit()
    db.refresh(n)
    return _necessidade_out(n, abrigo, 0)


@router.get("/necessidades", response_model=list[NecessidadeOut])
def mural(
    urgencia: UrgenciaNecessidade | None = None,
    abrigo_id: int | None = None,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    raio_km: float | None = Query(default=None, gt=0, le=2000),
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[NecessidadeOut]:
    """Mural público de necessidades em aberto (RF-35), mais urgentes primeiro."""
    if (lat is None) != (lng is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe latitude e longitude juntas.")
    if raio_km is not None and lat is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Para filtrar por raio, informe a sua posição (latitude e longitude).")
    origem = (lat, lng) if lat is not None else None
    linhas = [(n, a) for n, a in necessidades_abertas(db, abrigo_id) if urgencia is None or n.urgencia == urgencia]
    recebido = _recebido(db, [n.id for n, _ in linhas])
    itens = [_necessidade_out(n, a, recebido.get(n.id, 0), origem) for n, a in linhas]
    if raio_km is not None:
        itens = [i for i in itens if i.distancia_km <= raio_km]
    return ordenar_mural(itens)[:limite]


@router.get("/necessidades/minhas", response_model=list[NecessidadeOut])
def minhas_necessidades(abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> list[NecessidadeOut]:
    """Todas as do abrigo, abertas primeiro."""
    lista = list(db.scalars(select(Necessidade).where(Necessidade.abrigo_id == abrigo.usuario_id)))
    recebido = _recebido(db, [n.id for n in lista])
    itens = [_necessidade_out(n, abrigo, recebido.get(n.id, 0)) for n in lista]
    return sorted(itens, key=lambda n: (n.status != StatusNecessidade.ABERTA, ORDEM_URGENCIA[n.urgencia], -n.criado_em.timestamp()))


@router.patch("/necessidades/{necessidade_id}", response_model=NecessidadeOut)
def editar_necessidade(
    necessidade_id: int, dados: NecessidadeEdicao, abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db),
) -> NecessidadeOut:
    n = _minha_necessidade(db, necessidade_id, abrigo)
    if dados.status == StatusNecessidade.ABERTA and abrigo.status_validacao != StatusValidacao.APROVADO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, SEM_SELO)
    mudancas = dados.model_dump(exclude_none=True)
    for campo, valor in mudancas.items():
        setattr(n, campo, valor)
    auditoria.registrar(db, abrigo.usuario_id, "necessidade.atualizada", "necessidade", n.id, item=n.item, campos=sorted(mudancas))
    db.commit()
    db.refresh(n)
    return _necessidade_out(n, abrigo, _recebido(db, [n.id]).get(n.id, 0))


@router.delete("/necessidades/{necessidade_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_necessidade(necessidade_id: int, abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> Response:
    n = _minha_necessidade(db, necessidade_id, abrigo)
    if db.scalar(select(func.count()).select_from(Doacao).where(Doacao.necessidade_id == n.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta necessidade já tem doações registradas e não pode ser excluída. Marque-a como atendida.")
    auditoria.registrar(db, abrigo.usuario_id, "necessidade.excluida", "necessidade", n.id, item=n.item)
    db.delete(n)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- RF-31: doação do apoiador ----------

@router.post("/doacoes", response_model=DoacaoOut, status_code=status.HTTP_201_CREATED)
def registrar_doacao(
    dados: DoacaoIn, usuario: Usuario = Depends(exigir_tipo(TipoConta.APOIADOR)), db: Session = Depends(get_db),
) -> DoacaoOut:
    """O apoiador se compromete a doar. Fica "aguardando confirmação" até o abrigo receber."""
    item = dados.item
    if dados.necessidade_id is not None:
        necessidade = db.get(Necessidade, dados.necessidade_id)
        if necessidade is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Necessidade não encontrada.")
        if necessidade.status != StatusNecessidade.ABERTA:
            raise HTTPException(status.HTTP_409_CONFLICT, "Esta necessidade já foi atendida. Veja outras no mural.")
        abrigo_id, item = necessidade.abrigo_id, necessidade.item
    else:
        abrigo_id = dados.abrigo_id
    abrigo = db.get(Abrigo, abrigo_id)
    if abrigo is None or not abrigo.usuario.ativo or abrigo.status_validacao == StatusValidacao.REJEITADO:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abrigo não encontrado.")
    if abrigo.status_validacao != StatusValidacao.APROVADO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este abrigo ainda não tem o selo Verificado e não recebe doações pela plataforma.")

    doacao = Doacao(apoiador_id=usuario.id, abrigo_id=abrigo_id, necessidade_id=dados.necessidade_id, item=item, quantidade=dados.quantidade)
    db.add(doacao)
    db.flush()
    _notificar(db, abrigo_id, f"{usuario.nome} vai doar {dados.quantidade} × {item}. Confirme quando receber.", doacao.id)
    auditoria.registrar(db, usuario.id, "doacao.registrada", "doacao", doacao.id, item=item, quantidade=dados.quantidade, abrigo_id=abrigo_id)
    db.commit()
    db.refresh(doacao)
    return _doacao_out(doacao, usuario, abrigo, ver_contato_de="abrigo")


@router.get("/doacoes/minhas", response_model=list[DoacaoOut])
def minhas_doacoes(usuario: Usuario = Depends(exigir_tipo(TipoConta.APOIADOR)), db: Session = Depends(get_db)) -> list[DoacaoOut]:
    linhas = db.execute(
        select(Doacao, Abrigo).join(Abrigo, Abrigo.usuario_id == Doacao.abrigo_id)
        .where(Doacao.apoiador_id == usuario.id).order_by(Doacao.registrado_em.desc(), Doacao.id.desc())
    ).tuples()
    return [_doacao_out(d, usuario, a, ver_contato_de="abrigo") for d, a in linhas]


@router.delete("/doacoes/{doacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_doacao(doacao_id: int, usuario: Usuario = Depends(exigir_tipo(TipoConta.APOIADOR)), db: Session = Depends(get_db)) -> Response:
    """O apoiador desiste enquanto o abrigo não respondeu."""
    d = db.get(Doacao, doacao_id)
    if d is None or d.apoiador_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doação não encontrada.")
    if d.status != StatusDoacao.AGUARDANDO_CONFIRMACAO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta doação já foi respondida pelo abrigo e não pode ser cancelada.")
    _notificar(db, d.abrigo_id, f"{usuario.nome} cancelou a doação de {d.quantidade} × {d.item}.", d.id)
    auditoria.registrar(db, usuario.id, "doacao.cancelada", "doacao", d.id, item=d.item, quantidade=d.quantidade)
    db.delete(d)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- RF-32: confirmação do abrigo ----------

@router.get("/doacoes/recebidas", response_model=list[DoacaoOut])
def doacoes_recebidas(
    status_doacao: StatusDoacao | None = Query(default=None, alias="status"),
    abrigo: Abrigo = Depends(get_abrigo_operante),
    db: Session = Depends(get_db),
) -> list[DoacaoOut]:
    """Aguardando confirmação primeiro (é o que exige ação), depois as mais recentes."""
    consulta = select(Doacao, Usuario).join(Usuario, Usuario.id == Doacao.apoiador_id).where(Doacao.abrigo_id == abrigo.usuario_id)
    if status_doacao:
        consulta = consulta.where(Doacao.status == status_doacao)
    linhas = db.execute(consulta.order_by(Doacao.registrado_em.desc(), Doacao.id.desc())).tuples()
    itens = [_doacao_out(d, u, abrigo, ver_contato_de="apoiador") for d, u in linhas]
    return sorted(itens, key=lambda d: d.status != StatusDoacao.AGUARDANDO_CONFIRMACAO)


@router.patch("/doacoes/{doacao_id}", response_model=DoacaoOut)
def decidir_doacao(
    doacao_id: int, dados: DecisaoDoacao, abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db),
) -> DoacaoOut:
    d = db.get(Doacao, doacao_id)
    if d is None or d.abrigo_id != abrigo.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doação não encontrada.")
    if d.status != StatusDoacao.AGUARDANDO_CONFIRMACAO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta doação já foi respondida e não pode ser alterada.")
    d.status = dados.status
    apoiador = db.get(Usuario, d.apoiador_id)
    if dados.status == StatusDoacao.CONFIRMADA:
        d.confirmado_em = datetime.datetime.now(datetime.UTC)
        db.flush()
        pontuacao.recalcular(db, d.apoiador_id)
        if d.necessidade_id is not None:  # pedido completo vira "atendida" e sai do mural
            n = db.get(Necessidade, d.necessidade_id)
            if _recebido(db, [n.id]).get(n.id, 0) >= n.quantidade:
                n.status = StatusNecessidade.ATENDIDA
        _notificar(db, d.apoiador_id, f"{abrigo.nome_abrigo} confirmou o recebimento de {d.quantidade} × {d.item}. Obrigado! Sua pontuação foi atualizada.", d.id)
    else:
        _notificar(db, d.apoiador_id, f"{abrigo.nome_abrigo} informou que não recebeu {d.quantidade} × {d.item}. Fale com o abrigo se houver engano.", d.id)
    auditoria.registrar(
        db, abrigo.usuario_id, f"doacao.{dados.status.value}", "doacao", d.id, item=d.item, quantidade=d.quantidade, apoiador_id=d.apoiador_id,
    )
    db.commit()
    db.refresh(d)
    return _doacao_out(d, apoiador, abrigo, ver_contato_de="apoiador")
