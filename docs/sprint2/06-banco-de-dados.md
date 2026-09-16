# 6. Banco de dados criado

A estrutura inicial está implementada e pronta para ser aplicada — não em
dados fictícios prontos ainda (isso é trabalho de "gerador de dados de
teste", já previsto na Sprint 1 do plano de sprints), mas o schema completo
do modelo relacional da seção 4 já existe em duas formas equivalentes:

1. **Migration Alembic** (`api/alembic/versions/0001_initial_schema.py`) — a
   forma "de verdade" de criar o banco, com histórico versionado. Rodar:
   ```bash
   cd api
   pip install -r requirements.txt
   alembic upgrade head
   ```
2. **DDL direto** (`docs/schema.sql`) — mesma estrutura, para quem preferir
   colar direto no SQL Editor do Supabase sem passar por Python/Alembic.

## Onde o banco está hospedado

Decisão de DevOps (`notas-tecnicas-devops-ia-v1.md.pdf`, seção 3): **Supabase
free tier** (Postgres com PostGIS disponível). Atenção: o projeto Supabase
free pausa após 1 semana de inatividade — reativar pelo painel antes de cada
Sprint/apresentação é parte do checklist de entrega, não um imprevisto.

## O que falta (não é escopo da Sprint 2)

- Popular com dados de teste (abrigos, animais e fotos fictícias) — item já
  previsto no plano de sprints para a Sprint 1/2, responsabilidade de quem
  cuida do banco.
- Índices de performance além dos mínimos de integridade — só quando o
  volume justificar (ver seção 4, "Índices além das chaves").
- A extração de descritores visuais em si (RF-21) não roda ainda — a coluna
  e a tabela (`descritores_visuais`) existem, o algoritmo é trabalho do
  núcleo OpenCL na Sprint 3.

## Ambiente usado para gerar este material

Os artefatos desta Sprint (models, migration, DDL, docs) foram preparados
numa máquina sem Docker/Python instalados — por isso a migration não foi
executada neste ambiente. Cada integrante deve rodar `alembic upgrade head`
(ou aplicar `schema.sql` no Supabase) na própria máquina/ambiente do projeto
antes da apresentação, para poder mostrar o banco de fato criado.
