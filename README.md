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
  docs/schema.sql   modelo relacional (DDL), espelha api/app/models/
  docker-compose.yml
```

Documentação completa (escopo, plano de sprints, fluxos de tela, notas
técnicas, entregas de cada Sprint) fica no repositório
[`Docs`](https://github.com/Equipe-BuscaPet/Docs), separado deste.

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

- [`docs/schema.sql`](docs/schema.sql) — modelo relacional (neste repositório)
- [Repositório `Docs`](https://github.com/Equipe-BuscaPet/Docs) — escopo, RFs, plano de sprints, decisões técnicas e entregas de cada Sprint
  - [`planejamento/`](https://github.com/Equipe-BuscaPet/Docs/tree/main/planejamento) — escopo, plano de sprints, fluxos de tela, notas técnicas
  - [`sprints/sprint-2/`](https://github.com/Equipe-BuscaPet/Docs/tree/main/sprints/sprint-2) — arquitetura, diagrama de classes, MER, modelo relacional, protótipos

## Sprints

Cronograma completo em [`planejamento/plano-sprints-equipe-3.md`](https://github.com/Equipe-BuscaPet/Docs/blob/main/planejamento/plano-sprints-equipe-3.md) (repositório `Docs`). Entrega final: **05/12/2026**.
