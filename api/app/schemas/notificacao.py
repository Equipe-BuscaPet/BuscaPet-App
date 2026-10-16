"""Notificações da própria conta — RF-36 (avisos do sistema) e base dos alertas do reencontro (RF-24/26)."""
import datetime

from pydantic import BaseModel


class NotificacaoOut(BaseModel):
    id: int
    mensagem: str
    referencia_tipo: str | None
    referencia_id: int | None
    lida: bool
    criado_em: datetime.datetime
    # Tela que a notificação abre ao ser clicada (calculada pela API conforme o tipo de conta).
    destino: str | None


class ContagemNotificacoes(BaseModel):
    nao_lidas: int
