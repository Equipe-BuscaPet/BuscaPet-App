"""Doações e reconhecimento — RF-30 a RF-35: necessidades, doações, ranking e perfis públicos."""
import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import StatusDoacao, StatusNecessidade, TipoEstabelecimento, UrgenciaNecessidade


def _apara(v):
    return v.strip() if isinstance(v, str) else v


# ---------- necessidades (RF-30) ----------

class NecessidadeIn(BaseModel):
    item: str = Field(min_length=2, max_length=200, description="Ex.: ração para cão adulto (saco de 15 kg)")
    quantidade: int = Field(ge=1, le=10000)
    urgencia: UrgenciaNecessidade = UrgenciaNecessidade.MEDIA

    _apara_item = field_validator("item", mode="before")(_apara)


class NecessidadeEdicao(BaseModel):
    """Tudo opcional: só muda o que vier. `status` reabre ou marca como atendida."""

    item: str | None = Field(default=None, min_length=2, max_length=200)
    quantidade: int | None = Field(default=None, ge=1, le=10000)
    urgencia: UrgenciaNecessidade | None = None
    status: StatusNecessidade | None = None

    _apara_item = field_validator("item", mode="before")(_apara)


class NecessidadeOut(BaseModel):
    id: int
    abrigo_id: int
    nome_abrigo: str
    item: str
    quantidade: int
    quantidade_recebida: int  # soma das doações confirmadas
    urgencia: UrgenciaNecessidade
    status: StatusNecessidade
    criado_em: datetime.datetime
    distancia_km: float | None = None


# ---------- doações (RF-31, RF-32) ----------

class DoacaoIn(BaseModel):
    """Três formas: para uma necessidade do mural (`necessidade_id`), avulsa de itens (`abrigo_id` + `item`) ou em
    dinheiro (`abrigo_id` + `valor_centavos`, depois de fazer o PIX para a chave do abrigo)."""

    necessidade_id: int | None = None
    abrigo_id: int | None = None
    item: str | None = Field(default=None, min_length=2, max_length=200)
    quantidade: int = Field(default=1, ge=1, le=10000)
    valor_centavos: int | None = Field(default=None, ge=100, le=10_000_000, description="R$ 50,00 = 5000; mínimo R$ 1,00")

    _apara_item = field_validator("item", mode="before")(_apara)

    @model_validator(mode="after")
    def _destino(self):
        if self.valor_centavos is not None:
            if self.abrigo_id is None or self.necessidade_id is not None or self.item:
                raise ValueError("A doação em dinheiro vai para o abrigo: informe só o abrigo e o valor.")
        elif self.necessidade_id is None and (self.abrigo_id is None or not self.item):
            raise ValueError("Escolha uma necessidade do mural ou informe o abrigo e o item.")
        return self


class DecisaoDoacao(BaseModel):
    status: Literal[StatusDoacao.CONFIRMADA, StatusDoacao.RECUSADA]


class DoacaoOut(BaseModel):
    id: int
    apoiador_id: int  # quem doou (apoiador ou tutor)
    nome_apoiador: str
    perfil_publico_doador: bool = True  # tutor (pessoa física) não tem página de perfil
    abrigo_id: int
    nome_abrigo: str
    necessidade_id: int | None
    item: str
    quantidade: int
    valor_centavos: int | None = None  # doação em dinheiro
    status: StatusDoacao
    registrado_em: datetime.datetime
    confirmado_em: datetime.datetime | None
    # Para combinar a entrega: o abrigo vê o e-mail de quem doa; quem doa vê telefone e endereço do abrigo.
    contato: str | None = None


# ---------- ranking e perfis (RF-33, RF-34, RF-12) ----------

class PosicaoRanking(BaseModel):
    posicao: int
    apoiador_id: int
    nome: str
    tipo_estabelecimento: TipoEstabelecimento
    pontos: float
    pontos_volume: float
    pontos_regularidade: float
    doacoes_confirmadas: int
    meses_seguidos: int
    selo_ativo: bool
    perfil_publico: bool = True  # pessoa física (tutor) não tem página de perfil


class ApoiadorResumo(BaseModel):
    id: int
    nome: str
    tipo_estabelecimento: TipoEstabelecimento
    selo_ativo: bool
    latitude: float | None = None
    longitude: float | None = None


class AbrigoApoiado(BaseModel):
    id: int
    nome_abrigo: str
    doacoes_confirmadas: int


class ApoiadorPerfilOut(ApoiadorResumo):
    endereco: str
    pontos_mes: float
    pontos_ano: float
    meses_seguidos: int
    doacoes_confirmadas: int
    abrigos_apoiados: list[AbrigoApoiado]
    membro_desde: datetime.datetime


class MetaMensalOut(BaseModel):
    """Meta de gastos do mês (RF-31): o que o abrigo precisa e quanto já foi confirmado no mês (fuso de Recife)."""

    mes: str  # AAAA-MM
    valor_centavos: int
    descricao: str | None
    arrecadado_centavos: int
    doacoes_confirmadas: int


class AbrigoPerfilOut(BaseModel):
    id: int
    nome_abrigo: str
    endereco: str
    latitude: float
    longitude: float
    telefone: str | None
    horario_funcionamento: str | None
    descricao: str | None
    verificado: bool
    animais_disponiveis: int
    chave_doacao_financeira: str | None  # só com o selo Verificado (risco de golpe)
    meta_mensal: MetaMensalOut | None = None  # só com o selo Verificado e a meta definida
    necessidades: list[NecessidadeOut]  # só com o selo Verificado
    apoiadores: list[ApoiadorResumo]  # quem já teve doação confirmada por este abrigo
