# 4. Modelo Relacional

DDL completo em [`docs/schema.sql`](../schema.sql) (roda direto no SQL Editor
do Supabase) — espelhado nos models SQLAlchemy em `api/app/models/` e na
migration Alembic `api/alembic/versions/0001_initial_schema.py` (é essa
migration que efetivamente cria o banco, ver seção 6).

Resumo de tabelas, chaves primárias e estrangeiras:

| Tabela | PK | FKs | Observação |
|---|---|---|---|
| `usuarios` | `id` | `validado_por_id → usuarios.id` (via abrigos, ver abaixo) | Base de autenticação de todos os perfis |
| `tutores` | `usuario_id` | `usuario_id → usuarios.id` | PK = FK (1:1 com usuarios) |
| `abrigos` | `usuario_id` | `usuario_id → usuarios.id`, `validado_por_id → usuarios.id` | `status_validacao` controla RF-06 |
| `membros_equipe_abrigo` | `id` | `abrigo_id → abrigos.usuario_id`, `usuario_id → usuarios.id` | UNIQUE(`abrigo_id`,`usuario_id`) — RF equipe do abrigo |
| `apoiadores` | `usuario_id` | `usuario_id → usuarios.id` | `cnpj` UNIQUE |
| `animais` | `id` | `abrigo_id → abrigos.usuario_id` | — |
| `fotos` | `id` | nenhuma FK real (`entidade_tipo`+`entidade_id`) | associação polimórfica — ver justificativa na seção 3 (MER) |
| `interesses` | `id` | `animal_id → animais.id`, `tutor_id → tutores.usuario_id` | RF-16 |
| `animais_perdidos` | `id` | `tutor_id → tutores.usuario_id` | RF-19 |
| `avistamentos` | `id` | `usuario_id → usuarios.id` | RF-20 |
| `descritores_visuais` | `id` | `foto_id → fotos.id` (UNIQUE) | 1 descritor por foto — RF-21 |
| `buscas_salvas` | `id` | `tutor_id → tutores.usuario_id`, `animal_perdido_id → animais_perdidos.id` | RF-24 |
| `correspondencias` | `id` | `animal_perdido_id`, `animal_id`, `avistamento_id` (todas nullable, para `animais_perdidos`/`animais`/`avistamentos`) | RF-23, RF-25, RF-26, RF-27 |
| `necessidades` | `id` | `abrigo_id → abrigos.usuario_id` | RF-30 |
| `doacoes` | `id` | `apoiador_id → apoiadores.usuario_id`, `abrigo_id → abrigos.usuario_id`, `necessidade_id → necessidades.id` (nullable) | RF-31, RF-32 |
| `pontuacoes_apoiador` | `id` | `apoiador_id → apoiadores.usuario_id` | UNIQUE(`apoiador_id`,`mes_referencia`) — RF-33 |
| `notificacoes` | `id` | `usuario_id → usuarios.id` | RF-36 |
| `denuncias` | `id` | `denunciante_id → usuarios.id`, `animal_id → animais.id`, `resolvido_por_id → usuarios.id` | RF-41 |
| `logs_auditoria` | `id` | `usuario_id → usuarios.id` | RF-39 |

## Normalização

O modelo está em 3FN: nenhuma coluna não-chave depende de outra coluna
não-chave (ex.: `pontuacoes_apoiador` é uma tabela de cache separada, não
colunas de "pontos" espalhadas em `apoiadores`, justamente para não misturar
um dado derivado/recalculável com o dado de cadastro). A única quebra
deliberada de integridade referencial estrita é a de `fotos.entidade_id`,
documentada na seção 3.1 do MER.

## Índices além das chaves

- `ix_fotos_entidade` em `fotos (entidade_tipo, entidade_id)` — toda leitura de fotos de um animal/perdido/avistamento filtra por essas duas colunas.
- Índices de geolocalização (busca por raio no mapa, RF-07 a RF-11) ficam para quando o volume justificar — Supabase já tem PostGIS disponível se for necessário migrar `latitude`/`longitude` para um tipo `geography`. Ponto em aberto, não bloqueia a Sprint 2.
