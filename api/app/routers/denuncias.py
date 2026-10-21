"""Denúncia de anúncio (RF-41) e moderação pela administração.

Qualquer conta logada (menos o próprio abrigo) denuncia um anúncio de adoção visível. A administração decide:
- ignorado: denúncia improcedente (o denunciante é avisado);
- advertido: o abrigo recebe um aviso, o anúncio continua;
- removido: o anúncio sai do catálogo (`animais.removido_em`), os interesses abertos são encerrados;
- banido: além de remover o anúncio, o abrigo é suspenso (some do catálogo e do mapa, não publica).
A decisão vale para todas as denúncias pendentes do mesmo anúncio e fica no histórico de operações.
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import auditoria, regras
from app.core.deps import exigir_tipo, get_usuario_atual
from app.db.session import get_db
from app.models.animal import Animal
from app.models.enums import StatusDenuncia, StatusValidacao, TipoConta
from app.models.transversais import Denuncia, Notificacao
from app.models.usuario import Abrigo, Usuario
from app.routers.animais import _buscar_visivel
from app.schemas.denuncia import DecisaoDenuncia, DenunciaIn, DenunciaOut

router = APIRouter(tags=["denúncias"])
somente_admin = exigir_tipo(TipoConta.ADMIN)

AVISO_DENUNCIANTE = {
    StatusDenuncia.IGNORADO: "A administração analisou sua denúncia sobre {animal} e não encontrou irregularidade. Obrigado por avisar.",
    StatusDenuncia.ADVERTIDO: "Sua denúncia sobre {animal} foi analisada e o abrigo recebeu uma advertência. Obrigado por avisar.",
    StatusDenuncia.REMOVIDO: "Sua denúncia sobre {animal} foi analisada e o anúncio foi removido. Obrigado por avisar.",
    StatusDenuncia.BANIDO: "Sua denúncia sobre {animal} foi analisada: o anúncio foi removido e o abrigo, suspenso. Obrigado por avisar.",
}
AVISO_ABRIGO = {
    StatusDenuncia.ADVERTIDO: "Advertência da administração sobre o anúncio de {animal}: revise as informações e as regras de adoção.",
    StatusDenuncia.REMOVIDO: "O anúncio de {animal} foi removido pela administração após denúncia.",
    StatusDenuncia.BANIDO: "Seu abrigo foi suspenso pela administração após denúncia sobre o anúncio de {animal}.",
}


@router.post("/animais/{animal_id}/denuncias", status_code=status.HTTP_201_CREATED)
def denunciar(
    animal_id: int, dados: DenunciaIn, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db),
) -> dict:
    animal, abrigo = _buscar_visivel(animal_id, usuario, db)
    if usuario.id == animal.abrigo_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode denunciar o anúncio do seu próprio abrigo.")
    if usuario.tipo_conta == TipoConta.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A administração modera os anúncios diretamente.")
    if animal.removido_em is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este anúncio já foi removido pela administração.")
    ja = db.scalar(select(Denuncia.id).where(
        Denuncia.animal_id == animal.id, Denuncia.denunciante_id == usuario.id, Denuncia.status == StatusDenuncia.PENDENTE,
    ))
    if ja:
        raise HTTPException(status.HTTP_409_CONFLICT, "Você já denunciou este anúncio. A administração vai analisar.")
    denuncia = Denuncia(denunciante_id=usuario.id, animal_id=animal.id, motivo=dados.motivo)
    db.add(denuncia)
    db.flush()
    for admin_id in db.scalars(select(Usuario.id).where(Usuario.tipo_conta == TipoConta.ADMIN, Usuario.ativo.is_(True))):
        db.add(Notificacao(usuario_id=admin_id, referencia_tipo="denuncia", referencia_id=denuncia.id,
                           mensagem=f"Nova denúncia sobre o anúncio de {animal.nome} ({abrigo.nome_abrigo})."))
    auditoria.registrar(db, usuario.id, "denuncia.registrada", "denuncia", denuncia.id, animal_id=animal.id, animal=animal.nome)
    db.commit()
    return {"id": denuncia.id, "mensagem": "Denúncia registrada. A administração vai analisar o anúncio."}


def _saida(d: Denuncia, animal: Animal, abrigo: Abrigo, denunciante: Usuario, pendentes: int) -> DenunciaOut:
    return DenunciaOut(
        id=d.id, animal_id=animal.id, animal_nome=animal.nome, abrigo_id=abrigo.usuario_id, nome_abrigo=abrigo.nome_abrigo,
        denunciante_nome=denunciante.nome, motivo=d.motivo, status=d.status, criado_em=d.criado_em, resolvido_em=d.resolvido_em,
        denuncias_do_animal=pendentes,
    )


@router.get("/admin/denuncias", response_model=list[DenunciaOut])
def listar(
    status_denuncia: StatusDenuncia = Query(default=StatusDenuncia.PENDENTE, alias="status"),
    _: Usuario = Depends(somente_admin), db: Session = Depends(get_db),
) -> list[DenunciaOut]:
    """Fila de moderação: por padrão as pendentes, das mais antigas para as mais novas."""
    pendentes = dict(db.execute(
        select(Denuncia.animal_id, func.count()).where(Denuncia.status == StatusDenuncia.PENDENTE).group_by(Denuncia.animal_id)
    ).all())
    linhas = db.execute(
        select(Denuncia, Animal, Abrigo, Usuario)
        .join(Animal, Animal.id == Denuncia.animal_id).join(Abrigo, Abrigo.usuario_id == Animal.abrigo_id)
        .join(Usuario, Usuario.id == Denuncia.denunciante_id)
        .where(Denuncia.status == status_denuncia).order_by(Denuncia.criado_em, Denuncia.id)
    ).tuples()
    return [_saida(d, a, ab, u, pendentes.get(a.id, 0)) for d, a, ab, u in linhas]


@router.patch("/admin/denuncias/{denuncia_id}", response_model=DenunciaOut)
def decidir(
    denuncia_id: int, dados: DecisaoDenuncia, admin: Usuario = Depends(somente_admin), db: Session = Depends(get_db),
) -> DenunciaOut:
    denuncia = db.get(Denuncia, denuncia_id)
    if denuncia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Denúncia não encontrada.")
    if denuncia.status != StatusDenuncia.PENDENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta denúncia já foi analisada.")
    animal = db.get(Animal, denuncia.animal_id)
    abrigo = db.get(Abrigo, animal.abrigo_id)
    decisao = StatusDenuncia(dados.decisao)
    agora = datetime.datetime.now(datetime.UTC)

    if decisao in (StatusDenuncia.REMOVIDO, StatusDenuncia.BANIDO) and animal.removido_em is None:
        animal.removido_em = agora
        regras.encerrar_interesses_abertos(db, animal, admin.id, "anúncio removido pela administração")
    if decisao == StatusDenuncia.BANIDO:
        abrigo.status_validacao = StatusValidacao.REJEITADO
        abrigo.validado_por_id, abrigo.validado_em = admin.id, agora
        auditoria.registrar(db, admin.id, "abrigo.suspenso", "abrigo", abrigo.usuario_id, abrigo=abrigo.nome_abrigo, motivo="denúncia")

    # A decisão vale para todas as denúncias pendentes do mesmo anúncio (no ignorar/advertir, só para esta).
    mesmas = [denuncia]
    if decisao in (StatusDenuncia.REMOVIDO, StatusDenuncia.BANIDO):
        mesmas = list(db.scalars(select(Denuncia).where(Denuncia.animal_id == animal.id, Denuncia.status == StatusDenuncia.PENDENTE)))
    for d in mesmas:
        d.status, d.resolvido_por_id, d.resolvido_em = decisao, admin.id, agora
        db.add(Notificacao(usuario_id=d.denunciante_id, referencia_tipo="denuncia", referencia_id=d.id,
                           mensagem=AVISO_DENUNCIANTE[decisao].format(animal=animal.nome)))
    if decisao in AVISO_ABRIGO:
        texto = AVISO_ABRIGO[decisao].format(animal=animal.nome)
        if dados.observacao:
            texto = f"{texto} Observação: {dados.observacao.strip()}"
        db.add(Notificacao(usuario_id=abrigo.usuario_id, referencia_tipo="animal", referencia_id=animal.id, mensagem=texto))
    auditoria.registrar(db, admin.id, f"denuncia.{decisao.value}", "denuncia", denuncia.id, animal_id=animal.id,
                        animal=animal.nome, abrigo=abrigo.nome_abrigo, denuncias=len(mesmas))
    db.commit()
    denunciante = db.get(Usuario, denuncia.denunciante_id)
    return _saida(denuncia, animal, abrigo, denunciante, 0)
