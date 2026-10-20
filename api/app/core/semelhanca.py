"""Reencontro por semelhança visual — RF-22 a RF-27, usando o núcleo OpenCL (`app/core/nucleo.py`).

Um só motor, três gatilhos (escopo, seção 4):
- quem perdeu compara a foto contra avistamentos e animais dos abrigos (RF-22, RF-23);
- quem encontrou compara contra os perdidos (busca inversa, RF-27);
- cada foto nova (avistamento ou animal de abrigo) é comparada em lote contra as perdas ativas, e o tutor e o
  abrigo são avisados quando a semelhança é alta ou média (monitoramento contínuo, RF-24 a RF-26).

Filtros prévios (RF-22): só entra na comparação o que é da mesma espécie, está dentro do raio e faz sentido no
tempo (avistado depois do sumiço). Porte e cor são opcionais. Cada registro tem até 5 fotos: a nota de um
candidato é a MAIOR entre todas as combinações das fotos dele com as fotos buscadas.

O sistema nunca diz "é o seu animal": mostra candidatos com grau qualitativo (alta, média, baixa) e quem decide é
a pessoa (escopo, seção 4.3).
"""
import datetime
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import nucleo
from app.core.geo import distancia_km
from app.models.animal import Animal, Foto
from app.models.enums import EntidadeFoto, GrauSemelhanca, StatusAnimal, StatusValidacao, TipoCorrespondencia
from app.models.reencontro import AnimalPerdido, Avistamento, Correspondencia
from app.models.usuario import Abrigo, Usuario

CASAS = {EntidadeFoto.ANIMAL_PERDIDO: 2, EntidadeFoto.AVISTAMENTO: 3}  # mesma privacidade das listas públicas
GRAUS_QUE_AVISAM = {"alta", "media"}
STATUS_ABRIGADO = (StatusAnimal.DISPONIVEL, StatusAnimal.EM_PROCESSO)


@dataclass
class Alvo:
    tipo: EntidadeFoto
    registro: object
    latitude: float
    longitude: float
    data: datetime.datetime | None
    rotulo: str
    fotos: list[Foto] = field(default_factory=list)


@dataclass
class Resultado:
    disponivel: bool
    notas: dict[tuple[str, int], tuple[float, str]]  # (tipo, id) → (nota, grau)
    fotos_comparadas: int = 0
    tempo_nucleo_ms: float = 0.0
    tempo_total_ms: float = 0.0
    modo: str = "opencl"
    motivo: str | None = None


def fotos_de(db: Session, tipo: EntidadeFoto, ids: list[int]) -> dict[int, list[Foto]]:
    if not ids:
        return {}
    por_id: dict[int, list[Foto]] = {i: [] for i in ids}
    for f in db.scalars(select(Foto).where(Foto.entidade_tipo == tipo.value, Foto.entidade_id.in_(ids)).order_by(Foto.ordem, Foto.id)):
        por_id[f.entidade_id].append(f)
    return por_id


def comparar(db: Session, fotos_buscadas: list[Foto], alvos: list[Alvo], modo: str = "opencl") -> Resultado:
    """Compara as fotos buscadas contra todas as fotos dos alvos, numa chamada só ao núcleo."""
    inicio = time.perf_counter()
    todas = fotos_buscadas + [f for a in alvos for f in a.fotos]
    try:
        desc = nucleo.descritores(db, todas)
        consultas = [desc[f.id] for f in fotos_buscadas if f.id in desc]
        candidatos = [(f.id, desc[f.id]) for a in alvos for f in a.fotos if f.id in desc]
        if not consultas:
            return Resultado(False, {}, motivo="As fotos deste registro ainda não foram processadas pelo núcleo.")
        resposta = nucleo.comparar(consultas, candidatos, modo) if candidatos else {"resultados": [], "tempos": {}}
    except nucleo.NucleoIndisponivel as erro:
        return Resultado(False, {}, motivo=f"Comparação por foto indisponível no momento ({erro}).")

    melhor_por_foto: dict[int, tuple[float, str]] = {}
    for lista in resposta["resultados"]:
        for item in lista:
            if item["nota"] > melhor_por_foto.get(item["id"], (-1.0, ""))[0]:
                melhor_por_foto[item["id"]] = (item["nota"], item["grau"])
    notas: dict[tuple[str, int], tuple[float, str]] = {}
    for a in alvos:
        das_fotos = [melhor_por_foto[f.id] for f in a.fotos if f.id in melhor_por_foto]
        if das_fotos:
            notas[(a.tipo.value, a.registro.id)] = max(das_fotos)
    return Resultado(
        True, notas, fotos_comparadas=len(candidatos) * len(consultas),
        tempo_nucleo_ms=resposta.get("tempos", {}).get("total_ms", 0.0),
        tempo_total_ms=(time.perf_counter() - inicio) * 1000, modo=resposta.get("modo", modo),
    )


# ---------- quem são os candidatos de cada busca (filtros prévios) ----------

def _mesmo(a: str | None, b: str | None) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def alvos_para_perdido(db: Session, perdido: AnimalPerdido, raio_km: float, mesmo_porte: bool, mesma_cor: bool) -> list[Alvo]:
    """Quem perdeu compara contra avistamentos (vistos depois do sumiço) e animais abrigados (RF-22)."""
    alvos: list[Alvo] = []
    avistamentos = db.scalars(select(Avistamento).where(
        Avistamento.especie == perdido.especie, Avistamento.data_avistamento >= perdido.data_desaparecimento,
        Avistamento.usuario_id != perdido.tutor_id,
    ))
    for av in avistamentos:
        if mesmo_porte and av.porte != perdido.porte or mesma_cor and not _mesmo(av.cor_predominante, perdido.cor_predominante):
            continue
        if distancia_km(perdido.latitude, perdido.longitude, av.latitude, av.longitude) <= raio_km:
            alvos.append(Alvo(EntidadeFoto.AVISTAMENTO, av, av.latitude, av.longitude, av.data_avistamento, "Avistamento"))
    animais = db.execute(
        select(Animal, Abrigo).join(Abrigo, Abrigo.usuario_id == Animal.abrigo_id).join(Usuario, Usuario.id == Abrigo.usuario_id)
        .where(Animal.especie == perdido.especie, Animal.status.in_(STATUS_ABRIGADO), Animal.removido_em.is_(None),
               Abrigo.status_validacao != StatusValidacao.REJEITADO, Usuario.ativo.is_(True))
    )
    for animal, abrigo in animais:
        if mesmo_porte and animal.porte != perdido.porte:
            continue
        if distancia_km(perdido.latitude, perdido.longitude, abrigo.latitude, abrigo.longitude) <= raio_km:
            alvos.append(Alvo(EntidadeFoto.ANIMAL, animal, abrigo.latitude, abrigo.longitude,
                              animal.data_entrada or animal.criado_em, f"{animal.nome} · {abrigo.nome_abrigo}"))
    _anexar_fotos(db, alvos)
    return alvos


def perdas_ativas_perto(db: Session, especie, latitude: float, longitude: float, ate: datetime.datetime | None,
                        excluir_tutor: int | None = None, raio_km: float | None = None) -> list[Alvo]:
    """Perdas não resolvidas da espécie cujo raio de busca (o do tutor, ou `raio_km`) alcança o ponto (RF-25 a RF-27)."""
    consulta = select(AnimalPerdido).where(AnimalPerdido.resolvido.is_(False), AnimalPerdido.especie == especie)
    if ate is not None:
        consulta = consulta.where(AnimalPerdido.data_desaparecimento <= ate)
    if excluir_tutor is not None:
        consulta = consulta.where(AnimalPerdido.tutor_id != excluir_tutor)
    alvos = []
    for p in db.scalars(consulta):
        limite = raio_km if raio_km is not None else p.raio_busca_km
        if distancia_km(p.latitude, p.longitude, latitude, longitude) <= limite:
            alvos.append(Alvo(EntidadeFoto.ANIMAL_PERDIDO, p, p.latitude, p.longitude, p.data_desaparecimento, "Animal perdido"))
    _anexar_fotos(db, alvos)
    return alvos


def _anexar_fotos(db: Session, alvos: list[Alvo]) -> None:
    for tipo in {a.tipo for a in alvos}:
        por_id = fotos_de(db, tipo, [a.registro.id for a in alvos if a.tipo == tipo])
        for a in alvos:
            if a.tipo == tipo:
                a.fotos = por_id.get(a.registro.id, [])


def ponto_publico(tipo: EntidadeFoto, lat: float, lng: float) -> tuple[float, float]:
    casas = CASAS.get(tipo)
    return (round(lat, casas), round(lng, casas)) if casas is not None else (lat, lng)


# ---------- monitoramento contínuo (RF-24 a RF-26) ----------

def registrar_correspondencia(db: Session, tipo: TipoCorrespondencia, perdido_id: int, nota: float, grau: str,
                              animal_id: int | None = None, avistamento_id: int | None = None) -> bool:
    """Guarda o match (base da grade de candidatos e da medição de acerto). Devolve False se já existia."""
    existe = db.scalar(select(Correspondencia.id).where(
        Correspondencia.animal_perdido_id == perdido_id, Correspondencia.animal_id == animal_id,
        Correspondencia.avistamento_id == avistamento_id,
    ))
    if existe:
        return False
    db.add(Correspondencia(tipo=tipo, animal_perdido_id=perdido_id, animal_id=animal_id, avistamento_id=avistamento_id,
                           score=nota, grau_semelhanca=GrauSemelhanca(grau), notificado=True))
    return True
