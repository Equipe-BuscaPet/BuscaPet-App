"""Registro de animal perdido (RF-19) e de avistamento (RF-20) — entradas do reencontro.

São as duas bases que o núcleo de similaridade (OpenCL) vai comparar (escopo, seção 4.1):
quem perdeu compara contra abrigos e avistamentos; quem encontrou compara contra os perdidos.
Esta etapa só registra e consulta; a comparação por foto entra com o núcleo (RF-21 em diante).

Regras de perfil:
- Consultar (lista e detalhe): público, inclusive visitante (escopo, seção 2.2).
- Registrar perdido: só tutor. Registrar avistamento: qualquer conta logada.
- Marcar como resolvido (RF-28): só o tutor que registrou a perda.
- Excluir: o autor do registro ou o administrador (moderação).

Alerta por proximidade (antes do núcleo): todo avistamento novo avisa os tutores com perda ativa da mesma
espécie, sumida até a data do avistamento, quando o ponto cai dentro do raio de busca que o tutor escolheu.
É a versão por distância do RF-25; o núcleo vai acrescentar a semelhança da foto.

Privacidade (escopo, seção 9): a resposta pública não traz nada de quem registrou, e a localização sai
arredondada (perdido: ~1 km; avistamento: ~100 m). A distância também é calculada sobre o ponto
arredondado, para que não dê para descobrir o ponto exato consultando de vários lugares.
"""
import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import auditoria
from app.core import fotos as armazenamento
from app.core.deps import exigir_tipo, get_usuario_atual, get_usuario_opcional
from app.core.geo import distancia_km
from app.db.session import get_db
from app.models.animal import Foto
from app.models.enums import EntidadeFoto, Especie, StatusBusca, TipoConta
from app.models.reencontro import AnimalPerdido, Avistamento, BuscaSalva, DescritorVisual
from app.models.transversais import Notificacao
from app.models.usuario import Usuario
from app.routers.animais import _para_datetime
from app.schemas.reencontro import AvistamentoIn, AvistamentoOut, PerdidoIn, PerdidoOut

router = APIRouter(tags=["reencontro"])

# multipart explícito: sem isso o Swagger anuncia formulário de texto e não mostra o botão de escolher arquivo.
FormularioComFotos = Form(media_type="multipart/form-data")

CASAS_PERDIDO = 2  # 0,01° ≈ 1,1 km
CASAS_AVISTAMENTO = 3  # 0,001° ≈ 110 m: quem procura precisa saber a rua, e o ponto é onde o animal estava
ESPECIE_NO_ALERTA = {Especie.CAO: "Um cão", Especie.GATO: "Um gato", Especie.OUTRO: "Um animal"}


# ---------- apoio ----------

async def _processar_fotos(fotos: list[UploadFile] | None) -> list[bytes]:
    """Valida todas as fotos antes de gravar qualquer coisa: ou entram todas, ou nenhuma."""
    fotos = [f for f in fotos or [] if f.filename]  # input de arquivo vazio no formulário chega sem nome
    if not fotos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Envie pelo menos uma foto do animal.")
    if len(fotos) > armazenamento.MAX_FOTOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Envie no máximo {armazenamento.MAX_FOTOS} fotos.")
    prontas = []
    for numero, foto in enumerate(fotos, start=1):
        conteudo = await foto.read(armazenamento.tamanho_maximo_bytes() + 1)
        try:
            prontas.append(armazenamento.processar(conteudo))
        except armazenamento.FotoInvalida as erro:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Foto {numero}: {erro}")
    return prontas


def _gravar(db: Session, registro, tipo: EntidadeFoto, prontas: list[bytes]) -> list[str]:
    """Grava o registro e as fotos na mesma operação. Se o banco falhar, apaga os arquivos já escritos."""
    nomes: list[str] = []
    try:
        db.add(registro)
        db.flush()  # gera o id do registro, usado pelas fotos
        for ordem, jpeg in enumerate(prontas):
            nome = armazenamento.salvar(jpeg)
            nomes.append(nome)
            db.add(Foto(entidade_tipo=tipo.value, entidade_id=registro.id, url=armazenamento.url_publica(nome), ordem=ordem))
        db.commit()
    except Exception:
        db.rollback()
        armazenamento.apagar(nomes)
        raise
    db.refresh(registro)
    return nomes


def _fotos_de(db: Session, tipo: EntidadeFoto, ids: list[int]) -> dict[int, list[str]]:
    if not ids:
        return {}
    linhas = db.scalars(
        select(Foto).where(Foto.entidade_tipo == tipo.value, Foto.entidade_id.in_(ids)).order_by(Foto.ordem, Foto.id)
    )
    por_registro: dict[int, list[str]] = {i: [] for i in ids}
    for foto in linhas:
        por_registro[foto.entidade_id].append(foto.url)
    return por_registro


def _comum(registro, fotos: list[str], casas: int | None, origem: tuple[float, float] | None) -> dict:
    """Campos compartilhados da resposta. casas=None devolve o ponto exato (só para o autor)."""
    lat, lng = registro.latitude, registro.longitude
    if casas is not None:
        lat, lng = round(lat, casas), round(lng, casas)
    distancia = round(distancia_km(origem[0], origem[1], lat, lng), 1) if origem else None
    return {
        "id": registro.id, "especie": registro.especie, "porte": registro.porte,
        "cor_predominante": registro.cor_predominante, "pelagem": registro.pelagem, "sexo": registro.sexo,
        "sinais_particulares": registro.sinais_particulares, "latitude": lat, "longitude": lng,
        "localizacao_aproximada": casas is not None, "fotos": fotos, "criado_em": registro.criado_em,
        "distancia_km": distancia,
    }


def _perdido_out(p: AnimalPerdido, fotos: list[str], exato: bool = False, origem=None) -> PerdidoOut:
    return PerdidoOut(
        **_comum(p, fotos, None if exato else CASAS_PERDIDO, origem),
        raio_busca_km=p.raio_busca_km, data_desaparecimento=p.data_desaparecimento, resolvido=p.resolvido,
    )


def _avistamento_out(a: Avistamento, fotos: list[str], exato: bool = False, origem=None) -> AvistamentoOut:
    return AvistamentoOut(
        **_comum(a, fotos, None if exato else CASAS_AVISTAMENTO, origem), data_avistamento=a.data_avistamento,
    )


def _origem(lat: float | None, lng: float | None, raio_km: float | None) -> tuple[float, float] | None:
    if (lat is None) != (lng is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe latitude e longitude juntas.")
    if raio_km is not None and lat is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Para filtrar por raio, informe a sua posição (latitude e longitude).")
    return (lat, lng) if lat is not None else None


def _filtrar_e_paginar(saidas: list, raio_km: float | None, limite: int, deslocamento: int) -> list:
    """Filtro de raio e ordenação por distância são feitos aqui (haversine, sem PostGIS), como no mapa de abrigos."""
    if raio_km is not None:
        saidas = [s for s in saidas if s.distancia_km <= raio_km]
    if saidas and saidas[0].distancia_km is not None:
        saidas.sort(key=lambda s: s.distancia_km)
    return saidas[deslocamento:deslocamento + limite]


def _excluir(db: Session, registro, tipo: EntidadeFoto, usuario: Usuario, dono_id: int) -> None:
    if usuario.tipo_conta != TipoConta.ADMIN and usuario.id != dono_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só quem fez o registro pode excluí-lo.")
    fotos = list(db.scalars(select(Foto).where(Foto.entidade_tipo == tipo.value, Foto.entidade_id == registro.id)))
    foto_ids = [f.id for f in fotos]
    if foto_ids:
        db.execute(delete(DescritorVisual).where(DescritorVisual.foto_id.in_(foto_ids)))
        db.execute(delete(Foto).where(Foto.id.in_(foto_ids)))
    if isinstance(registro, AnimalPerdido):
        db.execute(delete(BuscaSalva).where(BuscaSalva.animal_perdido_id == registro.id))
    nome = "perdido" if isinstance(registro, AnimalPerdido) else "avistamento"
    auditoria.registrar(db, usuario.id, f"{nome}.excluido", nome, registro.id, pelo_admin=(usuario.id != dono_id) or None)
    db.delete(registro)
    try:
        db.commit()
    except IntegrityError:  # já há correspondências do reencontro apontando para ele
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este registro já tem possíveis correspondências e não pode ser excluído. Marque o caso como resolvido.",
        )
    armazenamento.apagar([armazenamento.nome_da_url(f.url) for f in fotos])  # só depois do banco confirmar


# Filtros comuns às duas listas públicas.
def _filtros(
    especie: Especie | None = None,
    porte: str | None = Query(default=None, description="pequeno, medio ou grande"),
    lat: float | None = Query(default=None, ge=-90, le=90, description="Latitude de quem consulta"),
    lng: float | None = Query(default=None, ge=-180, le=180, description="Longitude de quem consulta"),
    raio_km: float | None = Query(default=None, gt=0, le=2000, description="Só registros até esta distância"),
    limite: int = Query(default=20, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
) -> dict:
    return {"especie": especie, "porte": porte, "origem": _origem(lat, lng, raio_km), "raio_km": raio_km,
            "limite": limite, "deslocamento": deslocamento}


# ---------- RF-19: animal perdido ----------

@router.post("/perdidos", response_model=PerdidoOut, status_code=status.HTTP_201_CREATED)
async def registrar_perdido(
    dados: Annotated[PerdidoIn, FormularioComFotos],
    tutor: Usuario = Depends(exigir_tipo(TipoConta.TUTOR)),
    db: Session = Depends(get_db),
) -> PerdidoOut:
    """Formulário multipart: características, local (latitude/longitude), data e de 1 a 5 fotos (campo `fotos`)."""
    prontas = await _processar_fotos(dados.fotos)
    campos = dados.model_dump(exclude={"fotos"})
    campos["data_desaparecimento"] = _para_datetime(campos["data_desaparecimento"])
    perdido = AnimalPerdido(tutor_id=tutor.id, **campos)
    nomes = _gravar(db, perdido, EntidadeFoto.ANIMAL_PERDIDO, prontas)
    auditoria.registrar(db, tutor.id, "perdido.registrado", "perdido", perdido.id, especie=perdido.especie.value)
    db.commit()
    return _perdido_out(perdido, [armazenamento.url_publica(n) for n in nomes], exato=True)


@router.get("/perdidos", response_model=list[PerdidoOut])
def listar_perdidos(filtros: dict = Depends(_filtros), db: Session = Depends(get_db)) -> list[PerdidoOut]:
    """Animais perdidos ainda não resolvidos, mais recentes primeiro (ou mais perto, se informar a posição)."""
    consulta = select(AnimalPerdido).where(AnimalPerdido.resolvido.is_(False))
    if filtros["especie"]:
        consulta = consulta.where(AnimalPerdido.especie == filtros["especie"])
    if filtros["porte"]:
        consulta = consulta.where(AnimalPerdido.porte == filtros["porte"])
    perdidos = list(db.scalars(consulta.order_by(AnimalPerdido.criado_em.desc(), AnimalPerdido.id.desc())))
    fotos = _fotos_de(db, EntidadeFoto.ANIMAL_PERDIDO, [p.id for p in perdidos])
    saidas = [_perdido_out(p, fotos[p.id], origem=filtros["origem"]) for p in perdidos]
    return _filtrar_e_paginar(saidas, filtros["raio_km"], filtros["limite"], filtros["deslocamento"])


@router.get("/perdidos/meus", response_model=list[PerdidoOut])
def listar_meus_perdidos(
    tutor: Usuario = Depends(exigir_tipo(TipoConta.TUTOR)),
    db: Session = Depends(get_db),
) -> list[PerdidoOut]:
    """Os registros do próprio tutor, inclusive os resolvidos, com a localização exata que ele marcou."""
    perdidos = list(db.scalars(
        select(AnimalPerdido).where(AnimalPerdido.tutor_id == tutor.id).order_by(AnimalPerdido.criado_em.desc(), AnimalPerdido.id.desc())
    ))
    fotos = _fotos_de(db, EntidadeFoto.ANIMAL_PERDIDO, [p.id for p in perdidos])
    return [_perdido_out(p, fotos[p.id], exato=True) for p in perdidos]


@router.patch("/perdidos/{perdido_id}/resolvido", response_model=PerdidoOut)
def marcar_resolvido(
    perdido_id: int,
    tutor: Usuario = Depends(exigir_tipo(TipoConta.TUTOR)),
    db: Session = Depends(get_db),
) -> PerdidoOut:
    """RF-28: o tutor encontrou o animal. O caso sai da lista pública e do mapa e para de gerar alertas.

    Não tem volta pela interface: se foi engano, o tutor registra a perda de novo.
    """
    perdido = db.get(AnimalPerdido, perdido_id)
    if perdido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    if perdido.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só quem registrou a perda pode marcar o caso como resolvido.")
    if perdido.resolvido:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este caso já está marcado como resolvido.")
    perdido.resolvido = True
    agora = datetime.datetime.now(datetime.UTC)
    for busca in db.scalars(select(BuscaSalva).where(BuscaSalva.animal_perdido_id == perdido.id, BuscaSalva.status == StatusBusca.MONITORANDO)):
        busca.status, busca.resolvida_em = StatusBusca.RESOLVIDA, agora
    auditoria.registrar(db, tutor.id, "perdido.resolvido", "perdido", perdido.id)
    db.commit()
    db.refresh(perdido)
    return _perdido_out(perdido, _fotos_de(db, EntidadeFoto.ANIMAL_PERDIDO, [perdido.id])[perdido.id], exato=True)


@router.get("/perdidos/{perdido_id}", response_model=PerdidoOut)
def consultar_perdido(
    perdido_id: int,
    usuario: Usuario | None = Depends(get_usuario_opcional),
    db: Session = Depends(get_db),
) -> PerdidoOut:
    perdido = db.get(AnimalPerdido, perdido_id)
    if perdido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    autor = usuario is not None and usuario.id == perdido.tutor_id
    return _perdido_out(perdido, _fotos_de(db, EntidadeFoto.ANIMAL_PERDIDO, [perdido.id])[perdido.id], exato=autor)


@router.delete("/perdidos/{perdido_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_perdido(
    perdido_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    perdido = db.get(AnimalPerdido, perdido_id)
    if perdido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    _excluir(db, perdido, EntidadeFoto.ANIMAL_PERDIDO, usuario, perdido.tutor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- RF-20: avistamento ----------

@router.post("/avistamentos", response_model=AvistamentoOut, status_code=status.HTTP_201_CREATED)
async def registrar_avistamento(
    dados: Annotated[AvistamentoIn, FormularioComFotos],
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> AvistamentoOut:
    """Qualquer conta logada registra um animal visto na rua: características, local, data e de 1 a 5 fotos."""
    prontas = await _processar_fotos(dados.fotos)
    campos = dados.model_dump(exclude={"fotos"})
    campos["data_avistamento"] = _para_datetime(campos["data_avistamento"])
    avistamento = Avistamento(usuario_id=usuario.id, **campos)
    nomes = _gravar(db, avistamento, EntidadeFoto.AVISTAMENTO, prontas)
    auditoria.registrar(db, usuario.id, "avistamento.registrado", "avistamento", avistamento.id, especie=avistamento.especie.value)
    _alertar_perdidos_proximos(db, avistamento, campos["data_avistamento"])
    return _avistamento_out(avistamento, [armazenamento.url_publica(n) for n in nomes], exato=True)


def _alertar_perdidos_proximos(db: Session, avistamento: Avistamento, data_avistamento: datetime.datetime) -> None:
    """Avisa cada tutor com perda ativa da mesma espécie se o avistamento caiu dentro do raio de busca dele.

    A distância usa os pontos exatos (é cálculo interno); a mensagem mostra só o valor arredondado.
    A data entra como o valor gravado (e não o lido de volta) para comparar igual em SQLite e Postgres.
    Um alerta por tutor, com a perda mais próxima: quem tem duas perdas da mesma espécie não recebe dois avisos iguais.
    """
    candidatos = db.scalars(select(AnimalPerdido).where(
        AnimalPerdido.resolvido.is_(False),
        AnimalPerdido.especie == avistamento.especie,
        AnimalPerdido.tutor_id != avistamento.usuario_id,  # quem avistou não é avisado do próprio registro
        AnimalPerdido.data_desaparecimento <= data_avistamento,  # visto antes de sumir não é ele
    ))
    mais_perto: dict[int, float] = {}  # tutor -> menor distância entre as perdas dele
    for perdido in candidatos:
        km = distancia_km(perdido.latitude, perdido.longitude, avistamento.latitude, avistamento.longitude)
        if km <= perdido.raio_busca_km and km < mais_perto.get(perdido.tutor_id, float("inf")):
            mais_perto[perdido.tutor_id] = km
    for tutor_id, km in mais_perto.items():
        perto = "a menos de 1 km" if km < 1 else f"a cerca de {round(km):d} km"
        db.add(Notificacao(
            usuario_id=tutor_id,
            mensagem=f"{ESPECIE_NO_ALERTA[avistamento.especie]} foi avistado {perto} de onde o seu animal sumiu. Veja se é ele.",
            referencia_tipo="avistamento", referencia_id=avistamento.id,
        ))
    db.commit()


@router.get("/avistamentos", response_model=list[AvistamentoOut])
def listar_avistamentos(filtros: dict = Depends(_filtros), db: Session = Depends(get_db)) -> list[AvistamentoOut]:
    consulta = select(Avistamento)
    if filtros["especie"]:
        consulta = consulta.where(Avistamento.especie == filtros["especie"])
    if filtros["porte"]:
        consulta = consulta.where(Avistamento.porte == filtros["porte"])
    avistamentos = list(db.scalars(consulta.order_by(Avistamento.criado_em.desc(), Avistamento.id.desc())))
    fotos = _fotos_de(db, EntidadeFoto.AVISTAMENTO, [a.id for a in avistamentos])
    saidas = [_avistamento_out(a, fotos[a.id], origem=filtros["origem"]) for a in avistamentos]
    return _filtrar_e_paginar(saidas, filtros["raio_km"], filtros["limite"], filtros["deslocamento"])


@router.get("/avistamentos/meus", response_model=list[AvistamentoOut])
def listar_meus_avistamentos(
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> list[AvistamentoOut]:
    avistamentos = list(db.scalars(
        select(Avistamento).where(Avistamento.usuario_id == usuario.id).order_by(Avistamento.criado_em.desc(), Avistamento.id.desc())
    ))
    fotos = _fotos_de(db, EntidadeFoto.AVISTAMENTO, [a.id for a in avistamentos])
    return [_avistamento_out(a, fotos[a.id], exato=True) for a in avistamentos]


@router.get("/avistamentos/{avistamento_id}", response_model=AvistamentoOut)
def consultar_avistamento(
    avistamento_id: int,
    usuario: Usuario | None = Depends(get_usuario_opcional),
    db: Session = Depends(get_db),
) -> AvistamentoOut:
    avistamento = db.get(Avistamento, avistamento_id)
    if avistamento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    autor = usuario is not None and usuario.id == avistamento.usuario_id
    fotos = _fotos_de(db, EntidadeFoto.AVISTAMENTO, [avistamento.id])[avistamento.id]
    return _avistamento_out(avistamento, fotos, exato=autor)


@router.delete("/avistamentos/{avistamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_avistamento(
    avistamento_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    avistamento = db.get(Avistamento, avistamento_id)
    if avistamento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado.")
    _excluir(db, avistamento, EntidadeFoto.AVISTAMENTO, usuario, avistamento.usuario_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
