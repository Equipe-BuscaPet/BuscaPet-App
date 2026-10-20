"""Envio real por SMTP (RF-36), com um servidor falso: sem rede, mas passando pelo mesmo caminho da produção."""
import smtplib

import pytest

from app.core import email
from app.core.config import settings
from tests.conftest import dados_tutor


class SMTPFalso:
    enviados: list = []
    falhar = False

    def __init__(self, host, porta, timeout):
        self.host, self.porta = host, porta

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.tls = True

    def login(self, usuario, senha):
        self.usuario = usuario

    def send_message(self, msg):
        if SMTPFalso.falhar:
            raise smtplib.SMTPException("servidor recusou")
        SMTPFalso.enviados.append((self.host, self.porta, getattr(self, "tls", False), getattr(self, "usuario", None), msg))


@pytest.fixture()
def smtp(monkeypatch):
    SMTPFalso.enviados, SMTPFalso.falhar = [], False
    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.com")
    monkeypatch.setattr(settings, "smtp_porta", 587)
    monkeypatch.setattr(settings, "smtp_usuario", "buscapet")
    monkeypatch.setattr(settings, "smtp_senha", "segredo")
    return SMTPFalso


def test_com_smtp_configurado_envia_com_starttls_e_login(smtp, caixa_de_saida):
    email.enviar("ana@exemplo.com", "Assunto", "Corpo")
    [(host, porta, tls, usuario, msg)] = smtp.enviados
    assert (host, porta, tls, usuario) == ("smtp.exemplo.com", 587, True, "buscapet")
    assert msg["To"] == "ana@exemplo.com" and msg["From"] == settings.email_remetente
    assert not caixa_de_saida.exists()  # com SMTP, nada vai para a caixa de saída


def test_falha_no_smtp_nao_derruba_a_acao(client, smtp):
    smtp.falhar = True
    client.post("/auth/cadastro", json=dados_tutor())
    r = client.post("/auth/esqueci-senha", json={"email": "tutor@exemplo.com"})
    assert r.status_code == 202  # o pedido continua respondendo normalmente; a falha fica só no log
