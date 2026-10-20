"""Envio de e-mail (RF-05 e RF-36).

Com `SMTP_HOST` configurado, envia de verdade (SMTP com STARTTLS). Sem ele — desenvolvimento, testes e
demonstração —, grava cada e-mail como arquivo `.eml` na "caixa de saída" (`api/caixa-de-saida/`, fora do Git),
que abre em qualquer leitor de e-mail. Assim o fluxo inteiro funciona sem depender de um servidor de e-mail.

E-mail é "melhor esforço": se o envio falhar, a ação que o pediu não falha (o aviso continua no sino).

Avisos do sino por e-mail: um gancho do SQLAlchemy junta as notificações novas de cada transação e envia os
e-mails **depois do commit** — se a ação desfizer (rollback), nenhum e-mail sai.
"""
import datetime
import logging
import smtplib
import uuid
from email.message import EmailMessage

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import settings

log = logging.getLogger("buscapet.email")


def enviar(destinatario: str, assunto: str, texto: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.email_remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg["Date"] = datetime.datetime.now(datetime.UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg.set_content(texto)
    try:
        if settings.smtp_host:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_porta, timeout=10) as smtp:
                smtp.starttls()
                if settings.smtp_usuario:
                    smtp.login(settings.smtp_usuario, settings.smtp_senha)
                smtp.send_message(msg)
        else:
            pasta = settings.pasta_caixa_saida
            pasta.mkdir(parents=True, exist_ok=True)
            momento = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            (pasta / f"{momento}-{uuid.uuid4().hex[:6]}.eml").write_bytes(bytes(msg))
    except Exception:  # noqa: BLE001 — e-mail nunca derruba a ação principal
        log.exception("Falha ao enviar e-mail para %s", destinatario)


def texto_padrao(nome: str, corpo: str, link: str | None = None) -> str:
    partes = [f"Olá, {nome}!", "", corpo]
    if link:
        partes += ["", link]
    partes += ["", "—", "BuscaPet · adoção, reencontro e doações", "Você recebe este e-mail porque tem uma conta no BuscaPet."]
    return "\n".join(partes)


# ---------- avisos do sino também por e-mail (RF-36) ----------

def _ao_preparar_gravacao(sessao: Session, _contexto, _instancias) -> None:
    from app.models.transversais import Notificacao
    from app.models.usuario import Usuario
    from app.routers.notificacoes import _destino

    for obj in list(sessao.new):
        if isinstance(obj, Notificacao):
            usuario = sessao.get(Usuario, obj.usuario_id)
            if usuario is None or not usuario.ativo:
                continue
            destino = _destino(obj, usuario) or "/notificacoes"
            sessao.info.setdefault("emails_pendentes", []).append(
                (usuario.email, usuario.nome, obj.mensagem, f"{settings.url_interface}{destino}")
            )


def _depois_do_commit(sessao: Session) -> None:
    for email, nome, mensagem, link in sessao.info.pop("emails_pendentes", []):
        enviar(email, "BuscaPet: você tem um novo aviso", texto_padrao(nome, mensagem, f"Abra no BuscaPet: {link}"))


def _depois_do_rollback(sessao: Session) -> None:
    sessao.info.pop("emails_pendentes", None)


event.listen(Session, "before_flush", _ao_preparar_gravacao)
event.listen(Session, "after_commit", _depois_do_commit)
event.listen(Session, "after_rollback", _depois_do_rollback)
