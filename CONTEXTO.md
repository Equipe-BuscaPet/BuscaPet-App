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
     de erro claras, navegação coerente, commits organizados). *Entregue* (documento em `BuscaPet-Docs/sprints/sprint-4/`).
2. **Plano interno** (`BuscaPet-Docs/planejamento/plano-sprints-equipe-3.md`): organiza o trabalho até
   05/12 e põe o **núcleo OpenCL** na sua "Sprint 3". Ele é independente da contagem oficial. O núcleo
   continua obrigatório para Tópicos Avançados, mas **está fora das entregas oficiais** de Fábrica.

Ao falar "Sprint N", diga qual das duas.

## 4. Onde estamos (2026-10-16)

> Parte do que está abaixo ainda está em **Pull Requests empilhados** (cada um depende do anterior):
> #5 API de perdidos/avistamentos → `feature/telas-perdi-encontrei` → `feature/e2e-playwright` →
> `feature/mapa-camadas-reencontro` → `feature/pwa-instalar` → `feature/notificacoes` → `feature/menu-conta` →
> `feature/reencontro-completo` (alerta e caso resolvido). Independente:
> `feature/nucleo-spike-servico`. Fazer o merge nessa ordem.

**Funciona, validado no Postgres local e por testes automatizados:**
- Cadastro e login (JWT) de tutor, abrigo e apoiador; admin criado só por script. Login volta para a página que o
  pediu (`?voltar=`, só caminhos internos).
- Perfis e permissões: cada tipo de conta só acessa o que lhe cabe (a regra vale na API; a interface apenas reflete).
- CRUD de animais pelo abrigo; catálogo público com busca e filtros (inclusive por abrigo); ficha do animal.
- **Mapa** (`/mapa`, primeiro item do menu; OpenStreetMap + Leaflet; RF-07 a RF-09): acima do mapa só as abas
  **Abrigos** e **Perdidos e avistados**; sobre a lista, contagem, **Perto de mim** e **Filtros** (painel: tipo,
  espécie, porte, período e distância para animais; só verificados, só com animais e distância para abrigos).
  A lista acompanha a aba (mista para animais). URL: `?ver=animais&mostrar=perdidos`.
- Verificação de abrigos pelo administrador (selo Verificado, retirar o selo ou suspender), com aviso ao abrigo.
- Interesse de adoção completo (API e telas: ficha do animal, Meus interesses, Interessados).
- **Perdidos e achados (RF-19/RF-20)**: API e telas (detalhes abaixo).
- **Notificações (RF-36)**: `GET /notificacoes`, `GET /notificacoes/contagem`, `PATCH /notificacoes/{id}/lida`,
  `POST /notificacoes/marcar-todas-lidas`. Cada uma traz o `destino` (tela que abre). Sino com contador no cabeçalho
  e página `/notificacoes`. Geradas hoje por: interesse de adoção (cada passo) e mudança do selo do abrigo.
- **Cabeçalho com menu ☰ da conta** (`feature/menu-conta`): menu principal só com Mapa, Animais e Perdidos e achados;
  o resto (Minha conta, itens do perfil, Meus registros, Notificações, "Em breve", Sair) fica no ☰. Página
  **Minha conta** (`/conta`, RF-37) usando a API `/usuarios/eu` que já existia: editar dados/perfil e trocar senha.
- **PWA**: instalável na tela inicial (manifesto, ícones do logo oficial, service worker só em produção, botão
  "Instalar app" no rodapé). O celular não roda OpenCL: só envia a foto; o núcleo roda no servidor.
- **Núcleo OpenCL** (PR `feature/nucleo-spike-servico`): spike `soma_vetores` com teste de equivalência
  (gate da Sprint 1 interna), serviço HTTP em C com `GET /saude`; descritores e comparação ainda a fazer.
- Migrations `0001` a `0003`. **Testes:** 87 na API (`pytest`) e 50 de ponta a ponta (Playwright, banco `buscapet_e2e`
  isolado). CI: `api`, `frontend`, `e2e` e `nucleo-opencl`.

**Interesse de adoção (Sprint 4):** tutor registra interesse
(`POST /animais/{id}/interesses`), lista os seus (`GET /interesses/meus`) e pode desistir
(`DELETE /interesses/{id}`); o abrigo vê os recebidos com o contato do tutor (`GET /interesses/recebidos`)
e decide (`PATCH /interesses/{id}`: em conversa / aprovado / recusado). Aprovar põe o animal em
`em_processo`. O telefone do abrigo só vem na resposta de quem registrou interesse. Cada passo gera uma
`Notificacao`. Migration `0003` (coluna `mensagem` e unicidade tutor+animal).

**Animal perdido e avistamento (RF-19/RF-20):** `POST /perdidos` (tutor) e
`POST /avistamentos` (qualquer conta logada) recebem um formulário multipart com as características, o
local, a data e de 1 a 5 fotos (campo `fotos`). Consulta pública em `GET /perdidos` e `GET /avistamentos`
(filtros de espécie, porte e raio a partir de `lat`/`lng`), `GET .../meus` e `DELETE` pelo autor ou admin.
Privacidade (escopo §9): a resposta pública não traz dados de quem registrou e o local sai arredondado
(perdido ~1 km, avistamento ~100 m). Fotos: validadas e regravadas como JPEG **sem metadados** (remove o
GPS da foto de celular), até 1280 px, nome aleatório, em `api/uploads/fotos/` (fora do Git), servidas por
`GET /fotos/{nome}` (`app/core/fotos.py`). Dependência: `pillow` (no Docker: `docker compose up -d --build api`).
Telas: `/reencontro` (lista pública), detalhe de cada registro, assistentes `/perdi` e `/encontrei` (5 etapas; o
visitante preenche e entra só para publicar) e `/meus-registros`. A etapa de resultados mostra registros reais
da outra base por distância até o núcleo comparar as fotos (detalhes em `frontend/README.md`).

**Alerta e caso resolvido (fecha o fluxo do reencontro, Sprint 5 oficial):** todo `POST /avistamentos` cria
uma notificação (`referencia_tipo="avistamento"`, o clique abre o avistamento) para o tutor com perda ativa da
mesma espécie, sumida até a data do avistamento e dentro do `raio_busca_km` dele — **um alerta por tutor**, com
a perda mais próxima (versão por distância do RF-25; o núcleo vai somar a semelhança da foto).
`PATCH /perdidos/{id}/resolvido` (RF-28, só o tutor autor; 409 se já resolvido): o caso sai da lista pública e
do mapa, a `BuscaSalva` vira `resolvida` e para de gerar alertas. Na interface: botão "Encontrei meu animal" no
detalhe e em Meus registros.
**Datas "do dia"** (`data_entrada`, `data_desaparecimento`, `data_avistamento`) são colunas `DateTime` gravadas como
meia-noite UTC; a saída usa o tipo `DataDoDia` (`app/schemas/datas.py`) para não voltar um dia no Postgres em UTC-3.

**Existe só como modelo de dados, sem rota nem tela:** busca salva, correspondência, descritor visual, necessidade,
doação, pontuação/ranking de apoiadores, denúncia, log de auditoria, membros da equipe do abrigo.

**Próximo passo:** confirmar o roteiro da **Sprint 5 oficial** (entrega no Teams). Pelo plano interno: núcleo
(descritores e comparação, com o Nivaldo) → busca por foto (RF-21 a 23) → busca salva e alertas (RF-24 a 27) →
doações e ranking (RF-30 a 34, onde o selo Verificado passa a ser exigido) → painel admin e relatórios → deploy.

**Mudança da Sprint 4 (já implementada):** abrigo **não depende mais de aprovação humana para usar a
conta**. Cadastra e opera na hora, aparece como "não verificado", e o administrador só concede o selo
**Verificado**. Mapeamento no banco, sem migration: `pendente` = não verificado, `aprovado` = verificado,
`rejeitado` = suspenso (some do catálogo e não publica). A API devolve `abrigo_verificado` em cada animal.
O selo será exigido apenas para o que carrega risco de golpe: **exibir a chave de doação financeira,
aparecer no ranking e no mural de necessidades** (ainda não implementados, então ainda não há o que bloquear).

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
  da Sprint 3 e o das datas "um dia antes" (fuso) só apareceram no Postgres. Valide mudanças de banco num
  Postgres real. **Ponta a ponta:** `cd frontend && npm run e2e` (Playwright; cria e usa o banco `buscapet_e2e`,
  API :8100 e interface :5174, sem sujar o banco de desenvolvimento).
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
5. ~~Visitante completa os assistentes "Perdi/Encontrei" e só é barrado na ação final?~~ **Decidido (16/10): sim**, com login dentro da etapa de revisão, sem perder as fotos.
6. "Encontrei um animal" tem monitoramento contínuo ou só publica avistamento? (recomendado: só avistamento)
7. Apoiador precisa de verificação (CNPJ falso entra no ranking)? Encaixa no novo modelo de selo.
8. Data da oficina de capacitação com a instituição parceira (Extensão IV).
