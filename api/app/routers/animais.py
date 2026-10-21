"""CRUD de animais para adoção — RF-12 a RF-18 (entidade principal da Sprint 3).

Regras de perfil:
- Consultar (lista e detalhe): público. O visitante vê animais de abrigos ativos e
  não suspensos (verificados ou não: o selo aparece na resposta); o dono (e o admin)
  enxergam também os seus/todos.
- Cadastrar e atualizar: só abrigo não suspenso, e só os animais do próprio abrigo.
- Excluir: o abrigo dono ou o administrador (moderação).
- Fotos (RF-17): de 1 a 5 por animal, enviadas e removidas pelo abrigo dono; a primeira é a capa do catálogo.
  Mesmo tratamento das fotos do reencontro: validadas, reduzidas e regravadas sem metadados (GPS).
- Alerta ao abrigo (RF-26): cada foto nova vira descritor (núcleo OpenCL) e é comparada com as perdas ativas
  da mesma espécie cujo raio alcança o abrigo. Semelhança alta ou média avisa o tutor e o abrigo.
"""
import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core import auditoria, nucleo, regras, semelhanca
from app.core import fotos as armazenamento
from app.core.deps import exigir_tipo, get_abrigo_operante, get_usuario_opcional
from app.db.session import get_db
from app.models.animal import Animal, Foto, Interesse
from app.models.enums import EntidadeFoto, Especie, Sexo, StatusAnimal, StatusValidacao, TipoConta, TipoCorrespondencia
from app.models.reencontro import Correspondencia, DescritorVisual
from app.models.transversais import Notificacao
from app.models.usuario import Abrigo, Usuario
from app.schemas.animal import AnimalCreate, AnimalOut, AnimalUpdate

router = APIRouter(prefix="/animais", tags=["animais"])


def _para_datetime(dia: datetime.date | None) -> datetime.datetime | None:
    # A coluna data_entrada é DateTime; o formulário envia só a data.
    return datetime.datetime.combine(dia, datetime.time.min, tzinfo=datetime.UTC) if dia else None


def _saida(animal: Animal, abrigo: Abrigo) -> AnimalOut:
    """As fotos vêm do relacionamento Animal.fotos (ordenado; a primeira é a capa), carregado em lote nas listas."""
    saida = AnimalOut.model_validate(animal)
    saida.nome_abrigo = abrigo.nome_abrigo
    saida.abrigo_verificado = abrigo.status_validacao == StatusValidacao.APROVADO
    return saida


def _publico_visivel(consulta):
    """Filtro de visibilidade pública: conta ativa, abrigo não suspenso e anúncio não removido pela moderação."""
    return consulta.where(
        Abrigo.status_validacao != StatusValidacao.REJEITADO,
        Usuario.ativo.is_(True),
        Animal.removido_em.is_(None),
    )


def _consulta_base():
    return (
        select(Animal, Abrigo)
        .options(selectinload(Animal.fotos))  # fotos de todos os animais da página numa consulta só (sem N+1)
        .join(Abrigo, Abrigo.usuario_id == Animal.abrigo_id)
        .join(Usuario, Usuario.id == Abrigo.usuario_id)
    )


# Situações em que o animal não volta a ficar disponível: os interesses que esperavam resposta são encerrados.
FORA_PARA_SEMPRE = {StatusAnimal.ADOTADO, StatusAnimal.OBITO, StatusAnimal.TRANSFERIDO}
MOTIVO = {StatusAnimal.ADOTADO: "foi adotado", StatusAnimal.OBITO: "o abrigo registrou o falecimento",
          StatusAnimal.TRANSFERIDO: "foi transferido para outro lugar"}


@router.post("", response_model=AnimalOut, status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: AnimalCreate,
    abrigo: Abrigo = Depends(get_abrigo_operante),
    db: Session = Depends(get_db),
) -> AnimalOut:
    """O abrigo cadastra um animal para adoção (RF-13). As fotos vão depois, em `POST /animais/{id}/fotos`."""
    campos = dados.model_dump()
    campos["data_entrada"] = _para_datetime(campos["data_entrada"])
    animal = Animal(abrigo_id=abrigo.usuario_id, **campos)
    db.add(animal)
    db.flush()
    auditoria.registrar(db, abrigo.usuario_id, "animal.cadastrado", "animal", animal.id, animal=animal.nome)
    db.commit()
    db.refresh(animal)
    return _saida(animal, abrigo)


@router.get("", response_model=list[AnimalOut])
def listar(
    especie: Especie | None = None,
    porte: str | None = Query(default=None, description="pequeno, medio ou grande"),
    status_animal: StatusAnimal | None = Query(default=StatusAnimal.DISPONIVEL, alias="status"),
    abrigo_id: int | None = None,
    busca: str | None = Query(default=None, max_length=100, description="Trecho do nome ou da raça"),
    sexo: Sexo | None = None,
    idade: Literal["filhote", "adulto", "idoso"] | None = Query(default=None, description="filhote < 1 ano; idoso a partir de 8 anos"),
    castrado: bool | None = None,
    vacinado: bool | None = None,
    convive_criancas: bool | None = Query(default=None, description="true: só quem convive bem com crianças"),
    convive_animais: bool | None = Query(default=None, description="true: só quem convive bem com outros animais"),
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
    # RF-14: filtros combinados (cada um só restringe; juntos, valem todos ao mesmo tempo)
    if sexo:
        consulta = consulta.where(Animal.sexo == sexo)
    if idade:
        faixas = {"filhote": (0, 11), "adulto": (12, 95), "idoso": (96, 600)}
        minimo, maximo = faixas[idade]
        consulta = consulta.where(Animal.idade_estimada_meses.between(minimo, maximo))
    for coluna, valor in ((Animal.castrado, castrado), (Animal.vacinado, vacinado),
                          (Animal.convivencia_criancas, convive_criancas), (Animal.convivencia_outros_animais, convive_animais)):
        if valor is not None:
            consulta = consulta.where(coluna.is_(valor))
    linhas = db.execute(
        consulta.order_by(Animal.criado_em.desc(), Animal.id.desc()).limit(limite).offset(deslocamento)
    ).all()
    return [_saida(animal, abrigo) for animal, abrigo in linhas]


@router.get("/meus", response_model=list[AnimalOut])
def listar_meus(
    usuario: Usuario = Depends(exigir_tipo(TipoConta.ABRIGO)),
    db: Session = Depends(get_db),
) -> list[AnimalOut]:
    """Todos os animais do abrigo logado, em qualquer status."""
    linhas = db.execute(
        _consulta_base().where(Animal.abrigo_id == usuario.id).order_by(Animal.criado_em.desc(), Animal.id.desc())
    ).all()
    return [_saida(animal, abrigo) for animal, abrigo in linhas]


def _buscar_visivel(animal_id: int, usuario: Usuario | None, db: Session) -> tuple[Animal, Abrigo]:
    linha = db.execute(_consulta_base().where(Animal.id == animal_id)).first()
    if linha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    animal, abrigo = linha
    dono = usuario is not None and usuario.id == animal.abrigo_id
    admin = usuario is not None and usuario.tipo_conta == TipoConta.ADMIN
    publico = abrigo.status_validacao != StatusValidacao.REJEITADO and abrigo.usuario.ativo and animal.removido_em is None
    if not (publico or dono or admin):
        # 404 (e não 403) para não confirmar a existência de cadastros suspensos ou desativados.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    return animal, abrigo


@router.get("/{animal_id}", response_model=AnimalOut)
def consultar(
    animal_id: int,
    usuario: Usuario | None = Depends(get_usuario_opcional),
    db: Session = Depends(get_db),
) -> AnimalOut:
    """Ficha do animal. Anúncio removido pela moderação só aparece para o próprio abrigo e para a administração."""
    animal, abrigo = _buscar_visivel(animal_id, usuario, db)
    return _saida(animal, abrigo)


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
    abrigo: Abrigo = Depends(get_abrigo_operante),
    db: Session = Depends(get_db),
) -> AnimalOut:
    """O abrigo dono edita o animal; só os campos enviados mudam."""
    animal = _animal_do_abrigo(animal_id, abrigo, db)
    enviados = dados.model_dump(exclude_unset=True)
    obrigatorios = {"nome", "especie", "porte", "sexo", "status"}
    vazios = sorted(c for c in obrigatorios if c in enviados and enviados[c] is None)
    if vazios:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Campos obrigatórios não podem ficar vazios: {', '.join(vazios)}.")
    if "data_entrada" in enviados:
        enviados["data_entrada"] = _para_datetime(enviados["data_entrada"])
    situacao_antes = animal.status
    for campo, valor in enviados.items():
        setattr(animal, campo, valor)
    if animal.status != situacao_antes and animal.status in FORA_PARA_SEMPRE:
        regras.encerrar_interesses_abertos(db, animal, abrigo.usuario_id, MOTIVO[animal.status])
    if situacao_antes == StatusAnimal.EM_PROCESSO and animal.status == StatusAnimal.DISPONIVEL:
        regras.desfazer_aprovacao(db, animal, abrigo.usuario_id)
    auditoria.registrar(
        db, abrigo.usuario_id, "animal.atualizado", "animal", animal.id, animal=animal.nome, campos=sorted(enviados),
        situacao=f"{situacao_antes.value} → {animal.status.value}" if animal.status != situacao_antes else None,
    )
    db.commit()
    db.refresh(animal)
    return _saida(animal, abrigo)


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    animal_id: int,
    usuario: Usuario = Depends(exigir_tipo(TipoConta.ABRIGO, TipoConta.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    """Exclusão de verdade (a linha some). Remove antes o que depende só deste
    animal: interesses, fotos, os descritores dessas fotos e as correspondências
    do reencontro. Se ainda houver vínculos (ex.: doações), responde 409: nesse
    caso o caminho certo é mudar o status para adotado/transferido."""
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Animal não encontrado.")
    if usuario.tipo_conta == TipoConta.ABRIGO and animal.abrigo_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este animal pertence a outro abrigo.")
    if usuario.tipo_conta == TipoConta.ABRIGO and (usuario.abrigo is None or usuario.abrigo.status_validacao == StatusValidacao.REJEITADO):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu abrigo foi suspenso pela administração.")

    fotos_do_animal = list(db.scalars(select(Foto).where(Foto.entidade_tipo == "animal", Foto.entidade_id == animal.id)))
    foto_ids = [f.id for f in fotos_do_animal]
    if foto_ids:
        db.execute(delete(DescritorVisual).where(DescritorVisual.foto_id.in_(foto_ids)))
        db.execute(delete(Foto).where(Foto.id.in_(foto_ids)))
    db.execute(delete(Interesse).where(Interesse.animal_id == animal.id))
    db.execute(delete(Correspondencia).where(Correspondencia.animal_id == animal.id))
    auditoria.registrar(db, usuario.id, "animal.excluido", "animal", animal.id, animal=animal.nome)
    db.delete(animal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este animal tem registros vinculados e não pode ser excluído. Altere o status para adotado ou transferido.",
        )
    armazenamento.apagar([armazenamento.nome_da_url(f.url) for f in fotos_do_animal])  # só depois do banco confirmar
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- RF-17: fotos do animal ----------

def _fotos_do_animal(db: Session, animal_id: int) -> list[Foto]:
    return list(db.scalars(select(Foto).where(Foto.entidade_tipo == EntidadeFoto.ANIMAL.value, Foto.entidade_id == animal_id)
                           .order_by(Foto.ordem, Foto.id)))


def _com_fotos(db: Session, animal: Animal, abrigo: Abrigo) -> AnimalOut:
    db.expire(animal, ["fotos"])  # relê as fotos depois da mudança
    return _saida(animal, abrigo)


@router.post("/{animal_id}/fotos", response_model=AnimalOut, status_code=status.HTTP_201_CREATED)
async def enviar_fotos(
    animal_id: int,
    fotos: list[UploadFile] = File(..., description="De 1 a 5 fotos no total por animal (JPEG, PNG ou WebP)"),
    abrigo: Abrigo = Depends(get_abrigo_operante),
    db: Session = Depends(get_db),
) -> AnimalOut:
    """Acrescenta fotos ao animal. Ou entram todas, ou nenhuma (se uma for inválida, nada é gravado)."""
    animal = _animal_do_abrigo(animal_id, abrigo, db)
    existentes = _fotos_do_animal(db, animal.id)
    fotos = [f for f in fotos if f.filename]
    if not fotos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escolha pelo menos uma foto.")
    if len(existentes) + len(fotos) > armazenamento.MAX_FOTOS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Cada animal pode ter no máximo {armazenamento.MAX_FOTOS} fotos (este já tem {len(existentes)}).",
        )
    prontas = []
    for numero, foto in enumerate(fotos, start=1):
        try:
            prontas.append(armazenamento.processar(await foto.read(armazenamento.tamanho_maximo_bytes() + 1)))
        except armazenamento.FotoInvalida as erro:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Foto {numero}: {erro}")
    nomes: list[str] = []
    novas: list[Foto] = []
    try:
        proxima = max((f.ordem for f in existentes), default=-1) + 1
        for i, jpeg in enumerate(prontas):
            nome = armazenamento.salvar(jpeg)
            nomes.append(nome)
            novas.append(Foto(entidade_tipo=EntidadeFoto.ANIMAL.value, entidade_id=animal.id, url=armazenamento.url_publica(nome), ordem=proxima + i))
        db.add_all(novas)
        auditoria.registrar(db, abrigo.usuario_id, "animal.fotos", "animal", animal.id, animal=animal.nome, enviadas=len(prontas))
        db.commit()
    except Exception:
        db.rollback()
        armazenamento.apagar(nomes)
        raise
    nucleo.indexar(db, novas)
    _alertar_perdas_parecidas(db, animal, abrigo, novas)
    return _com_fotos(db, animal, abrigo)


def _alertar_perdas_parecidas(db: Session, animal: Animal, abrigo: Abrigo, fotos: list[Foto]) -> None:
    """RF-26: o abrigo cadastrou um animal parecido com um perdido próximo → avisa o tutor e o abrigo.

    Só com o núcleo no ar (sem a foto não há critério: avisar todo tutor da espécie seria ruído). Cada par
    animal × perda avisa uma vez só, mesmo que o abrigo mande mais fotos depois.
    """
    if animal.status not in semelhanca.STATUS_ABRIGADO or animal.removido_em is not None:
        return
    alvos = semelhanca.perdas_ativas_perto(db, animal.especie, abrigo.latitude, abrigo.longitude, ate=None)
    if not alvos:
        return
    resultado = semelhanca.comparar(db, fotos, alvos)
    if not resultado.disponivel:
        return
    especie = {Especie.CAO: "um cão", Especie.GATO: "um gato"}.get(animal.especie, "um animal")
    avisados = []
    for alvo in alvos:
        nota, grau = resultado.notas.get(("animal_perdido", alvo.registro.id), (None, None))
        if grau not in semelhanca.GRAUS_QUE_AVISAM:
            continue
        if not semelhanca.registrar_correspondencia(db, TipoCorrespondencia.ALERTA_ABRIGO, alvo.registro.id, nota, grau,
                                                    animal_id=animal.id):
            continue
        rotulo = "alta" if grau == "alta" else "média"
        db.add(Notificacao(
            usuario_id=alvo.registro.tutor_id,
            mensagem=f"O abrigo {abrigo.nome_abrigo} cadastrou {especie} com semelhança {rotulo} com o seu. Veja se é ele.",
            referencia_tipo="animal_semelhante", referencia_id=animal.id,
        ))
        avisados.append((nota, alvo.registro.id))
    if avisados:
        _, melhor = max(avisados)
        qtd = len(avisados)
        db.add(Notificacao(
            usuario_id=abrigo.usuario_id,
            mensagem=(f"As fotos de {animal.nome} parecem com {qtd} animal(is) perdido(s) por perto. "
                      "O(s) tutor(es) foi(ram) avisado(s) e pode(m) entrar em contato."),
            referencia_tipo="perdido_semelhante", referencia_id=melhor,
        ))
    db.commit()


def _foto_do_animal(db: Session, animal: Animal, foto_id: int) -> Foto:
    foto = db.get(Foto, foto_id)
    if foto is None or foto.entidade_tipo != EntidadeFoto.ANIMAL.value or foto.entidade_id != animal.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto não encontrada.")
    return foto


@router.delete("/{animal_id}/fotos/{foto_id}", response_model=AnimalOut)
def excluir_foto(animal_id: int, foto_id: int, abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> AnimalOut:
    """O abrigo dono remove uma foto do animal (e o descritor visual dela)."""
    animal = _animal_do_abrigo(animal_id, abrigo, db)
    foto = _foto_do_animal(db, animal, foto_id)
    url = foto.url
    db.execute(delete(DescritorVisual).where(DescritorVisual.foto_id == foto.id))
    db.delete(foto)
    auditoria.registrar(db, abrigo.usuario_id, "animal.fotos", "animal", animal.id, animal=animal.nome, removida=foto_id)
    db.commit()
    armazenamento.apagar([armazenamento.nome_da_url(url)])
    return _com_fotos(db, animal, abrigo)


@router.patch("/{animal_id}/fotos/{foto_id}/capa", response_model=AnimalOut)
def definir_capa(animal_id: int, foto_id: int, abrigo: Abrigo = Depends(get_abrigo_operante), db: Session = Depends(get_db)) -> AnimalOut:
    """A foto escolhida passa a ser a primeira (a capa do catálogo); as outras mantêm a ordem."""
    animal = _animal_do_abrigo(animal_id, abrigo, db)
    capa = _foto_do_animal(db, animal, foto_id)
    for ordem, foto in enumerate([capa] + [f for f in _fotos_do_animal(db, animal.id) if f.id != capa.id]):
        foto.ordem = ordem
    db.commit()
    return _com_fotos(db, animal, abrigo)
