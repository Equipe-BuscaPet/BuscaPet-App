"""Denúncia de anúncio suspeito — RF-41 (ex.: venda disfarçada de adoção)."""
import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import StatusDenuncia


class DenunciaIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=1000, description="O que há de errado no anúncio")

    @field_validator("motivo", mode="before")
    @classmethod
    def _apara(cls, v):
        return v.strip() if isinstance(v, str) else v


class DecisaoDenuncia(BaseModel):
    """ignorado: improcedente · advertido: aviso ao abrigo · removido: anúncio sai do ar · banido: abrigo suspenso."""

    decisao: Literal[StatusDenuncia.IGNORADO, StatusDenuncia.ADVERTIDO, StatusDenuncia.REMOVIDO, StatusDenuncia.BANIDO]
    observacao: str | None = Field(default=None, max_length=500, description="Enviada ao abrigo junto com o aviso")


class DenunciaOut(BaseModel):
    id: int
    animal_id: int
    animal_nome: str
    abrigo_id: int
    nome_abrigo: str
    denunciante_nome: str
    motivo: str
    status: StatusDenuncia
    criado_em: datetime.datetime
    resolvido_em: datetime.datetime | None
    denuncias_do_animal: int  # quantas denúncias pendentes o mesmo anúncio tem
