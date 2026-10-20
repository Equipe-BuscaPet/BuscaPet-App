"""Fixtures dos testes. Cada teste roda num SQLite em memória, criado do zero a
partir dos models: os testes nunca tocam no banco real (Supabase)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registra todas as tabelas em Base.metadata
from app.core.seguranca import hash_senha
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import TipoConta
from app.models.usuario import Usuario

SENHA = "senha-segura-123"
CNPJ_VALIDO = "11.222.333/0001-81"


@pytest.fixture(autouse=True)
def caixa_de_saida(tmp_path, monkeypatch):
    """Os e-mails dos testes (sem SMTP) vão para uma pasta temporária, nunca para api/caixa-de-saida."""
    from app.core.config import settings

    pasta = tmp_path / "caixa-de-saida"
    monkeypatch.setattr(settings, "pasta_caixa_saida", pasta)
    monkeypatch.setattr(settings, "smtp_host", None)
    return pasta


@pytest.fixture(autouse=True)
def pasta_de_fotos(tmp_path, monkeypatch):
    """As fotos gravadas pelos testes vão para uma pasta temporária, nunca para api/uploads."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "pasta_fotos", tmp_path / "fotos-teste")


@pytest.fixture(autouse=True)
def nucleo_desligado(monkeypatch):
    """Por padrão os testes rodam SEM o núcleo OpenCL (nem tentam a rede): vale o comportamento de reserva.
    Quem precisa da comparação por foto usa a fixture `nucleo_falso` (ou `test_nucleo_real.py`, opcional)."""
    from app.core import nucleo

    def fora_do_ar(*_args, **_kwargs):
        raise nucleo.NucleoIndisponivel("núcleo desligado nos testes")

    monkeypatch.setattr(nucleo, "_pedir", fora_do_ar)


class NucleoFalso:
    """Imita o serviço em C com a MESMA fórmula de nota (src/descritor.c, nota_semelhanca), mas com um
    descritor simples: a cor média da foto marca um tom no histograma. Suficiente para testar a integração
    (filtros, ordenação, alertas); o descritor de verdade é testado no próprio núcleo (`make teste`)."""

    def __init__(self):
        self.extracoes = 0
        self.comparacoes = 0

    def descritor(self, rgb: bytes) -> list[float]:
        n = len(rgb) // 3
        r, g, b = (sum(rgb[c::3]) // n for c in range(3))
        d = [0.0] * 224
        d[(r // 64) * 16 + (g // 64) * 4 + b // 64] = 1.0
        for k in range(208, 218):
            d[k] = 0.1
        d[218:223] = [0.5] * 5
        return d

    @staticmethod
    def nota(a: list[float], b: list[float]) -> float:
        def qui(ini, fim):
            return 0.5 * sum((a[k] - b[k]) ** 2 / (a[k] + b[k]) for k in range(ini, fim) if a[k] + b[k] > 0)
        prop = sum(abs(a[k] - b[k]) for k in range(218, 223)) / 5
        return 1 - (0.6 * qui(0, 208) + 0.3 * qui(208, 218) + 0.1 * prop)

    @staticmethod
    def grau(nota: float) -> str:
        return "alta" if nota >= 0.75 else "media" if nota >= 0.55 else "baixa"

    def pedir(self, metodo, caminho, timeout, **kwargs):
        import base64

        corpo = kwargs.get("json") or {}
        if caminho == "/extrair-descritor":
            self.extracoes += 1
            return {"descritor": self.descritor(base64.b64decode(corpo["pixels"])), "versao": "v1", "tempos": {}}
        if caminho == "/comparar":
            self.comparacoes += 1
            resultados = []
            for q in corpo["consultas"]:
                lista = [{"id": c["id"], "nota": self.nota(q, c["descritor"])} for c in corpo["candidatos"]]
                lista.sort(key=lambda x: (-x["nota"], x["id"]))
                resultados.append([{**x, "grau": self.grau(x["nota"])} for x in lista])
            return {"resultados": resultados, "tempos": {"total_ms": 1.0}, "modo": corpo.get("modo", "opencl")}
        if caminho == "/saude":
            return {"status": "ok", "opencl": {"dispositivo": "CPU falsa"}}
        if caminho == "/benchmark":
            p = kwargs["params"]
            return {"etapa": p["etapa"], "n": p["n"], "speedup": 3.2, "resultados_iguais": True,
                    "sequencial": {"total_ms": 32.0}, "opencl": {"total_ms": 10.0}}
        raise AssertionError(f"rota inesperada no núcleo falso: {metodo} {caminho}")


@pytest.fixture()
def nucleo_falso(monkeypatch) -> NucleoFalso:
    from app.core import nucleo

    falso = NucleoFalso()
    monkeypatch.setattr(nucleo, "_pedir", falso.pedir)
    return falso


@pytest.fixture()
def sessao_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(sessao_factory):
    def _get_db():
        db = sessao_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def cabecalho(client: TestClient, email: str, senha: str = SENHA) -> dict:
    resp = client.post("/auth/login", data={"username": email, "password": senha})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def dados_tutor(email="tutor@exemplo.com", **extra) -> dict:
    return {
        "tipo_conta": "tutor", "nome": "Maria Tutora", "email": email, "senha": SENHA,
        "telefone": "81999990000", "cidade": "Recife", **extra,
    }


def dados_abrigo(email="abrigo@exemplo.com", **extra) -> dict:
    return {
        "tipo_conta": "abrigo", "nome": "Joana Protetora", "email": email, "senha": SENHA,
        "nome_abrigo": "Abrigo Patinhas", "endereco": "Rua das Flores, 10, Recife",
        "latitude": -8.05, "longitude": -34.9, **extra,
    }


def dados_animal(**extra) -> dict:
    return {"nome": "Thor", "especie": "cao", "porte": "medio", "sexo": "macho", **extra}


@pytest.fixture()
def admin(client, sessao_factory) -> dict:
    """Cria um administrador direto no banco (não existe cadastro público de admin)."""
    with sessao_factory() as db:
        db.add(Usuario(nome="Admin", email="admin@exemplo.com", senha_hash=hash_senha(SENHA), tipo_conta=TipoConta.ADMIN))
        db.commit()
    return cabecalho(client, "admin@exemplo.com")


@pytest.fixture()
def abrigo_aprovado(client, admin) -> dict:
    """Abrigo cadastrado e já aprovado pelo admin; devolve cabeçalho e id."""
    resp = client.post("/auth/cadastro", json=dados_abrigo())
    assert resp.status_code == 201, resp.text
    usuario_id = resp.json()["id"]
    ok = client.patch(f"/admin/abrigos/{usuario_id}/validacao", json={"status": "aprovado"}, headers=admin)
    assert ok.status_code == 200, ok.text
    return {"headers": cabecalho(client, "abrigo@exemplo.com"), "id": usuario_id}


# Um de cada perfil, mais um animal do abrigo: usado pela matriz de permissões e pela suíte de validação.
@pytest.fixture()
def contas(client, admin, abrigo_aprovado) -> dict:
    client.post("/auth/cadastro", json=dados_tutor())
    client.post("/auth/cadastro", json={
        "tipo_conta": "apoiador", "nome": "Loja", "email": "loja@exemplo.com", "senha": SENHA,
        "cnpj": CNPJ_VALIDO, "tipo_estabelecimento": "petshop", "endereco": "Av. Brasil, 1",
    })
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    return {
        "cabecalhos": {
            "visitante": {}, "tutor": cabecalho(client, "tutor@exemplo.com"), "abrigo": abrigo_aprovado["headers"],
            "apoiador": cabecalho(client, "loja@exemplo.com"), "admin": admin,
        },
        "animal": animal["id"],
    }
