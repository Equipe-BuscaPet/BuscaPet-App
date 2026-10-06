"""Ponto de entrada do backend — Sprint 3: banco conectado, cadastro, login,
perfis de acesso e CRUD de animais. O núcleo de similaridade visual (OpenCL)
entra nas sprints seguintes, conforme o plano no repositório BuscaPet-Docs."""
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.routers import admin, animais, auth, usuarios

app = FastAPI(
    title="BuscaPet API",
    description="Backend da plataforma de adoção, reencontro e doação de animais.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origens,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(animais.router)
app.include_router(admin.router)


@app.get("/health", tags=["infra"])
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/health/db", tags=["infra"])
def healthcheck_banco(db: Session = Depends(get_db)) -> dict:
    """Prova que a API alcança o banco: executa uma consulta de verdade."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        # Detalhes do erro (host, usuário) ficam fora da resposta.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponível.")
    return {"status": "ok", "banco": "conectado", "sgbd": db.get_bind().dialect.name}
