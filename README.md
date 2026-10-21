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
  frontend/         interface web — React + Vite, instalável como app (PWA)
  frontend/e2e/     testes de ponta a ponta (Playwright)
  docs/schema.sql   modelo relacional (DDL), espelha api/app/models/
  .github/workflows CI: api, frontend, e2e, nucleo-opencl
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
# 1) Crie o arquivo .env na raiz (nunca é versionado) com estas linhas:
#      DATABASE_URL=postgresql+psycopg://buscapet:buscapet@db:5432/buscapet
#      JWT_SECRET=troque-por-um-valor-aleatorio-longo
#      REDIS_URL=redis://redis:6379/0
#      NUCLEO_OPENCL_URL=http://nucleo-opencl:8001
# 2) Suba os serviços:
docker compose up -d --build db redis api frontend
docker compose exec api alembic upgrade head          # cria o schema no Postgres do Docker
docker compose exec api python -m app.scripts.popular_demo   # abrigos, animais e contas de exemplo (iguais para todo o time)
```

O último comando carrega o mesmo cenário de demonstração em qualquer máquina (7 contas, 4 abrigos, 8 animais; senha de
todas: `Senha1234!`; as contas estão listadas no topo de `api/app/scripts/popular_demo.py`). É seguro repetir e **só roda
em banco local**: ele se recusa a rodar contra o Supabase.

API em `http://localhost:8000/docs` e interface em `http://localhost:5173`. O núcleo OpenCL sobe à
parte com `docker compose up -d --build nucleo-opencl` (`http://localhost:8001/saude`). Por enquanto ele só
responde à rota de saúde e roda o spike; detalhes em [`nucleo-opencl/README.md`](nucleo-opencl/README.md). O Postgres do Docker
começa vazio e é local de cada pessoa (o volume `db_data` guarda os dados entre reinícios;
`docker compose down` mantém, `docker compose down -v` apaga). Para criar o admin nele:
`docker compose exec api python -m app.scripts.criar_admin --nome "Seu Nome" --email voce@exemplo.com`.
Caminho validado em 2026-10-08 (cadastro, login e `/health/db` funcionando).

> Depois de puxar mudanças que alteram o `frontend/package.json` (dependência nova), renove o volume do
> `node_modules` do container: `docker compose up -d --build -V frontend`. Sem isso o frontend não encontra o pacote.

### Roteiro rápido para ver tudo funcionando (pela interface)

Com os dados de demonstração (`popular_demo`; senha de todas as contas: `Senha1234!`):

1. **Mapa** (primeiro item do menu): aba *Abrigos* com os abrigos de Recife e região; aba *Perdidos e avistados*
   com a lista mista. Teste **📍 Perto de mim** e o botão **⚙️ Filtros**.
2. **Perdi meu animal** (página inicial ou *Perdidos e achados*): preencha o assistente **sem conta** e entre na
   etapa *Revisar* com `maria@exemplo.com`. As fotos continuam lá. Publique e veja os avistamentos próximos.
3. Entre como `joao@exemplo.com`, abra a ficha de um animal e clique em **Tenho interesse**.
4. Entre como `patinhas@exemplo.com` (abrigo): o **sino 🔔** mostra o aviso do interesse; clique para ir a
   *Interessados* e responder. Em *Meus animais*, cadastre, edite ou exclua animais.
5. Entre como `admin@exemplo.com`: em *Validar abrigos*, dê ou retire o selo **Verificado** (o abrigo é avisado
   pelo sino) ou **Suspenda** (some do catálogo e não publica).
6. Tente abrir `/painel` com um tutor: a tela barra o acesso (e a API também devolveria 403).
7. No rodapé, **📲 Instalar app** (Chrome/Edge; no iPhone, o passo a passo do Safari). Em produção
   (`npm run build && npx vite preview`), o app instalado abre até sem internet.

Quem preferir testar sem a interface, tudo isso também está no Swagger (`/docs`): use o botão
**Authorize** com o e-mail e a senha de cada conta.

## Testes e integração contínua

| Camada | Ferramenta | O que garante | Comando |
|---|---|---|---|
| Estilo do código Python | `ruff` | padrão de código e erros comuns | `cd api && ruff check .` |
| API (unidade e integração) | `pytest` + `pytest-cov` | regras de negócio, matriz de permissões (25 rotas × 5 perfis), validações (CV-01 a CV-29) e e-mail; cobertura mínima de 90% | `cd api && pytest --cov=app` |
| Interface | `vite build` | a interface compila | `cd frontend && npm run build` |
| **Ponta a ponta (E2E)** | **Playwright** | um navegador de verdade usa as telas contra a API e um **Postgres real**: cadastro, login, perfis, adoção, perdidos e achados, doações, relatórios, moderação, celular | `cd frontend && npm run e2e` |
| Varredura de navegação | Playwright (`e2e/varredura.spec.js`) | cada perfil visita todas as telas que alcança e nenhuma dá erro no console, erro 500 ou "página não encontrada" | `npx playwright test varredura` |
| Acessibilidade | axe-core (`e2e/acessibilidade.spec.js`) | 24 telas sem violação grave das regras WCAG 2.1 A/AA (contraste, rótulos, nomes de botões…) | `npx playwright test acessibilidade` |
| Núcleo OpenCL | `make teste` | saída paralela igual à sequencial | `docker compose build nucleo-opencl` |

Os testes E2E rodam num **ambiente só deles**, para não sujar o banco de desenvolvimento: banco `buscapet_e2e`
(criado e migrado sozinho por `app/scripts/preparar_banco_teste.py`, que só aceita banco local terminado em `_e2e`),
API na porta 8100 e interface na 5174. O `npm run e2e` sobe tudo isso sozinho; basta o Postgres local estar ligado.
Cada teste cria as próprias contas, com e-mail único, e não depende dos dados de demonstração. `npm run e2e:ver` abre a janela do Playwright para acompanhar passo a passo, e
`npm run e2e:relatorio` mostra o relatório com captura, vídeo e *trace* das falhas.

A **CI** (`.github/workflows/ci.yml`) roda tudo isso a cada Pull Request (e falha se a cobertura da API cair abaixo de 90%). O job `e2e` só começa depois que lint,
testes da API e build passam, sobe um Postgres 16, roda a API com a sessão no fuso de Recife (onde o defeito das
datas aparecia) e publica o relatório do Playwright como artefato.

## Documentação

- [`docs/schema.sql`](docs/schema.sql) — modelo relacional (neste repositório)
- [Repositório `BuscaPet-Docs`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs) — escopo, RFs, plano de sprints, decisões técnicas e entregas de cada Sprint
  - [`planejamento/`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/planejamento) — escopo, plano de sprints, fluxos de tela, notas técnicas
  - [`sprints/sprint-2/`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/sprints/sprint-2) — arquitetura, diagrama de classes, MER, modelo relacional, protótipos

## Sprints

Cronograma completo em [`planejamento/plano-sprints-equipe-3.md`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/blob/main/planejamento/plano-sprints-equipe-3.md) (repositório `BuscaPet-Docs`). Entrega final: **05/12/2026**.
