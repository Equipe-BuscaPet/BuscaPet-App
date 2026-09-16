"""Ponto de entrada do backend. Sprint 2: healthcheck + esqueleto de rotas —
regra de negócio completa (auth, CRUDs) é trabalho da Sprint 2 em andamento e
da Sprint 3 em diante, conforme docs/plano-sprints-equipe-3.md."""
from fastapi import FastAPI

app = FastAPI(
    title="BuscaPet API",
    description="Backend da plataforma de adoção, reencontro e doação de animais.",
    version="0.1.0",
)


@app.get("/health", tags=["infra"])
def healthcheck() -> dict:
    return {"status": "ok"}
