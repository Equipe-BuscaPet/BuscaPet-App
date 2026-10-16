"""Prepara o banco usado pelos testes de ponta a ponta (Playwright): cria se não existir e aplica as migrations.

Uso, a partir da pasta api/ (o Playwright chama sozinho, ver frontend/playwright.config.js):
    python -m app.scripts.preparar_banco_teste postgresql+psycopg://buscapet:buscapet@localhost:5432/buscapet_e2e

Os testes E2E criam muitas contas e registros. Rodando num banco separado, o banco de desenvolvimento (e os
dados de demonstração) ficam limpos. Por segurança, só aceita banco local e cujo nome termine em `_e2e`.
"""
import os
import subprocess
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

HOSTS_LOCAIS = {"localhost", "127.0.0.1", "db"}


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    url = make_url(sys.argv[1])
    if url.host not in HOSTS_LOCAIS or not (url.database or "").endswith("_e2e"):
        sys.exit("Recusado: o banco de teste precisa ser local e ter nome terminado em _e2e.")

    # Conecta no banco administrativo "postgres" do mesmo servidor só para criar o de teste.
    conexao = psycopg.connect(
        host=url.host, port=url.port or 5432, user=url.username, password=url.password, dbname="postgres", autocommit=True
    )
    with conexao:
        existe = conexao.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)).fetchone()
        if not existe:
            conexao.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))
            print(f"[e2e] banco {url.database} criado", flush=True)

    # As migrations leem DATABASE_URL do ambiente (alembic/env.py).
    ambiente = {**os.environ, "DATABASE_URL": sys.argv[1]}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=ambiente)
    print(f"[e2e] banco {url.database} pronto")


if __name__ == "__main__":
    main()
