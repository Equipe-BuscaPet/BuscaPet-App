"""Regras de negócio compartilhadas entre módulos (revisão geral da Sprint 8).

Ficam aqui, e não num roteador, para serem usadas por mais de um (animais, denúncias) sem import circular.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import auditoria
from app.models.animal import Animal, Interesse
from app.models.enums import StatusInteresse
from app.models.transversais import Notificacao

ABERTOS = (StatusInteresse.AGUARDANDO, StatusInteresse.EM_CONVERSA)


def encerrar_interesses_abertos(db: Session, animal: Animal, ator_id: int, motivo: str) -> int:
    """Quando o animal deixa de estar disponível para sempre (adotado por fora, óbito, transferido ou anúncio
    removido), os interesses que ainda esperavam resposta são encerrados e cada tutor é avisado — antes, eles
    ficavam "aguardando" para sempre. Interesse já aprovado ou recusado não muda. Sem commit."""
    abertos = list(db.scalars(select(Interesse).where(Interesse.animal_id == animal.id, Interesse.status.in_(ABERTOS))))
    for interesse in abertos:
        interesse.status = StatusInteresse.RECUSADO
        db.add(Notificacao(
            usuario_id=interesse.tutor_id, referencia_tipo="interesse", referencia_id=interesse.id,
            mensagem=f"{animal.nome} não está mais disponível para adoção ({motivo}). Seu interesse foi encerrado.",
        ))
        auditoria.registrar(db, ator_id, "interesse.recusado", "interesse", interesse.id, animal_id=animal.id,
                            animal=animal.nome, motivo=motivo)
    return len(abertos)


def desfazer_aprovacao(db: Session, animal: Animal, ator_id: int) -> int:
    """O animal voltou de "em processo de adoção" para "disponível": a adoção não se concretizou. O interesse
    aprovado é encerrado e o tutor avisado — sem isso, o abrigo poderia aprovar um segundo interesse e o animal
    ficaria com dois aprovados (contra a regra "um aprovado por animal" da Sprint 4). Sem commit."""
    aprovados = list(db.scalars(select(Interesse).where(Interesse.animal_id == animal.id, Interesse.status == StatusInteresse.APROVADO)))
    for interesse in aprovados:
        interesse.status = StatusInteresse.RECUSADO
        db.add(Notificacao(
            usuario_id=interesse.tutor_id, referencia_tipo="interesse", referencia_id=interesse.id,
            mensagem=f"A adoção de {animal.nome} não foi concluída e o animal voltou a ficar disponível no abrigo.",
        ))
        auditoria.registrar(db, ator_id, "interesse.recusado", "interesse", interesse.id, animal_id=animal.id,
                            animal=animal.nome, motivo="adoção não concluída")
    return len(aprovados)
