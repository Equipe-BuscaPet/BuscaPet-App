# BuscaPet

Plataforma web de adoção, reencontro de animais perdidos por similaridade
visual e canalização de doações — projeto acadêmico da Universidade Maurício
de Nassau (UNINASSAU), curso de Ciência da Computação, integrando as
disciplinas de Fábrica de Software, Tópicos Avançados e Atividades Práticas
Interdisciplinares de Extensão IV.

## Equipe
- Nivaldo José de Arruda Filho — 01486768 — banco de dados, documentação e núcleo OpenCL
- Kaian Guthierry da Silva — 01617843
- Marlon Porto Torres — 01611478

## Estrutura do repositório

```
buscapet/
  api/              backend web — FastAPI + SQLAlchemy/Alembic (Python)
  nucleo-opencl/    serviço de comparação por similaridade visual — C + OpenCL (PoCL)
  frontend/         interface web
  docs/             documento de escopo, plano de sprints, fluxos de tela, notas técnicas, entregas de cada Sprint
  docker-compose.yml
```

## Rodando localmente

```bash
cp .env.example .env
docker compose up -d db redis
cd api && alembic upgrade head   # cria o schema no Postgres local
docker compose up
```

API sobe em `http://localhost:8000/docs` (Swagger gerado automaticamente pelo
FastAPI — é o contrato de API usado pelo frontend). Núcleo OpenCL em
`http://localhost:8001` (ainda placeholder — implementação na Sprint 3).

## Documentação

- [`docs/`](docs/) — escopo, RFs, plano de sprints e decisões técnicas completas
- [`docs/schema.sql`](docs/schema.sql) — modelo relacional
- [`docs/sprint2/`](docs/sprint2/) — entregas da Sprint 2 (arquitetura, diagrama de classes, MER, modelo relacional, protótipos)

## Sprints

Cronograma completo em `docs/plano-sprints-equipe-3.md`. Entrega final: **05/12/2026**.
