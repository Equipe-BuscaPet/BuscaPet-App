"""Transversais — RF-36 a RF-41."""
import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import StatusDenuncia


class Notificacao(Base):
    """Alertas de correspondência (RF-24, RF-26) e demais avisos do sistema —
    RF-36. referencia_tipo/referencia_id apontam pra origem (ex.: 'correspondencia', id)
    pra abrir a tela certa ao clicar, sem precisar de uma tabela por tipo de evento."""

    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    mensagem: Mapped[str] = mapped_column(String(500))
    referencia_tipo: Mapped[str | None] = mapped_column(String(30))
    referencia_id: Mapped[int | None] = mapped_column(Integer)
    lida: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Denuncia(Base):
    """Denúncia de anúncio suspeito — RF-41 (ex.: venda disfarçada de adoção)."""

    __tablename__ = "denuncias"

    id: Mapped[int] = mapped_column(primary_key=True)
    denunciante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    animal_id: Mapped[int] = mapped_column(ForeignKey("animais.id"))
    motivo: Mapped[str] = mapped_column(String(1000))
    status: Mapped[StatusDenuncia] = mapped_column(Enum(StatusDenuncia, name="status_denuncia"), default=StatusDenuncia.PENDENTE)
    resolvido_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    resolvido_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LogAuditoria(Base):
    """Registro de toda ação sensível — RF-39 (ex.: validar abrigo, confirmar
    doação, resolver denúncia, banir conta)."""

    __tablename__ = "logs_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    acao: Mapped[str] = mapped_column(String(100))
    entidade_tipo: Mapped[str] = mapped_column(String(50))
    entidade_id: Mapped[int] = mapped_column(Integer)
    detalhes_json: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
