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
    """Para uma necessidade do mural (`necessidade_id`) ou avulsa (`abrigo_id` + `item`)."""

    necessidade_id: int | None = None
    abrigo_id: int | None = None
    item: str | None = Field(default=None, min_length=2, max_length=200)
    quantidade: int = Field(ge=1, le=10000)

    _apara_item = field_validator("item", mode="before")(_apara)

    @model_validator(mode="after")
    def _destino(self):
        if self.necessidade_id is None and (self.abrigo_id is None or not self.item):
            raise ValueError("Escolha uma necessidade do mural ou informe o abrigo e o item.")
        return self


class DecisaoDoacao(BaseModel):
    status: Literal[StatusDoacao.CONFIRMADA, StatusDoacao.RECUSADA]


class DoacaoOut(BaseModel):
    id: int
    apoiador_id: int
    nome_apoiador: str
    abrigo_id: int
    nome_abrigo: str
    necessidade_id: int | None
    item: str
    quantidade: int
    status: StatusDoacao
    registrado_em: datetime.datetime
    confirmado_em: datetime.datetime | None
    # Para combinar a entrega: o abrigo vê o e-mail do apoiador; o apoiador vê telefone e endereço do abrigo.
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
    necessidades: list[NecessidadeOut]  # só com o selo Verificado
    apoiadores: list[ApoiadorResumo]  # quem já teve doação confirmada por este abrigo
