"""Abrigo como aparece no mapa público — só dados institucionais, nada de e-mail ou conta."""
from pydantic import BaseModel


class AbrigoMapaOut(BaseModel):
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
    distancia_km: float | None = None
