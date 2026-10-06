"""Hash de senha (bcrypt) e tokens JWT — RF-02."""
import datetime

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Hash fixo usado quando o e-mail não existe, para o login gastar o mesmo tempo
# nos dois casos e não revelar quais e-mails estão cadastrados.
_HASH_FALSO = bcrypt.hashpw(b"senha-que-nunca-sera-usada", bcrypt.gensalt()).decode()


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), (senha_hash or _HASH_FALSO).encode()) and senha_hash is not None
    except ValueError:
        return False


def criar_token(usuario_id: int) -> str:
    expira = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=settings.jwt_expira_minutos)
    return jwt.encode({"sub": str(usuario_id), "exp": expira}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> int | None:
    try:
        dados = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(dados["sub"])
    except (JWTError, KeyError, ValueError):
        return None
