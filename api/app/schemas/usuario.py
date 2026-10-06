"""Schemas de conta e perfil — RF-01 a RF-06."""
import datetime
import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import StatusValidacao, TipoConta, TipoEstabelecimento


def _senha_valida(senha: str) -> str:
    # bcrypt só considera os primeiros 72 bytes; rejeitar acima disso evita
    # que duas senhas diferentes gerem o mesmo hash sem o usuário perceber.
    if len(senha.encode()) > 72:
        raise ValueError("A senha pode ter no máximo 72 bytes.")
    return senha


def _cnpj_valido(valor: str) -> str:
    cnpj = re.sub(r"\D", "", valor)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        raise ValueError("CNPJ inválido.")

    def digito(base: str, pesos: list[int]) -> str:
        resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(cnpj[:12] + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if cnpj[12:] != d1 + d2:
        raise ValueError("CNPJ inválido.")
    return cnpj


class _CadastroBase(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8)

    _checa_senha = field_validator("senha")(_senha_valida)


class CadastroTutor(_CadastroBase):
    tipo_conta: Literal["tutor"]
    telefone: str | None = Field(default=None, max_length=20)
    cidade: str | None = Field(default=None, max_length=120)


class CadastroAbrigo(_CadastroBase):
    tipo_conta: Literal["abrigo"]
    nome_abrigo: str = Field(min_length=2, max_length=150)
    endereco: str = Field(min_length=3, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    horario_funcionamento: str | None = Field(default=None, max_length=255)
    descricao: str | None = Field(default=None, max_length=2000)
    telefone: str | None = Field(default=None, max_length=20)
    # Só exibida no perfil; a plataforma nunca processa doação financeira.
    chave_doacao_financeira: str | None = Field(default=None, max_length=140)


class CadastroApoiador(_CadastroBase):
    tipo_conta: Literal["apoiador"]
    cnpj: str
    tipo_estabelecimento: TipoEstabelecimento
    endereco: str = Field(min_length=3, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    _checa_cnpj = field_validator("cnpj")(_cnpj_valido)


# "admin" não está aqui de propósito: ninguém vira administrador pelo cadastro
# público (ver app/scripts/criar_admin.py).
Cadastro = Annotated[Union[CadastroTutor, CadastroAbrigo, CadastroApoiador], Field(discriminator="tipo_conta")]


class TutorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    telefone: str | None
    cidade: str | None


class AbrigoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nome_abrigo: str
    endereco: str
    latitude: float
    longitude: float
    horario_funcionamento: str | None
    descricao: str | None
    telefone: str | None
    chave_doacao_financeira: str | None
    status_validacao: StatusValidacao


class ApoiadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cnpj: str
    tipo_estabelecimento: TipoEstabelecimento
    endereco: str
    latitude: float | None
    longitude: float | None
    status_validacao: StatusValidacao


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    tipo_conta: TipoConta
    ativo: bool
    criado_em: datetime.datetime
    perfil: TutorOut | AbrigoOut | ApoiadorOut | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class AtualizaUsuario(BaseModel):
    """Atualização parcial: só os campos enviados mudam. Campos que não se
    aplicam ao tipo da conta (ex.: nome_abrigo numa conta de tutor) são recusados."""

    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=2, max_length=150)
    telefone: str | None = Field(default=None, max_length=20)
    cidade: str | None = Field(default=None, max_length=120)
    nome_abrigo: str | None = Field(default=None, min_length=2, max_length=150)
    endereco: str | None = Field(default=None, min_length=3, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    horario_funcionamento: str | None = Field(default=None, max_length=255)
    descricao: str | None = Field(default=None, max_length=2000)
    chave_doacao_financeira: str | None = Field(default=None, max_length=140)
    tipo_estabelecimento: TipoEstabelecimento | None = None


class TrocaSenha(BaseModel):
    senha_atual: str
    senha_nova: str = Field(min_length=8)

    _checa_senha = field_validator("senha_nova")(_senha_valida)


class ValidacaoAbrigo(BaseModel):
    status: Literal[StatusValidacao.APROVADO, StatusValidacao.REJEITADO]
