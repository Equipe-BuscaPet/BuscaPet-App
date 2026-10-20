"""Histórico de operações (logs de auditoria) — RF-39.

Toda ação sensível chama `registrar(...)` antes do commit da própria ação: o log entra na **mesma transação**
e só existe se a ação deu certo. Os detalhes guardam o que ajuda a ler o histórico depois (nome do animal,
situação nova...), nunca senha ou token.

As ações seguem o padrão "entidade.verbo" e têm um rótulo em português em ROTULOS (usado na tela e no CSV).
"""
import json

from sqlalchemy.orm import Session

from app.models.transversais import LogAuditoria

ROTULOS = {
    "conta.criada": "Conta criada",
    "conta.atualizada": "Dados da conta alterados",
    "conta.senha_trocada": "Senha trocada",
    "conta.desativada": "Conta desativada",
    "abrigo.verificado": "Selo Verificado concedido",
    "abrigo.selo_retirado": "Selo Verificado retirado",
    "abrigo.suspenso": "Abrigo suspenso",
    "animal.cadastrado": "Animal cadastrado",
    "animal.atualizado": "Animal alterado",
    "animal.excluido": "Animal excluído",
    "interesse.registrado": "Interesse de adoção registrado",
    "interesse.desistencia": "Tutor desistiu do interesse",
    "interesse.em_conversa": "Abrigo iniciou conversa",
    "interesse.aprovado": "Adoção aprovada",
    "interesse.recusado": "Interesse recusado",
    "perdido.registrado": "Animal perdido registrado",
    "perdido.resolvido": "Caso de perda resolvido",
    "perdido.excluido": "Registro de perda excluído",
    "avistamento.registrado": "Avistamento registrado",
    "avistamento.excluido": "Avistamento excluído",
    "necessidade.publicada": "Necessidade publicada",
    "necessidade.atualizada": "Necessidade alterada",
    "necessidade.excluida": "Necessidade excluída",
    "doacao.registrada": "Doação registrada",
    "doacao.cancelada": "Doação cancelada pelo apoiador",
    "doacao.confirmada": "Doação confirmada pelo abrigo",
    "doacao.recusada": "Doação marcada como não recebida",
}


def registrar(db: Session, usuario_id: int, acao: str, entidade_tipo: str, entidade_id: int, **detalhes) -> None:
    """Acrescenta o log à sessão (sem commit: quem chama faz o commit junto com a ação)."""
    assert acao in ROTULOS, f"ação de auditoria desconhecida: {acao}"
    limpos = {k: v for k, v in detalhes.items() if v is not None}
    db.add(LogAuditoria(
        usuario_id=usuario_id, acao=acao, entidade_tipo=entidade_tipo, entidade_id=entidade_id,
        detalhes_json=json.dumps(limpos, ensure_ascii=False, default=str) if limpos else None,
    ))


def detalhes(log: LogAuditoria) -> dict:
    return json.loads(log.detalhes_json) if log.detalhes_json else {}
