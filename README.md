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

**Interface web** (em outro terminal, com a API rodando; precisa do Node 20+):

```powershell
cd frontend
npm install
npm run dev                            # abre em http://localhost:5173
```

### B) Docker Compose

```bash
cp .env.example .env                                  # Windows: Copy-Item .env.example .env
docker compose up -d --build db redis api frontend
docker compose exec api alembic upgrade head          # cria o schema no Postgres do Docker
docker compose exec api python -m app.scripts.popular_demo   # abrigos, animais e contas de exemplo (iguais para todo o time)
```

O último comando carrega o mesmo cenário de demonstração em qualquer máquina (7 contas, 4 abrigos, 8 animais; senha de
todas: `Senha1234!`; as contas estão listadas no topo de `api/app/scripts/popular_demo.py`). É seguro repetir e **só roda
em banco local**: ele se recusa a rodar contra o Supabase.

API em `http://localhost:8000/docs` e interface em `http://localhost:5173`. O núcleo OpenCL
(`http://localhost:8001`) ainda é placeholder, por isso não sobe junto. O Postgres do Docker
começa vazio e é local de cada pessoa (o volume `db_data` guarda os dados entre reinícios;
`docker compose down` mantém, `docker compose down -v` apaga). Para criar o admin nele:
`docker compose exec api python -m app.scripts.criar_admin --nome "Seu Nome" --email voce@exemplo.com`.
Caminho validado em 2026-10-08 (cadastro, login e `/health/db` funcionando).

> Depois de puxar mudanças que alteram o `frontend/package.json` (dependência nova), renove o volume do
> `node_modules` do container: `docker compose up -d --build -V frontend`. Sem isso o frontend não encontra o pacote.

### Roteiro rápido para ver tudo funcionando (pela interface)

1. Em **Cadastrar**, crie uma conta de **abrigo**. Ela entra em *Meus animais* e já pode
   cadastrar, editar e excluir animais: o abrigo nasce **não verificado**, mas opera na hora.
2. Crie o admin (comando acima), entre com ele: abre em *Verificação de abrigos*. Clique em
   **Verificar** para dar o selo (ou **Suspender**, que tira o abrigo do catálogo e bloqueia a publicação).
3. Sem login, abra o catálogo (`/`): os animais aparecem com o selo *Verificado* ou *Não verificado*.
5. Cadastre um **tutor** e tente abrir `/painel`: a tela barra o acesso (e a API também
   devolveria 403).

Quem preferir testar sem a interface, tudo isso também está no Swagger (`/docs`): use o botão
**Authorize** com o e-mail e a senha de cada conta.

## Testes e integração contínua

| Camada | Ferramenta | O que garante | Comando |
|---|---|---|---|
| Estilo do código Python | `ruff` | padrão de código e erros comuns | `cd api && ruff check .` |
| API (unidade e integração) | `pytest` | regras de negócio e permissões de cada rota (SQLite em memória) | `cd api && pytest` |
| Interface | `vite build` | a interface compila | `cd frontend && npm run build` |
| **Ponta a ponta (E2E)** | **Playwright** | um navegador de verdade usa as telas contra a API e um **Postgres real**: cadastro, login, perfis, adoção, perdidos e achados, celular | `cd frontend && npm run e2e` |
| Núcleo OpenCL | `make teste` | saída paralela igual à sequencial | `docker compose build nucleo-opencl` |

Os testes E2E criam as próprias contas, com e-mail único, e por isso rodam em qualquer banco sem depender dos dados
de demonstração. O `npm run e2e` sobe sozinho a API e a interface, se ainda não estiverem no ar, e precisa do banco
com as migrations aplicadas. `npm run e2e:ver` abre a janela do Playwright para acompanhar passo a passo, e
`npm run e2e:relatorio` mostra o relatório com captura, vídeo e *trace* das falhas.

A **CI** (`.github/workflows/ci.yml`) roda tudo isso a cada Pull Request. O job `e2e` só começa depois que lint,
testes da API e build passam, sobe um Postgres 16 com a sessão no fuso de Recife (onde o defeito das datas
aparecia) e publica o relatório do Playwright como artefato.

## Documentação

- [`docs/schema.sql`](docs/schema.sql) — modelo relacional (neste repositório)
- [Repositório `BuscaPet-Docs`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs) — escopo, RFs, plano de sprints, decisões técnicas e entregas de cada Sprint
  - [`planejamento/`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/planejamento) — escopo, plano de sprints, fluxos de tela, notas técnicas
  - [`sprints/sprint-2/`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/sprints/sprint-2) — arquitetura, diagrama de classes, MER, modelo relacional, protótipos

## Sprints

Cronograma completo em [`planejamento/plano-sprints-equipe-3.md`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/blob/main/planejamento/plano-sprints-equipe-3.md) (repositório `BuscaPet-Docs`). Entrega final: **05/12/2026**.
