# 7. Projeto estruturado no GitHub

Repositório: **https://github.com/Equipe-BuscaPet** _(link a confirmar pelo
Scrum Master — completar com a URL exata do repositório do projeto dentro da
organização antes de enviar o PDF final)_.

## Estrutura entregue nesta Sprint

```
buscapet/
  api/                    backend FastAPI — models, config, esqueleto de rotas, testes, Alembic
  nucleo-opencl/          serviço C/OpenCL — contrato de API definido, Dockerfile com PoCL, implementação na Sprint 3
  frontend/               a estruturar por quem assumir a interface
  docs/                   escopo, plano de sprints, fluxos de tela, notas técnicas e as entregas desta Sprint 2
  docker-compose.yml      orquestra os 5 serviços locais (frontend, api, nucleo-opencl, db, redis)
  .github/workflows/ci.yml   lint (ruff) + testes (pytest) a cada Pull Request
  CLAUDE.md               contexto do projeto para quem usa IA no desenvolvimento
  README.md
```

## Checklist de entrega (item 7 do roteiro)

- [x] Estrutura inicial de pastas
- [x] `README.md` com descrição do projeto
- [x] Modelos de banco, migration inicial e DDL versionados
- [x] Workflow de CI configurado
- [ ] Primeiro commit de cada integrante — **pendente**: fazer localmente e dar push (`git init`, `git add`, `git commit`, `git remote add origin <url>`, `git push -u origin main`) antes do prazo
- [ ] Repositório criado dentro da organização `Equipe-BuscaPet` no GitHub, se ainda não existir
- [ ] Link definitivo do repositório inserido neste documento antes de gerar o PDF final

## Nota sobre o ambiente de preparação

Este material foi montado localmente (sem `gh` autenticado nem Docker
disponíveis no ambiente de geração), então o `git init` e o push para o
GitHub precisam ser feitos por um integrante com acesso configurado. Os
arquivos já estão prontos em disco, faltando só a etapa de versionamento e
envio.
