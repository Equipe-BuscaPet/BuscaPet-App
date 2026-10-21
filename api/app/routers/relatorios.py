"""Dashboard, relatórios, pesquisa, filtros, exportação e histórico — Sprint 7 oficial (RF-38, RF-39, RF-40).

- Administração: painel com indicadores (`/admin/painel`), pesquisa de contas (`/admin/usuarios`), histórico de
  operações com filtros (`/admin/logs`) e exportações CSV (abrigos, histórico).
- Abrigo: relatório do próprio abrigo (`/relatorios/abrigo`), o próprio histórico e exportações CSV
  (interesses, doações, animais).

Filtro de período: `de` e `ate` são dias no fuso de Recife (UTC-3, sem horário de verão); o padrão é os últimos
90 dias. Os limites viram instantes em UTC antes de ir ao banco, o que funciona igual no PostgreSQL e no SQLite.

CSV: separador ";" e BOM UTF-8, para abrir com acentos no Excel em português; datas no fuso de Recife.
"""
import csv
import datetime
import io
from collections import Counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import auditoria
from app.core.deps import exigir_tipo, get_abrigo_operante
from app.db.session import get_db
from app.models.animal import Animal, Interesse
from app.models.doacao import Doacao, Necessidade
from app.models.enums import StatusAnimal, StatusDenuncia, StatusDoacao, StatusNecessidade, StatusValidacao, TipoConta, TipoEstabelecimento
from app.models.reencontro import AnimalPerdido, Avistamento
from app.models.transversais import Denuncia, LogAuditoria
from app.models.usuario import Abrigo, Apoiador, Tutor, Usuario
from app.schemas.relatorio import (
    ApoiadorDoAbrigo,
    Contagem,
    LinhaRelatorio,
    LogOut,
    PaginaLinhas,
    PaginaLogs,
    PainelAdminOut,
    Periodo,
    PontoMensal,
    RelatorioAbrigoOut,
    UsuarioResumoOut,
)

router = APIRouter(tags=["relatórios"])
somente_admin = exigir_tipo(TipoConta.ADMIN)

FUSO = datetime.timezone(datetime.timedelta(hours=-3), "America/Recife")
PADRAO_DIAS = 90
MESES_NA_SERIE = 6


# ---------- período, datas e CSV ----------

def periodo(
    de: datetime.date | None = Query(default=None, description="Primeiro dia (padrão: 90 dias atrás)"),
    ate: datetime.date | None = Query(default=None, description="Último dia, inclusive (padrão: hoje)"),
) -> Periodo:
    ate = ate or datetime.datetime.now(FUSO).date()
    de = de or ate - datetime.timedelta(days=PADRAO_DIAS - 1)
    if de > ate:
        raise HTTPException(422, "A data inicial precisa ser anterior ou igual à final.")
    return Periodo(de=de, ate=ate)


def _limites(p: Periodo) -> tuple[datetime.datetime, datetime.datetime]:
    inicio = datetime.datetime.combine(p.de, datetime.time(), FUSO).astimezone(datetime.UTC)
    fim = datetime.datetime.combine(p.ate + datetime.timedelta(days=1), datetime.time(), FUSO).astimezone(datetime.UTC)
    return inicio, fim


def _no(coluna, p: Periodo):
    inicio, fim = _limites(p)
    return (coluna >= inicio) & (coluna < fim)


def _local(momento: datetime.datetime) -> datetime.datetime:
    """Instante no fuso de Recife. O SQLite devolve sem fuso (o valor gravado é UTC)."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=datetime.UTC)
    return momento.astimezone(FUSO)


def _meses(p: Periodo) -> list[str]:
    ano, mes = p.ate.year, p.ate.month
    saida = []
    for _ in range(MESES_NA_SERIE):
        saida.append(f"{ano:04d}-{mes:02d}")
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return saida[::-1]


def _serie(p: Periodo, interesses, reencontro, doacoes) -> list[PontoMensal]:
    """Últimos 6 meses até o fim do período, contando por mês (no fuso de Recife)."""
    meses = _meses(p)
    contar = lambda momentos: Counter(_local(m).strftime("%Y-%m") for m in momentos if m is not None)  # noqa: E731
    i, r, d = contar(interesses), contar(reencontro), contar(doacoes)
    return [PontoMensal(mes=m, interesses=i[m], registros_reencontro=r[m], doacoes_confirmadas=d[m]) for m in meses]


def _inicio_serie(p: Periodo) -> datetime.datetime:
    ano, mes = (int(x) for x in _meses(p)[0].split("-"))
    return datetime.datetime(ano, mes, 1, tzinfo=FUSO).astimezone(datetime.UTC)


def _csv(nome: str, cabecalho: list[str], linhas) -> Response:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return Response(
        content="﻿" + saida.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _data(momento) -> str:
    return _local(momento).strftime("%d/%m/%Y %H:%M") if momento else ""


SELO = {StatusValidacao.APROVADO: "verificado", StatusValidacao.PENDENTE: "não verificado", StatusValidacao.REJEITADO: "suspenso"}


def _dia(coluna_do_dia) -> datetime.date:
    """Colunas "do dia" (ex.: data de entrada) são gravadas como meia-noite UTC: o dia é o da data em UTC."""
    if coluna_do_dia.tzinfo is not None:
        coluna_do_dia = coluna_do_dia.astimezone(datetime.UTC)
    return coluna_do_dia.date()


def _contagem(pares) -> list[Contagem]:
    return [Contagem(chave=str(getattr(k, "value", k)), total=int(v)) for k, v in pares]


# ---------- histórico (RF-39) ----------

def _consulta_logs(p: Periodo, acao: str | None, q: str | None, entidade: str | None, usuario_id: int | None = None):
    consulta = select(LogAuditoria, Usuario).join(Usuario, Usuario.id == LogAuditoria.usuario_id).where(_no(LogAuditoria.criado_em, p))
    if acao:
        consulta = consulta.where(LogAuditoria.acao == acao)
    if entidade:
        consulta = consulta.where(LogAuditoria.entidade_tipo == entidade)
    if usuario_id is not None:
        consulta = consulta.where(LogAuditoria.usuario_id == usuario_id)
    if q:
        termo = f"%{q.strip().lower()}%"
        consulta = consulta.where(or_(
            func.lower(Usuario.nome).like(termo), func.lower(Usuario.email).like(termo), func.lower(LogAuditoria.detalhes_json).like(termo),
        ))
    return consulta


def _log_out(log: LogAuditoria, u: Usuario) -> LogOut:
    return LogOut(
        id=log.id, criado_em=log.criado_em, usuario_id=u.id, usuario_nome=u.nome, usuario_email=u.email, tipo_conta=u.tipo_conta.value,
        acao=log.acao, rotulo=auditoria.ROTULOS.get(log.acao, log.acao), entidade_tipo=log.entidade_tipo, entidade_id=log.entidade_id,
        detalhes=auditoria.detalhes(log),
    )


ROTULO_DETALHE = {
    "animal": "Animal", "item": "Item", "quantidade": "Quantidade", "abrigo": "Abrigo", "campos": "Campos",
    "situacao": "Situação", "tipo": "Tipo de conta", "especie": "Espécie", "pelo_admin": "Pela administração",
}


def _texto_detalhes(d: dict) -> str:
    """Detalhes legíveis para o CSV: sem ids internos e separados por " | " (o ";" é o separador das colunas)."""
    def valor(v):
        return ", ".join(map(str, v)) if isinstance(v, list) else "sim" if v is True else str(v)
    return " | ".join(f"{ROTULO_DETALHE.get(k, k)}: {valor(v)}" for k, v in d.items() if not k.endswith("_id"))


@router.get("/admin/acoes", response_model=dict[str, str])
def acoes(_: Usuario = Depends(somente_admin)) -> dict[str, str]:
    """Ações registradas no histórico, com o rótulo em português (para o filtro da tela)."""
    return auditoria.ROTULOS


@router.get("/admin/logs", response_model=PaginaLogs)
def logs(
    p: Periodo = Depends(periodo),
    acao: str | None = None,
    q: str | None = Query(default=None, description="Pesquisa no nome ou e-mail de quem fez e nos detalhes"),
    entidade: str | None = None,
    limite: int = Query(default=50, ge=1, le=500),
    deslocamento: int = Query(default=0, ge=0),
    _: Usuario = Depends(somente_admin),
    db: Session = Depends(get_db),
) -> PaginaLogs:
    """Histórico de operações (RF-39), paginado; filtra por período, ação, entidade e texto."""
    consulta = _consulta_logs(p, acao, q, entidade)
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    linhas = db.execute(consulta.order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc()).offset(deslocamento).limit(limite)).tuples()
    return PaginaLogs(total=total or 0, itens=[_log_out(log, u) for log, u in linhas])


@router.get("/admin/logs.csv")
def logs_csv(
    p: Periodo = Depends(periodo), acao: str | None = None, q: str | None = None, entidade: str | None = None,
    _: Usuario = Depends(somente_admin), db: Session = Depends(get_db),
) -> Response:
    """O histórico de operações em CSV, com os mesmos filtros."""
    linhas = db.execute(_consulta_logs(p, acao, q, entidade).order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc())).tuples()
    return _csv(
        f"historico-{p.de}-a-{p.ate}.csv", ["Data", "Quem", "E-mail", "Tipo de conta", "Ação", "Registro", "Detalhes"],
        ([_data(log.criado_em), u.nome, u.email, u.tipo_conta.value, auditoria.ROTULOS.get(log.acao, log.acao),
          f"{log.entidade_tipo} #{log.entidade_id}", _texto_detalhes(auditoria.detalhes(log))] for log, u in linhas),
    )


# ---------- pesquisa de contas (administração) ----------

@router.get("/admin/usuarios", response_model=list[UsuarioResumoOut])
def pesquisar_usuarios(
    q: str | None = Query(default=None, description="Parte do nome, e-mail ou nome do abrigo"),
    tipo: TipoConta | None = None,
    ativo: bool | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    _: Usuario = Depends(somente_admin),
    db: Session = Depends(get_db),
) -> list[UsuarioResumoOut]:
    """Pesquisa de contas pela administração: por nome, e-mail ou nome do abrigo, tipo de conta e situação."""
    consulta = select(Usuario).outerjoin(Abrigo, Abrigo.usuario_id == Usuario.id)
    if q:
        termo = f"%{q.strip().lower()}%"
        consulta = consulta.where(or_(
            func.lower(Usuario.nome).like(termo), func.lower(Usuario.email).like(termo), func.lower(Abrigo.nome_abrigo).like(termo),
        ))
    if tipo:
        consulta = consulta.where(Usuario.tipo_conta == tipo)
    if ativo is not None:
        consulta = consulta.where(Usuario.ativo.is_(ativo))
    saida = []
    for u in db.scalars(consulta.order_by(Usuario.criado_em.desc(), Usuario.id.desc()).limit(limite)):
        detalhe = None
        if u.abrigo:
            detalhe = f"{u.abrigo.nome_abrigo} ({SELO[u.abrigo.status_validacao]})"
        elif u.apoiador:
            detalhe = u.apoiador.tipo_estabelecimento.value
        elif u.tutor:
            detalhe = u.tutor.cidade
        saida.append(UsuarioResumoOut(id=u.id, nome=u.nome, email=u.email, tipo_conta=u.tipo_conta.value, ativo=u.ativo,
                                      criado_em=u.criado_em, detalhe=detalhe))
    return saida


# ---------- painel da administração (RF-38) ----------

@router.get("/admin/painel", response_model=PainelAdminOut)
def painel_admin(p: Periodo = Depends(periodo), _: Usuario = Depends(somente_admin), db: Session = Depends(get_db)) -> PainelAdminOut:
    """Painel da administração (RF-38): contas, abrigos, animais e a atividade do período (interesses, adoções, reencontros, doações)."""
    contar = lambda modelo, *cond: db.scalar(select(func.count()).select_from(modelo).where(*cond)) or 0  # noqa: E731
    contas = db.execute(select(Usuario.tipo_conta, func.count()).where(Usuario.ativo.is_(True)).group_by(Usuario.tipo_conta)).all()
    abrigos = db.execute(select(Abrigo.status_validacao, func.count()).group_by(Abrigo.status_validacao)).all()
    animais = db.execute(select(Animal.status, func.count()).group_by(Animal.status)).all()

    no_periodo = {
        "interesses": contar(Interesse, _no(Interesse.criado_em, p)),
        "adocoes_aprovadas": contar(LogAuditoria, LogAuditoria.acao == "interesse.aprovado", _no(LogAuditoria.criado_em, p)),
        "perdidos": contar(AnimalPerdido, _no(AnimalPerdido.criado_em, p)),
        "resolvidos": contar(LogAuditoria, LogAuditoria.acao == "perdido.resolvido", _no(LogAuditoria.criado_em, p)),
        "avistamentos": contar(Avistamento, _no(Avistamento.criado_em, p)),
        "doacoes_confirmadas": contar(Doacao, Doacao.status == StatusDoacao.CONFIRMADA, _no(Doacao.confirmado_em, p)),
        "novas_contas": contar(Usuario, _no(Usuario.criado_em, p)),
    }
    agora = {
        "doacoes_aguardando": contar(Doacao, Doacao.status == StatusDoacao.AGUARDANDO_CONFIRMACAO),
        "necessidades_abertas": contar(Necessidade, Necessidade.status == StatusNecessidade.ABERTA),
        "perdidos_ativos": contar(AnimalPerdido, AnimalPerdido.resolvido.is_(False)),
        "abrigos_para_verificar": contar(Abrigo, Abrigo.status_validacao == StatusValidacao.PENDENTE),
        "denuncias_pendentes": contar(Denuncia, Denuncia.status == StatusDenuncia.PENDENTE),
    }
    desde = _inicio_serie(p)
    _, fim = _limites(p)
    serie = _serie(
        p,
        db.scalars(select(Interesse.criado_em).where(Interesse.criado_em >= desde, Interesse.criado_em < fim)),
        list(db.scalars(select(AnimalPerdido.criado_em).where(AnimalPerdido.criado_em >= desde, AnimalPerdido.criado_em < fim)))
        + list(db.scalars(select(Avistamento.criado_em).where(Avistamento.criado_em >= desde, Avistamento.criado_em < fim))),
        db.scalars(select(Doacao.confirmado_em).where(Doacao.status == StatusDoacao.CONFIRMADA, Doacao.confirmado_em >= desde, Doacao.confirmado_em < fim)),
    )
    ultimas = db.execute(
        select(LogAuditoria, Usuario).join(Usuario, Usuario.id == LogAuditoria.usuario_id)
        .order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc()).limit(8)
    ).tuples()
    return PainelAdminOut(
        periodo=p, contas=_contagem(contas), abrigos=_contagem(abrigos), animais=_contagem(animais),
        no_periodo=no_periodo, agora=agora, serie_mensal=serie, ultimas_acoes=[_log_out(log, u) for log, u in ultimas],
    )


@router.get("/admin/relatorios/abrigos.csv")
def abrigos_csv(p: Periodo = Depends(periodo), _: Usuario = Depends(somente_admin), db: Session = Depends(get_db)) -> Response:
    """Uma linha por abrigo: situação, animais e o movimento do período (adoções e doações)."""
    aprovacoes = Counter(
        u for (u,) in db.execute(select(LogAuditoria.usuario_id).where(LogAuditoria.acao == "interesse.aprovado", _no(LogAuditoria.criado_em, p)))
    )
    doacoes = dict(db.execute(
        select(Doacao.abrigo_id, func.count()).where(Doacao.status == StatusDoacao.CONFIRMADA, _no(Doacao.confirmado_em, p)).group_by(Doacao.abrigo_id)
    ).all())
    disponiveis = dict(db.execute(select(Animal.abrigo_id, func.count()).where(Animal.status == StatusAnimal.DISPONIVEL, Animal.removido_em.is_(None)).group_by(Animal.abrigo_id)).all())
    abertas = dict(db.execute(select(Necessidade.abrigo_id, func.count()).where(Necessidade.status == StatusNecessidade.ABERTA).group_by(Necessidade.abrigo_id)).all())
    situacao = {"aprovado": "Verificado", "pendente": "Não verificado", "rejeitado": "Suspenso"}
    linhas = db.execute(select(Abrigo, Usuario).join(Usuario, Usuario.id == Abrigo.usuario_id).order_by(Abrigo.nome_abrigo)).tuples()
    return _csv(
        f"abrigos-{p.de}-a-{p.ate}.csv",
        ["Abrigo", "Responsável", "E-mail", "Situação", "Animais disponíveis", "Adoções aprovadas no período",
         "Doações confirmadas no período", "Necessidades em aberto"],
        ([a.nome_abrigo, u.nome, u.email, situacao[a.status_validacao.value], disponiveis.get(a.usuario_id, 0),
          aprovacoes.get(a.usuario_id, 0), doacoes.get(a.usuario_id, 0), abertas.get(a.usuario_id, 0)] for a, u in linhas),
    )


# ---------- relatório do abrigo (RF-40) ----------

def _tempo_medio_adocao(db: Session, abrigo_id: int, p: Periodo) -> tuple[int, float | None]:
    """Aprovações no período (pelo histórico) e a média de dias entre a entrada do animal no abrigo (ou o cadastro,
    se a entrada não foi informada) e a aprovação do interesse."""
    aprovacoes = list(db.scalars(select(LogAuditoria).where(
        LogAuditoria.acao == "interesse.aprovado", LogAuditoria.usuario_id == abrigo_id, _no(LogAuditoria.criado_em, p),
    )))
    dias = []
    for log in aprovacoes:
        animal = db.get(Animal, auditoria.detalhes(log).get("animal_id"))
        if animal is None:  # animal excluído depois: a aprovação conta, o tempo não
            continue
        # Dias de calendário: entrou no dia 10 e foi aprovado no dia 20 = 10 dias.
        entrada = _dia(animal.data_entrada) if animal.data_entrada else _local(animal.criado_em).date()
        dias.append(max((_local(log.criado_em).date() - entrada).days, 0))
    return len(aprovacoes), (round(sum(dias) / len(dias), 1) if dias else None)


PREVIA = 5  # linhas de cada lista no relatório; o resto vem de /relatorios/abrigo/lista/{lista}


def _confirmadas(aid: int, p: Periodo):
    return (Doacao.abrigo_id == aid) & (Doacao.status == StatusDoacao.CONFIRMADA) & _no(Doacao.confirmado_em, p)


def _origem(db: Session, aid: int, p: Periodo) -> list[tuple[str, int]]:
    """Cidade dos interessados. Agrupa pela coluna e trata a cidade vazia aqui: agrupar por coalesce(cidade, '...')
    passa no SQLite mas o PostgreSQL recusa (cada cópia do texto vira um parâmetro diferente)."""
    por_cidade = Counter()
    for cidade, total in db.execute(
        select(Tutor.cidade, func.count())
        .select_from(Interesse).join(Animal, Animal.id == Interesse.animal_id).join(Tutor, Tutor.usuario_id == Interesse.tutor_id)
        .where(Animal.abrigo_id == aid, _no(Interesse.criado_em, p)).group_by(Tutor.cidade)
    ):
        por_cidade[(cidade or "").strip() or "Não informada"] += total
    return sorted(por_cidade.items(), key=lambda c: (-c[1], c[0]))


def _apoiadores(db: Session, aid: int, p: Periodo) -> list[tuple[str, int, int]]:
    linhas = db.execute(
        select(Usuario.nome, func.count(Doacao.id), func.sum(Doacao.quantidade)).join(Usuario, Usuario.id == Doacao.apoiador_id)
        .where(_confirmadas(aid, p)).group_by(Usuario.id, Usuario.nome).order_by(func.count(Doacao.id).desc(), Usuario.nome)
    ).all()
    return [(n, int(c), int(q or 0)) for n, c, q in linhas]


def _itens(db: Session, aid: int, p: Periodo) -> list[tuple[str, int]]:
    linhas = db.execute(
        select(Doacao.item, func.sum(Doacao.quantidade)).where(_confirmadas(aid, p))
        .group_by(Doacao.item).order_by(func.sum(Doacao.quantidade).desc(), Doacao.item)
    ).all()
    return [(i, int(q or 0)) for i, q in linhas]


# Listas do relatório que podem crescer sem limite: colunas e a função que calcula a lista inteira, ordenada.
LISTAS = {
    "origem": (["Cidade", "Interesses"], _origem),
    "apoiadores": (["Apoiador", "Doações", "Itens"], _apoiadores),
    "itens": (["Item", "Quantidade"], _itens),
}


@router.get("/relatorios/abrigo", response_model=RelatorioAbrigoOut)
def relatorio_abrigo(p: Periodo = Depends(periodo), abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> RelatorioAbrigoOut:
    """Relatório do abrigo (RF-40) no período: animais, interesses, adoções e tempo médio, doações, apoiadores e necessidades."""
    aid = abrigo.usuario_id
    animais = db.execute(select(Animal.status, func.count()).where(Animal.abrigo_id == aid).group_by(Animal.status)).all()
    interesses = db.execute(
        select(Interesse.status, func.count()).join(Animal, Animal.id == Interesse.animal_id)
        .where(Animal.abrigo_id == aid, _no(Interesse.criado_em, p)).group_by(Interesse.status)
    ).all()
    aprovadas, tempo = _tempo_medio_adocao(db, aid, p)
    doacoes = db.execute(
        select(Doacao.status, func.count()).where(Doacao.abrigo_id == aid, _no(Doacao.registrado_em, p)).group_by(Doacao.status)
    ).all()
    origem, apoiadores, itens = (LISTAS[nome][1](db, aid, p) for nome in ("origem", "apoiadores", "itens"))
    necessidades = db.execute(select(Necessidade.status, func.count()).where(Necessidade.abrigo_id == aid).group_by(Necessidade.status)).all()

    desde = _inicio_serie(p)
    _, fim = _limites(p)
    serie = _serie(
        p,
        db.scalars(select(Interesse.criado_em).join(Animal, Animal.id == Interesse.animal_id)
                   .where(Animal.abrigo_id == aid, Interesse.criado_em >= desde, Interesse.criado_em < fim)),
        [],  # o reencontro não pertence a um abrigo
        db.scalars(select(Doacao.confirmado_em).where(Doacao.abrigo_id == aid, Doacao.status == StatusDoacao.CONFIRMADA,
                                                      Doacao.confirmado_em >= desde, Doacao.confirmado_em < fim)),
    )
    return RelatorioAbrigoOut(
        periodo=p, animais=_contagem(animais), interesses=_contagem(interesses), adocoes_aprovadas=aprovadas,
        tempo_medio_adocao_dias=tempo, origem_interessados=_contagem(origem[:PREVIA]), doacoes=_contagem(doacoes),
        por_apoiador=[ApoiadorDoAbrigo(nome=n, doacoes=c, quantidade=q) for n, c, q in apoiadores[:PREVIA]],
        por_item=_contagem(itens[:PREVIA]), necessidades=_contagem(necessidades), serie_mensal=serie,
        totais_listas={"origem": len(origem), "apoiadores": len(apoiadores), "itens": len(itens)},
    )


@router.get("/relatorios/abrigo/lista/{lista}", response_model=PaginaLinhas)
def lista_completa(
    lista: Literal["origem", "apoiadores", "itens"],
    p: Periodo = Depends(periodo),
    limite: int = Query(default=20, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
    abrigo: Abrigo = Depends(get_abrigo_operante),
    db: Session = Depends(get_db),
) -> PaginaLinhas:
    """Uma lista do relatório inteira, em páginas: a tela mostra só as primeiras e busca o resto quando pedem."""
    colunas, calcular = LISTAS[lista]
    linhas = calcular(db, abrigo.usuario_id, p)
    return PaginaLinhas(
        total=len(linhas), colunas=colunas,
        itens=[LinhaRelatorio(rotulo=str(r[0]), valores=[int(v) for v in r[1:]]) for r in linhas[deslocamento:deslocamento + limite]],
    )


@router.get("/relatorios/abrigo/historico", response_model=PaginaLogs)
def historico_abrigo(
    p: Periodo = Depends(periodo), acao: str | None = None, q: str | None = None,
    limite: int = Query(default=50, ge=1, le=500), deslocamento: int = Query(default=0, ge=0),
    abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db),
) -> PaginaLogs:
    """As operações feitas pela própria conta do abrigo."""
    consulta = _consulta_logs(p, acao, q, None, usuario_id=abrigo.usuario_id)
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    linhas = db.execute(consulta.order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc()).offset(deslocamento).limit(limite)).tuples()
    return PaginaLogs(total=total or 0, itens=[_log_out(log, u) for log, u in linhas])


STATUS_INTERESSE = {"aguardando": "Aguardando", "em_conversa": "Em conversa", "aprovado": "Aprovado", "recusado": "Recusado"}
STATUS_DOACAO = {"aguardando_confirmacao": "Aguardando confirmação", "confirmada": "Confirmada", "recusada": "Não recebida"}


@router.get("/relatorios/abrigo/interesses.csv")
def interesses_csv(p: Periodo = Depends(periodo), abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> Response:
    """Interesses recebidos no período, em CSV."""
    linhas = db.execute(
        select(Interesse, Animal, Usuario, Tutor).join(Animal, Animal.id == Interesse.animal_id)
        .join(Usuario, Usuario.id == Interesse.tutor_id).join(Tutor, Tutor.usuario_id == Interesse.tutor_id)
        .where(Animal.abrigo_id == abrigo.usuario_id, _no(Interesse.criado_em, p)).order_by(Interesse.criado_em.desc())
    ).tuples()
    return _csv(
        f"interesses-{p.de}-a-{p.ate}.csv", ["Data", "Animal", "Interessado", "E-mail", "Telefone", "Cidade", "Situação"],
        ([_data(i.criado_em), a.nome, u.nome, u.email, t.telefone or "", t.cidade or "", STATUS_INTERESSE[i.status.value]] for i, a, u, t in linhas),
    )


@router.get("/relatorios/abrigo/doacoes.csv")
def doacoes_csv(p: Periodo = Depends(periodo), abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> Response:
    """Doações registradas no período, em CSV (inclui pessoa física e o valor das doações em dinheiro)."""
    linhas = db.execute(
        select(Doacao, Usuario, Apoiador).join(Usuario, Usuario.id == Doacao.apoiador_id).outerjoin(Apoiador, Apoiador.usuario_id == Doacao.apoiador_id)
        .where(Doacao.abrigo_id == abrigo.usuario_id, _no(Doacao.registrado_em, p)).order_by(Doacao.registrado_em.desc())
    ).tuples()
    return _csv(
        f"doacoes-{p.de}-a-{p.ate}.csv",
        ["Registrada em", "Quem doou", "Categoria", "Item", "Quantidade", "Valor (R$)", "Situação", "Confirmada em"],
        ([_data(d.registrado_em), u.nome, ap.tipo_estabelecimento.value if ap else TipoEstabelecimento.PESSOA_FISICA.value, d.item,
          d.quantidade, f"{d.valor_centavos / 100:.2f}".replace(".", ",") if d.valor_centavos is not None else "",
          STATUS_DOACAO[d.status.value], _data(d.confirmado_em)] for d, u, ap in linhas),
    )


@router.get("/relatorios/abrigo/animais.csv")
def animais_csv(abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> Response:
    """Todos os animais do abrigo (é um retrato de hoje, sem período)."""
    animais = db.scalars(select(Animal).where(Animal.abrigo_id == abrigo.usuario_id).order_by(Animal.nome))
    return _csv(
        "animais.csv", ["Nome", "Espécie", "Porte", "Sexo", "Idade (meses)", "Situação", "Entrada no abrigo", "Cadastrado em"],
        ([a.nome, a.especie.value, a.porte, a.sexo.value, a.idade_estimada_meses or "", a.status.value,
          _dia(a.data_entrada).strftime("%d/%m/%Y") if a.data_entrada else "", _data(a.criado_em)] for a in animais),
    )
