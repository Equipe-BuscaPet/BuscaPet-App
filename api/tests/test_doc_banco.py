"""A documentação do banco acompanha os modelos: o MER (docs/mer.md) é gerado deles e o schema.sql tem as mesmas
tabelas e colunas."""
import re

from app.db.base import Base
from app.scripts.gerar_mer import DESTINO, MODULOS, _carregar_modelos, gerar

SCHEMA = DESTINO.parent / "schema.sql"
PALAVRAS_DE_RESTRICAO = {"PRIMARY", "UNIQUE", "CONSTRAINT", "FOREIGN", "CHECK"}


def _tabelas_do_schema_sql() -> dict[str, set[str]]:
    texto = re.sub(r"--[^\n]*", "", SCHEMA.read_text(encoding="utf-8"))
    tabelas = {}
    for nome, corpo in re.findall(r"CREATE TABLE (\w+)\s*\((.*?)\n\);", texto, flags=re.S):
        colunas = set()
        for linha in corpo.splitlines():
            primeira = linha.strip().split(" ")[0].rstrip(",")
            if primeira and primeira.upper() not in PALAVRAS_DE_RESTRICAO:
                colunas.add(primeira)
        tabelas[nome] = colunas
    return tabelas


def test_mer_esta_em_dia_com_os_modelos():
    atual = DESTINO.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert atual == gerar(), "docs/mer.md desatualizado: rode `python -m app.scripts.gerar_mer` na pasta api/"


def test_todo_modelo_esta_em_um_modulo_do_mer():
    _carregar_modelos()
    assert set(Base.metadata.tables) == set().union(*MODULOS.values())


def test_schema_sql_tem_as_mesmas_tabelas_e_colunas_dos_modelos():
    _carregar_modelos()
    modelos = {nome: {c.name for c in t.columns} for nome, t in Base.metadata.tables.items()}
    schema = _tabelas_do_schema_sql()
    assert set(schema) == set(modelos)
    for nome, colunas in modelos.items():
        assert schema[nome] == colunas, f"{nome}: só no schema.sql {schema[nome] - colunas}, só nos modelos {colunas - schema[nome]}"
