"""CRUD de animais para adoção — RF-12 a RF-18 (entidade principal da Sprint 3).

Regras de perfil:
- Consultar (lista e detalhe): público. O visitante só vê animais de abrigos
  APROVADOS e ativos; o dono (e o admin) enxergam também os seus/todos.
- Cadastrar e atualizar: só abrigo APROVADO, e só os animais do próprio abrigo.
- Excluir: o abrigo dono ou o administrador (moderação).
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import exigir_tipo, get_abrigo_aprovado, get_usuario_opcional
from app.db.session import get_db
from app.models.animal import Animal, Foto, Interesse
from app.models.enums import Especie, StatusAnimal, StatusValidacao, TipoConta
from app.models.reencontro import DescritorVisual
from app.models.usuario import Abrigo, Usuario
from app.schemas.animal import AnimalCreate, AnimalOut, AnimalUpdate

router = APIRouter(prefix="/animais", tags=["animais"])


def _para_datetime(dia: datetime.date | None) -> datetime.datetime | None:
    # A coluna data_entrada é DateTime; o formulário envia só a data.
    return datetime.datetime.combine(dia, datetime.time.min, tzinfo=datetime.UTC) if dia else None


def _saida(animal: Animal, nome_abrigo: str | None) -> AnimalOut:
    saida = AnimalOut.model_validate(animal)
    saida.nome_abrigo = nome_abrigo
    return saida


def _publico_visivel(consulta):
    """Filtro de visibilidade pública: abrigo aprovado e conta ativa."""
    return consulta.where(
        Abrigo.status_validacao == StatusValidacao.APROVADO,
        Usuario.ativo.is_(True),
    )


def _consulta_base():
    return (
        select(Animal, Abrigo.nome_abrigo)
        .join(Abrigo, Abrigo.usuario_id == Animal.abrigo_id)
        .join(Usuario, Usuario.id == Abrigo.usuario_id)
    )


@router.post("", response_model=AnimalOut, status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: AnimalCreate,
    abrigo: Abrigo = Depends(get_abrigo_aprovado),
    db: Session = Depends(get_db),
) -> AnimalOut:
    campos = dados.model_dump()
    campos["data_entrada"] = _para_datetime(campos["data_entrada"])
    animal = Animal(abrigo_id=abrigo.usuario_id, **campos)
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return _saida(animal, abrigo.nome_abrigo)


@router.get("", response_model=list[AnimalOut])
def listar(
    especie: Especie | None = None,
    porte: str | None = Query(default=None, description="pequeno, medio ou grande"),
    status_animal: StatusAnimal | None = Query(default=StatusAnimal.DISPONIVEL, alias="status"),
    abrigo_id: int | None = None,
    busca: str | None = Query(default=None, max_length=100, description="Trecho do nome ou da raça"),
    limite: int = Query(default=20, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AnimalOut]:
    """Catálogo público, mais recentes primeiro. Por padrão só mostra animais
    disponíveis; passe `status` para ver outros."""
    consulta = _publico_visivel(_consulta_base())
    if especie:
        consulta = consulta.where(Animal.especie == especie)
    if porte:
        consulta = consulta.where(Animal.porte == porte)
    if status_animal:
        consulta = consulta.where(Animal.status == status_animal)
    if abrigo_id:
        consulta = consulta.where(Animal.abrigo_id == abrigo_id)
    if busca:
        trecho = f"%{busca.lower()}%"
        consulta = consulta.where(or_(func.lower(Animal.nome).like(trecho), func.lower(Animal.raca_aproximada).like(trecho)))
    linhas = db.execute(
        consulta.order_by(Animal.criado_em.desc(), Animal.id.desc()).limit(limite).offset(deslocamento)
    ).all()
    return [_saida(animal, nome) for animal, nome in linhas]


@router.get("/meus", response_model=list[AnimalOut])
def listar_meus(
    usuario: Usuario = Depends(exigir_tipo(TipoConta.ABRIGO)),
    db: Session = Depends(get_db),
) -> list[AnimalOut]:
    """Todos os animais do abrigo logado, em qualquer status."""
    linhas = db.execute(
        _consulta_base().where(Animal.abrigo_id == usuario.id).order_by(Animal.criado_em.desc(), Animal.id.desc())
    ).all()
    return [_saida(animal, nome) for animal, nome in linhas]


def _buscar_visivel(animal_id: int, usuario: Usuario | None, db: Session) -> tuple[Animal, str]:
    linha = db.execute(_consulta_base().where(Animal.id == animal_id)).first()
    if linha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    animal, nome_abrigo = linha
    abrigo = db.get(Abrigo, animal.abrigo_id)
    dono = usuario is not None and usuario.id == animal.abrigo_id
    admin = usuario is not None and usuario.tipo_conta == TipoConta.ADMIN
    publico = abrigo.status_validacao == StatusValidacao.APROVADO and abrigo.usuario.ativo
    if not (publico or dono or admin):
        # 404 (e não 403) para não confirmar a existência de cadastros ainda não validados.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    return animal, nome_abrigo


@router.get("/{animal_id}", response_model=AnimalOut)
def consultar(
    animal_id: int,
    usuario: Usuario | None = Depends(get_usuario_opcional),
    db: Session = Depends(get_db),
) -> AnimalOut:
    animal, nome_abrigo = _buscar_visivel(animal_id, usuario, db)
    return _saida(animal, nome_abrigo)


def _animal_do_abrigo(animal_id: int, abrigo: Abrigo, db: Session) -> Animal:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    if animal.abrigo_id != abrigo.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este animal pertence a outro abrigo.")
    return animal


@router.patch("/{animal_id}", response_model=AnimalOut)
def atualizar(
    animal_id: int,
    dados: AnimalUpdate,
    abrigo: Abrigo = Depends(get_abrigo_aprovado),
    db: Session = Depends(get_db),
) -> AnimalOut:
    animal = _animal_do_abrigo(animal_id, abrigo, db)
    enviados = dados.model_dump(exclude_unset=True)
    obrigatorios = {"nome", "especie", "porte", "sexo", "status"}
    vazios = sorted(c for c in obrigatorios if c in enviados and enviados[c] is None)
    if vazios:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Campos obrigatórios não podem ficar vazios: {', '.join(vazios)}.")
    if "data_entrada" in enviados:
        enviados["data_entrada"] = _para_datetime(enviados["data_entrada"])
    for campo, valor in enviados.items():
        setattr(animal, campo, valor)
    db.commit()
    db.refresh(animal)
    return _saida(animal, abrigo.nome_abrigo)


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    animal_id: int,
    usuario: Usuario = Depends(exigir_tipo(TipoConta.ABRIGO, TipoConta.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    """Exclusão de verdade (a linha some). Remove antes o que depende só deste
    animal: interesses, fotos e os descritores dessas fotos. Se ainda houver
    vínculos (ex.: correspondências do reencontro), responde 409: nesse caso o
    caminho certo é mudar o status para adotado/transferido."""
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    if usuario.tipo_conta == TipoConta.ABRIGO and animal.abrigo_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este animal pertence a outro abrigo.")
    if usuario.tipo_conta == TipoConta.ABRIGO and (usuario.abrigo is None or usuario.abrigo.status_validacao != StatusValidacao.APROVADO):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu abrigo ainda não foi validado pelo administrador.")

    foto_ids = list(db.scalars(select(Foto.id).where(Foto.entidade_tipo == "animal", Foto.entidade_id == animal.id)))
    if foto_ids:
        db.execute(delete(DescritorVisual).where(DescritorVisual.foto_id.in_(foto_ids)))
        db.execute(delete(Foto).where(Foto.id.in_(foto_ids)))
    db.execute(delete(Interesse).where(Interesse.animal_id == animal.id))
    db.delete(animal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este animal tem registros vinculados e não pode ser excluído. Altere o status para adotado ou transferido.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
