"""Abrigos e animais — RF-12 a RF-18."""
import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Especie, Sexo, StatusAnimal, StatusInteresse


class Animal(Base):
    """Ficha do animal disponível para adoção — RF-17. Os mesmos campos
    reaparecem no Detalhe do Animal (escopo, seção 3.3) e no formulário de
    cadastro do abrigo (descricao-paginas-fluxos, seção 'Cadastro de animais')."""

    __tablename__ = "animais"

    id: Mapped[int] = mapped_column(primary_key=True)
    abrigo_id: Mapped[int] = mapped_column(ForeignKey("abrigos.usuario_id"))
    nome: Mapped[str] = mapped_column(String(120))
    especie: Mapped[Especie] = mapped_column(Enum(Especie, name="especie_animal"))
    raca_aproximada: Mapped[str | None] = mapped_column(String(120))
    porte: Mapped[str] = mapped_column(String(20))  # pequeno / medio / grande
    idade_estimada_meses: Mapped[int | None] = mapped_column(Integer)
    sexo: Mapped[Sexo] = mapped_column(Enum(Sexo, name="sexo_animal"))
    castrado: Mapped[bool] = mapped_column(Boolean, default=False)
    vacinado: Mapped[bool] = mapped_column(Boolean, default=False)
    vermifugado: Mapped[bool] = mapped_column(Boolean, default=False)
    temperamento: Mapped[str | None] = mapped_column(String(500))
    convivencia_criancas: Mapped[bool | None] = mapped_column(Boolean)
    convivencia_outros_animais: Mapped[bool | None] = mapped_column(Boolean)
    historia_resgate: Mapped[str | None] = mapped_column(String(2000))
    data_entrada: Mapped[datetime.date | None] = mapped_column(DateTime(timezone=True))
    condicao_chegada: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[StatusAnimal] = mapped_column(Enum(StatusAnimal, name="status_animal"), default=StatusAnimal.DISPONIVEL)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fotos: Mapped[list["Foto"]] = relationship(
        primaryjoin="and_(Foto.entidade_tipo=='animal', foreign(Foto.entidade_id)==Animal.id)",
        viewonly=True,
        order_by="Foto.ordem",
    )
    interesses: Mapped[list["Interesse"]] = relationship(back_populates="animal")


class Foto(Base):
    """Associação polimórfica: uma foto pertence a um Animal, um AnimalPerdido
    ou um Avistamento (entidade_tipo + entidade_id), em vez de três tabelas
    quase idênticas (FotoAnimal, FotoAnimalPerdido, FotoAvistamento).

    Trade-off assumido: entidade_id não tem FK de banco de verdade (não dá pra
    apontar uma FK para "uma de três tabelas"), a integridade é garantida na
    camada de aplicação. Ganho: um único lugar para a extração de descritores
    (RF-21) rodar, independente da origem da foto. Identificador de arquivo é
    aleatório (uuid), sem expor dados do autor (escopo, seção 9).
    """

    __tablename__ = "fotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    entidade_tipo: Mapped[str] = mapped_column(String(20))  # ver EntidadeFoto
    entidade_id: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String(500))
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    descritor: Mapped["DescritorVisual"] = relationship(back_populates="foto", uselist=False)


class Interesse(Base):
    """Registro de interesse gerado ANTES de abrir o WhatsApp — RF-16. Sem isso
    o abrigo não sabe quantas pessoas se interessaram por cada animal."""

    __tablename__ = "interesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animais.id"))
    tutor_id: Mapped[int] = mapped_column(ForeignKey("tutores.usuario_id"))
    status: Mapped[StatusInteresse] = mapped_column(Enum(StatusInteresse, name="status_interesse"), default=StatusInteresse.AGUARDANDO)
    criado_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    animal: Mapped[Animal] = relationship(back_populates="interesses")
