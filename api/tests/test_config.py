"""Configuração: a API não sobe em um banco de verdade com a chave de exemplo que assina os logins."""
import pytest
from pydantic import ValidationError

from app.core.config import SEGREDO_PADRAO, Settings

SUPABASE = "postgresql+psycopg://usuario:senha@exemplo.pooler.supabase.com:6543/postgres"


@pytest.mark.parametrize("url", ["postgresql+psycopg://u:s@localhost:5432/b", "postgresql+psycopg://u:s@db:5432/b", "sqlite://"])
def test_segredo_de_exemplo_vale_em_banco_local(url):
    assert Settings(database_url=url, jwt_secret=SEGREDO_PADRAO).jwt_secret == SEGREDO_PADRAO


def test_banco_de_verdade_exige_segredo_proprio():
    with pytest.raises(ValidationError, match="Defina JWT_SECRET"):
        Settings(database_url=SUPABASE, jwt_secret=SEGREDO_PADRAO)
    assert Settings(database_url=SUPABASE, jwt_secret="x" * 48).database_url == SUPABASE


def test_url_do_banco_ganha_o_driver_quando_a_hospedagem_entrega_so_postgresql():
    from app.core.config import normalizar_url_banco

    assert normalizar_url_banco("postgresql://u:p@host:5432/db") == "postgresql+psycopg://u:p@host:5432/db"
    assert normalizar_url_banco("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalizar_url_banco(" postgresql+psycopg://u:p@h/db ") == "postgresql+psycopg://u:p@h/db"
