"""Aba "Quem apoia": ranking por categoria (RF-33), perfil público do apoiador (RF-34) e lista para o mapa.

O ranking lê o cache mensal `pontuacoes_apoiador` (regra em app/core/pontuacao.py). Dois períodos (escopo
5.2): o mês (para quem chegou agora aparecer) e o acumulado do ano.

A categoria "pessoa física" reúne os tutores que doam. Por privacidade, aparecem só com o primeiro nome e a
inicial do sobrenome, e não têm perfil público nem posição no mapa (o perfil e o mapa são das empresas).
"""
import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import pontuacao
from app.db.session import get_db
from app.models.doacao import Doacao, PontuacaoApoiador
from app.models.enums import StatusDoacao, StatusValidacao, TipoConta, TipoEstabelecimento
from app.models.usuario import Abrigo, Apoiador, Usuario
from app.schemas.doacao import AbrigoApoiado, ApoiadorPerfilOut, ApoiadorResumo, PosicaoRanking

router = APIRouter(prefix="/apoiadores", tags=["apoiadores"])


def _ativos(db: Session, categoria: TipoEstabelecimento | None = None) -> dict[int, tuple[Apoiador, Usuario]]:
    consulta = (
        select(Apoiador, Usuario).join(Usuario, Usuario.id == Apoiador.usuario_id)
        .where(Usuario.ativo.is_(True), Apoiador.status_validacao == StatusValidacao.APROVADO)
    )
    if categoria:
        consulta = consulta.where(Apoiador.tipo_estabelecimento == categoria)
    return {ap.usuario_id: (ap, u) for ap, u in db.execute(consulta).tuples()}


def _tutores(db: Session) -> dict[int, Usuario]:
    """Tutores ativos que já doaram: entram no ranking como pessoa física."""
    consulta = select(Usuario).where(
        Usuario.tipo_conta == TipoConta.TUTOR, Usuario.ativo.is_(True), Usuario.id.in_(select(Doacao.apoiador_id)),
    )
    return {u.id: u for u in db.scalars(consulta)}


def nome_publico(nome: str) -> str:
    """"Maria da Silva Souza" → "Maria S.": a pessoa física aparece no ranking sem o nome completo."""
    partes = nome.split()
    return f"{partes[0]} {partes[-1][0].upper()}." if len(partes) > 1 else partes[0]


def _pontos_por_mes(db: Session, ids) -> dict[int, dict[tuple[int, int], PontuacaoApoiador]]:
    saida: dict[int, dict[tuple[int, int], PontuacaoApoiador]] = {i: {} for i in ids}
    if saida:
        for p in db.scalars(select(PontuacaoApoiador).where(PontuacaoApoiador.apoiador_id.in_(list(saida)))):
            saida[p.apoiador_id][pontuacao.mes_de(p.mes_referencia)] = p
    return saida


def _mes_pedido(mes: str | None) -> tuple[int, int]:
    if mes is None:
        hoje = datetime.datetime.now(datetime.UTC)
        return hoje.year, hoje.month
    try:
        ano, m = (int(x) for x in mes.split("-"))
        datetime.date(ano, m, 1)
    except ValueError:
        raise HTTPException(422, "Informe o mês no formato AAAA-MM (exemplo: 2026-10).")
    return ano, m


@router.get("/ranking", response_model=list[PosicaoRanking])
def ranking(
    categoria: TipoEstabelecimento | None = Query(default=None, description="Sem categoria: todas juntas (destaques)"),
    periodo: Literal["mes", "ano"] = "mes",
    mes: str | None = Query(default=None, description="AAAA-MM; padrão: o mês atual"),
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PosicaoRanking]:
    """Ranking de quem apoia (RF-33): por categoria (`petshop`, `clinica`, `distribuidora`, `pessoa_fisica`), no mês ou no ano. Pessoa física aparece como "Maria S."."""
    ano, m = _mes_pedido(mes)
    # id → (nome exibido, categoria, tem perfil público)
    doadores = {aid: (u.nome, ap.tipo_estabelecimento, True) for aid, (ap, u) in _ativos(db, categoria).items()}
    if categoria in (None, TipoEstabelecimento.PESSOA_FISICA):
        doadores |= {tid: (nome_publico(u.nome), TipoEstabelecimento.PESSOA_FISICA, False) for tid, u in _tutores(db).items()}
    pontos = _pontos_por_mes(db, doadores)
    linhas = []
    for aid, meses in pontos.items():
        escolhidos = [p for (a, mm), p in meses.items() if a == ano and (mm <= m if periodo == "ano" else mm == m)]
        if not escolhidos:
            continue
        nome, tipo, perfil_publico = doadores[aid]
        ate = [p for (a, mm), p in meses.items() if (a, mm) <= (ano, m)]
        ultimo = max(ate, key=lambda p: p.mes_referencia.replace(tzinfo=None)) if ate else None
        linhas.append(dict(
            apoiador_id=aid, nome=nome, tipo_estabelecimento=tipo, perfil_publico=perfil_publico,
            pontos=sum(p.pontos_total for p in escolhidos), pontos_volume=sum(p.pontos_volume for p in escolhidos),
            pontos_regularidade=sum(p.pontos_regularidade for p in escolhidos),
            doacoes_confirmadas=int(sum(p.pontos_volume for p in escolhidos) // pontuacao.PONTOS_POR_DOACAO),
            meses_seguidos=int(ultimo.pontos_regularidade // pontuacao.PONTOS_POR_MES_SEGUIDO) if ultimo else 0,
            selo_ativo=pontuacao.selo_ativo(set(meses)),
        ))
    # Empate: quem tem mais meses seguidos fica na frente (premia a constância), depois ordem alfabética.
    linhas.sort(key=lambda r: (-r["pontos"], -r["meses_seguidos"], r["nome"].lower()))
    return [PosicaoRanking(posicao=i, **r) for i, r in enumerate(linhas[:limite], start=1)]


@router.get("", response_model=list[ApoiadorResumo])
def listar(db: Session = Depends(get_db)) -> list[ApoiadorResumo]:
    """Parceiros para o mapa da aba "Quem apoia": só quem já teve doação confirmada."""
    apoiadores = _ativos(db)
    pontos = _pontos_por_mes(db, apoiadores)
    return sorted([
        ApoiadorResumo(id=aid, nome=u.nome, tipo_estabelecimento=ap.tipo_estabelecimento, selo_ativo=pontuacao.selo_ativo(set(pontos[aid])),
                       latitude=ap.latitude, longitude=ap.longitude)
        for aid, (ap, u) in apoiadores.items() if pontos[aid]
    ], key=lambda a: a.nome.lower())


@router.get("/{apoiador_id}", response_model=ApoiadorPerfilOut)
def perfil(apoiador_id: int, db: Session = Depends(get_db)) -> ApoiadorPerfilOut:
    """Perfil público do apoiador (RF-34): pontos, meses seguidos e abrigos apoiados. Só empresas têm perfil (pessoa física: 404)."""
    ativos = _ativos(db)
    if apoiador_id not in ativos:
        raise HTTPException(404, "Apoiador não encontrado.")
    apoiador, usuario = ativos[apoiador_id]
    meses = _pontos_por_mes(db, [apoiador_id])[apoiador_id]
    hoje = datetime.datetime.now(datetime.UTC)
    do_ano = [p for (a, _), p in meses.items() if a == hoje.year]
    atual = meses.get((hoje.year, hoje.month))
    anterior = meses.get(pontuacao.mes_anterior(hoje.year, hoje.month))
    seguidos = atual or anterior  # a sequência só vale se ainda está viva (mês atual ou o anterior)
    apoiados = db.execute(
        select(Abrigo.usuario_id, Abrigo.nome_abrigo, func.count(Doacao.id))
        .join(Doacao, Doacao.abrigo_id == Abrigo.usuario_id)
        .where(Doacao.apoiador_id == apoiador_id, Doacao.status == StatusDoacao.CONFIRMADA)
        .group_by(Abrigo.usuario_id, Abrigo.nome_abrigo)
        .order_by(func.count(Doacao.id).desc())
    ).all()
    return ApoiadorPerfilOut(
        id=apoiador_id, nome=usuario.nome, tipo_estabelecimento=apoiador.tipo_estabelecimento,
        selo_ativo=pontuacao.selo_ativo(set(meses)), latitude=apoiador.latitude, longitude=apoiador.longitude,
        endereco=apoiador.endereco, pontos_mes=atual.pontos_total if atual else 0, pontos_ano=sum(p.pontos_total for p in do_ano),
        meses_seguidos=int(seguidos.pontos_regularidade // pontuacao.PONTOS_POR_MES_SEGUIDO) if seguidos else 0,
        doacoes_confirmadas=sum(total for _, _, total in apoiados),
        abrigos_apoiados=[AbrigoApoiado(id=i, nome_abrigo=n, doacoes_confirmadas=t) for i, n, t in apoiados],
        membro_desde=usuario.criado_em,
    )
