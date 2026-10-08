"""Interesse de adoção — RF-16. Módulo Adoção da Sprint 4.

Fluxo: o tutor registra interesse em um animal disponível (e só então vê o contato do
abrigo) → o abrigo vê quem se interessou, conversa e decide → ao aceitar, o animal passa
para "em processo de adoção". Cada decisão gera uma notificação para a outra parte.

Regras de perfil:
- Registrar, listar os seus e desistir: só tutor.
- Ver os recebidos e decidir: só o abrigo dono do animal (e não suspenso).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import exigir_tipo, get_abrigo_operante
from app.db.session import get_db
from app.models.animal import Animal, Interesse
from app.models.enums import StatusAnimal, StatusInteresse, TipoConta
from app.models.transversais import Notificacao
from app.models.usuario import Abrigo, Tutor, Usuario
from app.routers.animais import _buscar_visivel
from app.schemas.interesse import DecisaoInteresse, InteresseAbrigoOut, InteresseCreate, InteresseTutorOut

router = APIRouter(tags=["interesses"])

ENCERRADOS = {StatusInteresse.APROVADO, StatusInteresse.RECUSADO}
MSG_JA_REGISTROU = "Você já registrou interesse neste animal. Acompanhe em “Meus interesses”."


def _saida_tutor(interesse: Interesse, animal: Animal, abrigo: Abrigo) -> InteresseTutorOut:
    return InteresseTutorOut(
        id=interesse.id,
        animal_id=animal.id,
        animal_nome=animal.nome,
        nome_abrigo=abrigo.nome_abrigo,
        abrigo_telefone=abrigo.telefone,
        abrigo_endereco=abrigo.endereco,
        status=interesse.status,
        mensagem=interesse.mensagem,
        criado_em=interesse.criado_em,
    )


def _saida_abrigo(interesse: Interesse, animal: Animal, tutor: Tutor) -> InteresseAbrigoOut:
    return InteresseAbrigoOut(
        id=interesse.id,
        animal_id=animal.id,
        animal_nome=animal.nome,
        tutor_nome=tutor.usuario.nome,
        tutor_email=tutor.usuario.email,
        tutor_telefone=tutor.telefone,
        tutor_cidade=tutor.cidade,
        status=interesse.status,
        mensagem=interesse.mensagem,
        criado_em=interesse.criado_em,
    )


def _notificar(db: Session, usuario_id: int, mensagem: str, interesse_id: int) -> None:
    db.add(Notificacao(usuario_id=usuario_id, mensagem=mensagem, referencia_tipo="interesse", referencia_id=interesse_id))


@router.post("/animais/{animal_id}/interesses", response_model=InteresseTutorOut, status_code=status.HTTP_201_CREATED)
def registrar_interesse(
    animal_id: int,
    dados: InteresseCreate,
    tutor_usuario: Usuario = Depends(exigir_tipo(TipoConta.TUTOR)),
    db: Session = Depends(get_db),
) -> InteresseTutorOut:
    animal, abrigo = _buscar_visivel(animal_id, tutor_usuario, db)
    if animal.status != StatusAnimal.DISPONIVEL:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este animal não está mais disponível para adoção.")
    ja_existe = db.scalar(select(Interesse.id).where(Interesse.animal_id == animal.id, Interesse.tutor_id == tutor_usuario.id))
    if ja_existe:
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_JA_REGISTROU)

    interesse = Interesse(animal_id=animal.id, tutor_id=tutor_usuario.id, mensagem=dados.mensagem)
    db.add(interesse)
    try:
        db.flush()
    except IntegrityError:  # duas requisições ao mesmo tempo: a restrição única do banco decide
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_JA_REGISTROU)
    _notificar(db, abrigo.usuario_id, f"{tutor_usuario.nome} tem interesse em adotar {animal.nome}.", interesse.id)
    db.commit()
    db.refresh(interesse)
    return _saida_tutor(interesse, animal, abrigo)


@router.get("/interesses/meus", response_model=list[InteresseTutorOut])
def listar_meus(
    tutor_usuario: Usuario = Depends(exigir_tipo(TipoConta.TUTOR)),
    db: Session = Depends(get_db),
) -> list[InteresseTutorOut]:
    linhas = db.execute(
        select(Interesse, Animal, Abrigo)
        .join(Animal, Animal.id == Interesse.animal_id)
        .join(Abrigo, Abrigo.usuario_id == Animal.abrigo_id)
        .where(Interesse.tutor_id == tutor_usuario.id)
        .order_by(Interesse.criado_em.desc(), Interesse.id.desc())
    ).all()
    return [_saida_tutor(i, a, ab) for i, a, ab in linhas]


@router.get("/interesses/recebidos", response_model=list[InteresseAbrigoOut])
def listar_recebidos(
    status_interesse: StatusInteresse | None = Query(default=None, alias="status"),
    animal_id: int | None = None,
    usuario: Usuario = Depends(exigir_tipo(TipoConta.ABRIGO)),
    db: Session = Depends(get_db),
) -> list[InteresseAbrigoOut]:
    consulta = (
        select(Interesse, Animal, Tutor)
        .join(Animal, Animal.id == Interesse.animal_id)
        .join(Tutor, Tutor.usuario_id == Interesse.tutor_id)
        .where(Animal.abrigo_id == usuario.id)
    )
    if status_interesse:
        consulta = consulta.where(Interesse.status == status_interesse)
    if animal_id:
        consulta = consulta.where(Animal.id == animal_id)
    linhas = db.execute(consulta.order_by(Interesse.criado_em.desc(), Interesse.id.desc())).all()
    return [_saida_abrigo(i, a, t) for i, a, t in linhas]


@router.delete("/interesses/{interesse_id}", status_code=status.HTTP_204_NO_CONTENT)
def desistir(
    interesse_id: int,
    tutor_usuario: Usuario = Depends(exigir_tipo(TipoConta.TUTOR)),
    db: Session = Depends(get_db),
) -> Response:
    interesse = db.get(Interesse, interesse_id)
    if interesse is None or interesse.tutor_id != tutor_usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interesse não encontrado.")
    if interesse.status in ENCERRADOS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este interesse já foi encerrado pelo abrigo e não pode ser cancelado.")
    animal = db.get(Animal, interesse.animal_id)
    _notificar(db, animal.abrigo_id, f"{tutor_usuario.nome} desistiu do interesse em {animal.nome}.", interesse.id)
    db.delete(interesse)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/interesses/{interesse_id}", response_model=InteresseAbrigoOut)
def decidir(
    interesse_id: int,
    dados: DecisaoInteresse,
    abrigo: Abrigo = Depends(get_abrigo_operante),
    db: Session = Depends(get_db),
) -> InteresseAbrigoOut:
    """Abrigo: aguardando → em conversa / aprovado / recusado; em conversa → aprovado / recusado.
    Aprovar muda o animal para "em processo de adoção"."""
    interesse = db.get(Interesse, interesse_id)
    animal = db.get(Animal, interesse.animal_id) if interesse else None
    if interesse is None or animal.abrigo_id != abrigo.usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interesse não encontrado.")
    novo = dados.status
    if interesse.status in ENCERRADOS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este interesse já foi encerrado e não pode mais ser alterado.")
    if interesse.status == novo:
        raise HTTPException(status.HTTP_409_CONFLICT, "O interesse já está nesta situação.")
    if novo == StatusInteresse.APROVADO:
        if animal.status != StatusAnimal.DISPONIVEL:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Este animal já não está disponível: outro interesse foi aprovado ou a situação do animal foi alterada.",
            )
        animal.status = StatusAnimal.EM_PROCESSO

    interesse.status = novo
    mensagens = {
        StatusInteresse.EM_CONVERSA: f"O abrigo {abrigo.nome_abrigo} quer conversar sobre a adoção de {animal.nome}.",
        StatusInteresse.APROVADO: f"Boa notícia! {abrigo.nome_abrigo} aprovou seu interesse em adotar {animal.nome}.",
        StatusInteresse.RECUSADO: f"O abrigo {abrigo.nome_abrigo} não pôde seguir com seu interesse em {animal.nome}.",
    }
    _notificar(db, interesse.tutor_id, mensagens[novo], interesse.id)
    db.commit()
    db.refresh(interesse)
    return _saida_abrigo(interesse, animal, interesse.tutor)
