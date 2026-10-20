"""Dashboard, relatórios, pesquisa e histórico — RF-38, RF-39, RF-40 (Sprint 7 oficial)."""
import datetime

from pydantic import BaseModel


class Periodo(BaseModel):
    de: datetime.date
    ate: datetime.date


class PontoMensal(BaseModel):
    mes: str  # AAAA-MM
    interesses: int
    registros_reencontro: int  # perdidos + avistamentos
    doacoes_confirmadas: int


class Contagem(BaseModel):
    chave: str
    total: int


class LogOut(BaseModel):
    id: int
    criado_em: datetime.datetime
    usuario_id: int
    usuario_nome: str
    usuario_email: str
    tipo_conta: str
    acao: str
    rotulo: str
    entidade_tipo: str
    entidade_id: int
    detalhes: dict


class PaginaLogs(BaseModel):
    total: int
    itens: list[LogOut]


class PainelAdminOut(BaseModel):
    periodo: Periodo
    contas: list[Contagem]  # por tipo de conta (ativas)
    abrigos: list[Contagem]  # verificado / nao_verificado / suspenso
    animais: list[Contagem]  # por situação, hoje
    no_periodo: dict[str, int]  # interesses, adocoes_aprovadas, perdidos, resolvidos, avistamentos, doacoes_confirmadas, novas_contas
    agora: dict[str, int]  # doacoes_aguardando, necessidades_abertas, perdidos_ativos, abrigos_para_verificar
    serie_mensal: list[PontoMensal]
    ultimas_acoes: list[LogOut]


class ApoiadorDoAbrigo(BaseModel):
    nome: str
    doacoes: int
    quantidade: int


class RelatorioAbrigoOut(BaseModel):
    periodo: Periodo
    animais: list[Contagem]
    interesses: list[Contagem]  # por situação, criados no período
    adocoes_aprovadas: int
    tempo_medio_adocao_dias: float | None  # do cadastro/entrada do animal até a aprovação
    origem_interessados: list[Contagem]  # cidade do tutor (só as primeiras; ver totais_listas)
    doacoes: list[Contagem]  # por situação, registradas no período
    por_apoiador: list[ApoiadorDoAbrigo]  # confirmadas no período (só os primeiros)
    por_item: list[Contagem]  # quantidade confirmada no período (só os primeiros)
    totais_listas: dict[str, int]  # quantas linhas cada lista tem: origem, apoiadores, itens
    necessidades: list[Contagem]  # aberta / atendida (hoje)
    serie_mensal: list[PontoMensal]


class LinhaRelatorio(BaseModel):
    rotulo: str
    valores: list[int]


class PaginaLinhas(BaseModel):
    """Uma lista do relatório completa, em páginas (carregada só quando a pessoa pede para ver tudo)."""

    total: int
    colunas: list[str]
    itens: list[LinhaRelatorio]


class UsuarioResumoOut(BaseModel):
    id: int
    nome: str
    email: str
    tipo_conta: str
    ativo: bool
    criado_em: datetime.datetime
    detalhe: str | None  # nome do abrigo (com selo), tipo de estabelecimento ou cidade
