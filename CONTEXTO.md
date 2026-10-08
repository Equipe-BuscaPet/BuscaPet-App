# BuscaPet — guia de contexto para quem chega (pessoas e Claude)

> **Claude Code não lê este arquivo sozinho.** Ao abrir uma sessão neste repositório,
> comece com: *"Leia o CONTEXTO.md e o README.md antes de qualquer coisa."*
> Última atualização: 2026-10-08.

## 1. O que é o projeto

Plataforma web (não é app nativo) de **adoção de animais**, **reencontro de animais perdidos
por similaridade visual** e **doações** a abrigos. Projeto acadêmico da UNINASSAU
(Ciência da Computação, Recife) que integra três disciplinas:

| Disciplina | O que ela cobra do projeto |
|---|---|
| Fábrica de Software | Construção do sistema, entregue em sprints com documento em PDF |
| Tópicos Avançados | Núcleo de processamento paralelo em **OpenCL** (comparação de fotos) |
| Extensão IV | Capacitar uma instituição parceira de proteção animal |

**Entrega final: 05/12/2026.** Os professores disseram que pesa mais a entrega final do que a data
de cada sprint.

Três públicos: **tutores/adotantes**, **abrigos/protetores** e **apoiadores** (petshops,
clínicas, distribuidoras). Mais um perfil **administrador**.

## 2. Equipe e papéis

| Pessoa | Papel | Foco |
|---|---|---|
| Nivaldo José de Arruda Filho (líder / Scrum Master) | P1 | banco de dados, documentação, núcleo OpenCL |
| Kaian Guthierry da Silva | P2 | backend, integração, DevOps, apoio ao núcleo |
| Marlon Porto Torres | P3 | frontend, UX, roteiro dos vídeos |

Repositórios (organização `Equipe-BuscaPet`):
- **`BuscaPet-App`** (este) — código.
- **`BuscaPet-Docs`** — documentação: `planejamento/` (escopo, plano de sprints, fluxos, notas
  técnicas), `sprints/sprint-N/` (entrega de cada sprint), `processos/` (como fazer X).
  **Clone-o ao lado deste.** Ele é a fonte de verdade dos requisitos (RF-01 a RF-41).
- `.github` — README do perfil da organização.

## 3. Duas contagens de "Sprint" — não confundir

1. **Sprints oficiais da disciplina Fábrica de Software** (o que a professora cobra, um PDF por
   sprint, sempre acumulando as anteriores):
   - Sprint 1 — definição do problema, requisitos, backlog. *Entregue.*
   - Sprint 2 — arquitetura, diagrama de classes, MER, modelo relacional, protótipo, banco criado,
     GitHub. *Entregue.*
   - Sprint 3 — banco conectado, login, cadastro persistido, perfis/permissões, CRUD da entidade
     principal (animais), primeiro deploy local. *Entregue e enviada.*
   - **Sprint 4 — "primeiro módulo completo"** (fluxo completo, persistência, validações, mensagens
     de erro claras, navegação coerente, commits organizados). **Em andamento.**
2. **Plano interno** (`BuscaPet-Docs/planejamento/plano-sprints-equipe-3.md`): organiza o trabalho até
   05/12 e põe o **núcleo OpenCL** na sua "Sprint 3". Ele é independente da contagem oficial. O núcleo
   continua obrigatório para Tópicos Avançados, mas **está fora das entregas oficiais** de Fábrica.

Ao falar "Sprint N", diga qual das duas.

## 4. Onde estamos (2026-10-08)

**Funciona, validado no banco real:**
- Cadastro e login (JWT) de tutor, abrigo e apoiador; admin criado só por script.
- Perfis e permissões: cada tipo de conta só acessa o que lhe cabe (a regra vale na API; a interface
  apenas reflete).
- CRUD de animais pelo abrigo; catálogo público com busca e filtros; ficha do animal.
- Fila do administrador para validar abrigos.
- Migrations `0001` (schema) e `0002` (alinha models e banco). 37 testes automatizados passando.
- Docker Compose validado em 2026-10-08 (`db`, `redis`, `api`, `frontend`).

**Existe só como modelo de dados, sem rota nem tela:** interesse de adoção (`Interesse`), animal
perdido, avistamento, busca salva, correspondência, necessidade, doação, ranking de apoiadores,
denúncia, notificação, log de auditoria. O módulo `nucleo-opencl/` é só contrato e Dockerfile.

**Próximo passo (Sprint 4 oficial): módulo Adoção.** Fluxo completo: abrigo cadastra animal → tutor vê
no catálogo → tutor registra **interesse de adoção** → abrigo aceita ou recusa → status do animal muda.
Inclui validações no frontend, mensagens de erro amigáveis e navegação coerente.

**Mudança decidida para a Sprint 4:** abrigo **não depende mais de aprovação humana para usar a conta**.
Cadastra e opera na hora, aparece como "não verificado", e o administrador só concede o selo
**Verificado**. O selo é exigido apenas para o que carrega risco de golpe: exibir a chave de doação
financeira, aparecer no ranking e no mural de necessidades. O campo `status_validacao` já existe.

## 5. Decisões de arquitetura já fechadas (não reabrir sem motivo novo)

- **Login único** para todos os perfis; o tipo de conta é escolhido só no cadastro.
- Visitante sem conta pode **navegar e executar busca por foto**; só precisa logar para agir
  (registrar perdido/avistamento, salvar busca, contatar abrigo).
- O sistema **nunca afirma correspondência definitiva** — só candidatos ordenados por semelhança
  (alta/média/baixa). A decisão final é do tutor.
- Busca por similaridade é única e bidirecional; busca salva fica ativa e cada novo registro é
  comparado contra as buscas ativas (é o argumento de paralelismo de Tópicos Avançados).
- Ranking de apoiadores por categoria, pondera regularidade (meses consecutivos); doação só conta após
  **confirmação do abrigo**.
- Abrigo tem **vários usuários vinculados** (não depende de uma única pessoa).
- Mapa: OpenStreetMap + Leaflet (gratuito).
- **Núcleo OpenCL em C puro, via PoCL (CPU, sem GPU), como serviço HTTP separado** (`nucleo-opencl/`),
  chamado pela API com `httpx`. **Nunca embutir no backend.**
- Backend: Python + FastAPI, SQLAlchemy 2.0 + Alembic; fila RQ + Redis para o monitoramento contínuo.
- Fora do escopo: app nativo, pagamento dentro da plataforma (a chave PIX do abrigo é só exibida),
  API oficial do WhatsApp, prontuário veterinário, chat em tempo real.
- **Nunca cortar** se o prazo apertar: RF-19 a RF-29 (núcleo + reencontro) e o benchmark RF-29.
  Ordem de corte: RF-41 → RF-40 → RF-28 → RF-33 → RF-05.

## 6. Como rodar

Detalhes completos no `README.md`. Resumo:

- **Docker (mais simples):** `cp .env.example .env`, depois `docker compose up -d --build db redis api frontend`
  e `docker compose exec api alembic upgrade head`. API em `localhost:8000/docs`, interface em `localhost:5173`.
  O Postgres do Docker começa vazio e é só seu.
- **Python direto (usado na demonstração):** venv em `api/`, `api/.env` com `DATABASE_URL` e
  `JWT_SECRET`, `alembic upgrade head`, `uvicorn app.main:app --reload`; front com `npm install && npm run dev`.
- **Testes:** `cd api && pytest` (SQLite em memória). **Atenção:** SQLite não pega tudo — o bug dos enums
  da Sprint 3 só apareceu no Postgres. Valide mudanças de banco num Postgres real (o do Docker serve).
- O login da API usa formulário OAuth2 (`username` = e-mail, `password`), não JSON.
- Criar administrador: `python -m app.scripts.criar_admin --nome "..." --email ...`.

**Segredos:** `.env` e `api/.env` nunca vão para o Git. A `DATABASE_URL` do Supabase compartilhado e a
lista de contas de demonstração são passadas **por Nivaldo, fora do repositório**. O Supabase gratuito
pausa após ~1 semana sem uso; quem tem acesso restaura pelo painel.

## 7. Convenções de trabalho

- Nomes de tabelas e campos em **português, snake_case**.
- `docs/schema.sql` e `api/app/models/` descrevem o mesmo modelo — **mudou um, mude o outro** e crie
  uma migration Alembic (`alembic check` deve ficar limpo).
- Commits descritivos e pequenos; o roteiro oficial avalia a participação de cada integrante, então
  **commite com o seu próprio usuário do Git** (`git config user.name` / `user.email`, o e-mail vinculado
  ao seu GitHub).
- **Não inclua trailer `Co-Authored-By: Claude`** nos commits. A equipe não quer o Claude listado como
  contribuidor no GitHub (já reescrevemos o histórico uma vez por isso). Vale mesmo que a ferramenta sugira.
- Trabalhe em branch e abra PR; **Definition of Done:** revisado por outro integrante, CI verde
  (`ruff` + `pytest` na API, `npm run build` no front), demonstrável.
- Uma sessão do Claude por tarefa, não uma sessão para o projeto inteiro. No núcleo OpenCL, mande só o
  arquivo/kernel relevante.
- Diário de sessões: cada sessão de produção do Nivaldo deixa um resumo em `registro-sessoes/` (pasta
  local, fora do Git). Quem chega **não tem esse histórico** — este arquivo e o `BuscaPet-Docs` o substituem.
  Se criar resumos, escreva para um leigo: termo técnico explicado, com o raciocínio por trás das decisões.

## 8. Pontos ainda em aberto

1. Base inicial de fotos para desenvolvimento e teste de escala do núcleo.
2. Características da ficha do animal (definir com o abrigo parceiro).
3. Peso exato volume × regularidade no ranking.
4. Abrangência inicial: uma cidade ou a região metropolitana.
5. Visitante completa os assistentes "Perdi/Encontrei" e só é barrado na ação final? (recomendado: sim)
6. "Encontrei um animal" tem monitoramento contínuo ou só publica avistamento? (recomendado: só avistamento)
7. Apoiador precisa de verificação (CNPJ falso entra no ranking)? Encaixa no novo modelo de selo.
8. Data da oficina de capacitação com a instituição parceira (Extensão IV).
