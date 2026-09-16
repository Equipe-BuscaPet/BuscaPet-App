"""Doações e reconhecimento — RF-30 a RF-35."""
import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StatusDoacao, StatusNecessidade, UrgenciaNecessidade


class Necessidade(Base):
    """Publicada pelo abrigo no mural — RF-30."""

    __tablename__ = "necessidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    abrigo_id: Mapped[int] = mapped_column(ForeignKey("abrigos.usuario_id"))
    item: Mapped[str] = mapped_column(String(200))
    quantidade: Mapped[int] = mapped_column(Integer)
    urgencia: Mapped[UrgenciaNecessidade] = mapped_column(Enum(UrgenciaNecessidade, name="urgencia_necessidade"))
    status: Mapped[StatusNecessidade] = mapped_column(Enum(StatusNecessidade, name="status_necessidade"), default=StatusNecessidade.ABERTA)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    doacoes: Mapped[list["Doacao"]] = relationship(back_populates="necessidade")


class Doacao(Base):
    """Registrada pelo apoiador, só conta no ranking após confirmação do
    abrigo (escopo, seção 5.4 — evita ranking autodeclarado)."""

    __tablename__ = "doacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    apoiador_id: Mapped[int] = mapped_column(ForeignKey("apoiadores.usuario_id"))
    abrigo_id: Mapped[int] = mapped_column(ForeignKey("abrigos.usuario_id"))
    necessidade_id: Mapped[int | None] = mapped_column(ForeignKey("necessidades.id"))
    item: Mapped[str] = mapped_column(String(200))
    quantidade: Mapped[int] = mapped_column(Integer)
    status: Mapped[StatusDoacao] = mapped_column(Enum(StatusDoacao, name="status_doacao"), default=StatusDoacao.AGUARDANDO_CONFIRMACAO)
    registrado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    necessidade: Mapped[Necessidade | None] = relationship(back_populates="doacoes")


class PontuacaoApoiador(Base):
    """Cache mensal da pontuação usada no ranking (RF-33) — recalculada a cada
    confirmação de doação. Guardar por mês (não só um total corrido) é o que
    permite os 'dois períodos' do escopo: destaque do mês e acumulado do ano
    (basta somar as linhas de todos os meses do ano)."""

    __tablename__ = "pontuacoes_apoiador"
    __table_args__ = (UniqueConstraint("apoiador_id", "mes_referencia", name="uq_pontuacao_apoiador_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    apoiador_id: Mapped[int] = mapped_column(ForeignKey("apoiadores.usuario_id"))
    mes_referencia: Mapped[datetime.date] = mapped_column(DateTime(timezone=True))  # sempre dia 1 do mês
    pontos_volume: Mapped[float] = mapped_column(Float, default=0)
    pontos_regularidade: Mapped[float] = mapped_column(Float, default=0)
    pontos_total: Mapped[float] = mapped_column(Float, default=0)
    atualizado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
