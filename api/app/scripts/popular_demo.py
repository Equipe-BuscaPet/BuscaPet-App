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
from app.models.animal import Animal
from app.models.enums import Especie, Sexo, StatusValidacao, TipoConta
from app.models.usuario import Abrigo, Tutor, Usuario

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

    db.commit()
    return criados


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
