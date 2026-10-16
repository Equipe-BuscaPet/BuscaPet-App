"""Datas "do dia" não podem voltar um dia por causa do fuso do banco (ver app/schemas/datas.py)."""
import datetime

from pydantic import BaseModel

from app.schemas.datas import DataDoDia

RECIFE = datetime.timezone(datetime.timedelta(hours=-3))


class _Exemplo(BaseModel):
    dia: DataDoDia
    opcional: DataDoDia | None = None


def test_meia_noite_utc_lida_no_fuso_de_recife_continua_no_mesmo_dia():
    # É assim que o Postgres devolve "14/10 00:00 UTC" para uma conexão em America/Recife.
    lido_do_banco = datetime.datetime(2026, 10, 13, 21, 0, tzinfo=RECIFE)
    assert _Exemplo(dia=lido_do_banco).dia == datetime.date(2026, 10, 14)


def test_datetime_sem_fuso_como_no_sqlite():
    assert _Exemplo(dia=datetime.datetime(2026, 10, 14)).dia == datetime.date(2026, 10, 14)


def test_data_e_nulo_passam_direto():
    exemplo = _Exemplo(dia=datetime.date(2026, 10, 14), opcional=None)
    assert exemplo.dia == datetime.date(2026, 10, 14)
    assert exemplo.opcional is None
    assert _Exemplo(dia="2026-10-14").model_dump(mode="json")["dia"] == "2026-10-14"
