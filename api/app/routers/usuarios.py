"""Leitura, atualização e exclusão da própria conta — RF-03 e RF-05."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.core.seguranca import hash_senha, verificar_senha
from app.db.session import get_db
from app.models.enums import TipoConta
from app.models.usuario import Usuario
from app.routers.serializers import usuario_out
from app.schemas.usuario import AtualizaUsuario, TrocaSenha, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["contas"])

# Campos de perfil que cada tipo de conta pode alterar.
_CAMPOS_POR_TIPO = {
    TipoConta.TUTOR: {"telefone", "cidade"},
    TipoConta.ABRIGO: {
        "nome_abrigo", "endereco", "latitude", "longitude",
        "horario_funcionamento", "descricao", "telefone", "chave_doacao_financeira",
    },
    TipoConta.APOIADOR: {"endereco", "latitude", "longitude", "tipo_estabelecimento"},
    TipoConta.ADMIN: set(),
}

# Colunas NOT NULL: não aceitam ser limpas com null.
_OBRIGATORIOS = {"nome_abrigo", "endereco", "latitude", "longitude", "tipo_estabelecimento"}


def _perfil(usuario: Usuario):
    return {
        TipoConta.TUTOR: usuario.tutor,
        TipoConta.ABRIGO: usuario.abrigo,
        TipoConta.APOIADOR: usuario.apoiador,
    }.get(usuario.tipo_conta)


@router.get("/eu", response_model=UsuarioOut)
def consultar(usuario: Usuario = Depends(get_usuario_atual)) -> UsuarioOut:
    return usuario_out(usuario)


@router.patch("/eu", response_model=UsuarioOut)
def atualizar(
    dados: AtualizaUsuario,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    enviados = dados.model_dump(exclude_unset=True)
    permitidos = _CAMPOS_POR_TIPO[usuario.tipo_conta] | {"nome"}
    invalidos = sorted(set(enviados) - permitidos)
    if invalidos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Campos que não se aplicam a uma conta de {usuario.tipo_conta.value}: {', '.join(invalidos)}.",
        )
    perfil = _perfil(usuario)
    for campo, valor in enviados.items():
        if valor is None and (campo == "nome" or campo in _OBRIGATORIOS):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"O campo {campo} não pode ficar vazio.")
        if campo == "nome":
            usuario.nome = valor.strip()
        else:
            setattr(perfil, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario_out(usuario)


@router.post("/eu/senha", status_code=status.HTTP_204_NO_CONTENT)
def trocar_senha(
    dados: TrocaSenha,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Senha atual incorreta.")
    usuario.senha_hash = hash_senha(dados.senha_nova)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/eu", status_code=status.HTTP_204_NO_CONTENT)
def excluir_conta(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)) -> Response:
    """Exclusão lógica: a conta é desativada (ativo=false) e deixa de logar, mas a
    linha permanece. Doações, interesses e logs apontam para o usuário; apagar de
    verdade quebraria esse histórico."""
    if usuario.tipo_conta == TipoConta.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Contas de administrador não podem ser excluídas por aqui.")
    usuario.ativo = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
