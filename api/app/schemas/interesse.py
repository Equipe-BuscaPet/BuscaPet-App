"""Interesse de adoção — RF-16."""
import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import StatusInteresse


class InteresseCreate(BaseModel):
    mensagem: str | None = Field(default=None, max_length=500, description="Apresentação do adotante (opcional)")

    @field_validator("mensagem")
    @classmethod
    def _sem_espacos_nas_pontas(cls, v: str | None) -> str | None:
        v = v.strip() if v else v
        return v or None


class DecisaoInteresse(BaseModel):
    status: Literal[StatusInteresse.EM_CONVERSA, StatusInteresse.APROVADO, StatusInteresse.RECUSADO]


class InteresseTutorOut(BaseModel):
    """O que o adotante vê. O contato do abrigo só aparece depois do interesse registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: int
    animal_nome: str
    nome_abrigo: str
    abrigo_telefone: str | None
    abrigo_endereco: str
    status: StatusInteresse
    mensagem: str | None
    criado_em: datetime.datetime


class InteresseAbrigoOut(BaseModel):
    """O que o abrigo vê: quem se interessou e como falar com a pessoa."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: int
    animal_nome: str
    tutor_nome: str
    tutor_email: str
    tutor_telefone: str | None
    tutor_cidade: str | None
    status: StatusInteresse
    mensagem: str | None
    criado_em: datetime.datetime
