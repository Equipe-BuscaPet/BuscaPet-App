"""Cria (ou promove) a conta de administrador. Administrador não se cadastra pela
API pública, por segurança: esta é a única porta de entrada.

Uso, a partir da pasta api/:
    python -m app.scripts.criar_admin --nome "Nome" --email admin@exemplo.com
A senha é pedida no terminal (não aparece na tela nem no histórico do shell).
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.seguranca import hash_senha
from app.db.session import SessionLocal
from app.models.enums import TipoConta
from app.models.usuario import Usuario


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria uma conta de administrador.")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    senha = getpass.getpass("Senha (mínimo 8 caracteres): ")
    if len(senha) < 8 or len(senha.encode()) > 72:
        print("Senha inválida: use de 8 caracteres até 72 bytes.", file=sys.stderr)
        return 1
    if senha != getpass.getpass("Repita a senha: "):
        print("As senhas não conferem.", file=sys.stderr)
        return 1

    email = args.email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(Usuario.id).where(Usuario.email == email)):
            print(f"Já existe uma conta com o e-mail {email}; nada foi alterado.", file=sys.stderr)
            return 1
        db.add(Usuario(nome=args.nome.strip(), email=email, senha_hash=hash_senha(senha), tipo_conta=TipoConta.ADMIN))
        db.commit()
    print(f"Administrador {email} criado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
