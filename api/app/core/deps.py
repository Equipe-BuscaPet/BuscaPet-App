"""Dependências de autenticação e de controle de perfil — RF-02 e RF-04.

A identidade vem do token, mas o usuário e o tipo de conta são sempre relidos do
banco: se a conta for desativada ou mudar, o token antigo deixa de valer.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.seguranca import decodificar_token
from app.db.session import get_db
from app.models.enums import StatusValidacao, TipoConta
from app.models.usuario import Abrigo, Usuario

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_opcional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

_NAO_AUTENTICADO = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Credenciais inválidas ou expiradas.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _usuario_do_token(token: str | None, db: Session) -> Usuario | None:
    if not token:
        return None
    usuario_id = decodificar_token(token)
    if usuario_id is None:
        return None
    usuario = db.get(Usuario, usuario_id)
    return usuario if usuario and usuario.ativo else None


def get_usuario_atual(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Usuario:
    usuario = _usuario_do_token(token, db)
    if usuario is None:
        raise _NAO_AUTENTICADO
    return usuario


def get_usuario_opcional(token: str | None = Depends(oauth2_opcional), db: Session = Depends(get_db)) -> Usuario | None:
    """Para rotas públicas que mostram mais coisas a quem está logado (RF-10)."""
    return _usuario_do_token(token, db)


def exigir_tipo(*tipos: TipoConta):
    """Fábrica de dependência: libera a rota só para os tipos de conta informados."""

    def dependencia(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.tipo_conta not in tipos:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu tipo de conta não tem permissão para esta ação.")
        return usuario

    return dependencia


def get_abrigo_operante(usuario: Usuario = Depends(exigir_tipo(TipoConta.ABRIGO))) -> Abrigo:
    """Abrigo opera assim que cria a conta: a verificação do administrador (RF-06)
    é um selo de confiança, não uma porta. Só um abrigo suspenso (rejeitado) é barrado."""
    abrigo = usuario.abrigo
    if abrigo is None or abrigo.status_validacao == StatusValidacao.REJEITADO:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Seu abrigo foi suspenso pela administração. Entre em contato com a equipe BuscaPet.",
        )
    return abrigo
