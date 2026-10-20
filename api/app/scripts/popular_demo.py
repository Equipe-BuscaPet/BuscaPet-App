"""Cria os dados de demonstração do BuscaPet: os mesmos abrigos, animais e contas para todo o time.

Uso, a partir da pasta api/ (ou dentro do container: `docker compose exec api python -m app.scripts.popular_demo`):
    python -m app.scripts.popular_demo

É seguro rodar mais de uma vez: o que já existe (pelo e-mail da conta ou pelo nome do animal no abrigo)
é ignorado. Por segurança, o script **só roda em banco local** (host `db`, `localhost` ou `127.0.0.1`):
as senhas abaixo são públicas e não podem existir no banco compartilhado (Supabase). Para forçar, `--forcar`.

Contas criadas (senha de todas: veja SENHA_DEMO):
    admin@exemplo.com                 administrador
    patinhas@exemplo.com              abrigo VERIFICADO (Abrigo Patinhas Felizes, Recife)
    gatinhos@exemplo.com              abrigo não verificado (Casa dos Gatinhos, Olinda)
    cordeiro@exemplo.com              abrigo não verificado (Protetores do Cordeiro, Recife)
    quatropatas@exemplo.com           abrigo não verificado (Amigos de Quatro Patas, Jaboatão)
    maria@exemplo.com / joao@exemplo.com   tutores
    amigofiel@, petcenter@, clinicaboavista@, racaonordeste@exemplo.com   apoiadores (petshop, petshop,
                                      clínica e distribuidora), com doações confirmadas em meses seguidos
                                      para o ranking, e uma doação aguardando a confirmação do Patinhas

O Abrigo Patinhas Felizes (verificado) ganha também necessidades publicadas no mural e um histórico de adoções
(Pingo, adotado pela Maria; Nina, aprovada para o João; um interesse aguardando no Thor), com os registros de
auditoria nas datas em que aconteceram, para o painel e os relatórios terem o que mostrar.
"""
import argparse
import datetime
import sys

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.seguranca import hash_senha
from app.db.session import SessionLocal
from pathlib import Path

from app.core import auditoria, pontuacao
from app.core import fotos as armazenamento
from app.models.animal import Animal, Foto, Interesse
from app.models.doacao import Doacao, Necessidade
from app.models.enums import (
    EntidadeFoto,
    Especie,
    Sexo,
    StatusAnimal,
    StatusDoacao,
    StatusInteresse,
    StatusValidacao,
    TipoConta,
    TipoEstabelecimento,
    UrgenciaNecessidade,
)
from app.models.transversais import LogAuditoria
from app.models.usuario import Abrigo, Apoiador, Tutor, Usuario

SENHA_DEMO = "Senha1234!"
HOSTS_LOCAIS = {"db", "localhost", "127.0.0.1"}

ADMIN = ("Administração BuscaPet", "admin@exemplo.com")

# nome do responsável, e-mail, dados do abrigo, verificado?, animais
ABRIGOS = [
    {
        "responsavel": "Helena Duarte", "email": "patinhas@exemplo.com", "verificado": True,
        "nome_abrigo": "Abrigo Patinhas Felizes", "endereco": "Av. Boa Viagem, 1200, Recife",
        "latitude": -8.1176, "longitude": -34.8996, "telefone": "81988880001", "horario": "Seg a sáb, 9h às 17h",
        "animais": [
            ("Thor", Especie.CAO, "grande", Sexo.MACHO, 36, "Brincalhão e leal"),
            ("Mel", Especie.CAO, "pequeno", Sexo.FEMEA, 8, "Tranquila e dócil"),
            ("Bolinha", Especie.CAO, "pequeno", Sexo.MACHO, 24, "Esperto e sociável"),
        ],
    },
    {
        "responsavel": "Carla Menezes", "email": "gatinhos@exemplo.com", "verificado": False,
        "nome_abrigo": "Casa dos Gatinhos", "endereco": "Rua Bispo Coutinho, 20, Olinda",
        "latitude": -8.0089, "longitude": -34.8553, "telefone": "81988880002", "horario": "Todos os dias, 10h às 16h",
        "animais": [
            ("Luna", Especie.GATO, "pequeno", Sexo.FEMEA, 14, "Carinhosa e curiosa"),
            ("Mia", Especie.GATO, "pequeno", Sexo.FEMEA, 5, "Brincalhona"),
            ("Simba", Especie.GATO, "medio", Sexo.MACHO, 30, "Independente e calmo"),
        ],
    },
    {
        "responsavel": "Paulo Andrade", "email": "cordeiro@exemplo.com", "verificado": False,
        "nome_abrigo": "Protetores do Cordeiro", "endereco": "Rua Real da Torre, 800, Recife",
        "latitude": -8.0457, "longitude": -34.9097, "telefone": "81988880003", "horario": "Sáb e dom, 8h às 12h",
        "animais": [("Rex", Especie.CAO, "medio", Sexo.MACHO, 48, "Protetor e obediente")],
    },
    {
        "responsavel": "Renata Lima", "email": "quatropatas@exemplo.com", "verificado": False,
        "nome_abrigo": "Amigos de Quatro Patas", "endereco": "Av. Barreto de Menezes, 500, Jaboatão dos Guararapes",
        "latitude": -8.1127, "longitude": -35.0149, "telefone": "81988880004", "horario": "Seg a sex, 9h às 15h",
        "animais": [("Pipoca", Especie.GATO, "pequeno", Sexo.FEMEA, 10, "Meiga")],
    },
]

TUTORES = [
    ("Maria Souza", "maria@exemplo.com", "81999990001", "Recife"),
    ("João Pereira", "joao@exemplo.com", "81999990002", "Olinda"),
]

# Necessidades do Abrigo Patinhas Felizes (o único verificado: só ele publica no mural).
NECESSIDADES = [
    ("Ração para cão adulto (saco de 15 kg)", 10, UrgenciaNecessidade.ALTA),
    ("Vermífugo para filhotes", 20, UrgenciaNecessidade.MEDIA),
    ("Material de limpeza (kit)", 5, UrgenciaNecessidade.MEDIA),
    ("Areia sanitária (pacote de 4 kg)", 8, UrgenciaNecessidade.BAIXA),
]

# nome, e-mail, CNPJ, tipo, endereço, lat, lng, doações confirmadas por mês (0 = este mês, 1 = o anterior...)
APOIADORES = [
    ("Pet Shop Amigo Fiel", "amigofiel@exemplo.com", "12034567000168", TipoEstabelecimento.PETSHOP,
     "Rua dos Navegantes, 300, Recife", -8.1203, -34.9011, {0: 1, 1: 1, 2: 1}),
    ("Pet Center Graças", "petcenter@exemplo.com", "23045678000196", TipoEstabelecimento.PETSHOP,
     "Rua das Graças, 150, Recife", -8.0469, -34.8985, {0: 2}),
    ("Clínica Veterinária Boa Vista", "clinicaboavista@exemplo.com", "34056789000114", TipoEstabelecimento.CLINICA,
     "Rua da Aurora, 900, Recife", -8.0601, -34.8820, {0: 1, 1: 1}),
    ("Distribuidora Ração Nordeste", "racaonordeste@exemplo.com", "45067890000197", TipoEstabelecimento.DISTRIBUIDORA,
     "Av. Recife, 4000, Recife", -8.1060, -34.9420, {0: 3}),
]


def _dia_do_mes(meses_atras: int) -> datetime.datetime:
    """Dia 5 de N meses atrás (dia 5 para cair no passado mesmo no começo do mês atual)."""
    hoje = datetime.datetime.now(datetime.UTC)
    ano, mes = hoje.year, hoje.month
    for _ in range(meses_atras):
        ano, mes = pontuacao.mes_anterior(ano, mes)
    return min(datetime.datetime(ano, mes, 5, 15, tzinfo=datetime.UTC), hoje)


def _usuario(db: Session, nome: str, email: str, tipo: TipoConta) -> tuple[Usuario, bool]:
    existente = db.scalar(select(Usuario).where(Usuario.email == email))
    if existente:
        return existente, False
    usuario = Usuario(nome=nome, email=email, senha_hash=hash_senha(SENHA_DEMO), tipo_conta=tipo)
    db.add(usuario)
    db.flush()
    return usuario, True


def popular(db: Session) -> dict[str, int]:
    """Cria o que faltar e devolve quantas contas, abrigos e animais foram criados agora."""
    criados = {"contas": 0, "animais": 0}

    admin, novo = _usuario(db, ADMIN[0], ADMIN[1], TipoConta.ADMIN)
    criados["contas"] += novo

    for dados in ABRIGOS:
        usuario, novo = _usuario(db, dados["responsavel"], dados["email"], TipoConta.ABRIGO)
        criados["contas"] += novo
        if novo:
            usuario.abrigo = Abrigo(
                nome_abrigo=dados["nome_abrigo"], endereco=dados["endereco"],
                latitude=dados["latitude"], longitude=dados["longitude"],
                telefone=dados["telefone"], horario_funcionamento=dados["horario"],
                status_validacao=StatusValidacao.APROVADO if dados["verificado"] else StatusValidacao.PENDENTE,
                validado_por_id=admin.id if dados["verificado"] else None,
                validado_em=datetime.datetime.now(datetime.UTC) if dados["verificado"] else None,
            )
            db.flush()
        for nome, especie, porte, sexo, meses, temperamento in dados["animais"]:
            if db.scalar(select(Animal.id).where(Animal.abrigo_id == usuario.id, Animal.nome == nome)):
                continue
            db.add(Animal(
                abrigo_id=usuario.id, nome=nome, especie=especie, porte=porte, sexo=sexo,
                idade_estimada_meses=meses, temperamento=temperamento, castrado=True, vacinado=True,
            ))
            criados["animais"] += 1

    for nome, email, telefone, cidade in TUTORES:
        usuario, novo = _usuario(db, nome, email, TipoConta.TUTOR)
        if novo:
            usuario.tutor = Tutor(telefone=telefone, cidade=cidade)
        criados["contas"] += novo

    _popular_doacoes(db, criados)
    _popular_historico(db, criados)
    _popular_fotos(db)
    db.commit()
    return criados


def _popular_doacoes(db: Session, criados: dict[str, int]) -> None:
    """Necessidades do Patinhas e apoiadores com histórico. Só cria doações para apoiador criado agora."""
    patinhas = db.scalar(select(Usuario).where(Usuario.email == "patinhas@exemplo.com"))
    necessidades = {}
    for item, quantidade, urgencia in NECESSIDADES:
        n = db.scalar(select(Necessidade).where(Necessidade.abrigo_id == patinhas.id, Necessidade.item == item))
        if n is None:
            n = Necessidade(abrigo_id=patinhas.id, item=item, quantidade=quantidade, urgencia=urgencia)
            db.add(n)
            db.flush()
        necessidades[item] = n
    racao, limpeza = necessidades[NECESSIDADES[0][0]], necessidades[NECESSIDADES[2][0]]

    for nome, email, cnpj, tipo, endereco, lat, lng, por_mes in APOIADORES:
        usuario, novo = _usuario(db, nome, email, TipoConta.APOIADOR)
        criados["contas"] += novo
        if not novo:
            continue
        usuario.apoiador = Apoiador(cnpj=cnpj, tipo_estabelecimento=tipo, endereco=endereco, latitude=lat, longitude=lng)
        db.flush()
        for meses_atras, quantas in por_mes.items():
            for _ in range(quantas):
                momento = _dia_do_mes(meses_atras)
                db.add(Doacao(apoiador_id=usuario.id, abrigo_id=patinhas.id, necessidade_id=racao.id if meses_atras == 0 else None,
                              item=racao.item, quantidade=1, status=StatusDoacao.CONFIRMADA, registrado_em=momento, confirmado_em=momento))
        if email == "amigofiel@exemplo.com":  # o que o abrigo tem para confirmar hoje
            db.add(Doacao(apoiador_id=usuario.id, abrigo_id=patinhas.id, necessidade_id=limpeza.id, item=limpeza.item, quantidade=2))
        db.flush()
        pontuacao.recalcular(db, usuario.id)


def _dias_atras(dias: int) -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=dias)


def _dia_utc(dias: int) -> datetime.datetime:
    """Data "do dia" como o sistema grava (meia-noite UTC)."""
    d = _dias_atras(dias).date()
    return datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.UTC)


# nome, espécie, porte, sexo, meses, dias desde a entrada, situação final, tutor, dias atrás do interesse e da aprovação
HISTORICO = [
    ("Pingo", Especie.CAO, "pequeno", Sexo.MACHO, 18, 50, StatusAnimal.ADOTADO, "maria@exemplo.com", 30, 28),
    ("Nina", Especie.CAO, "medio", Sexo.FEMEA, 30, 25, StatusAnimal.EM_PROCESSO, "joao@exemplo.com", 9, 6),
]


def _popular_historico(db: Session, criados: dict[str, int]) -> None:
    """Adoções passadas do Patinhas, com o histórico de auditoria nas datas certas. Só cria o que for novo."""
    patinhas = db.scalar(select(Usuario).where(Usuario.email == "patinhas@exemplo.com"))
    for nome, dias in (("Thor", 60), ("Mel", 35), ("Bolinha", 20)):
        animal = db.scalar(select(Animal).where(Animal.abrigo_id == patinhas.id, Animal.nome == nome))
        if animal is not None and animal.data_entrada is None:
            animal.data_entrada = _dia_utc(dias)

    def log(usuario_id, acao, tipo, entidade_id, quando, **detalhes):
        auditoria.registrar(db, usuario_id, acao, tipo, entidade_id, **detalhes)
        db.flush()
        ultimo = db.scalar(select(LogAuditoria).order_by(LogAuditoria.id.desc()).limit(1))
        ultimo.criado_em = quando

    for nome, especie, porte, sexo, meses, entrada, situacao, email, d_interesse, d_aprovacao in HISTORICO:
        if db.scalar(select(Animal.id).where(Animal.abrigo_id == patinhas.id, Animal.nome == nome)):
            continue
        tutor = db.scalar(select(Usuario).where(Usuario.email == email))
        animal = Animal(abrigo_id=patinhas.id, nome=nome, especie=especie, porte=porte, sexo=sexo, idade_estimada_meses=meses,
                        castrado=True, vacinado=True, data_entrada=_dia_utc(entrada), status=situacao, criado_em=_dias_atras(entrada))
        db.add(animal)
        db.flush()
        criados["animais"] += 1
        log(patinhas.id, "animal.cadastrado", "animal", animal.id, _dias_atras(entrada), animal=nome)
        interesse = Interesse(animal_id=animal.id, tutor_id=tutor.id, status=StatusInteresse.APROVADO, criado_em=_dias_atras(d_interesse),
                              mensagem="Tenho quintal e já tive cachorro.")
        db.add(interesse)
        db.flush()
        log(tutor.id, "interesse.registrado", "interesse", interesse.id, _dias_atras(d_interesse), animal_id=animal.id, animal=nome)
        log(patinhas.id, "interesse.aprovado", "interesse", interesse.id, _dias_atras(d_aprovacao), animal_id=animal.id, animal=nome)

    thor = db.scalar(select(Animal).where(Animal.abrigo_id == patinhas.id, Animal.nome == "Thor"))
    joao = db.scalar(select(Usuario).where(Usuario.email == "joao@exemplo.com"))
    if thor and not db.scalar(select(Interesse.id).where(Interesse.animal_id == thor.id, Interesse.tutor_id == joao.id)):
        interesse = Interesse(animal_id=thor.id, tutor_id=joao.id, criado_em=_dias_atras(2), mensagem="Moro em casa com quintal grande.")
        db.add(interesse)
        db.flush()
        log(joao.id, "interesse.registrado", "interesse", interesse.id, _dias_atras(2), animal_id=thor.id, animal="Thor")


FOTOS_DEMO = Path(__file__).with_name("fotos_demo")
FOTO_POR_ESPECIE = {Especie.CAO: "cachorro-caramelo.jpg", Especie.GATO: "gato-cinza.jpg"}


def _popular_fotos(db: Session) -> None:
    """Capa para os animais de demonstração que ainda não têm foto (RF-17), com o mesmo tratamento do envio real."""
    com_foto = set(db.scalars(select(Foto.entidade_id).where(Foto.entidade_tipo == EntidadeFoto.ANIMAL.value)))
    for animal in db.scalars(select(Animal)):
        arquivo = FOTO_POR_ESPECIE.get(animal.especie)
        if animal.id in com_foto or arquivo is None:
            continue
        nome = armazenamento.salvar(armazenamento.processar((FOTOS_DEMO / arquivo).read_bytes()))
        db.add(Foto(entidade_tipo=EntidadeFoto.ANIMAL.value, entidade_id=animal.id, url=armazenamento.url_publica(nome), ordem=0))


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria os dados de demonstração (abrigos, animais e contas).")
    parser.add_argument("--forcar", action="store_true", help="roda mesmo em banco que não é local (não use no Supabase)")
    args = parser.parse_args()

    host = make_url(settings.database_url).host
    if host not in HOSTS_LOCAIS and not args.forcar:
        print(
            f"Recusado: o banco configurado fica em '{host}', que não é local. Os dados de demonstração usam senhas "
            "públicas e não devem ir para o banco compartilhado. Use o Postgres do Docker (host 'db').",
            file=sys.stderr,
        )
        return 1

    with SessionLocal() as db:
        criados = popular(db)
    print(f"Pronto: {criados['contas']} conta(s) e {criados['animais']} animal(is) criados "
          f"(o que já existia foi mantido). Senha de todas as contas: {SENHA_DEMO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
