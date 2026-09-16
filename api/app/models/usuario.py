"""Contas e perfis — RF-01 a RF-06.

Usuario é a tabela base (autenticação). Cada tipo de conta ganha uma tabela de
perfil própria em relação 1:1 (FK = PK), no padrão "table per type": evita colunas
que só fazem sentido pra um perfil ficarem NULL nos outros, e mantém Tutor/Abrigo/
Apoiador como classes próprias no diagrama de classes (herdando de Usuario).
"""
import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PapelEquipeAbrigo, StatusValidacao, TipoConta, TipoEstabelecimento


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    tipo_conta: Mapped[TipoConta] = mapped_column(Enum(TipoConta, name="tipo_conta"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tutor: Mapped["Tutor"] = relationship(back_populates="usuario", uselist=False)
    abrigo: Mapped["Abrigo"] = relationship(back_populates="usuario", uselist=False, foreign_keys="Abrigo.usuario_id")
    apoiador: Mapped["Apoiador"] = relationship(back_populates="usuario", uselist=False)


class Tutor(Base):
    """Perfil de tutor/adotante — RF-01, opção 'Quero adotar ou encontrar meu animal'."""

    __tablename__ = "tutores"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    telefone: Mapped[str | None] = mapped_column(String(20))
    cidade: Mapped[str | None] = mapped_column(String(120))

    usuario: Mapped[Usuario] = relationship(back_populates="tutor")


class Abrigo(Base):
    """Perfil de abrigo/protetor — RF-01, RF-06, RF-12. Passa por validação do
    administrador (RF-06) antes de ficar público."""

    __tablename__ = "abrigos"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    nome_abrigo: Mapped[str] = mapped_column(String(150))
    endereco: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    horario_funcionamento: Mapped[str | None] = mapped_column(String(255))
    descricao: Mapped[str | None] = mapped_column(String(2000))
    telefone: Mapped[str | None] = mapped_column(String(20))
    # Só exibida no perfil — a plataforma nunca processa a doação financeira
    # (documento de escopo, seção 10, "fora do escopo"). Ver notas-tecnicas.
    chave_doacao_financeira: Mapped[str | None] = mapped_column(String(140))
    documento_comprobatorio_url: Mapped[str | None] = mapped_column(String(500))
    status_validacao: Mapped[StatusValidacao] = mapped_column(
        Enum(StatusValidacao, name="status_validacao"), default=StatusValidacao.PENDENTE
    )
    validado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    validado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="abrigo", foreign_keys=[usuario_id])
    membros: Mapped[list["MembroEquipeAbrigo"]] = relationship(back_populates="abrigo")


class MembroEquipeAbrigo(Base):
    """Vincula múltiplos usuários a um mesmo abrigo, com papéis distintos
    (escopo, seção 6.2 'Equipe') — evita depender de uma única pessoa."""

    __tablename__ = "membros_equipe_abrigo"
    __table_args__ = (UniqueConstraint("abrigo_id", "usuario_id", name="uq_membro_por_abrigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    abrigo_id: Mapped[int] = mapped_column(ForeignKey("abrigos.usuario_id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    papel: Mapped[PapelEquipeAbrigo] = mapped_column(Enum(PapelEquipeAbrigo, name="papel_equipe_abrigo"))
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    abrigo: Mapped[Abrigo] = relationship(back_populates="membros")


class Apoiador(Base):
    """Perfil de apoiador (petshop/clínica/distribuidora/pessoa física) — RF-01,
    seção 7 do escopo.

    status_validacao cobre um ponto em aberto do escopo (seção 6 dos fluxos):
    hoje não há aprovação de admin definida para apoiador como há para abrigo;
    a coluna existe para permitir ligar/desligar essa exigência sem migração
    nova, default já é APROVADO até a equipe decidir o contrário.
    """

    __tablename__ = "apoiadores"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    cnpj: Mapped[str] = mapped_column(String(18), unique=True)
    tipo_estabelecimento: Mapped[TipoEstabelecimento] = mapped_column(
        Enum(TipoEstabelecimento, name="tipo_estabelecimento")
    )
    endereco: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status_validacao: Mapped[StatusValidacao] = mapped_column(
        Enum(StatusValidacao, name="status_validacao_apoiador"), default=StatusValidacao.APROVADO
    )
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="apoiador")
