"""Cadastro e login — RF-01 e RF-02."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_usuario_atual
from app.core.seguranca import criar_token, hash_senha, verificar_senha
from app.db.session import get_db
from app.models.enums import TipoConta
from app.models.usuario import Abrigo, Apoiador, Tutor, Usuario
from app.routers.serializers import usuario_out
from app.schemas.usuario import (
    Cadastro,
    CadastroAbrigo,
    CadastroApoiador,
    CadastroTutor,
    TokenOut,
    UsuarioOut,
)

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/cadastro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: Cadastro, db: Session = Depends(get_db)) -> UsuarioOut:
    """Cria a conta e o perfil do tipo escolhido (tutor, abrigo ou apoiador) na
    mesma transação: ou grava tudo, ou nada."""
    email = dados.email.strip().lower()
    if db.scalar(select(Usuario.id).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")

    usuario = Usuario(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=hash_senha(dados.senha),
        tipo_conta=TipoConta(dados.tipo_conta),
    )
    if isinstance(dados, CadastroTutor):
        usuario.tutor = Tutor(telefone=dados.telefone, cidade=dados.cidade)
    elif isinstance(dados, CadastroAbrigo):
        # status_validacao nasce PENDENTE (default do model) = não verificado. Opera na hora; o selo vem do admin.
        usuario.abrigo = Abrigo(
            nome_abrigo=dados.nome_abrigo,
            endereco=dados.endereco,
            latitude=dados.latitude,
            longitude=dados.longitude,
            horario_funcionamento=dados.horario_funcionamento,
            descricao=dados.descricao,
            telefone=dados.telefone,
            chave_doacao_financeira=dados.chave_doacao_financeira,
        )
    elif isinstance(dados, CadastroApoiador):
        # dados.cnpj já chega só com dígitos (normalizado pelo validador do schema).
        if db.scalar(select(Apoiador.usuario_id).where(Apoiador.cnpj == dados.cnpj)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um apoiador com este CNPJ.")
        usuario.apoiador = Apoiador(
            cnpj=dados.cnpj,
            tipo_estabelecimento=dados.tipo_estabelecimento,
            endereco=dados.endereco,
            latitude=dados.latitude,
            longitude=dados.longitude,
        )

    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # Corrida entre duas requisições com o mesmo e-mail/CNPJ.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail ou CNPJ já cadastrado.")
    db.refresh(usuario)
    return usuario_out(usuario)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenOut:
    """`username` é o e-mail. Segue o padrão OAuth2 para o botão "Authorize" do
    Swagger funcionar."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == form.username.strip().lower()))
    senha_ok = verificar_senha(form.password, usuario.senha_hash if usuario else None)
    if usuario is None or not senha_ok or not usuario.ativo:
        # Mesma mensagem para e-mail inexistente, senha errada e conta desativada.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=criar_token(usuario.id), usuario=usuario_out(usuario))


@router.get("/eu", response_model=UsuarioOut)
def quem_sou_eu(usuario: Usuario = Depends(get_usuario_atual)) -> UsuarioOut:
    return usuario_out(usuario)
