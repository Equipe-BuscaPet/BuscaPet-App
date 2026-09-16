# Plano de Sprints — Equipe de 3 Pessoas

Planejamento detalhado do desenvolvimento, a partir da primeira entrega já realizada até a entrega final em 05/12/2026. Formato pensado para virar Issues no GitHub Projects — cada item de "Tarefas da semana" é uma Issue.

---

## 0. Como este plano foi montado

**Ponto de partida:** hoje é 04/09/2026. O documento de definição do projeto já foi entregue. Faltam 13 semanas até 05/12.

**Mudança em relação aos documentos anteriores:** o guia técnico e o documento de definição foram redigidos assumindo 5 papéis. Com 3 pessoas, várias funções precisam se sobrepor na mesma pessoa. Este plano substitui a divisão anterior.

**Papéis fixos** — o que cada pessoa carrega do início ao fim:

| Pessoa | Papel principal | Também responde por |
|---|---|---|
| **P1 — Nivaldo** | Banco de dados e documentação | Núcleo OpenCL (dono) |
| **P2** | Backend e integração | DevOps/CI, apoio ao núcleo em pareamento |
| **P3** | Frontend | UX, roteiro dos vídeos finais |

**A regra sobre o núcleo:** ele nunca deve ter dono único trabalhando sozinho no momento crítico de implementação — kernel OpenCL falha de forma silenciosa, e uma pessoa travada sozinha para o projeto inteiro. Com 3 pessoas, a solução não é uma dupla fixa o semestre todo — isso deixaria a terceira pessoa sobrecarregada com tudo o mais. A solução é **concentrar o núcleo em uma janela de 3 semanas (Sprint 3, semanas 5 a 7)**, com P1 e P2 pareados em tempo integral nesse período, enquanto P3 segue sozinha no frontend com dados simulados — o que funciona porque o contrato da API já foi fechado na Sprint 1.

**Convenção de nomenclatura das tarefas:** cada tarefa referencia o RF do documento de definição (RF-01 a RF-41) e, quando aplicável, o pacote técnico (P0.1 a P6.5) do guia técnico. Ao criar a Issue no GitHub, usar esse identificador no título — ex.: `RF-22 — Busca por similaridade visual`.

---

## 1. Visão geral das sprints

| Sprint | Semanas | Período | Foco |
|---|---|---|---|
| 1 | 1–2 | 08/09 – 20/09 | Contratos, ambiente, spike OpenCL |
| 2 | 3–4 | 21/09 – 04/10 | Autenticação, abrigos, animais, mapa |
| 3 | 5–7 | 05/10 – 25/10 | **Núcleo computacional** (janela crítica) |
| 4 | 8–9 | 26/10 – 08/11 | Reencontro completo + benchmark final |
| 5 | 10–11 | 09/11 – 22/11 | Doações, ranking, capacitação no abrigo |
| 6 | 12–13 | 23/11 – 05/12 | Congelamento, testes, vídeos, entrega |

**Congelamento de escopo: 23/11.** A partir dali, só correção de defeito — nenhuma funcionalidade nova entra.

---

## 2. Sprint 1 — Contratos, ambiente e spike OpenCL

**Objetivo da sprint:** ninguém começa a codar funcionalidade antes do contrato existir. Esta sprint entrega a base sobre a qual todo o resto se apoia.

### Semana 1 — 08/09 a 13/09

| Pessoa | Tarefas |
|---|---|
| **P1** | Modelagem completa do banco (DER) — todas as entidades do escopo; escrever as migrations iniciais em Alembic; pesquisar instalação do POCL nas três máquinas |
| **P2** | Criar a Organization e o repositório no GitHub (estrutura definida no guia técnico); `docker-compose.yml` com os 5 serviços; esqueleto do FastAPI com healthcheck; workflow de CI com lint (`ruff`) |
| **P3** | Escrever o contrato OpenAPI em conjunto com P2 (rotas, schemas, contratos de entrada/saída); protótipo no Figma das telas principais: mapa, perfil do abrigo, detalhe do animal |

**Reunião de sexta:** revisão do contrato da API fechado — depois desta reunião, o contrato só muda por decisão explícita registrada, não por ajuste silencioso.

### Semana 2 — 14/09 a 20/09

| Pessoa | Tarefas |
|---|---|
| **Todos** | **Spike de OpenCL** — kernel trivial (soma de vetores) rodando via PoCL na máquina dos três, com tempo de kernel medido separado do tempo de transferência. Critério de sucesso: os três executam e o resultado bate com a versão em CPU pura |
| **P1** | Fora do spike: continuar migrations, escrever o gerador de dados de teste (abrigos, animais e fotos fictícias) |
| **P2** | Fora do spike: endpoints esqueleto de cadastro/login (sem regra de negócio completa ainda); CI com os primeiros testes automatizados rodando |
| **P3** | Fora do spike: telas estáticas conectadas ao contrato com dados simulados — layout do mapa e dos cartões de animal, sem backend real ainda |

> **Se o spike falhar em alguma máquina até quinta-feira desta semana**, isso vira a prioridade de sexta-feira — nada mais avança sem essa confirmação.

**Gate de saída da Sprint 1:**
- [ ] `docker compose up` sobe sem erro nas três máquinas
- [ ] Contrato OpenAPI fechado e versionado em `/docs`
- [ ] Kernel OpenCL executando via PoCL nas três máquinas
- [ ] Banco com schema aplicado e populado com dados de teste

---

## 3. Sprint 2 — Autenticação, abrigos, animais, mapa

**Objetivo da sprint:** um visitante consegue navegar pelo mapa e ver o perfil de um abrigo real; um usuário consegue se cadastrar e logar.

### Semana 3 — 21/09 a 27/09

| Pessoa | Tarefas |
|---|---|
| **P2** | RF-01 cadastro com 3 tipos de conta · RF-02 login único com identificação por e-mail · RF-03 middleware de controle de acesso por perfil |
| **P1** | RF-12 CRUD de abrigo (backend) · RF-06 fluxo de validação do cadastro pelo admin (versão simples) |
| **P3** | RF-07/08/09 — mapa com camadas alternáveis e lista lateral sincronizada, ainda com dados simulados |

### Semana 4 — 28/09 a 04/10

| Pessoa | Tarefas |
|---|---|
| **P2** | RF-04 navegação liberada para visitante · RF-05 recuperação de senha · testes automatizados do módulo de autenticação |
| **P1** | RF-17 CRUD de animal com múltiplas fotos · RF-18 status do animal e fila de interessados · RF-14 filtros de busca dentro do abrigo |
| **P3** | RF-12/13 perfil do abrigo e grade de animais, agora plugados no backend real · RF-15 detalhe do animal com galeria · RF-16 botão de WhatsApp com registro de interesse |

**Gate de saída da Sprint 2:**
- [ ] Cadastro e login funcionando para os três tipos de conta
- [ ] Visitante navega sem login (mapa, abrigos, animais)
- [ ] Fluxo completo: mapa → perfil do abrigo → detalhe do animal → contato por WhatsApp, com dados reais do banco

---

## 4. Sprint 3 — Núcleo computacional (janela crítica, 3 semanas)

**Esta é a sprint que decide o projeto.** P1 e P2 ficam pareados em tempo integral nela. P3 segue sozinha no frontend — o contrato já fechado na Sprint 1 torna isso possível sem bloqueio.

### Semana 5 — 05/10 a 11/10

| Pessoa | Tarefas |
|---|---|
| **P1** (dono) | Extração de descritores em C sequencial — histograma de cor, textura, proporções. Testes de referência com imagens conhecidas |
| **P2** (apoio parcial) | Estrutura do serviço `/nucleo-opencl` (API HTTP enxuta `/comparar`); RF-19/20 — CRUD de registro de animal perdido e de avistamento (sem chamar o núcleo ainda) |
| **P3** | RF-19/20 (frontend) — telas "Perdi meu animal" e "Encontrei um animal", com dados simulados no lugar da resposta do núcleo |

### Semana 6 — 12/10 a 18/10

| Pessoa | Tarefas |
|---|---|
| **P1 + P2** | **Pareados em tempo integral.** Kernels OpenCL de pré-processamento e de extração de descritores. Teste de equivalência obrigatório a cada kernel: a saída paralela precisa bater com a sequencial antes de seguir para o próximo |
| **P3** | Telas de apresentação dos resultados de busca (grade de candidatos ordenados por similaridade), Minha Conta — ainda com dados simulados |

> Nesta semana o backend fica sem novas funcionalidades além do núcleo — é o custo aceito da concentração. Recuperado nas semanas seguintes.

### Semana 7 — 19/10 a 25/10

| Pessoa | Tarefas |
|---|---|
| **P1** | Kernel de comparação em massa; binding do núcleo com o serviço HTTP |
| **P2** | Backend chamando o serviço do núcleo via `httpx`; RF-21/22/23 — extração de descritores automática no cadastro, busca por similaridade com filtros prévios, resultados ordenados |
| **P3** | Conecta as telas de resultado à API real; primeiros testes de ponta a ponta do fluxo de busca |

**Gate de saída da Sprint 3 (não negociável):**
- [ ] Upload de foto → resultado de candidatos funcionando ponta a ponta
- [ ] Teste de equivalência sequencial × paralelo passando para todos os kernels
- [ ] Primeira medição de speedup registrada, mesmo que preliminar

---

## 5. Sprint 4 — Reencontro completo e benchmark final

**Objetivo da sprint:** o ciclo de reencontro fica completo — monitoramento contínuo, alerta automático ao abrigo, benchmark documentado.

### Semana 8 — 26/10 a 01/11

| Pessoa | Tarefas |
|---|---|
| **P2** | RF-24 busca salva com monitoramento contínuo (fila RQ/Redis) · RF-25 comparação em lote de cada novo registro contra as buscas ativas |
| **P1** | Curva de escala do benchmark (N = 10, 100, 1.000, 10.000) · medição do overhead de transferência host↔device |
| **P3** | Notificações na interface (sino, lista de alertas) · tela de buscas salvas em Minha Conta |

### Semana 9 — 02/11 a 08/11

| Pessoa | Tarefas |
|---|---|
| **P2** | RF-26 alerta automático ao abrigo · RF-27 busca inversa (quem encontrou compara contra os perdidos) · RF-28 marcação de caso resolvido |
| **P1** | RF-29 modo de comparação com/sem OpenCL consolidado; suite de benchmark em `/bench` com resultados em CSV e gráficos; redação da justificativa via Lei de Amdahl |
| **P3** | Polish do fluxo completo de reencontro; primeira rodada de teste de usabilidade interna com os três |

**Gate de saída da Sprint 4:**
- [ ] RF-19 a RF-29 completos
- [ ] Benchmark com curva de escala documentado e versionado em `/bench`
- [ ] Alerta automático ao abrigo funcionando de ponta a ponta

---

## 6. Sprint 5 — Doações, ranking e capacitação

**Objetivo da sprint:** módulo de doações completo, e a etapa de extensão — capacitação da instituição parceira — realizada e registrada.

### Semana 10 — 09/11 a 15/11

| Pessoa | Tarefas |
|---|---|
| **P2** | RF-30 publicação de necessidades · RF-31/32 registro e confirmação de doação |
| **P1** | RF-33 cálculo de pontuação e ranking por categoria · RF-34 perfil público do apoiador |
| **P3** | Telas "Quem apoia", mural de necessidades, perfil do apoiador |
| **Todos** | **Oficina de capacitação com a instituição parceira** — data a fixar nesta semana. Registro fotográfico e ata da atividade para a documentação de extensão |

### Semana 11 — 16/11 a 22/11

| Pessoa | Tarefas |
|---|---|
| **P2** | RF-38 painel administrativo · RF-06 validação de abrigo (versão completa) · RF-39 log de auditoria |
| **P1** | RF-40 relatórios do abrigo (adoções, tempo médio, doações) · ajustes de índices e performance do banco |
| **P3** | RF-41 denúncia de anúncio suspeito · revisão de responsividade em todas as telas |

**Gate de saída da Sprint 5:**
- [ ] Todos os RF de prioridade Alta implementados
- [ ] Oficina de capacitação realizada e documentada
- [ ] Painel administrativo funcional

---

## 7. Sprint 6 — Congelamento, testes, vídeos e entrega

**23/11 — congelamento de escopo.** A partir daqui, nenhuma tarefa nova de funcionalidade entra no board. Só correção de defeito.

### Semana 12 — 23/11 a 29/11

| Pessoa | Tarefas |
|---|---|
| **P1** | Documentação técnica final — README, ADRs consolidados, instruções de execução |
| **P2** | Deploy nos serviços gratuitos (Vercel, Render, Supabase); checklist de reativação testado; hardening (validação de entrada, revisão de permissões) |
| **P3** | Roteiro do vídeo horizontal e do vídeo vertical; seed de demonstração com dados realistas para a gravação |
| **Todos** | Cobertura de testes nas regras que ainda não têm; correção dos defeitos encontrados |

### Semana 13 — 30/11 a 05/12

| Dia | Atividade |
|---|---|
| 30/11 – 01/12 | Gravação do vídeo horizontal (bloco a bloco, não em uma tomada só) |
| 02/12 | Gravação e edição do vídeo vertical; publicação no Instagram marcando os professores |
| 03/12 | Ensaio da apresentação com perguntas difíceis simuladas |
| 04/12 | Revisão final, tag de release no GitHub, checklist de conformidade completo |
| **05/12** | **Entrega** |

**Gate final:**
- [ ] Sistema estável em produção (mesmo que na hospedagem gratuita, só para demo)
- [ ] Dois vídeos publicados
- [ ] Documentação completa em `/docs`
- [ ] Checklist de conformidade das três disciplinas revisado

---

## 8. O que cortar primeiro, se o prazo apertar

Com 3 pessoas, a margem de segurança é menor do que em uma equipe de 5. Se alguma sprint atrasar, cortar nesta ordem — nunca na ordem inversa:

| Ordem de corte | Item | Por quê pode esperar |
|---|---|---|
| 1º | RF-41 denúncia de anúncio | Prioridade Média, sem dependência de outros módulos |
| 2º | RF-40 relatórios do abrigo | Prioridade Média, não bloqueia nenhum outro fluxo |
| 3º | RF-28 marcação de caso resolvido | Cosmético — o reencontro funciona sem isso |
| 4º | RF-33 regra de regularidade no ranking | Fica só o ranking por volume, mais simples de calcular |
| 5º | RF-05 recuperação de senha | Contornável manualmente durante a demonstração |

**Nunca cortar:** RF-19 a RF-29 (núcleo e reencontro) e o benchmark do RF-29. São o que sustenta Tópicos Avançados — sem eles, não há projeto a defender nessa disciplina, independentemente de quanto o resto esteja completo.

---

## 9. Ritmo semanal da equipe

Com 3 pessoas, reuniões longas custam proporcionalmente mais tempo de projeto. Manter curtas.

| Momento | Duração | Conteúdo |
|---|---|---|
| Segunda | 15 min | O que cada um faz esta semana, direto das tabelas acima |
| Quinta | 10 min | Bloqueios — alguém travado precisa de ajuda ainda hoje, não na sexta |
| Sexta | 20 min | Demo rápida do que foi feito + atualização do board no GitHub Projects |

**Definition of Done** de qualquer tarefa: código na branch principal via Pull Request revisado por ao menos um dos outros dois, testes passando no CI, demonstrável funcionando.
