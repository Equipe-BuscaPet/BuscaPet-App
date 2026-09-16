# BuscaPet

Plataforma web de adoção, reencontro de animais perdidos (busca por
similaridade visual) e doações. Projeto acadêmico UNINASSAU — Fábrica de
Software, Tópicos Avançados e Extensão IV.

## Stack
- Backend web: Python + FastAPI, SQLAlchemy 2.0 + Alembic, Postgres (Supabase em produção/demo)
- Núcleo de similaridade visual: **C puro** (`cl.h`), rodando via PoCL, como serviço HTTP separado em `nucleo-opencl/` — nunca embutido no backend
- Fila para o monitoramento contínuo: RQ + Redis
- Frontend: `frontend/` (ver README próprio)
- Docker Compose local: `api`, `nucleo-opencl`, `db`, `redis`, `frontend`

## Onde estão as regras de negócio
- `docs/` tem o documento de escopo, o plano de sprints, a descrição de páginas/fluxos e as notas técnicas — são a fonte de verdade para requisitos (RF-01 a RF-41) e decisões de arquitetura. Consultar antes de assumir comportamento.
- `docs/schema.sql` é o modelo relacional; `api/app/models/` é a mesma coisa em SQLAlchemy — as duas fontes devem ficar em sincronia.

## Convenções
- Nomes de tabelas/campos em português, snake_case (segue o domínio do projeto).
- Nunca embutir o núcleo OpenCL no backend principal — comunicação é sempre via HTTP (`httpx`) contra `nucleo-opencl`.
- RF-19 a RF-29 (núcleo + reencontro) são prioridade inegociável do projeto — não simplificar nem adiar sem decisão explícita da equipe.
- Ao trabalhar no núcleo OpenCL, mandar só o arquivo/kernel relevante numa sessão dedicada, não o repositório inteiro.
