"""Cria os dados de demonstração do BuscaPet: os mesmos abrigos, animais e contas para todo o time.

Uso, a partir da pasta api/ (ou dentro do container: `docker compose exec api python -m app.scripts.popular_demo`):
    python -m app.scripts.popular_demo

É seguro rodar mais de uma vez: o que já existe (pelo e-mail da conta ou pelo nome do animal no abrigo)
é ignorado. Por segurança, o script **só roda em banco local** (host `db`, `localhost` ou `127.0.0.1`):
as senhas abaixo são públicas e não podem existir no banco compartilhado (Supabase). Para forçar, `--forcar` junto de
`--senha` (uma senha só sua para todas as contas, p. ex. para o site publicado) ou, de propósito, só `--forcar`.
Com `ARMAZENAMENTO_FOTOS=banco` as fotos vão para o banco (é o que a hospedagem gratuita usa).

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

O Patinhas tem chave PIX e meta de gastos do mês (R$ 3.000); Maria e João já doaram por PIX (confirmado) e
aparecem no ranking de pessoa física.

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
from app.routers.relatorios import FUSO
from pathlib import Path

from app.core import auditoria, pontuacao
from app.core import fotos as armazenamento
from app.models.animal import Animal, Foto, Interesse
from app.models.doacao import Doacao, Necessidade
from app.models.reencontro import AnimalPerdido, Avistamento, BuscaSalva
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
# Meta de gastos do mês do Patinhas e os PIX dos tutores (meses atrás → valor em centavos), já confirmados.
PIX_PATINHAS = "doacoes@patinhasfelizes.org.br"
META_PATINHAS = (300000, "Ração R$ 1.500 · veterinário e vacinas R$ 900 · água, luz e aluguel R$ 600")
PIX_TUTORES = {"maria@exemplo.com": {1: 5000, 0: 8000}, "joao@exemplo.com": {0: 3000}}

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
    _popular_reencontro(db)
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

    abrigo = patinhas.abrigo
    if abrigo.chave_doacao_financeira is None:
        abrigo.chave_doacao_financeira = PIX_PATINHAS
    if abrigo.meta_mensal_centavos is None:
        abrigo.meta_mensal_centavos, abrigo.meta_mensal_descricao = META_PATINHAS
    for email, por_mes in PIX_TUTORES.items():  # pessoas físicas no ranking e a meta do mês já andando
        tutor = db.scalar(select(Usuario).where(Usuario.email == email))
        if db.scalar(select(Doacao.id).where(Doacao.apoiador_id == tutor.id).limit(1)):
            continue
        for meses_atras, centavos in por_mes.items():
            momento = _dia_do_mes(meses_atras)
            db.add(Doacao(apoiador_id=tutor.id, abrigo_id=patinhas.id, item="Doação em dinheiro (PIX)", quantidade=1, valor_centavos=centavos,
                          status=StatusDoacao.CONFIRMADA, registrado_em=momento, confirmado_em=momento))
        db.flush()
        pontuacao.recalcular(db, tutor.id)


def _dias_atras(dias: int) -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=dias)


def _dia_utc(dias: int) -> datetime.datetime:
    """Data "do dia" como o sistema grava (meia-noite UTC). O dia é o do calendário de Recife, como a pessoa
    escolheria no formulário: entre 21h e 0h em Recife, a data UTC já é a de amanhã."""
    d = _dias_atras(dias).astimezone(FUSO).date()
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

# Fotos reais de cães (DogFaceNet, CC BY 4.0; créditos em fotos_demo/caes/CREDITOS.md): uma pasta por cão, 3 fotos.
CAES = FOTOS_DEMO / "caes"
CAPA_DOS_ANIMAIS = {"Thor": "preto-felpudo", "Mel": "bege-e-branco", "Bolinha": "preto-e-fogo", "Rex": "pastor-alemao"}


def _salvar_foto(arquivo: Path) -> str:
    """Grava a foto com o mesmo tratamento do envio real e devolve a URL pública."""
    return armazenamento.url_publica(armazenamento.salvar(armazenamento.processar(arquivo.read_bytes())))


def _popular_fotos(db: Session) -> None:
    """Capa para os animais de demonstração que ainda não têm foto (RF-17): o cão certo, ou a foto genérica da espécie."""
    com_foto = set(db.scalars(select(Foto.entidade_id).where(Foto.entidade_tipo == EntidadeFoto.ANIMAL.value)))
    for animal in db.scalars(select(Animal)):
        if animal.id in com_foto:
            continue
        if animal.nome in CAPA_DOS_ANIMAIS:
            arquivo = CAES / CAPA_DOS_ANIMAIS[animal.nome] / "1.jpg"
        elif animal.especie in FOTO_POR_ESPECIE:
            arquivo = FOTOS_DEMO / FOTO_POR_ESPECIE[animal.especie]
        else:
            continue
        db.add(Foto(entidade_tipo=EntidadeFoto.ANIMAL.value, entidade_id=animal.id, url=_salvar_foto(arquivo), ordem=0))


# Reencontro para a busca por foto. Cada cão aparece em dois lugares com fotos diferentes:
#   - a Branquinha, perdida pela Maria (fotos 1 e 2), foi avistada pelo João (foto 3);
#   - o pastor do João está perdido (fotos 2 e 3) e a capa do Rex, no Protetores do Cordeiro, é outra foto dele (1).
# Os demais avistamentos (cães diferentes) servem de distratores.
PERDIDOS = [
    # tutor, pasta, fotos, porte, cor, pelagem, sexo, sinais, lat, lng, dias desde o sumiço
    ("maria@exemplo.com", "branco-e-caramelo", (1, 2), "medio", "branco e caramelo", "curta", Sexo.FEMEA,
     "Orelhas caramelo e uma mancha na testa", -8.1180, -34.8990, 3),
    ("joao@exemplo.com", "pastor-alemao", (2, 3), "grande", "preto e marrom", "curta", Sexo.MACHO,
     "Pastor alemão, orelhas em pé", -8.0460, -34.9090, 5),
]
AVISTAMENTOS = [
    # quem viu, pasta, foto, porte, cor, pelagem, sexo, sinais, lat, lng, dias
    ("joao@exemplo.com", "branco-e-caramelo", 3, "medio", "branco e caramelo", "curta", Sexo.FEMEA,
     "Vi andando sozinha, sem coleira", -8.1203, -34.9011, 1),
    ("maria@exemplo.com", "caramelo", 1, "medio", "caramelo", "curta", Sexo.MACHO, "Bem dócil, aceitou carinho", -8.0975, -34.8920, 2),
    ("maria@exemplo.com", "marrom-avermelhado", 1, "grande", "marrom avermelhado", "curta", Sexo.MACHO,
     "Orelhas compridas, parecia cansado", -8.0580, -34.8800, 4),
    ("joao@exemplo.com", "preto-mancha-branca", 1, "medio", "preto", "curta", Sexo.FEMEA,
     "Mancha branca na testa", -8.0700, -34.9000, 6),
]


def _popular_reencontro(db: Session) -> None:
    """Perdidos e avistamentos de cães com fotos reais. Só cria se ainda não houver nenhum perdido no banco."""
    if db.scalar(select(AnimalPerdido.id).limit(1)):
        return
    usuarios = {u.email: u for u in db.scalars(select(Usuario).where(Usuario.email.in_(["maria@exemplo.com", "joao@exemplo.com"])))}
    if len(usuarios) < 2:
        return

    for email, pasta, fotos, porte, cor, pelagem, sexo, sinais, lat, lng, dias in PERDIDOS:
        perdido = AnimalPerdido(
            tutor_id=usuarios[email].id, especie=Especie.CAO, porte=porte, cor_predominante=cor, pelagem=pelagem,
            sexo=sexo, sinais_particulares=sinais, latitude=lat, longitude=lng, raio_busca_km=5.0,
            data_desaparecimento=_dia_utc(dias),
        )
        db.add(perdido)
        db.flush()
        db.add(BuscaSalva(tutor_id=perdido.tutor_id, animal_perdido_id=perdido.id))
        for ordem, numero in enumerate(fotos):
            db.add(Foto(entidade_tipo=EntidadeFoto.ANIMAL_PERDIDO.value, entidade_id=perdido.id,
                        url=_salvar_foto(CAES / pasta / f"{numero}.jpg"), ordem=ordem))

    for email, pasta, numero, porte, cor, pelagem, sexo, sinais, lat, lng, dias in AVISTAMENTOS:
        avistamento = Avistamento(
            usuario_id=usuarios[email].id, especie=Especie.CAO, porte=porte, cor_predominante=cor, pelagem=pelagem,
            sexo=sexo, sinais_particulares=sinais, latitude=lat, longitude=lng, data_avistamento=_dia_utc(dias),
        )
        db.add(avistamento)
        db.flush()
        db.add(Foto(entidade_tipo=EntidadeFoto.AVISTAMENTO.value, entidade_id=avistamento.id,
                    url=_salvar_foto(CAES / pasta / f"{numero}.jpg"), ordem=0))


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria os dados de demonstração (abrigos, animais e contas).")
    parser.add_argument("--forcar", action="store_true", help="roda mesmo em banco que não é local (não use no Supabase)")
    parser.add_argument("--senha", help="senha de todas as contas criadas (padrão: a senha pública da demonstração)")
    args = parser.parse_args()
    if args.senha:
        global SENHA_DEMO
        if len(args.senha) < 10:
            print("A senha precisa ter ao menos 10 caracteres.", file=sys.stderr)
            return 1
        SENHA_DEMO = args.senha

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
          f"(o que já existia foi mantido). "
          + ("Senha de todas as contas: a que você informou em --senha." if args.senha else f"Senha de todas as contas: {SENHA_DEMO}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
