"""Cadastro e login — RF-01 e RF-02."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import auditoria, email
from app.core.config import settings
from app.core.deps import get_usuario_atual
from app.core.seguranca import (
    criar_token,
    criar_token_redefinicao,
    hash_senha,
    impressao_confere,
    ler_token_redefinicao,
    verificar_senha,
)
from app.db.session import get_db
from app.models.enums import TipoConta
from app.models.usuario import Abrigo, Apoiador, Tutor, Usuario
from app.routers.serializers import usuario_out
from app.schemas.usuario import (
    Cadastro,
    CadastroAbrigo,
    CadastroApoiador,
    CadastroTutor,
    EsqueciSenha,
    RedefinirSenha,
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
        db.flush()
        auditoria.registrar(db, usuario.id, "conta.criada", "usuario", usuario.id, tipo=usuario.tipo_conta.value)
        db.commit()
    except IntegrityError:
        # Corrida entre duas requisições com o mesmo e-mail/CNPJ.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail ou CNPJ já cadastrado.")
    db.refresh(usuario)
    return usuario_out(usuario)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenOut:
    """Entra com e-mail e senha e devolve o token de acesso (`access_token`, vale 24 horas) e os dados da conta.
    Formulário no padrão OAuth2 (`username` = e-mail, `password` = senha), para o botão "Authorize" do Swagger funcionar."""
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
    """Dados da conta logada (mesmo conteúdo de `GET /usuarios/eu`), usado pela interface ao abrir."""
    return usuario_out(usuario)


# ---------- RF-05: recuperação de senha ----------

PEDIDO_RECEBIDO = ("Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha. "
                   "Ele vale por {minutos} minutos.")


@router.post("/esqueci-senha", status_code=status.HTTP_202_ACCEPTED)
def esqueci_senha(dados: EsqueciSenha, db: Session = Depends(get_db)) -> dict:
    """Sempre a mesma resposta, exista ou não a conta: não revela quais e-mails estão cadastrados."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email.lower()))
    if usuario is not None and usuario.ativo:
        token = criar_token_redefinicao(usuario.id, usuario.senha_hash)
        link = f"{settings.url_interface}/redefinir-senha?token={token}"
        email.enviar(usuario.email, "BuscaPet: crie uma nova senha", email.texto_padrao(
            usuario.nome,
            f"Recebemos um pedido para criar uma nova senha. O link abaixo vale por {settings.redefinir_senha_minutos} "
            "minutos e pode ser usado uma vez. Se não foi você, ignore este e-mail: sua senha continua a mesma.",
            link,
        ))
        auditoria.registrar(db, usuario.id, "conta.redefinicao_pedida", "usuario", usuario.id)
        db.commit()
    return {"mensagem": PEDIDO_RECEBIDO.format(minutos=settings.redefinir_senha_minutos)}


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(dados: RedefinirSenha, db: Session = Depends(get_db)) -> Response:
    """Define a senha nova com o token do link enviado por e-mail (vale 30 minutos e uma vez só)."""
    lido = ler_token_redefinicao(dados.token)
    usuario = db.get(Usuario, lido[0]) if lido else None
    if usuario is None or not usuario.ativo or not impressao_confere(usuario.senha_hash, lido[1]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Este link é inválido, já foi usado ou expirou. Peça um novo.")
    usuario.senha_hash = hash_senha(dados.senha_nova)
    auditoria.registrar(db, usuario.id, "conta.senha_redefinida", "usuario", usuario.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
