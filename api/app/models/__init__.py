"""Importa todos os models para popular Base.metadata — usado pelo Alembic
autogenerate e pelo create_all em ambiente de teste local."""
from app.models.animal import Animal, Foto, Interesse  # noqa: F401
from app.models.doacao import Doacao, Necessidade, PontuacaoApoiador  # noqa: F401
from app.models.reencontro import (  # noqa: F401
    AnimalPerdido,
    Avistamento,
    BuscaSalva,
    Correspondencia,
    DescritorVisual,
)
from app.models.transversais import Denuncia, LogAuditoria, Notificacao  # noqa: F401
from app.models.usuario import Abrigo, Apoiador, MembroEquipeAbrigo, Tutor, Usuario  # noqa: F401
