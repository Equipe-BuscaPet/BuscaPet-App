"""RF-05 (recuperação de senha) e RF-36 (avisos também por e-mail)."""
import datetime
import email
import re

import jwt

from app.core.config import settings
from tests.conftest import SENHA, cabecalho, dados_animal, dados_tutor

PEDIDO = "Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha. Ele vale por 30 minutos."


def emails(pasta) -> list[email.message.EmailMessage]:
    if not pasta.exists():
        return []
    return [email.message_from_bytes(p.read_bytes(), policy=email.policy.default) for p in sorted(pasta.iterdir())]


def token_do_link(msg) -> str:
    return re.search(r"redefinir-senha\?token=(\S+)", msg.get_content()).group(1)


def test_pedido_responde_igual_exista_ou_nao_a_conta(client, caixa_de_saida):
    client.post("/auth/cadastro", json=dados_tutor())
    existe = client.post("/auth/esqueci-senha", json={"email": "Tutor@Exemplo.com"})
    nao_existe = client.post("/auth/esqueci-senha", json={"email": "ninguem@exemplo.com"})
    assert existe.status_code == nao_existe.status_code == 202
    assert existe.json() == nao_existe.json() == {"mensagem": PEDIDO}
    [msg] = emails(caixa_de_saida)  # só a conta que existe recebe
    assert msg["To"] == "tutor@exemplo.com" and msg["Subject"] == "BuscaPet: crie uma nova senha"
    assert f"{settings.url_interface}/redefinir-senha?token=" in msg.get_content()


def test_link_cria_nova_senha_e_so_vale_uma_vez(client, caixa_de_saida):
    client.post("/auth/cadastro", json=dados_tutor())
    client.post("/auth/esqueci-senha", json={"email": "tutor@exemplo.com"})
    token = token_do_link(emails(caixa_de_saida)[0])

    assert client.post("/auth/redefinir-senha", json={"token": token, "senha_nova": "NovaSenha123!"}).status_code == 204
    assert client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": SENHA}).status_code == 401
    assert cabecalho(client, "tutor@exemplo.com", "NovaSenha123!")  # a nova senha funciona
    r = client.post("/auth/redefinir-senha", json={"token": token, "senha_nova": "OutraSenha123!"})
    assert r.status_code == 400 and "já foi usado" in r.json()["detail"]  # o mesmo link não serve de novo


def test_link_expirado_ou_forjado_e_recusado(client):
    usuario_id = client.post("/auth/cadastro", json=dados_tutor()).json()["id"]
    vencido = jwt.encode({"sub": str(usuario_id), "fim": "redefinir-senha", "h": "x",
                          "exp": datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1)},
                         settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert client.post("/auth/redefinir-senha", json={"token": vencido, "senha_nova": "NovaSenha123!"}).status_code == 400
    forjado = jwt.encode({"sub": str(usuario_id), "fim": "redefinir-senha", "h": "x"}, "outra-chave", algorithm="HS256")
    assert client.post("/auth/redefinir-senha", json={"token": forjado, "senha_nova": "NovaSenha123!"}).status_code == 400
    login = client.post("/auth/login", data={"username": "tutor@exemplo.com", "password": SENHA}).json()["access_token"]
    r = client.post("/auth/redefinir-senha", json={"token": login, "senha_nova": "NovaSenha123!"})
    assert r.status_code == 400  # o token de login não serve para redefinir


def test_link_de_redefinicao_nao_serve_como_login(client, caixa_de_saida):
    client.post("/auth/cadastro", json=dados_tutor())
    client.post("/auth/esqueci-senha", json={"email": "tutor@exemplo.com"})
    token = token_do_link(emails(caixa_de_saida)[0])
    assert client.get("/auth/eu", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_nova_senha_segue_as_regras_de_senha(client, caixa_de_saida):
    client.post("/auth/cadastro", json=dados_tutor())
    client.post("/auth/esqueci-senha", json={"email": "tutor@exemplo.com"})
    token = token_do_link(emails(caixa_de_saida)[0])
    assert client.post("/auth/redefinir-senha", json={"token": token, "senha_nova": "curta"}).status_code == 422


def test_avisos_do_sino_tambem_chegam_por_email(client, abrigo_aprovado, caixa_de_saida):
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    client.post("/auth/cadastro", json=dados_tutor())
    antes = len(emails(caixa_de_saida))
    client.post(f"/animais/{animal['id']}/interesses", json={}, headers=cabecalho(client, "tutor@exemplo.com"))
    [msg] = emails(caixa_de_saida)[antes:]
    assert msg["To"] == "abrigo@exemplo.com" and msg["Subject"] == "BuscaPet: você tem um novo aviso"
    corpo = msg.get_content()
    assert "Maria Tutora tem interesse em adotar Thor." in corpo and f"{settings.url_interface}/interessados" in corpo


def test_acao_que_falha_nao_envia_email(client, abrigo_aprovado, caixa_de_saida):
    animal = client.post("/animais", json=dados_animal(), headers=abrigo_aprovado["headers"]).json()
    client.post("/auth/cadastro", json=dados_tutor())
    tutor = cabecalho(client, "tutor@exemplo.com")
    client.post(f"/animais/{animal['id']}/interesses", json={}, headers=tutor)
    antes = len(emails(caixa_de_saida))
    assert client.post(f"/animais/{animal['id']}/interesses", json={}, headers=tutor).status_code == 409
    assert len(emails(caixa_de_saida)) == antes
