"""Pontuação do ranking de apoiadores — RF-33 (escopo, seção 5).

Regra (decide o ponto em aberto "peso volume × regularidade"): em cada mês,
- volume       = 10 pontos por doação confirmada no mês;
- regularidade = 10 pontos por mês seguido com doação confirmada, contando o próprio mês
                 (1º mês = 10, 2º seguido = 20, 3º seguido = 30...).
Assim, manter a constância vale tanto quanto doar mais: é o que dá chance ao petshop de bairro contra a
distribuidora grande. Conta-se a doação, não a quantidade, porque "10 sacos" e "2 caixas" não se comparam.

Só doação **confirmada pelo abrigo** pontua (escopo 5.4), no mês da confirmação. O resultado fica em cache por
mês na tabela `pontuacoes_apoiador`, recalculado a cada confirmação; o ranking do ano é a soma dos meses.
"""
import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.doacao import Doacao, PontuacaoApoiador
from app.models.enums import StatusDoacao

PONTOS_POR_DOACAO = 10
PONTOS_POR_MES_SEGUIDO = 10


def mes_de(momento: datetime.datetime) -> tuple[int, int]:
    """(ano, mês) em UTC. O SQLite devolve datas sem fuso: são tratadas como UTC."""
    if momento.tzinfo is not None:
        momento = momento.astimezone(datetime.UTC)
    return momento.year, momento.month


def mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def recalcular(db: Session, apoiador_id: int) -> None:
    """Refaz todas as linhas mensais do apoiador a partir das doações confirmadas (sem commit)."""
    confirmadas = db.scalars(
        select(Doacao.confirmado_em).where(Doacao.apoiador_id == apoiador_id, Doacao.status == StatusDoacao.CONFIRMADA)
    )
    por_mes: dict[tuple[int, int], int] = {}
    for momento in confirmadas:
        chave = mes_de(momento)
        por_mes[chave] = por_mes.get(chave, 0) + 1

    db.execute(delete(PontuacaoApoiador).where(PontuacaoApoiador.apoiador_id == apoiador_id))
    seguidos: dict[tuple[int, int], int] = {}
    for ano, mes in sorted(por_mes):
        seguidos[(ano, mes)] = seguidos.get(mes_anterior(ano, mes), 0) + 1
        volume = PONTOS_POR_DOACAO * por_mes[(ano, mes)]
        regularidade = PONTOS_POR_MES_SEGUIDO * seguidos[(ano, mes)]
        db.add(PontuacaoApoiador(
            apoiador_id=apoiador_id, mes_referencia=datetime.datetime(ano, mes, 1, tzinfo=datetime.UTC),
            pontos_volume=volume, pontos_regularidade=regularidade, pontos_total=volume + regularidade,
        ))


def selo_ativo(meses_com_pontos: set[tuple[int, int]], hoje: datetime.date | None = None) -> bool:
    """Apoiador ativo = doação confirmada neste mês ou no anterior (escopo 5.2, "selo no perfil")."""
    hoje = hoje or datetime.datetime.now(datetime.UTC).date()
    atual = (hoje.year, hoje.month)
    return atual in meses_com_pontos or mes_anterior(*atual) in meses_com_pontos
