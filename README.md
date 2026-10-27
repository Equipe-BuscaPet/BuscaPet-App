# BuscaPet

Plataforma web de **adoção**, **reencontro de animais perdidos por semelhança visual** e **canalização de doações**
para abrigos, voltada a Recife e região. Projeto acadêmico da Universidade Maurício de Nassau (UNINASSAU), curso de
Ciência da Computação, integrando as disciplinas de Fábrica de Software, Tópicos Avançados e Atividades Práticas
Interdisciplinares de Extensão IV.

**Versão atual: `1.0.0-rc.1` (Release Candidate, Sprint 10).** Entrega final: 05/12/2026.

## Objetivo

Hoje, quem perde um animal, quem quer adotar e quem quer ajudar um abrigo procura em grupos de rede social e em
perfis espalhados, sem garantia de que a informação é confiável ou está atualizada. O BuscaPet junta essas três
frentes num só lugar:

- **Adoção:** abrigos publicam os animais; tutores filtram, demonstram interesse e acompanham o processo.
- **Reencontro:** quem perdeu um animal ou avistou um na rua registra com foto e local. O **núcleo OpenCL** compara
  as fotos e mostra os registros mais parecidos e próximos, e continua vigiando: quando aparece uma foto parecida
  com um animal procurado, o tutor e o abrigo recebem um alerta.
- **Doações:** abrigos verificados publicam o que precisam; apoiadores (pet shops, clínicas, distribuidoras) doam, o
  abrigo confirma o recebimento e a doação conta no ranking público de quem apoia.
- **Administração:** verificação de abrigos (selo Verificado), denúncias, contas, painel, relatórios e histórico de
  operações.

## Equipe

- Nivaldo José de Arruda Filho — 01486768 — banco de dados, documentação e núcleo OpenCL
- Kaian Guthierry da Silva — 01617843
- Marlon Porto Torres — 01611478

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Interface web | React 18, Vite 5, React Router 7, Leaflet (mapas, OpenStreetMap), PWA (instalável, com *service worker*) |
| API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic (migrações), Pydantic 2, JWT (PyJWT) e bcrypt, Pillow (fotos), httpx |
| Banco de dados | PostgreSQL 16 (Supabase na demonstração; local ou Docker no desenvolvimento) |
| Núcleo de semelhança visual | C + **OpenCL 3.0** (PoCL, roda na CPU do servidor), libmicrohttpd, cJSON |
| Testes | pytest + pytest-cov (cobertura mínima de 90%), Playwright (ponta a ponta), axe-core (acessibilidade), ruff (estilo) |
| Infraestrutura | Docker e Docker Compose, GitHub Actions (CI a cada Pull Request) |

## Requisitos para executar

- **Python 3.12** (a API)
- **Node.js 20 ou mais novo** (a interface)
- **PostgreSQL 16**: um local, o do Docker Compose ou o do Supabase do projeto
- **Docker** (opcional): para subir tudo em containers e, principalmente, para rodar o **núcleo OpenCL** no Windows
  ou no macOS. Sem o núcleo o sistema funciona; a busca por foto mostra os registros por distância.
- Git

## Estrutura do projeto

```
BuscaPet-App/
  api/                      backend — FastAPI
    app/main.py             cria a aplicação e registra as rotas
    app/routers/            uma rota por assunto (auth, animais, interesses, reencontro, doacoes, admin, relatorios…)
    app/models/             tabelas do banco (SQLAlchemy)
    app/schemas/            formato dos dados de entrada e saída (Pydantic)
    app/core/               configuração, segurança, e-mail, fotos, cliente do núcleo, auditoria
    app/scripts/            popular_demo, criar_admin, indexar_fotos, preparar_banco_teste
    alembic/versions/       migrações do banco (0001 a 0004)
    tests/                  testes da API (pytest)
  frontend/                 interface — React + Vite
    src/pages/              uma tela por arquivo
    src/componentes/        peças reutilizadas (menu, sino, mapa, fotos…)
    e2e/                    testes de ponta a ponta (Playwright)
  nucleo-opencl/            serviço de semelhança visual — C + OpenCL
    kernels/                código que roda em paralelo (descritor.cl, comparar.cl)
    src/                    servidor HTTP, descritores e versão sequencial equivalente
  docs/schema.sql           modelo relacional (DDL), espelha api/app/models/
  docs/mer.md               diagrama entidade-relacionamento (gerado dos modelos)
  docs/api.md               guia das rotas da API
  docs/manual-tecnico.md    manual técnico (arquitetura, configuração, publicação, manutenção)
  .github/workflows/ci.yml  CI: api, frontend, e2e, nucleo-opencl
  docker-compose.yml
```

A documentação de projeto (escopo, requisitos, plano de sprints, fluxos de tela, notas técnicas e as entregas de cada
Sprint) fica no repositório [`BuscaPet-Docs`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs).

## Instalação e configuração

Há dois caminhos. O **A** é o que a demonstração usa; o **B** sobe tudo em containers.

### Início rápido (Windows, só com o Docker Desktop)

Para ver o sistema funcionando sem instalar Python nem Node, abra o Docker Desktop e, no PowerShell, dentro da pasta
do projeto:

```powershell
.\iniciar-demo.ps1
```

O script cria o `.env`, sobe banco, núcleo OpenCL, API e interface, aplica as migrações, cria os dados de
demonstração (com fotos reais de cães) e calcula os descritores das fotos. Ao terminar, abra
http://localhost:5173 (contas e senha no roteiro mais abaixo). Pode rodar de novo à vontade; `docker compose down`
para parar (os dados ficam guardados). Na primeira vez, o download e a construção do núcleo levam alguns minutos.

### A) Direto na máquina (Windows, macOS ou Linux)

**1. API**

```powershell
git clone https://github.com/Equipe-BuscaPet/BuscaPet-App.git
cd BuscaPet-App/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Crie o arquivo `api/.env` (ele **nunca** é versionado):

```
DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@HOST:5432/NOME_DO_BANCO
JWT_SECRET=<texto aleatório longo>     # ex.: python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Variáveis opcionais do mesmo arquivo:

| Variável | Para quê | Padrão |
|---|---|---|
| `NUCLEO_OPENCL_URL` | endereço do núcleo; fora do Docker, `http://127.0.0.1:8001` | `http://nucleo-opencl:8001` |
| `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_REMETENTE` | envio real de e-mail (recuperação de senha, avisos) | sem `SMTP_HOST`, os e-mails viram arquivos `.eml` em `api/caixa-de-saida/` |
| `URL_INTERFACE` | endereço da interface, usado nos links dos e-mails | `http://localhost:5173` |
| `CORS_ORIGENS` | endereços que podem chamar a API | `["http://localhost:5173"]` |

**2. Interface**

```powershell
cd ../frontend
npm install
```

Se a API não estiver em `http://localhost:8000`, defina `VITE_API_URL` (ex.: no arquivo `frontend/.env.local`).

### B) Docker Compose

Crie o arquivo `.env` na raiz do projeto (nunca é versionado):

```
DATABASE_URL=postgresql+psycopg://buscapet:buscapet@db:5432/buscapet
JWT_SECRET=troque-por-um-valor-aleatorio-longo
NUCLEO_OPENCL_URL=http://nucleo-opencl:8001
```

```bash
docker compose up -d --build db api frontend nucleo-opencl
```

## Banco de dados

1. **Criar as tabelas.** Com o banco vazio, rode as migrações. O Alembic lê a `DATABASE_URL` da **variável de
   ambiente** (não do `.env`):

   ```powershell
   cd api
   $env:DATABASE_URL = "<a mesma URL do api/.env>"     # bash: export DATABASE_URL=...
   alembic upgrade head
   ```

   No Docker: `docker compose exec api alembic upgrade head`. Alternativa sem Python: rodar
   [`docs/schema.sql`](docs/schema.sql) no SQL Editor do Supabase (descreve o mesmo schema das migrações).

2. **Dados de demonstração** (só em banco local; o script se recusa a rodar no Supabase, porque as senhas são
   públicas): `python -m app.scripts.popular_demo` (no Docker: `docker compose exec api python -m app.scripts.popular_demo`).
   Cria 11 contas, 4 abrigos e 10 animais, com histórico de adoções, mural de necessidades e doações. Senha de
   todas: `Senha1234!`. É seguro repetir.

3. **Administrador** (não existe cadastro público de admin):
   `python -m app.scripts.criar_admin --nome "Seu Nome" --email voce@exemplo.com`.

4. **Descritores das fotos** (com o núcleo no ar): `python -m app.scripts.indexar_fotos` calcula os descritores das
   fotos enviadas enquanto o núcleo estava fora do ar. Também há um botão para isso em Administração → Núcleo OpenCL.

O modelo está em [`docs/mer.md`](docs/mer.md) (diagrama entidade-relacionamento, completo e por módulo, gerado dos
modelos por `python -m app.scripts.gerar_mer`) e em [`docs/schema.sql`](docs/schema.sql) (as instruções SQL). Um teste
confere que os dois batem com os modelos, tabela por tabela e coluna por coluna.

## Execução

**Caminho A**, em três terminais:

```powershell
# 1) núcleo OpenCL (opcional; precisa do Docker)
docker compose up -d --build nucleo-opencl          # teste: http://localhost:8001/saude

# 2) API, na pasta api/ com o ambiente virtual ativo
uvicorn app.main:app --port 8000                    # teste: http://localhost:8000/health/db

# 3) interface, na pasta frontend/
npm run dev                                         # abre em http://localhost:5173
```

**Caminho B:** depois do `docker compose up`, os mesmos endereços já estão no ar.

| Endereço | O que é |
|---|---|
| <http://localhost:5173> | interface |
| <http://localhost:8000/docs> | documentação interativa da API (Swagger), onde se testa cada rota |
| <http://localhost:8000/health/db> | prova de conexão com o banco (`"banco": "conectado"`) |
| <http://localhost:8001/saude> | estado do núcleo OpenCL e do dispositivo |

Para publicar em produção (banco, API, núcleo e interface), siga a seção 13 do
[manual técnico](docs/manual-tecnico.md#13-publicação-em-produção). Para gerar a versão de produção da interface: `npm run build` (saída em `frontend/dist/`; `npx vite preview` para
conferir). Instalado como app, ele abre até sem internet.

### Roteiro rápido para ver tudo funcionando

Com os dados de demonstração (senha de todas as contas: `Senha1234!`):

1. **Mapa:** aba *Abrigos* e aba *Perdidos e avistados*; teste **📍 Perto de mim** e os **Filtros**.
2. **Perdi meu animal** (página inicial ou *Perdidos e achados*): preencha o assistente **sem conta** e entre na
   etapa *Revisar* com `maria@exemplo.com`; as fotos continuam lá. Publique e veja os registros parecidos.
3. Entre como `joao@exemplo.com`, abra a ficha de um animal e clique em **Tenho interesse**.
4. Entre como `patinhas@exemplo.com` (abrigo verificado): o **sino 🔔** mostra o aviso; responda em
   *Interessados*, cadastre animais com fotos em *Meus animais*, publique uma necessidade e confirme a doação que
   está aguardando; veja o relatório do abrigo.
5. Entre como `amigofiel@exemplo.com` (apoiador): doe pelo mural e veja a posição no ranking de *Quem apoia*.
6. Entre como `admin@exemplo.com`: verifique abrigos, trate denúncias, veja o painel, os relatórios, o histórico de
   operações e a aba **Núcleo OpenCL** (rode a comparação sequencial × OpenCL).
7. Tente abrir `/painel` com um tutor: a tela barra o acesso (e a API também devolveria 403).

## Documentação da API

- **Guia das rotas:** [`docs/api.md`](docs/api.md): autenticação, perfis, todas as rotas por módulo, com
  quem pode usar, parâmetros, corpo, respostas, erros e exemplos. É **gerado do código**
  (`cd api && python -m app.scripts.gerar_doc_api`), e um teste falha se ficar desatualizado.
- **Documentação interativa:** <http://localhost:8000/docs> (Swagger) e <http://localhost:8000/redoc>, geradas pela
  própria API e sempre iguais ao código. O botão **Authorize** do Swagger aceita o e-mail e a senha de uma conta.
- **Contrato do núcleo OpenCL:** [`nucleo-opencl/README.md`](nucleo-opencl/README.md).

## Testes e integração contínua

| Camada | Ferramenta | O que garante | Comando |
|---|---|---|---|
| Estilo do código Python | `ruff` | padrão de código e erros comuns | `cd api && ruff check .` |
| API (unidade e integração) | `pytest` + `pytest-cov` | regras de negócio, permissões de cada perfil, validações (CV-01 a CV-29), e-mail e busca por semelhança; cobertura mínima de 90% | `cd api && pytest --cov=app` |
| Interface | `vite build` | a interface compila | `cd frontend && npm run build` |
| **Ponta a ponta (E2E)** | **Playwright** | um navegador de verdade usa as telas contra a API e um **Postgres real**: cadastro, login, perfis, adoção, perdidos e achados, doações, relatórios, moderação, núcleo, celular | `cd frontend && npm run e2e` |
| Varredura de navegação | Playwright (`e2e/varredura.spec.js`) | cada perfil visita todas as telas que alcança e nenhuma dá erro no console, erro 500 ou "página não encontrada" | `npx playwright test varredura` |
| Acessibilidade | axe-core (`e2e/acessibilidade.spec.js`) | as telas de cada perfil sem violação das regras WCAG 2.1 A/AA (contraste, rótulos, nomes de botões…) | `npx playwright test acessibilidade` |
| Núcleo OpenCL | `make teste` | o resultado em paralelo é **idêntico** ao sequencial | `docker compose build nucleo-opencl` |

Os testes da API rodam em SQLite em memória e não tocam em nenhum banco real. Os testes E2E rodam num **ambiente só
deles**: banco `buscapet_e2e` (criado e migrado sozinho por `app/scripts/preparar_banco_teste.py`, que só aceita banco
local terminado em `_e2e`), API na porta 8100 e interface na 5174. O `npm run e2e` sobe tudo isso sozinho; basta o
Postgres local estar ligado. `npm run e2e:ver` abre a janela do Playwright e `npm run e2e:relatorio` mostra o
relatório com captura, vídeo e *trace* das falhas.

A **CI** (`.github/workflows/ci.yml`) roda tudo isso a cada Pull Request e falha se a cobertura da API cair abaixo de
90%. O job `e2e` só começa depois que lint, testes da API e build passam, sobe um Postgres 16 e roda a API com a sessão
no fuso de Recife. O job do núcleo compila, roda o teste de equivalência e testa a API contra o núcleo real com fotos.

## Mais documentação

- [`docs/manual-tecnico.md`](docs/manual-tecnico.md): **manual técnico** — arquitetura, variáveis de ambiente, núcleo
  OpenCL, segurança, **publicação em produção** e manutenção
- Manual do usuário: [`BuscaPet-Docs/manuais`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/tree/main/manuais)
- [`docs/mer.md`](docs/mer.md): diagrama entidade-relacionamento
- [`docs/schema.sql`](docs/schema.sql): modelo relacional
- [`docs/api.md`](docs/api.md): guia das rotas da API
- [`nucleo-opencl/README.md`](nucleo-opencl/README.md): como o núcleo funciona, benchmark e contrato HTTP
- [`frontend/README.md`](frontend/README.md): telas, decisões de interface e testes E2E
- [Repositório `BuscaPet-Docs`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs): escopo, requisitos, plano de
  sprints, fluxos de tela, notas técnicas e as entregas de cada Sprint
