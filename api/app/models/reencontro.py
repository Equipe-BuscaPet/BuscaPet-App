"""Reencontro por similaridade visual — núcleo computacional. RF-19 a RF-29.

Esta é a área que o núcleo OpenCL (serviço C separado) consome e alimenta:
- extração de descritores roda sobre toda linha nova em `fotos` (RF-21)
- busca/comparação em massa lê `descritores_visuais` (RF-22, RF-23, RF-27)
- monitoramento contínuo grava em `correspondencias` a cada novo match (RF-24, RF-25, RF-26)
"""
import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.animal import Foto
from app.models.enums import Especie, GrauSemelhanca, Sexo, StatusBusca, TipoCorrespondencia


class AnimalPerdido(Base):
    """Registro feito por um tutor — RF-19. Serve de base para a busca de
    quem encontrou (RF-27, busca inversa)."""

    __tablename__ = "animais_perdidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutores.usuario_id"))
    especie: Mapped[Especie] = mapped_column(Enum(Especie, name="especie_perdido"))
    porte: Mapped[str] = mapped_column(String(20))
    cor_predominante: Mapped[str] = mapped_column(String(60))
    pelagem: Mapped[str | None] = mapped_column(String(60))
    sexo: Mapped[Sexo] = mapped_column(Enum(Sexo, name="sexo_perdido"))
    sinais_particulares: Mapped[str | None] = mapped_column(String(500))
    # Área aproximada exibida no mapa — nunca o endereço exato (escopo, seção 9).
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    raio_busca_km: Mapped[float] = mapped_column(Float, default=5.0)
    data_desaparecimento: Mapped[datetime.date] = mapped_column(DateTime(timezone=True))
    resolvido: Mapped[bool] = mapped_column(default=False)  # RF-28
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    buscas_salvas: Mapped[list["BuscaSalva"]] = relationship(back_populates="animal_perdido")


class Avistamento(Base):
    """Registro feito por qualquer usuário autenticado — RF-20. Alimenta a
    busca de quem perdeu (junto com o catálogo de animais dos abrigos)."""

    __tablename__ = "avistamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    especie: Mapped[Especie] = mapped_column(Enum(Especie, name="especie_avistamento"))
    porte: Mapped[str] = mapped_column(String(20))
    cor_predominante: Mapped[str] = mapped_column(String(60))
    pelagem: Mapped[str | None] = mapped_column(String(60))
    sexo: Mapped[Sexo] = mapped_column(Enum(Sexo, name="sexo_avistamento"))
    sinais_particulares: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    data_avistamento: Mapped[datetime.date] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DescritorVisual(Base):
    """Saída da etapa de extração (RF-21) para UMA foto — histograma de cor,
    textura e proporções, sempre calculados pelo núcleo OpenCL (ou pela versão
    sequencial em C, no modo de comparação RF-29).

    Guardado como JSON por ora (Sprint 2: schema pronto, extração ainda não
    implementada — isso é trabalho da Sprint 3). Se o volume justificar depois,
    migrar para pgvector é uma extensão possível, não um requisito agora.
    """

    __tablename__ = "descritores_visuais"

    id: Mapped[int] = mapped_column(primary_key=True)
    foto_id: Mapped[int] = mapped_column(ForeignKey("fotos.id"), unique=True)
    histograma_cor: Mapped[str] = mapped_column(Text)  # JSON serializado
    textura: Mapped[str] = mapped_column(Text)  # JSON serializado
    proporcoes: Mapped[str] = mapped_column(Text)  # JSON serializado
    versao_algoritmo: Mapped[str] = mapped_column(String(20), default="v1")
    calculado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    foto: Mapped["Foto"] = relationship(back_populates="descritor")


class BuscaSalva(Base):
    """Busca ativa de um tutor sob monitoramento contínuo — RF-24. Cada novo
    registro (Animal ou Avistamento) é comparado em lote contra todas as
    linhas aqui com status=MONITORANDO (RF-25)."""

    __tablename__ = "buscas_salvas"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutores.usuario_id"))
    animal_perdido_id: Mapped[int] = mapped_column(ForeignKey("animais_perdidos.id"))
    status: Mapped[StatusBusca] = mapped_column(Enum(StatusBusca, name="status_busca"), default=StatusBusca.MONITORANDO)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolvida_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    animal_perdido: Mapped[AnimalPerdido] = relationship(back_populates="buscas_salvas")


class Correspondencia(Base):
    """Log de todo match relevante encontrado pelo motor de comparação —
    alimenta a grade de candidatos (RF-23), o alerta ao abrigo (RF-26) e a
    notificação de monitoramento contínuo (RF-24). Guardar o log, e não só
    disparar a notificação, é o que permite ao abrigo/tutor reabrir os
    candidatos depois e é a base para medir corretude (RNF-04)."""

    __tablename__ = "correspondencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoCorrespondencia] = mapped_column(Enum(TipoCorrespondencia, name="tipo_correspondencia"))
    animal_perdido_id: Mapped[int | None] = mapped_column(ForeignKey("animais_perdidos.id"))
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animais.id"))
    avistamento_id: Mapped[int | None] = mapped_column(ForeignKey("avistamentos.id"))
    score: Mapped[float] = mapped_column(Float)  # distância bruta calculada pelo núcleo
    grau_semelhanca: Mapped[GrauSemelhanca] = mapped_column(Enum(GrauSemelhanca, name="grau_semelhanca"))
    notificado: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
