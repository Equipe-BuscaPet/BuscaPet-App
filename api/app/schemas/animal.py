"""Schemas do animal para adoção — RF-17."""
import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Especie, Sexo, StatusAnimal

Porte = Literal["pequeno", "medio", "grande"]


class AnimalCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    especie: Especie
    raca_aproximada: str | None = Field(default=None, max_length=120)
    porte: Porte
    idade_estimada_meses: int | None = Field(default=None, ge=0, le=600)
    sexo: Sexo
    castrado: bool = False
    vacinado: bool = False
    vermifugado: bool = False
    temperamento: str | None = Field(default=None, max_length=500)
    convivencia_criancas: bool | None = None
    convivencia_outros_animais: bool | None = None
    historia_resgate: str | None = Field(default=None, max_length=2000)
    data_entrada: datetime.date | None = None
    condicao_chegada: str | None = Field(default=None, max_length=500)


class AnimalUpdate(BaseModel):
    """Atualização parcial (PATCH): só os campos enviados mudam."""

    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    especie: Especie | None = None
    raca_aproximada: str | None = Field(default=None, max_length=120)
    porte: Porte | None = None
    idade_estimada_meses: int | None = Field(default=None, ge=0, le=600)
    sexo: Sexo | None = None
    castrado: bool | None = None
    vacinado: bool | None = None
    vermifugado: bool | None = None
    temperamento: str | None = Field(default=None, max_length=500)
    convivencia_criancas: bool | None = None
    convivencia_outros_animais: bool | None = None
    historia_resgate: str | None = Field(default=None, max_length=2000)
    data_entrada: datetime.date | None = None
    condicao_chegada: str | None = Field(default=None, max_length=500)
    status: StatusAnimal | None = None


class AnimalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    abrigo_id: int
    nome_abrigo: str | None = None
    nome: str
    especie: Especie
    raca_aproximada: str | None
    porte: str
    idade_estimada_meses: int | None
    sexo: Sexo
    castrado: bool
    vacinado: bool
    vermifugado: bool
    temperamento: str | None
    convivencia_criancas: bool | None
    convivencia_outros_animais: bool | None
    historia_resgate: str | None
    data_entrada: datetime.datetime | None
    condicao_chegada: str | None
    status: StatusAnimal
    criado_em: datetime.datetime
