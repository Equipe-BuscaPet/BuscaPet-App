"""Monta as respostas de conta com o perfil certo para cada tipo de conta."""
from app.models.enums import TipoConta
from app.models.usuario import Usuario
from app.schemas.usuario import AbrigoOut, ApoiadorOut, TutorOut, UsuarioOut


def usuario_out(usuario: Usuario) -> UsuarioOut:
    perfil = None
    if usuario.tipo_conta == TipoConta.TUTOR and usuario.tutor:
        perfil = TutorOut.model_validate(usuario.tutor)
    elif usuario.tipo_conta == TipoConta.ABRIGO and usuario.abrigo:
        perfil = AbrigoOut.model_validate(usuario.abrigo)
    elif usuario.tipo_conta == TipoConta.APOIADOR and usuario.apoiador:
        perfil = ApoiadorOut.model_validate(usuario.apoiador)
    return UsuarioOut(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        tipo_conta=usuario.tipo_conta,
        ativo=usuario.ativo,
        criado_em=usuario.criado_em,
        perfil=perfil,
    )
