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
    """Token de login. Recusa tokens feitos para outra finalidade (ex.: o link de redefinir senha)."""
    try:
        dados = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if dados.get("fim"):
            return None
        return int(dados["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def _impressao(senha_hash: str) -> str:
    """Pedaço do hash atual: quando a senha muda, links de redefinição antigos deixam de valer (uso único)."""
    return senha_hash[-16:]


def criar_token_redefinicao(usuario_id: int, senha_hash: str) -> str:
    expira = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=settings.redefinir_senha_minutos)
    return jwt.encode({"sub": str(usuario_id), "fim": "redefinir-senha", "h": _impressao(senha_hash), "exp": expira},
                      settings.jwt_secret, algorithm=settings.jwt_algorithm)


def ler_token_redefinicao(token: str) -> tuple[int, str] | None:
    """Devolve (id do usuário, impressão do hash) se o link for válido, não expirado e desta finalidade."""
    try:
        dados = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if dados.get("fim") != "redefinir-senha":
            return None
        return int(dados["sub"]), dados["h"]
    except (JWTError, KeyError, ValueError):
        return None


def impressao_confere(senha_hash: str, impressao: str) -> bool:
    return _impressao(senha_hash) == impressao
