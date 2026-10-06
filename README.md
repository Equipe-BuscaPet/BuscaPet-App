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
[`BuscaPet-Docs`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs), separado deste.

## Rodando localmente

Há dois caminhos. O **A** é o que a demonstração usa; o **B** sobe tudo em containers.

### A) Python direto (venv) — Windows, macOS ou Linux

Precisa de Python 3.12 e de um banco Postgres: o do Supabase do projeto (recebe a
`DATABASE_URL` do time) ou um Postgres local qualquer.

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Crie api/.env (nunca é versionado) com duas linhas:
#   DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@HOST:5432/postgres
#   JWT_SECRET=<texto aleatório longo>   # ex.: python -c "import secrets; print(secrets.token_urlsafe(48))"

$env:DATABASE_URL = "<mesma URL>"      # só o Alembic lê a variável de ambiente
alembic upgrade head                   # cria as tabelas (se o banco ainda estiver vazio)
uvicorn app.main:app --reload --port 8000
```

- Swagger (documentação interativa e onde se testa tudo): <http://localhost:8000/docs>
- Prova de conexão com o banco: <http://localhost:8000/health/db> (deve responder `"banco": "conectado"`)
- Criar o administrador (único jeito, não existe cadastro público de admin):
  `python -m app.scripts.criar_admin --nome "Seu Nome" --email voce@exemplo.com`
- Testes automatizados (rodam em SQLite em memória, não tocam no banco real): `pytest`

### B) Docker Compose

```bash
cp .env.example .env
docker compose up -d db redis
cd api && alembic upgrade head   # cria o schema no Postgres local
docker compose up
```

API em `http://localhost:8000/docs`. O núcleo OpenCL (`http://localhost:8001`) ainda é
placeholder e o `frontend/` ainda não foi implementado, então `docker compose up`
sobe esses dois serviços sem função por enquanto; para a Sprint 3, suba só
`docker compose up api db redis`.

### Roteiro rápido para testar no Swagger

1. `POST /auth/cadastro` com um abrigo (`tipo_conta: "abrigo"`) — nasce **pendente**.
2. Crie o admin (comando acima), faça login com ele em **Authorize** e aprove o abrigo em
   `PATCH /admin/abrigos/{id}/validacao` com `{"status": "aprovado"}`.
3. Faça login com o abrigo e use `POST /animais`, `GET /animais`, `PATCH /animais/{id}` e
   `DELETE /animais/{id}`.
4. Cadastre um `tutor` e veja `POST /animais` responder **403** (perfil sem permissão).

## Documentação

- [`docs/schema.sql`](docs/schema.sql) — modelo relacional (neste repositório)
- [Repositório `BuscaPet-Docs`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs) — escopo, RFs, plano de sprints, decisões técnicas e entregas de cada Sprint
  - [`planejamento/`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/planejamento) — escopo, plano de sprints, fluxos de tela, notas técnicas
  - [`sprints/sprint-2/`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/sprints/sprint-2) — arquitetura, diagrama de classes, MER, modelo relacional, protótipos

## Sprints

Cronograma completo em [`planejamento/plano-sprints-equipe-3.md`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/blob/main/planejamento/plano-sprints-equipe-3.md) (repositório `BuscaPet-Docs`). Entrega final: **05/12/2026**.
