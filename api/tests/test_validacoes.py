"""Sprint 9 — testes de validação: dados inválidos, obrigatórios, formatos e regras de negócio.

Cada caso (CV-xx) diz o que é enviado, o código esperado e um trecho que precisa aparecer na resposta (a mensagem
ou o nome do campo). A mesma tabela está no documento da Sprint 9 como "casos de teste de validação".
"""
import datetime

import pytest

from tests.conftest import SENHA, dados_abrigo, dados_tutor

AMANHA = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()

# (id, perfil, método, rota, corpo JSON, código esperado, trecho esperado na resposta)
CASOS = [
    ("CV-01", None, "POST", "/auth/cadastro", dados_tutor(email="nao-e-email"), 422, "email"),
    ("CV-02", None, "POST", "/auth/cadastro", dados_tutor(email="novo@exemplo.com", senha="123"), 422, "senha"),
    ("CV-03", None, "POST", "/auth/cadastro", dados_tutor(email="novo@exemplo.com", nome=""), 422, "nome"),
    ("CV-04", None, "POST", "/auth/cadastro", {**dados_tutor(email="novo@exemplo.com"), "tipo_conta": "admin"}, 422, "tipo_conta"),
    ("CV-05", None, "POST", "/auth/cadastro", {"tipo_conta": "apoiador", "nome": "Loja", "email": "l2@exemplo.com", "senha": SENHA,
                                              "cnpj": "11.111.111/1111-11", "tipo_estabelecimento": "petshop", "endereco": "Rua 1"}, 422, "CNPJ inválido"),
    ("CV-06", None, "POST", "/auth/cadastro", dados_tutor(), 409, "Já existe uma conta com este e-mail"),
    ("CV-07", None, "POST", "/auth/cadastro", dados_abrigo(email="ab2@exemplo.com", latitude=95), 422, "latitude"),
    ("CV-08", "abrigo", "POST", "/animais", {"especie": "cao", "porte": "medio", "sexo": "macho"}, 422, "nome"),
    ("CV-09", "abrigo", "POST", "/animais", {"nome": "Rex", "especie": "cao", "porte": "medio", "sexo": "macho", "idade_estimada_meses": 700}, 422, "idade_estimada_meses"),
    ("CV-10", "abrigo", "POST", "/animais", {"nome": "Rex", "especie": "dragao", "porte": "medio", "sexo": "macho"}, 422, "especie"),
    ("CV-11", "abrigo", "POST", "/animais", {"nome": "Rex", "especie": "cao", "porte": "gigante", "sexo": "macho"}, 422, "porte"),
    ("CV-12", "tutor", "POST", "/animais/{animal}/interesses", {"mensagem": "x" * 501}, 422, "mensagem"),
    ("CV-13", "abrigo", "POST", "/necessidades", {"item": "Ração", "quantidade": 0}, 422, "quantidade"),
    ("CV-14", "abrigo", "POST", "/necessidades", {"item": "R", "quantidade": 2}, 422, "item"),
    ("CV-15", "abrigo", "POST", "/necessidades", {"item": "Ração", "quantidade": 2, "urgencia": "urgentissima"}, 422, "urgencia"),
    ("CV-16", "apoiador", "POST", "/doacoes", {"quantidade": 2}, 422, "Escolha uma necessidade do mural"),
    ("CV-17", "apoiador", "POST", "/doacoes", {"necessidade_id": 1, "quantidade": 20000}, 422, "quantidade"),
    ("CV-18", "tutor", "POST", "/animais/{animal}/denuncias", {"motivo": "ruim"}, 422, "motivo"),
    ("CV-19", None, "POST", "/auth/redefinir-senha", {"token": "token-qualquer-123", "senha_nova": "123"}, 422, "senha_nova"),
    ("CV-20", None, "POST", "/auth/redefinir-senha", {"token": "token-qualquer-123", "senha_nova": "NovaSenha123!"}, 400, "Este link é inválido"),
    ("CV-21", "tutor", "POST", "/usuarios/eu/senha", {"senha_atual": "errada-errada", "senha_nova": "NovaSenha123!"}, 400, "Senha atual incorreta"),
    ("CV-22", "tutor", "PATCH", "/usuarios/eu", {"nome_abrigo": "Não sou abrigo"}, 422, "não se aplicam"),
    ("CV-23", "admin", "GET", "/admin/logs?de=2026-10-20&ate=2026-10-01", None, 422, "data inicial precisa ser anterior"),
    ("CV-24", None, "GET", "/abrigos?raio_km=10", None, 422, "informe a sua posição"),
    ("CV-25", None, "GET", "/apoiadores/ranking?mes=2026-13", None, 422, "AAAA-MM"),
    ("CV-26", None, "GET", "/animais?idade=bebe", None, 422, "idade"),
    ("CV-27", "abrigo", "POST", "/animais/{animal}/interesses", {}, 403, "não tem permissão"),
]


@pytest.mark.parametrize("cid, perfil, metodo, rota, corpo, codigo, trecho", CASOS, ids=[c[0] for c in CASOS])
def test_validacao(client, contas, cid, perfil, metodo, rota, corpo, codigo, trecho):
    cab = contas["cabecalhos"][perfil] if perfil else {}
    r = client.request(metodo, rota.format(animal=contas["animal"]), json=corpo, headers=cab)
    assert r.status_code == codigo, f"{cid}: esperado {codigo}, obtido {r.status_code} — {r.text}"
    assert trecho in r.text, f"{cid}: a resposta não menciona {trecho!r}: {r.text}"


# ---------- validações que usam formulário com fotos ou login ----------

def test_cv28_perdido_sem_foto_e_com_data_no_futuro(client, contas):
    tutor = contas["cabecalhos"]["tutor"]
    base = {"especie": "cao", "porte": "medio", "cor_predominante": "preto", "latitude": "-8.05", "longitude": "-34.9"}
    sem_foto = client.post("/perdidos", data={**base, "data_desaparecimento": "2026-10-01"}, headers=tutor)
    assert sem_foto.status_code == 422 and "Envie pelo menos uma foto do animal." in sem_foto.text
    no_futuro = client.post("/perdidos", data={**base, "data_desaparecimento": AMANHA}, files=[("fotos", ("a.jpg", b"x", "image/jpeg"))], headers=tutor)
    assert no_futuro.status_code == 422 and "A data não pode estar no futuro." in no_futuro.text


def test_cv29_login_errado_nao_revela_se_o_email_existe(client, contas):
    existe = client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": "errada-123"})
    nao_existe = client.post("/auth/login", data={"username": "ninguem@exemplo.com", "password": "errada-123"})
    assert existe.status_code == nao_existe.status_code == 401
    assert existe.json() == nao_existe.json() == {"detail": "E-mail ou senha incorretos."}
