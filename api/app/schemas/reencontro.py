"""Animal perdido (RF-19) e avistamento (RF-20).

Os dados chegam como um único formulário multipart: os campos e as fotos (`fotos`, de 1 a 5) no mesmo
envio, para o registro nunca ficar sem foto. O FastAPI 0.115 só aceita modelo de formulário se ele for o
único parâmetro do corpo, por isso as fotos são um campo do próprio modelo.

Na saída, as coordenadas públicas são **aproximadas** (escopo, seção 9): quem consulta vê a região, não o
ponto exato; só o autor do registro vê o ponto que marcou.
"""
import datetime
from typing import Literal

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Especie, Sexo

Porte = Literal["pequeno", "medio", "grande"]


class _CaracteristicasIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    especie: Especie
    porte: Porte
    cor_predominante: str = Field(min_length=2, max_length=60)
    pelagem: str | None = Field(default=None, max_length=60)
    sexo: Sexo = Sexo.INDEFINIDO
    sinais_particulares: str | None = Field(default=None, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    # Opcional aqui só para a falta de foto cair na mensagem amigável da rota ("envie pelo menos uma foto").
    fotos: list[UploadFile] | None = Field(default=None, description="De 1 a 5 fotos (JPEG, PNG ou WebP)")

    @field_validator("cor_predominante", mode="before")
    @classmethod
    def _apara(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("pelagem", "sinais_particulares", mode="before")
    @classmethod
    def _vazio_vira_nulo(cls, v):
        # Campo opcional de formulário deixado em branco chega como "": é "não informado".
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


def _nao_no_futuro(dia: datetime.date) -> datetime.date:
    # Folga de um dia por causa do fuso horário de quem envia.
    if dia > datetime.date.today() + datetime.timedelta(days=1):
        raise ValueError("A data não pode estar no futuro.")
    return dia


class PerdidoIn(_CaracteristicasIn):
    raio_busca_km: float = Field(default=5.0, gt=0, le=100)
    data_desaparecimento: datetime.date

    _checa_data = field_validator("data_desaparecimento")(_nao_no_futuro)


class AvistamentoIn(_CaracteristicasIn):
    data_avistamento: datetime.date

    _checa_data = field_validator("data_avistamento")(_nao_no_futuro)


class _RegistroOut(BaseModel):
    id: int
    especie: Especie
    porte: str
    cor_predominante: str
    pelagem: str | None
    sexo: Sexo
    sinais_particulares: str | None
    latitude: float
    longitude: float
    localizacao_aproximada: bool
    fotos: list[str]
    criado_em: datetime.datetime
    distancia_km: float | None = None


class PerdidoOut(_RegistroOut):
    raio_busca_km: float
    data_desaparecimento: datetime.datetime
    resolvido: bool


class AvistamentoOut(_RegistroOut):
    data_avistamento: datetime.datetime
