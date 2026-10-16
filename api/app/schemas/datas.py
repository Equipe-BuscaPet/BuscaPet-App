"""Tipo para datas "do dia" guardadas em colunas DateTime(timezone=True).

O formulário envia só a data (ex.: 14/10), e a rota grava meia-noite em UTC (`_para_datetime`). Ao ler,
o Postgres devolve esse instante no fuso da conexão: em Recife (UTC-3), `2026-10-13 21:00-03:00`.
Pegar `.date()` daí mostraria o dia anterior. Por isso a saída converte de volta para UTC antes de
extrair a data. O SQLite dos testes não guarda fuso, e o defeito só aparecia no Postgres.
"""
import datetime
from typing import Annotated

from pydantic import BeforeValidator


def _dia_em_utc(valor):
    if isinstance(valor, datetime.datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(datetime.UTC)
        return valor.date()
    return valor


DataDoDia = Annotated[datetime.date, BeforeValidator(_dia_em_utc)]
