# BuscaPet — guia da API

> Gerado a partir do código por `python -m app.scripts.gerar_doc_api` (pasta `api/`). Não edite à mão: mude a rota
> (a descrição é a docstring da função) e gere de novo. O teste `tests/test_doc_api.py` acusa se ficar desatualizado.

A API do BuscaPet foi **desenvolvida pela equipe** (FastAPI, Python 3.12) e é a única API de dados que a interface
consome. São **77 rotas**. Ela, por sua vez, chama o **núcleo OpenCL** (serviço próprio, em C) para comparar
fotos; o contrato do núcleo está em [`nucleo-opencl/README.md`](../nucleo-opencl/README.md).

## Como usar

- **Endereço:** `http://localhost:8000` no desenvolvimento.
- **Documentação interativa:** `/docs` (Swagger, dá para testar cada rota) e `/redoc`. O contrato bruto fica em
  `/openapi.json`.
- **Formato:** JSON em UTF-8. Datas e horas em ISO 8601 (UTC); datas "do dia" como `AAAA-MM-DD`. **Dinheiro em
  centavos** (`valor_centavos: 5000` = R$ 50,00), para não haver erro de arredondamento.
- **Erros:** sempre com `detail`. Nos erros de regra, `detail` é uma frase pronta para mostrar à pessoa
  (`{"detail": "Esta necessidade já foi atendida."}`); nos de validação (`422`), é a lista de campos com problema.

### Autenticação

1. `POST /auth/login` com **formulário** (`username` = e-mail, `password` = senha). A resposta traz `access_token`.
2. Nas rotas protegidas, envie o cabeçalho `Authorization: Bearer <access_token>`. O token vale **24 horas**.
3. No Swagger, o botão **Authorize** faz isso: use o e-mail e a senha de uma conta.

```bash
curl -X POST http://localhost:8000/auth/login -d "username=maria@exemplo.com" -d "password=Senha1234!"
# {"access_token": "eyJhbGciOi...", "token_type": "bearer", "usuario": {...}}
```

### Perfis e permissões

Login único; o tipo de conta é escolhido no cadastro. A coluna **Quem pode usar** de cada rota diz quem passa:

| Perfil | Quem é |
|---|---|
| público | qualquer pessoa, sem login |
| público (logado vê mais) | sem login funciona; logado, a resposta traz mais (ex.: o local exato do próprio registro) |
| qualquer conta logada | tutor, abrigo, apoiador ou admin |
| `tutor` | pessoa que adota, procura o animal perdido e doa como pessoa física |
| `abrigo` | abrigo ou protetor; publicar necessidades e receber doações exige o selo **Verificado** |
| `apoiador` | empresa (petshop, clínica, distribuidora) que doa e aparece no ranking da categoria |
| `admin` | administração do sistema (não há cadastro público de admin) |

Sem login numa rota protegida: `401`. Com login, mas perfil sem acesso: `403`.

### Códigos de resposta

| Código | Quando |
|---|---|
| `200` / `201` / `204` | deu certo (consulta / criado / sem corpo) |
| `400` | pedido inválido (ex.: senha atual errada, link de senha vencido) |
| `401` | sem login ou token vencido |
| `403` | o perfil não pode fazer isso (ou falta o selo Verificado) |
| `404` | não existe, ou não é seu |
| `409` | conflito com o estado atual (ex.: doação já respondida, e-mail já cadastrado) |
| `422` | dados inválidos (campo faltando, formato errado, regra de negócio dos dados) |
| `503` | o núcleo OpenCL não respondeu |

### Exemplos

```bash
API=http://localhost:8000
TOKEN=$(curl -s -X POST $API/auth/login -d "username=maria@exemplo.com" -d "password=Senha1234!" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Catálogo: gatos pequenos disponíveis
curl "$API/animais?especie=gato&porte=pequeno"

# Interesse de adoção (tutor)
curl -X POST "$API/animais/1/interesses" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"mensagem": "Moro em casa com quintal."}'

# Doação em dinheiro: depois do PIX para a chave do abrigo, informar o valor (R$ 50,00)
curl -X POST "$API/doacoes" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"abrigo_id": 2, "valor_centavos": 5000}'

# Busca por semelhança a partir de um animal perdido
curl "$API/reencontro/semelhantes?origem=perdido&id=1&raio_km=20" -H "Authorization: Bearer $TOKEN"
```

## Sumário

- [Autenticação](#autenticação) (5)
- [Contas](#contas) (4)
- [Animais](#animais) (9)
- [Interesses](#interesses) (5)
- [Abrigos](#abrigos) (2)
- [Reencontro](#reencontro) (13)
- [Doações](#doações) (10)
- [Apoiadores](#apoiadores) (3)
- [Notificações](#notificações) (4)
- [Denúncias](#denúncias) (3)
- [Administração](#administração) (2)
- [Relatórios](#relatórios) (12)
- [Núcleo OpenCL](#núcleo-opencl) (3)
- [Infra](#infra) (2)

---

## Autenticação

Cadastro, login e recuperação de senha. O login devolve o token usado nas outras rotas.

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `POST` | `/auth/cadastro` | público | Cria a conta e o perfil do tipo escolhido (tutor, abrigo ou apoiador) na |
| `POST` | `/auth/login` | público | Entra com e-mail e senha e devolve o token de acesso (`access_token`, vale 24 horas) e os dados da conta |
| `GET` | `/auth/eu` | qualquer conta logada | Dados da conta logada (mesmo conteúdo de `GET /usuarios/eu`), usado pela interface ao abrir |
| `POST` | `/auth/esqueci-senha` | público | Sempre a mesma resposta, exista ou não a conta: não revela quais e-mails estão cadastrados |
| `POST` | `/auth/redefinir-senha` | público | Define a senha nova com o token do link enviado por e-mail (vale 30 minutos e uma vez só) |

### `POST /auth/cadastro`

Cria a conta e o perfil do tipo escolhido (tutor, abrigo ou apoiador) na
mesma transação: ou grava tudo, ou nada.

- **Quem pode usar:** público
- **Corpo (JSON):** um de três formatos

  Um destes formatos, escolhido pelo campo `tipo_conta`: `CadastroTutor`, `CadastroAbrigo`, `CadastroApoiador`.

- **Resposta:** `201` (criado) — [`UsuarioOut`](#usuarioout)
- **Erros possíveis:** `409` conflito com o estado atual, `422` dados inválidos


### `POST /auth/login`

Entra com e-mail e senha e devolve o token de acesso (`access_token`, vale 24 horas) e os dados da conta.
Formulário no padrão OAuth2 (`username` = e-mail, `password` = senha), para o botão "Authorize" do Swagger funcionar.

- **Quem pode usar:** público
- **Corpo (formulário (x-www-form-urlencoded)):** `Body_login_auth_login_post`

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `grant_type` | texto (ou null) | não |  |
  | `username` | texto | sim |  |
  | `password` | texto | sim |  |
  | `scope` | texto | não | padrão `` |
  | `client_id` | texto (ou null) | não |  |
  | `client_secret` | texto (ou null) | não |  |

- **Resposta:** `200` (OK) — [`TokenOut`](#tokenout)
- **Erros possíveis:** `401` não autenticado, `422` dados inválidos


### `GET /auth/eu`

Dados da conta logada (mesmo conteúdo de `GET /usuarios/eu`), usado pela interface ao abrir.

- **Quem pode usar:** qualquer conta logada
- **Resposta:** `200` (OK) — [`UsuarioOut`](#usuarioout)
- **Erros possíveis:** `401` não autenticado


### `POST /auth/esqueci-senha`

Sempre a mesma resposta, exista ou não a conta: não revela quais e-mails estão cadastrados.

- **Quem pode usar:** público
- **Corpo (JSON):** [`EsqueciSenha`](#esquecisenha)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `email` | e-mail | sim |  |

- **Resposta:** `202` () — objeto
- **Erros possíveis:** `422` dados inválidos


### `POST /auth/redefinir-senha`

Define a senha nova com o token do link enviado por e-mail (vale 30 minutos e uma vez só).

- **Quem pode usar:** público
- **Corpo (JSON):** [`RedefinirSenha`](#redefinirsenha)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `token` | texto | sim | mín. 10 caracteres |
  | `senha_nova` | texto | sim | mín. 8 caracteres |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `400` pedido inválido, `422` dados inválidos


## Contas

A própria conta: consultar, editar o perfil, trocar a senha e excluir.

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/usuarios/eu` | qualquer conta logada | Dados da conta logada, com o perfil do tipo de conta (tutor, abrigo ou apoiador) |
| `PATCH` | `/usuarios/eu` | qualquer conta logada | Atualiza só os campos enviados |
| `POST` | `/usuarios/eu/senha` | qualquer conta logada | Troca a senha, conferindo a senha atual |
| `DELETE` | `/usuarios/eu` | qualquer conta logada | Exclusão lógica: a conta é desativada (ativo=false) e deixa de logar, mas a |

### `GET /usuarios/eu`

Dados da conta logada, com o perfil do tipo de conta (tutor, abrigo ou apoiador).

- **Quem pode usar:** qualquer conta logada
- **Resposta:** `200` (OK) — [`UsuarioOut`](#usuarioout)
- **Erros possíveis:** `401` não autenticado


### `PATCH /usuarios/eu`

Atualiza só os campos enviados. Cada tipo de conta tem os seus campos; campo de outro tipo é recusado (422).

- **Quem pode usar:** qualquer conta logada
- **Corpo (JSON):** [`AtualizaUsuario`](#atualizausuario)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `nome` | texto (ou null) | não | mín. 2 caracteres; máx. 150 caracteres |
  | `telefone` | texto (ou null) | não | máx. 20 caracteres |
  | `cidade` | texto (ou null) | não | máx. 120 caracteres |
  | `nome_abrigo` | texto (ou null) | não | mín. 2 caracteres; máx. 150 caracteres |
  | `endereco` | texto (ou null) | não | mín. 3 caracteres; máx. 255 caracteres |
  | `latitude` | número (ou null) | não | ≥ -90; ≤ 90 |
  | `longitude` | número (ou null) | não | ≥ -180; ≤ 180 |
  | `horario_funcionamento` | texto (ou null) | não | máx. 255 caracteres |
  | `descricao` | texto (ou null) | não | máx. 2000 caracteres |
  | `chave_doacao_financeira` | texto (ou null) | não | máx. 140 caracteres |
  | `meta_mensal_centavos` | inteiro (ou null) | não | ≥ 100; ≤ 100000000 |
  | `meta_mensal_descricao` | texto (ou null) | não | máx. 500 caracteres |
  | `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` (ou null) | não |  |

- **Resposta:** `200` (OK) — [`UsuarioOut`](#usuarioout)
- **Erros possíveis:** `401` não autenticado, `422` dados inválidos


### `POST /usuarios/eu/senha`

Troca a senha, conferindo a senha atual.

- **Quem pode usar:** qualquer conta logada
- **Corpo (JSON):** [`TrocaSenha`](#trocasenha)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `senha_atual` | texto | sim |  |
  | `senha_nova` | texto | sim | mín. 8 caracteres |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `400` pedido inválido, `401` não autenticado, `422` dados inválidos


### `DELETE /usuarios/eu`

Exclusão lógica: a conta é desativada (ativo=false) e deixa de logar, mas a
linha permanece. Doações, interesses e logs apontam para o usuário; apagar de
verdade quebraria esse histórico.

- **Quem pode usar:** qualquer conta logada
- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


## Animais

Animais para adoção (RF-13 a RF-18): catálogo com filtros, cadastro pelo abrigo e fotos.

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `POST` | `/animais` | abrigo | O abrigo cadastra um animal para adoção (RF-13) |
| `GET` | `/animais` | público | Catálogo público, mais recentes primeiro |
| `GET` | `/animais/meus` | abrigo | Todos os animais do abrigo logado, em qualquer status |
| `GET` | `/animais/{animal_id}` | público (logado vê mais) | Ficha do animal |
| `PATCH` | `/animais/{animal_id}` | abrigo | O abrigo dono edita o animal; só os campos enviados mudam |
| `DELETE` | `/animais/{animal_id}` | abrigo, admin | Exclusão de verdade (a linha some) |
| `POST` | `/animais/{animal_id}/fotos` | abrigo | Acrescenta fotos ao animal |
| `DELETE` | `/animais/{animal_id}/fotos/{foto_id}` | abrigo | O abrigo dono remove uma foto do animal (e o descritor visual dela) |
| `PATCH` | `/animais/{animal_id}/fotos/{foto_id}/capa` | abrigo | A foto escolhida passa a ser a primeira (a capa do catálogo); as outras mantêm a ordem |

### `POST /animais`

O abrigo cadastra um animal para adoção (RF-13). As fotos vão depois, em `POST /animais/{id}/fotos`.

- **Quem pode usar:** abrigo
- **Corpo (JSON):** [`AnimalCreate`](#animalcreate)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `nome` | texto | sim | mín. 1 caracteres; máx. 120 caracteres |
  | `especie` | `cao` \| `gato` \| `outro` | sim |  |
  | `raca_aproximada` | texto (ou null) | não | máx. 120 caracteres |
  | `porte` | `pequeno` \| `medio` \| `grande` | sim |  |
  | `idade_estimada_meses` | inteiro (ou null) | não | ≥ 0; ≤ 600 |
  | `sexo` | `macho` \| `femea` \| `indefinido` | sim |  |
  | `castrado` | sim/não | não | padrão `False` |
  | `vacinado` | sim/não | não | padrão `False` |
  | `vermifugado` | sim/não | não | padrão `False` |
  | `temperamento` | texto (ou null) | não | máx. 500 caracteres |
  | `convivencia_criancas` | sim/não (ou null) | não |  |
  | `convivencia_outros_animais` | sim/não (ou null) | não |  |
  | `historia_resgate` | texto (ou null) | não | máx. 2000 caracteres |
  | `data_entrada` | data (AAAA-MM-DD) (ou null) | não |  |
  | `condicao_chegada` | texto (ou null) | não | máx. 500 caracteres |

- **Resposta:** `201` (criado) — [`AnimalOut`](#animalout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /animais`

Catálogo público, mais recentes primeiro. Por padrão só mostra animais
disponíveis; passe `status` para ver outros.

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `especie` | consulta (?) | `cao` \| `gato` \| `outro` (ou null) | não |  |
  | `porte` | consulta (?) | texto (ou null) | não | pequeno, medio ou grande |
  | `status` | consulta (?) | `disponivel` \| `em_processo` \| `adotado` \| `obito` \| `transferido` (ou null) | não | padrão `disponivel` |
  | `abrigo_id` | consulta (?) | inteiro (ou null) | não |  |
  | `busca` | consulta (?) | texto (ou null) | não | máx. 100 caracteres; Trecho do nome ou da raça |
  | `sexo` | consulta (?) | `macho` \| `femea` \| `indefinido` (ou null) | não |  |
  | `idade` | consulta (?) | `filhote` \| `adulto` \| `idoso` (ou null) | não | filhote < 1 ano; idoso a partir de 8 anos |
  | `castrado` | consulta (?) | sim/não (ou null) | não |  |
  | `vacinado` | consulta (?) | sim/não (ou null) | não |  |
  | `convive_criancas` | consulta (?) | sim/não (ou null) | não | true: só quem convive bem com crianças |
  | `convive_animais` | consulta (?) | sim/não (ou null) | não | true: só quem convive bem com outros animais |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `20` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |

- **Resposta:** `200` (OK) — lista de [`AnimalOut`](#animalout)
- **Erros possíveis:** `422` dados inválidos


### `GET /animais/meus`

Todos os animais do abrigo logado, em qualquer status.

- **Quem pode usar:** abrigo
- **Resposta:** `200` (OK) — lista de [`AnimalOut`](#animalout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `GET /animais/{animal_id}`

Ficha do animal. Anúncio removido pela moderação só aparece para o próprio abrigo e para a administração.

- **Quem pode usar:** público (logado vê mais)
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`AnimalOut`](#animalout)
- **Erros possíveis:** `422` dados inválidos


### `PATCH /animais/{animal_id}`

O abrigo dono edita o animal; só os campos enviados mudam.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`AnimalUpdate`](#animalupdate)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `nome` | texto (ou null) | não | mín. 1 caracteres; máx. 120 caracteres |
  | `especie` | `cao` \| `gato` \| `outro` (ou null) | não |  |
  | `raca_aproximada` | texto (ou null) | não | máx. 120 caracteres |
  | `porte` | `pequeno` \| `medio` \| `grande` (ou null) | não |  |
  | `idade_estimada_meses` | inteiro (ou null) | não | ≥ 0; ≤ 600 |
  | `sexo` | `macho` \| `femea` \| `indefinido` (ou null) | não |  |
  | `castrado` | sim/não (ou null) | não |  |
  | `vacinado` | sim/não (ou null) | não |  |
  | `vermifugado` | sim/não (ou null) | não |  |
  | `temperamento` | texto (ou null) | não | máx. 500 caracteres |
  | `convivencia_criancas` | sim/não (ou null) | não |  |
  | `convivencia_outros_animais` | sim/não (ou null) | não |  |
  | `historia_resgate` | texto (ou null) | não | máx. 2000 caracteres |
  | `data_entrada` | data (AAAA-MM-DD) (ou null) | não |  |
  | `condicao_chegada` | texto (ou null) | não | máx. 500 caracteres |
  | `status` | `disponivel` \| `em_processo` \| `adotado` \| `obito` \| `transferido` (ou null) | não |  |

- **Resposta:** `200` (OK) — [`AnimalOut`](#animalout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `DELETE /animais/{animal_id}`

Exclusão de verdade (a linha some). Remove antes o que depende só deste
animal: interesses, fotos, os descritores dessas fotos e as correspondências
do reencontro. Se ainda houver vínculos (ex.: doações), responde 409: nesse
caso o caminho certo é mudar o status para adotado/transferido.

- **Quem pode usar:** abrigo, admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


### `POST /animais/{animal_id}/fotos`

Acrescenta fotos ao animal. Ou entram todas, ou nenhuma (se uma for inválida, nada é gravado).

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |

- **Corpo (formulário com arquivos (multipart)):** `Body_enviar_fotos_animais__animal_id__fotos_post`

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `fotos` | lista de arquivo | sim | De 1 a 5 fotos no total por animal (JPEG, PNG ou WebP) |

- **Resposta:** `201` (criado) — [`AnimalOut`](#animalout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `DELETE /animais/{animal_id}/fotos/{foto_id}`

O abrigo dono remove uma foto do animal (e o descritor visual dela).

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |
  | `foto_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`AnimalOut`](#animalout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `PATCH /animais/{animal_id}/fotos/{foto_id}/capa`

A foto escolhida passa a ser a primeira (a capa do catálogo); as outras mantêm a ordem.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |
  | `foto_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`AnimalOut`](#animalout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


## Interesses

Interesse de adoção (RF-16): o tutor demonstra, o abrigo conversa e decide.

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `POST` | `/animais/{animal_id}/interesses` | tutor | O tutor demonstra interesse em adotar (RF-16); o abrigo é avisado |
| `GET` | `/interesses/meus` | tutor | Interesses do tutor, com a situação de cada um e o contato do abrigo |
| `GET` | `/interesses/recebidos` | abrigo | Interesses recebidos pelo abrigo, com os dados do interessado; filtra por situação e por animal |
| `DELETE` | `/interesses/{interesse_id}` | tutor | O tutor desiste enquanto o abrigo não encerrou o interesse; o abrigo é avisado |
| `PATCH` | `/interesses/{interesse_id}` | abrigo | Abrigo: aguardando → em conversa / aprovado / recusado; em conversa → aprovado / recusado |

### `POST /animais/{animal_id}/interesses`

O tutor demonstra interesse em adotar (RF-16); o abrigo é avisado. Um interesse por animal.

- **Quem pode usar:** tutor
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`InteresseCreate`](#interessecreate)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `mensagem` | texto (ou null) | não | máx. 500 caracteres; Apresentação do adotante (opcional) |

- **Resposta:** `201` (criado) — [`InteresseTutorOut`](#interessetutorout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `409` conflito com o estado atual, `422` dados inválidos


### `GET /interesses/meus`

Interesses do tutor, com a situação de cada um e o contato do abrigo.

- **Quem pode usar:** tutor
- **Resposta:** `200` (OK) — lista de [`InteresseTutorOut`](#interessetutorout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `GET /interesses/recebidos`

Interesses recebidos pelo abrigo, com os dados do interessado; filtra por situação e por animal.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `status` | consulta (?) | `aguardando` \| `em_conversa` \| `aprovado` \| `recusado` (ou null) | não |  |
  | `animal_id` | consulta (?) | inteiro (ou null) | não |  |

- **Resposta:** `200` (OK) — lista de [`InteresseAbrigoOut`](#interesseabrigoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `DELETE /interesses/{interesse_id}`

O tutor desiste enquanto o abrigo não encerrou o interesse; o abrigo é avisado.

- **Quem pode usar:** tutor
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `interesse_id` | caminho | inteiro | sim |  |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


### `PATCH /interesses/{interesse_id}`

Abrigo: aguardando → em conversa / aprovado / recusado; em conversa → aprovado / recusado.
Aprovar muda o animal para "em processo de adoção".

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `interesse_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`DecisaoInteresse`](#decisaointeresse)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `status` | `em_conversa` \| `aprovado` \| `recusado` | sim |  |

- **Resposta:** `200` (OK) — [`InteresseAbrigoOut`](#interesseabrigoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


## Abrigos

Abrigos no mapa e o perfil público, que junta animais, necessidades, meta do mês e apoiadores (RF-12).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/abrigos` | público | Abrigos ativos para o mapa, com a quantidade de animais disponíveis |
| `GET` | `/abrigos/{abrigo_id}` | público | Perfil público (RF-12): integra os três módulos — animais para adoção, necessidades em aberto e quem apoia |

### `GET /abrigos`

Abrigos ativos para o mapa, com a quantidade de animais disponíveis. Com `lat`/`lng`, ordena por distância; com `raio_km`, filtra.

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `lat` | consulta (?) | número (ou null) | não | ≥ -90; ≤ 90; Latitude de quem consulta |
  | `lng` | consulta (?) | número (ou null) | não | ≥ -180; ≤ 180; Longitude de quem consulta |
  | `raio_km` | consulta (?) | número (ou null) | não | > 0; ≤ 2000; Só abrigos até esta distância |

- **Resposta:** `200` (OK) — lista de [`AbrigoMapaOut`](#abrigomapaout)
- **Erros possíveis:** `422` dados inválidos


### `GET /abrigos/{abrigo_id}`

Perfil público (RF-12): integra os três módulos — animais para adoção, necessidades em aberto e quem apoia.
A chave de doação e as necessidades só aparecem com o selo Verificado (risco de golpe).

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `abrigo_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`AbrigoPerfilOut`](#abrigoperfilout)
- **Erros possíveis:** `404` não encontrado, `422` dados inválidos


## Reencontro

Animais perdidos e avistados (RF-19 a RF-28), busca por semelhança visual com o núcleo OpenCL e as fotos.

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `POST` | `/perdidos` | tutor | Formulário multipart: características, local (latitude/longitude), data e de 1 a 5 fotos (campo `fotos`) |
| `GET` | `/perdidos` | público | Animais perdidos ainda não resolvidos, mais recentes primeiro (ou mais perto, se informar a posição) |
| `GET` | `/perdidos/meus` | tutor | Os registros do próprio tutor, inclusive os resolvidos, com a localização exata que ele marcou |
| `PATCH` | `/perdidos/{perdido_id}/resolvido` | tutor | RF-28: o tutor encontrou o animal |
| `GET` | `/perdidos/{perdido_id}` | público (logado vê mais) | Um registro de animal perdido |
| `DELETE` | `/perdidos/{perdido_id}` | qualquer conta logada | Quem registrou (ou a administração) exclui o registro e as fotos |
| `POST` | `/avistamentos` | qualquer conta logada | Qualquer conta logada registra um animal visto na rua: características, local, data e de 1 a 5 fotos |
| `GET` | `/reencontro/semelhantes` | público | Candidatos ordenados por semelhança visual com as fotos do registro, com origem, distância e data |
| `GET` | `/avistamentos` | público | Avistamentos de animais na rua, mais recentes primeiro; filtra por espécie, porte e raio a partir de uma posição |
| `GET` | `/avistamentos/meus` | qualquer conta logada | Avistamentos registrados pela conta logada, com o local exato |
| `GET` | `/avistamentos/{avistamento_id}` | público (logado vê mais) | Um avistamento |
| `DELETE` | `/avistamentos/{avistamento_id}` | qualquer conta logada | Quem registrou (ou a administração) exclui o avistamento e as fotos |
| `GET` | `/fotos/{nome}` | público | Arquivo da foto (JPEG, sem metadados) |

### `POST /perdidos`

Formulário multipart: características, local (latitude/longitude), data e de 1 a 5 fotos (campo `fotos`).

- **Quem pode usar:** tutor
- **Corpo (formulário com arquivos (multipart)):** [`PerdidoIn`](#perdidoin)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `especie` | `cao` \| `gato` \| `outro` | sim |  |
  | `porte` | `pequeno` \| `medio` \| `grande` | sim |  |
  | `cor_predominante` | texto | sim | mín. 2 caracteres; máx. 60 caracteres |
  | `pelagem` | texto (ou null) | não | máx. 60 caracteres |
  | `sexo` | `macho` \| `femea` \| `indefinido` | não | padrão `indefinido` |
  | `sinais_particulares` | texto (ou null) | não | máx. 500 caracteres |
  | `latitude` | número | sim | ≥ -90; ≤ 90 |
  | `longitude` | número | sim | ≥ -180; ≤ 180 |
  | `fotos` | lista de arquivo (ou null) | não | De 1 a 5 fotos (JPEG, PNG ou WebP) |
  | `raio_busca_km` | número | não | > 0; ≤ 100; padrão `5.0` |
  | `data_desaparecimento` | data (AAAA-MM-DD) | sim |  |

- **Resposta:** `201` (criado) — [`PerdidoOut`](#perdidoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /perdidos`

Animais perdidos ainda não resolvidos, mais recentes primeiro (ou mais perto, se informar a posição).

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `especie` | consulta (?) | `cao` \| `gato` \| `outro` (ou null) | não |  |
  | `porte` | consulta (?) | texto (ou null) | não | pequeno, medio ou grande |
  | `lat` | consulta (?) | número (ou null) | não | ≥ -90; ≤ 90; Latitude de quem consulta |
  | `lng` | consulta (?) | número (ou null) | não | ≥ -180; ≤ 180; Longitude de quem consulta |
  | `raio_km` | consulta (?) | número (ou null) | não | > 0; ≤ 2000; Só registros até esta distância |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `20` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |

- **Resposta:** `200` (OK) — lista de [`PerdidoOut`](#perdidoout)


### `GET /perdidos/meus`

Os registros do próprio tutor, inclusive os resolvidos, com a localização exata que ele marcou.

- **Quem pode usar:** tutor
- **Resposta:** `200` (OK) — lista de [`PerdidoOut`](#perdidoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `PATCH /perdidos/{perdido_id}/resolvido`

RF-28: o tutor encontrou o animal. O caso sai da lista pública e do mapa e para de gerar alertas.

Não tem volta pela interface: se foi engano, o tutor registra a perda de novo.

- **Quem pode usar:** tutor
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `perdido_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`PerdidoOut`](#perdidoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


### `GET /perdidos/{perdido_id}`

Um registro de animal perdido. O local exato só aparece para quem registrou; os outros veem o local aproximado.

- **Quem pode usar:** público (logado vê mais)
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `perdido_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`PerdidoOut`](#perdidoout)
- **Erros possíveis:** `404` não encontrado, `422` dados inválidos


### `DELETE /perdidos/{perdido_id}`

Quem registrou (ou a administração) exclui o registro e as fotos.

- **Quem pode usar:** qualquer conta logada
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `perdido_id` | caminho | inteiro | sim |  |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `404` não encontrado, `422` dados inválidos


### `POST /avistamentos`

Qualquer conta logada registra um animal visto na rua: características, local, data e de 1 a 5 fotos.

- **Quem pode usar:** qualquer conta logada
- **Corpo (formulário com arquivos (multipart)):** [`AvistamentoIn`](#avistamentoin)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `especie` | `cao` \| `gato` \| `outro` | sim |  |
  | `porte` | `pequeno` \| `medio` \| `grande` | sim |  |
  | `cor_predominante` | texto | sim | mín. 2 caracteres; máx. 60 caracteres |
  | `pelagem` | texto (ou null) | não | máx. 60 caracteres |
  | `sexo` | `macho` \| `femea` \| `indefinido` | não | padrão `indefinido` |
  | `sinais_particulares` | texto (ou null) | não | máx. 500 caracteres |
  | `latitude` | número | sim | ≥ -90; ≤ 90 |
  | `longitude` | número | sim | ≥ -180; ≤ 180 |
  | `fotos` | lista de arquivo (ou null) | não | De 1 a 5 fotos (JPEG, PNG ou WebP) |
  | `data_avistamento` | data (AAAA-MM-DD) | sim |  |

- **Resposta:** `201` (criado) — [`AvistamentoOut`](#avistamentoout)
- **Erros possíveis:** `401` não autenticado, `422` dados inválidos


### `GET /reencontro/semelhantes`

Candidatos ordenados por semelhança visual com as fotos do registro, com origem, distância e data.

- `origem=perdido`: quem perdeu compara contra avistamentos (vistos depois do sumiço) e animais dos abrigos.
- `origem=avistamento`: busca inversa, contra os animais perdidos que ainda não foram encontrados.

Filtros prévios (RF-22): mesma espécie e dentro do raio; porte e cor opcionais. `modo=sequencial` faz a mesma
comparação sem OpenCL (modo comparativo do RF-29). Pública, como as listas: só usa dados que já são públicos,
e as distâncias são calculadas sobre os pontos arredondados.

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `origem` | consulta (?) | `perdido` \| `avistamento` | sim |  |
  | `id` | consulta (?) | inteiro | sim |  |
  | `raio_km` | consulta (?) | número (ou null) | não | > 0; ≤ 100; Padrão: o raio do tutor (perdido) ou 10 km |
  | `mesmo_porte` | consulta (?) | sim/não | não | padrão `False` |
  | `mesma_cor` | consulta (?) | sim/não | não | padrão `False` |
  | `modo` | consulta (?) | `opencl` \| `sequencial` | não | padrão `opencl` |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `30` |

- **Resposta:** `200` (OK) — [`SemelhantesOut`](#semelhantesout)
- **Erros possíveis:** `404` não encontrado, `422` dados inválidos


### `GET /avistamentos`

Avistamentos de animais na rua, mais recentes primeiro; filtra por espécie, porte e raio a partir de uma posição.

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `especie` | consulta (?) | `cao` \| `gato` \| `outro` (ou null) | não |  |
  | `porte` | consulta (?) | texto (ou null) | não | pequeno, medio ou grande |
  | `lat` | consulta (?) | número (ou null) | não | ≥ -90; ≤ 90; Latitude de quem consulta |
  | `lng` | consulta (?) | número (ou null) | não | ≥ -180; ≤ 180; Longitude de quem consulta |
  | `raio_km` | consulta (?) | número (ou null) | não | > 0; ≤ 2000; Só registros até esta distância |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `20` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |

- **Resposta:** `200` (OK) — lista de [`AvistamentoOut`](#avistamentoout)


### `GET /avistamentos/meus`

Avistamentos registrados pela conta logada, com o local exato.

- **Quem pode usar:** qualquer conta logada
- **Resposta:** `200` (OK) — lista de [`AvistamentoOut`](#avistamentoout)
- **Erros possíveis:** `401` não autenticado


### `GET /avistamentos/{avistamento_id}`

Um avistamento. O local exato só aparece para quem registrou.

- **Quem pode usar:** público (logado vê mais)
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `avistamento_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`AvistamentoOut`](#avistamentoout)
- **Erros possíveis:** `404` não encontrado, `422` dados inválidos


### `DELETE /avistamentos/{avistamento_id}`

Quem registrou (ou a administração) exclui o avistamento e as fotos.

- **Quem pode usar:** qualquer conta logada
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `avistamento_id` | caminho | inteiro | sim |  |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `404` não encontrado, `422` dados inválidos


### `GET /fotos/{nome}`

Arquivo da foto (JPEG, sem metadados). O nome é aleatório e o conteúdo não muda, por isso fica em cache por 7 dias.

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `nome` | caminho | texto | sim |  |

- **Resposta:** `200` (OK) — JSON (objeto) ou arquivo, conforme a rota
- **Erros possíveis:** `404` não encontrado, `422` dados inválidos


## Doações

Mural de necessidades, doações de itens e em dinheiro (PIX fora da plataforma) e confirmação pelo abrigo (RF-30 a RF-32).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `POST` | `/necessidades` | abrigo | O abrigo verificado publica uma necessidade no mural (RF-30) |
| `GET` | `/necessidades` | público | Mural público de necessidades em aberto (RF-35), mais urgentes primeiro |
| `GET` | `/necessidades/minhas` | abrigo | Todas as do abrigo, abertas primeiro |
| `PATCH` | `/necessidades/{necessidade_id}` | abrigo | O abrigo edita a necessidade, marca como atendida (`status: atendida`) ou reabre |
| `DELETE` | `/necessidades/{necessidade_id}` | abrigo | O abrigo exclui uma necessidade sem doações; com doações registradas, deve marcá-la como atendida (409) |
| `POST` | `/doacoes` | tutor, apoiador | Quem doa se compromete (itens) ou informa o PIX que fez (dinheiro) |
| `GET` | `/doacoes/minhas` | tutor, apoiador | Doações de quem está logado (apoiador ou tutor), com a situação e o contato do abrigo |
| `DELETE` | `/doacoes/{doacao_id}` | tutor, apoiador | Quem doou desiste enquanto o abrigo não respondeu |
| `GET` | `/doacoes/recebidas` | abrigo | Aguardando confirmação primeiro (é o que exige ação), depois as mais recentes |
| `PATCH` | `/doacoes/{doacao_id}` | abrigo | O abrigo confirma (`confirmada`) ou recusa (`recusada`) uma doação, uma vez só (RF-32) |

### `POST /necessidades`

O abrigo verificado publica uma necessidade no mural (RF-30). Sem o selo: 403.

- **Quem pode usar:** abrigo
- **Corpo (JSON):** [`NecessidadeIn`](#necessidadein)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `item` | texto | sim | mín. 2 caracteres; máx. 200 caracteres; Ex.: ração para cão adulto (saco de 15 kg) |
  | `quantidade` | inteiro | sim | ≥ 1; ≤ 10000 |
  | `urgencia` | `baixa` \| `media` \| `alta` | não | padrão `media` |

- **Resposta:** `201` (criado) — [`NecessidadeOut`](#necessidadeout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /necessidades`

Mural público de necessidades em aberto (RF-35), mais urgentes primeiro.

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `urgencia` | consulta (?) | `baixa` \| `media` \| `alta` (ou null) | não |  |
  | `abrigo_id` | consulta (?) | inteiro (ou null) | não |  |
  | `lat` | consulta (?) | número (ou null) | não | ≥ -90; ≤ 90 |
  | `lng` | consulta (?) | número (ou null) | não | ≥ -180; ≤ 180 |
  | `raio_km` | consulta (?) | número (ou null) | não | > 0; ≤ 2000 |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 200; padrão `50` |

- **Resposta:** `200` (OK) — lista de [`NecessidadeOut`](#necessidadeout)
- **Erros possíveis:** `422` dados inválidos


### `GET /necessidades/minhas`

Todas as do abrigo, abertas primeiro.

- **Quem pode usar:** abrigo
- **Resposta:** `200` (OK) — lista de [`NecessidadeOut`](#necessidadeout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `PATCH /necessidades/{necessidade_id}`

O abrigo edita a necessidade, marca como atendida (`status: atendida`) ou reabre.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `necessidade_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`NecessidadeEdicao`](#necessidadeedicao)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `item` | texto (ou null) | não | mín. 2 caracteres; máx. 200 caracteres |
  | `quantidade` | inteiro (ou null) | não | ≥ 1; ≤ 10000 |
  | `urgencia` | `baixa` \| `media` \| `alta` (ou null) | não |  |
  | `status` | `aberta` \| `atendida` (ou null) | não |  |

- **Resposta:** `200` (OK) — [`NecessidadeOut`](#necessidadeout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `DELETE /necessidades/{necessidade_id}`

O abrigo exclui uma necessidade sem doações; com doações registradas, deve marcá-la como atendida (409).

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `necessidade_id` | caminho | inteiro | sim |  |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `409` conflito com o estado atual, `422` dados inválidos


### `POST /doacoes`

Quem doa se compromete (itens) ou informa o PIX que fez (dinheiro). Fica "aguardando confirmação" até o abrigo
receber; só então conta para a necessidade, para a meta do mês e para o ranking.

- **Quem pode usar:** tutor, apoiador
- **Corpo (JSON):** [`DoacaoIn`](#doacaoin)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `necessidade_id` | inteiro (ou null) | não |  |
  | `abrigo_id` | inteiro (ou null) | não |  |
  | `item` | texto (ou null) | não | mín. 2 caracteres; máx. 200 caracteres |
  | `quantidade` | inteiro | não | ≥ 1; ≤ 10000; padrão `1` |
  | `valor_centavos` | inteiro (ou null) | não | ≥ 100; ≤ 10000000; R$ 50,00 = 5000; mínimo R$ 1,00 |

- **Resposta:** `201` (criado) — [`DoacaoOut`](#doacaoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


### `GET /doacoes/minhas`

Doações de quem está logado (apoiador ou tutor), com a situação e o contato do abrigo.

- **Quem pode usar:** tutor, apoiador
- **Resposta:** `200` (OK) — lista de [`DoacaoOut`](#doacaoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `DELETE /doacoes/{doacao_id}`

Quem doou desiste enquanto o abrigo não respondeu.

- **Quem pode usar:** tutor, apoiador
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `doacao_id` | caminho | inteiro | sim |  |

- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


### `GET /doacoes/recebidas`

Aguardando confirmação primeiro (é o que exige ação), depois as mais recentes.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `status` | consulta (?) | `aguardando_confirmacao` \| `confirmada` \| `recusada` (ou null) | não |  |

- **Resposta:** `200` (OK) — lista de [`DoacaoOut`](#doacaoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `PATCH /doacoes/{doacao_id}`

O abrigo confirma (`confirmada`) ou recusa (`recusada`) uma doação, uma vez só (RF-32). Confirmada, ela pontua no ranking, conta para a necessidade e, se for em dinheiro, para a meta do mês.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `doacao_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`DecisaoDoacao`](#decisaodoacao)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `status` | `confirmada` \| `recusada` | sim |  |

- **Resposta:** `200` (OK) — [`DoacaoOut`](#doacaoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


## Apoiadores

Ranking de quem apoia e perfil público do apoiador (RF-33, RF-34).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/apoiadores/ranking` | público | Ranking de quem apoia (RF-33): por categoria (`petshop`, `clinica`, `distribuidora`, `pessoa_fisica`), no mês ou no ano |
| `GET` | `/apoiadores` | público | Parceiros para o mapa da aba "Quem apoia": só quem já teve doação confirmada |
| `GET` | `/apoiadores/{apoiador_id}` | público | Perfil público do apoiador (RF-34): pontos, meses seguidos e abrigos apoiados |

### `GET /apoiadores/ranking`

Ranking de quem apoia (RF-33): por categoria (`petshop`, `clinica`, `distribuidora`, `pessoa_fisica`), no mês ou no ano. Pessoa física aparece como "Maria S.".

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `categoria` | consulta (?) | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` (ou null) | não | Sem categoria: todas juntas (destaques) |
  | `periodo` | consulta (?) | `mes` \| `ano` | não | padrão `mes` |
  | `mes` | consulta (?) | texto (ou null) | não | AAAA-MM; padrão: o mês atual |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `20` |

- **Resposta:** `200` (OK) — lista de [`PosicaoRanking`](#posicaoranking)
- **Erros possíveis:** `422` dados inválidos


### `GET /apoiadores`

Parceiros para o mapa da aba "Quem apoia": só quem já teve doação confirmada.

- **Quem pode usar:** público
- **Resposta:** `200` (OK) — lista de [`ApoiadorResumo`](#apoiadorresumo)


### `GET /apoiadores/{apoiador_id}`

Perfil público do apoiador (RF-34): pontos, meses seguidos e abrigos apoiados. Só empresas têm perfil (pessoa física: 404).

- **Quem pode usar:** público
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `apoiador_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`ApoiadorPerfilOut`](#apoiadorperfilout)
- **Erros possíveis:** `404` não encontrado, `422` dados inválidos


## Notificações

O sino: avisos de cada conta (RF-36).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/notificacoes` | qualquer conta logada | As notificações de quem está logado, das mais novas para as mais antigas |
| `GET` | `/notificacoes/contagem` | qualquer conta logada | Quantas notificações não lidas a conta tem (o número do sino) |
| `PATCH` | `/notificacoes/{notificacao_id}/lida` | qualquer conta logada | Marca uma notificação da conta como lida |
| `POST` | `/notificacoes/marcar-todas-lidas` | qualquer conta logada | Marca todas as notificações da conta como lidas |

### `GET /notificacoes`

As notificações de quem está logado, das mais novas para as mais antigas.

- **Quem pode usar:** qualquer conta logada
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `somente_nao_lidas` | consulta (?) | sim/não | não | padrão `False` |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `20` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |

- **Resposta:** `200` (OK) — lista de [`NotificacaoOut`](#notificacaoout)
- **Erros possíveis:** `401` não autenticado, `422` dados inválidos


### `GET /notificacoes/contagem`

Quantas notificações não lidas a conta tem (o número do sino).

- **Quem pode usar:** qualquer conta logada
- **Resposta:** `200` (OK) — [`ContagemNotificacoes`](#contagemnotificacoes)
- **Erros possíveis:** `401` não autenticado


### `PATCH /notificacoes/{notificacao_id}/lida`

Marca uma notificação da conta como lida.

- **Quem pode usar:** qualquer conta logada
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `notificacao_id` | caminho | inteiro | sim |  |

- **Resposta:** `200` (OK) — [`NotificacaoOut`](#notificacaoout)
- **Erros possíveis:** `401` não autenticado, `404` não encontrado, `422` dados inválidos


### `POST /notificacoes/marcar-todas-lidas`

Marca todas as notificações da conta como lidas.

- **Quem pode usar:** qualquer conta logada
- **Resposta:** `204` (sem conteúdo) — sem corpo
- **Erros possíveis:** `401` não autenticado


## Denúncias

Denúncia de anúncio e moderação pela administração (RF-41).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `POST` | `/animais/{animal_id}/denuncias` | qualquer conta logada | Denuncia um anúncio (RF-41): a administração é avisada |
| `GET` | `/admin/denuncias` | admin | Fila de moderação: por padrão as pendentes, das mais antigas para as mais novas |
| `PATCH` | `/admin/denuncias/{denuncia_id}` | admin | A administração decide a denúncia (`removido`, `advertido`, `banido` ou `ignorado`) |

### `POST /animais/{animal_id}/denuncias`

Denuncia um anúncio (RF-41): a administração é avisada. Uma denúncia pendente por pessoa e anúncio.

- **Quem pode usar:** qualquer conta logada
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `animal_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`DenunciaIn`](#denunciain)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `motivo` | texto | sim | mín. 10 caracteres; máx. 1000 caracteres; O que há de errado no anúncio |

- **Resposta:** `201` (criado) — objeto
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `409` conflito com o estado atual, `422` dados inválidos


### `GET /admin/denuncias`

Fila de moderação: por padrão as pendentes, das mais antigas para as mais novas.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `status` | consulta (?) | `pendente` \| `removido` \| `advertido` \| `banido` \| `ignorado` | não | padrão `pendente` |

- **Resposta:** `200` (OK) — lista de [`DenunciaOut`](#denunciaout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `PATCH /admin/denuncias/{denuncia_id}`

A administração decide a denúncia (`removido`, `advertido`, `banido` ou `ignorado`). Removido ou banido tira o anúncio do ar (banido também suspende o abrigo); quem denunciou e o abrigo são avisados.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `denuncia_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`DecisaoDenuncia`](#decisaodenuncia)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `decisao` | `ignorado` \| `advertido` \| `removido` \| `banido` | sim |  |
  | `observacao` | texto (ou null) | não | máx. 500 caracteres; Enviada ao abrigo junto com o aviso |

- **Resposta:** `200` (OK) — [`DenunciaOut`](#denunciaout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `409` conflito com o estado atual, `422` dados inválidos


## Administração

Verificação de abrigos pela administração (RF-06).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/admin/abrigos` | admin | Fila de verificação: por padrão, os abrigos ainda não verificados, do mais antigo ao mais novo |
| `PATCH` | `/admin/abrigos/{usuario_id}/validacao` | admin | A administração dá ou retira o selo Verificado, ou suspende o abrigo (RF-06); o abrigo é avisado |

### `GET /admin/abrigos`

Fila de verificação: por padrão, os abrigos ainda não verificados, do mais antigo ao mais novo.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `status` | consulta (?) | `pendente` \| `aprovado` \| `rejeitado` | não | padrão `pendente` |

- **Resposta:** `200` (OK) — lista de [`UsuarioOut`](#usuarioout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `PATCH /admin/abrigos/{usuario_id}/validacao`

A administração dá ou retira o selo Verificado, ou suspende o abrigo (RF-06); o abrigo é avisado.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `usuario_id` | caminho | inteiro | sim |  |

- **Corpo (JSON):** [`ValidacaoAbrigo`](#validacaoabrigo)

  | Campo | Tipo | Obrigatório | Regras |
  |---|---|---|---|
  | `status` | `pendente` \| `aprovado` \| `rejeitado` | sim |  |

- **Resposta:** `200` (OK) — [`UsuarioOut`](#usuarioout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `404` não encontrado, `422` dados inválidos


## Relatórios

Painel da administração, relatórios do abrigo, exportação CSV e histórico de operações (RF-38 a RF-40).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/admin/acoes` | admin | Ações registradas no histórico, com o rótulo em português (para o filtro da tela) |
| `GET` | `/admin/logs` | admin | Histórico de operações (RF-39), paginado; filtra por período, ação, entidade e texto |
| `GET` | `/admin/logs.csv` | admin | O histórico de operações em CSV, com os mesmos filtros |
| `GET` | `/admin/usuarios` | admin | Pesquisa de contas pela administração: por nome, e-mail ou nome do abrigo, tipo de conta e situação |
| `GET` | `/admin/painel` | admin | Painel da administração (RF-38): contas, abrigos, animais e a atividade do período (interesses, adoções, reencontros, doações) |
| `GET` | `/admin/relatorios/abrigos.csv` | admin | Uma linha por abrigo: situação, animais e o movimento do período (adoções e doações) |
| `GET` | `/relatorios/abrigo` | abrigo | Relatório do abrigo (RF-40) no período: animais, interesses, adoções e tempo médio, doações, apoiadores e necessidades |
| `GET` | `/relatorios/abrigo/lista/{lista}` | abrigo | Uma lista do relatório inteira, em páginas: a tela mostra só as primeiras e busca o resto quando pedem |
| `GET` | `/relatorios/abrigo/historico` | abrigo | As operações feitas pela própria conta do abrigo |
| `GET` | `/relatorios/abrigo/interesses.csv` | abrigo | Interesses recebidos no período, em CSV |
| `GET` | `/relatorios/abrigo/doacoes.csv` | abrigo | Doações registradas no período, em CSV (inclui pessoa física e o valor das doações em dinheiro) |
| `GET` | `/relatorios/abrigo/animais.csv` | abrigo | Todos os animais do abrigo (é um retrato de hoje, sem período) |

### `GET /admin/acoes`

Ações registradas no histórico, com o rótulo em português (para o filtro da tela).

- **Quem pode usar:** admin
- **Resposta:** `200` (OK) — objeto
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `GET /admin/logs`

Histórico de operações (RF-39), paginado; filtra por período, ação, entidade e texto.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `acao` | consulta (?) | texto (ou null) | não |  |
  | `q` | consulta (?) | texto (ou null) | não | Pesquisa no nome ou e-mail de quem fez e nos detalhes |
  | `entidade` | consulta (?) | texto (ou null) | não |  |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 500; padrão `50` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — [`PaginaLogs`](#paginalogs)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /admin/logs.csv`

O histórico de operações em CSV, com os mesmos filtros.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `acao` | consulta (?) | texto (ou null) | não |  |
  | `q` | consulta (?) | texto (ou null) | não |  |
  | `entidade` | consulta (?) | texto (ou null) | não |  |
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — JSON (objeto) ou arquivo, conforme a rota
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /admin/usuarios`

Pesquisa de contas pela administração: por nome, e-mail ou nome do abrigo, tipo de conta e situação.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `q` | consulta (?) | texto (ou null) | não | Parte do nome, e-mail ou nome do abrigo |
  | `tipo` | consulta (?) | `tutor` \| `abrigo` \| `apoiador` \| `admin` (ou null) | não |  |
  | `ativo` | consulta (?) | sim/não (ou null) | não |  |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 200; padrão `50` |

- **Resposta:** `200` (OK) — lista de [`UsuarioResumoOut`](#usuarioresumoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /admin/painel`

Painel da administração (RF-38): contas, abrigos, animais e a atividade do período (interesses, adoções, reencontros, doações).

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — [`PainelAdminOut`](#paineladminout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /admin/relatorios/abrigos.csv`

Uma linha por abrigo: situação, animais e o movimento do período (adoções e doações).

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — JSON (objeto) ou arquivo, conforme a rota
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /relatorios/abrigo`

Relatório do abrigo (RF-40) no período: animais, interesses, adoções e tempo médio, doações, apoiadores e necessidades.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — [`RelatorioAbrigoOut`](#relatorioabrigoout)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /relatorios/abrigo/lista/{lista}`

Uma lista do relatório inteira, em páginas: a tela mostra só as primeiras e busca o resto quando pedem.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `lista` | caminho | `origem` \| `apoiadores` \| `itens` | sim |  |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 100; padrão `20` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — [`PaginaLinhas`](#paginalinhas)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /relatorios/abrigo/historico`

As operações feitas pela própria conta do abrigo.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `acao` | consulta (?) | texto (ou null) | não |  |
  | `q` | consulta (?) | texto (ou null) | não |  |
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 500; padrão `50` |
  | `deslocamento` | consulta (?) | inteiro | não | ≥ 0; padrão `0` |
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — [`PaginaLogs`](#paginalogs)
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /relatorios/abrigo/interesses.csv`

Interesses recebidos no período, em CSV.

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — JSON (objeto) ou arquivo, conforme a rota
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /relatorios/abrigo/doacoes.csv`

Doações registradas no período, em CSV (inclui pessoa física e o valor das doações em dinheiro).

- **Quem pode usar:** abrigo
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `de` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Primeiro dia (padrão: 90 dias atrás) |
  | `ate` | consulta (?) | data (AAAA-MM-DD) (ou null) | não | Último dia, inclusive (padrão: hoje) |

- **Resposta:** `200` (OK) — JSON (objeto) ou arquivo, conforme a rota
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos


### `GET /relatorios/abrigo/animais.csv`

Todos os animais do abrigo (é um retrato de hoje, sem período).

- **Quem pode usar:** abrigo
- **Resposta:** `200` (OK) — JSON (objeto) ou arquivo, conforme a rota
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


## Núcleo OpenCL

Estado do núcleo, indexação das fotos e o benchmark sequencial × OpenCL (RF-29).

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/admin/nucleo` | admin | Estado do núcleo OpenCL (no ar? dispositivo, núcleos) e quantas fotos já têm descritor visual |
| `GET` | `/admin/nucleo/benchmark` | admin | `busca`: 1 foto contra n candidatos · `lote`: 100 fotos novas contra n buscas ativas · `extracao`: n fotos |
| `POST` | `/admin/nucleo/indexar` | admin | Calcula no núcleo os descritores das fotos que ficaram sem (enviadas com o núcleo fora do ar) |

### `GET /admin/nucleo`

Estado do núcleo OpenCL (no ar? dispositivo, núcleos) e quantas fotos já têm descritor visual.

- **Quem pode usar:** admin
- **Resposta:** `200` (OK) — objeto
- **Erros possíveis:** `401` não autenticado, `403` sem permissão


### `GET /admin/nucleo/benchmark`

`busca`: 1 foto contra n candidatos · `lote`: 100 fotos novas contra n buscas ativas · `extracao`: n fotos.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `etapa` | consulta (?) | `busca` \| `lote` \| `extracao` | não | padrão `busca` |
  | `n` | consulta (?) | inteiro | não | ≥ 1; padrão `1000` |

- **Resposta:** `200` (OK) — objeto
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos, `503` serviço indisponível


### `POST /admin/nucleo/indexar`

Calcula no núcleo os descritores das fotos que ficaram sem (enviadas com o núcleo fora do ar). 503 se o núcleo não responder.

- **Quem pode usar:** admin
- **Parâmetros:**

  | Nome | Onde | Tipo | Obrigatório | Regras |
  |---|---|---|---|---|
  | `limite` | consulta (?) | inteiro | não | ≥ 1; ≤ 5000; padrão `500` |

- **Resposta:** `200` (OK) — objeto
- **Erros possíveis:** `401` não autenticado, `403` sem permissão, `422` dados inválidos, `503` serviço indisponível


## Infra

Saúde do serviço.

| Método | Rota | Quem pode usar | O que faz |
|---|---|---|---|
| `GET` | `/health` | público | A API está no ar (não consulta o banco) |
| `GET` | `/health/db` | público | Prova que a API alcança o banco: executa uma consulta de verdade |

### `GET /health`

A API está no ar (não consulta o banco).

- **Quem pode usar:** público
- **Resposta:** `200` (OK) — objeto


### `GET /health/db`

Prova que a API alcança o banco: executa uma consulta de verdade.

- **Quem pode usar:** público
- **Resposta:** `200` (OK) — objeto
- **Erros possíveis:** `503` serviço indisponível


---

## Formatos de dados

Os objetos que aparecem nos corpos e nas respostas acima.
### `AbrigoApoiado`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome_abrigo` | texto | sim |  |
| `doacoes_confirmadas` | inteiro | sim |  |

### `AbrigoMapaOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome_abrigo` | texto | sim |  |
| `endereco` | texto | sim |  |
| `latitude` | número | sim |  |
| `longitude` | número | sim |  |
| `telefone` | texto (ou null) | sim |  |
| `horario_funcionamento` | texto (ou null) | sim |  |
| `descricao` | texto (ou null) | sim |  |
| `verificado` | sim/não | sim |  |
| `animais_disponiveis` | inteiro | sim |  |
| `distancia_km` | número (ou null) | não |  |

### `AbrigoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome_abrigo` | texto | sim |  |
| `endereco` | texto | sim |  |
| `latitude` | número | sim |  |
| `longitude` | número | sim |  |
| `horario_funcionamento` | texto (ou null) | sim |  |
| `descricao` | texto (ou null) | sim |  |
| `telefone` | texto (ou null) | sim |  |
| `chave_doacao_financeira` | texto (ou null) | sim |  |
| `meta_mensal_centavos` | inteiro (ou null) | não |  |
| `meta_mensal_descricao` | texto (ou null) | não |  |
| `status_validacao` | `pendente` \| `aprovado` \| `rejeitado` | sim |  |

### `AbrigoPerfilOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome_abrigo` | texto | sim |  |
| `endereco` | texto | sim |  |
| `latitude` | número | sim |  |
| `longitude` | número | sim |  |
| `telefone` | texto (ou null) | sim |  |
| `horario_funcionamento` | texto (ou null) | sim |  |
| `descricao` | texto (ou null) | sim |  |
| `verificado` | sim/não | sim |  |
| `animais_disponiveis` | inteiro | sim |  |
| `chave_doacao_financeira` | texto (ou null) | sim |  |
| `meta_mensal` | [`MetaMensalOut`](#metamensalout) (ou null) | não |  |
| `necessidades` | lista de [`NecessidadeOut`](#necessidadeout) | sim |  |
| `apoiadores` | lista de [`ApoiadorResumo`](#apoiadorresumo) | sim |  |

### `AnimalCreate`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto | sim | mín. 1 caracteres; máx. 120 caracteres |
| `especie` | `cao` \| `gato` \| `outro` | sim |  |
| `raca_aproximada` | texto (ou null) | não | máx. 120 caracteres |
| `porte` | `pequeno` \| `medio` \| `grande` | sim |  |
| `idade_estimada_meses` | inteiro (ou null) | não | ≥ 0; ≤ 600 |
| `sexo` | `macho` \| `femea` \| `indefinido` | sim |  |
| `castrado` | sim/não | não | padrão `False` |
| `vacinado` | sim/não | não | padrão `False` |
| `vermifugado` | sim/não | não | padrão `False` |
| `temperamento` | texto (ou null) | não | máx. 500 caracteres |
| `convivencia_criancas` | sim/não (ou null) | não |  |
| `convivencia_outros_animais` | sim/não (ou null) | não |  |
| `historia_resgate` | texto (ou null) | não | máx. 2000 caracteres |
| `data_entrada` | data (AAAA-MM-DD) (ou null) | não |  |
| `condicao_chegada` | texto (ou null) | não | máx. 500 caracteres |

### `AnimalOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `abrigo_id` | inteiro | sim |  |
| `nome_abrigo` | texto (ou null) | não |  |
| `abrigo_verificado` | sim/não | não | padrão `False` |
| `nome` | texto | sim |  |
| `especie` | `cao` \| `gato` \| `outro` | sim |  |
| `raca_aproximada` | texto (ou null) | sim |  |
| `porte` | texto | sim |  |
| `idade_estimada_meses` | inteiro (ou null) | sim |  |
| `sexo` | `macho` \| `femea` \| `indefinido` | sim |  |
| `castrado` | sim/não | sim |  |
| `vacinado` | sim/não | sim |  |
| `vermifugado` | sim/não | sim |  |
| `temperamento` | texto (ou null) | sim |  |
| `convivencia_criancas` | sim/não (ou null) | sim |  |
| `convivencia_outros_animais` | sim/não (ou null) | sim |  |
| `historia_resgate` | texto (ou null) | sim |  |
| `data_entrada` | data (AAAA-MM-DD) (ou null) | sim |  |
| `condicao_chegada` | texto (ou null) | sim |  |
| `status` | `disponivel` \| `em_processo` \| `adotado` \| `obito` \| `transferido` | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `removido_em` | data e hora (ISO 8601) (ou null) | não |  |
| `fotos` | lista de [`FotoOut`](#fotoout) | não | padrão `[]` |

### `AnimalUpdate`

Atualização parcial (PATCH): só os campos enviados mudam.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto (ou null) | não | mín. 1 caracteres; máx. 120 caracteres |
| `especie` | `cao` \| `gato` \| `outro` (ou null) | não |  |
| `raca_aproximada` | texto (ou null) | não | máx. 120 caracteres |
| `porte` | `pequeno` \| `medio` \| `grande` (ou null) | não |  |
| `idade_estimada_meses` | inteiro (ou null) | não | ≥ 0; ≤ 600 |
| `sexo` | `macho` \| `femea` \| `indefinido` (ou null) | não |  |
| `castrado` | sim/não (ou null) | não |  |
| `vacinado` | sim/não (ou null) | não |  |
| `vermifugado` | sim/não (ou null) | não |  |
| `temperamento` | texto (ou null) | não | máx. 500 caracteres |
| `convivencia_criancas` | sim/não (ou null) | não |  |
| `convivencia_outros_animais` | sim/não (ou null) | não |  |
| `historia_resgate` | texto (ou null) | não | máx. 2000 caracteres |
| `data_entrada` | data (AAAA-MM-DD) (ou null) | não |  |
| `condicao_chegada` | texto (ou null) | não | máx. 500 caracteres |
| `status` | `disponivel` \| `em_processo` \| `adotado` \| `obito` \| `transferido` (ou null) | não |  |

### `ApoiadorDoAbrigo`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto | sim |  |
| `doacoes` | inteiro | sim |  |
| `quantidade` | inteiro | sim |  |

### `ApoiadorOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `cnpj` | texto | sim |  |
| `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` | sim |  |
| `endereco` | texto | sim |  |
| `latitude` | número (ou null) | sim |  |
| `longitude` | número (ou null) | sim |  |
| `status_validacao` | `pendente` \| `aprovado` \| `rejeitado` | sim |  |

### `ApoiadorPerfilOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome` | texto | sim |  |
| `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` | sim |  |
| `selo_ativo` | sim/não | sim |  |
| `latitude` | número (ou null) | não |  |
| `longitude` | número (ou null) | não |  |
| `endereco` | texto | sim |  |
| `pontos_mes` | número | sim |  |
| `pontos_ano` | número | sim |  |
| `meses_seguidos` | inteiro | sim |  |
| `doacoes_confirmadas` | inteiro | sim |  |
| `abrigos_apoiados` | lista de [`AbrigoApoiado`](#abrigoapoiado) | sim |  |
| `membro_desde` | data e hora (ISO 8601) | sim |  |

### `ApoiadorResumo`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome` | texto | sim |  |
| `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` | sim |  |
| `selo_ativo` | sim/não | sim |  |
| `latitude` | número (ou null) | não |  |
| `longitude` | número (ou null) | não |  |

### `AtualizaUsuario`

Atualização parcial: só os campos enviados mudam. Campos que não se
aplicam ao tipo da conta (ex.: nome_abrigo numa conta de tutor) são recusados.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto (ou null) | não | mín. 2 caracteres; máx. 150 caracteres |
| `telefone` | texto (ou null) | não | máx. 20 caracteres |
| `cidade` | texto (ou null) | não | máx. 120 caracteres |
| `nome_abrigo` | texto (ou null) | não | mín. 2 caracteres; máx. 150 caracteres |
| `endereco` | texto (ou null) | não | mín. 3 caracteres; máx. 255 caracteres |
| `latitude` | número (ou null) | não | ≥ -90; ≤ 90 |
| `longitude` | número (ou null) | não | ≥ -180; ≤ 180 |
| `horario_funcionamento` | texto (ou null) | não | máx. 255 caracteres |
| `descricao` | texto (ou null) | não | máx. 2000 caracteres |
| `chave_doacao_financeira` | texto (ou null) | não | máx. 140 caracteres |
| `meta_mensal_centavos` | inteiro (ou null) | não | ≥ 100; ≤ 100000000 |
| `meta_mensal_descricao` | texto (ou null) | não | máx. 500 caracteres |
| `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` (ou null) | não |  |

### `AvistamentoIn`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `especie` | `cao` \| `gato` \| `outro` | sim |  |
| `porte` | `pequeno` \| `medio` \| `grande` | sim |  |
| `cor_predominante` | texto | sim | mín. 2 caracteres; máx. 60 caracteres |
| `pelagem` | texto (ou null) | não | máx. 60 caracteres |
| `sexo` | `macho` \| `femea` \| `indefinido` | não | padrão `indefinido` |
| `sinais_particulares` | texto (ou null) | não | máx. 500 caracteres |
| `latitude` | número | sim | ≥ -90; ≤ 90 |
| `longitude` | número | sim | ≥ -180; ≤ 180 |
| `fotos` | lista de arquivo (ou null) | não | De 1 a 5 fotos (JPEG, PNG ou WebP) |
| `data_avistamento` | data (AAAA-MM-DD) | sim |  |

### `AvistamentoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `especie` | `cao` \| `gato` \| `outro` | sim |  |
| `porte` | texto | sim |  |
| `cor_predominante` | texto | sim |  |
| `pelagem` | texto (ou null) | sim |  |
| `sexo` | `macho` \| `femea` \| `indefinido` | sim |  |
| `sinais_particulares` | texto (ou null) | sim |  |
| `latitude` | número | sim |  |
| `longitude` | número | sim |  |
| `localizacao_aproximada` | sim/não | sim |  |
| `fotos` | lista de texto | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `distancia_km` | número (ou null) | não |  |
| `data_avistamento` | data (AAAA-MM-DD) | sim |  |

### `CadastroAbrigo`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto | sim | mín. 2 caracteres; máx. 150 caracteres |
| `email` | e-mail | sim |  |
| `senha` | texto | sim | mín. 8 caracteres |
| `tipo_conta` | `abrigo` | sim |  |
| `nome_abrigo` | texto | sim | mín. 2 caracteres; máx. 150 caracteres |
| `endereco` | texto | sim | mín. 3 caracteres; máx. 255 caracteres |
| `latitude` | número | sim | ≥ -90; ≤ 90 |
| `longitude` | número | sim | ≥ -180; ≤ 180 |
| `horario_funcionamento` | texto (ou null) | não | máx. 255 caracteres |
| `descricao` | texto (ou null) | não | máx. 2000 caracteres |
| `telefone` | texto (ou null) | não | máx. 20 caracteres |
| `chave_doacao_financeira` | texto (ou null) | não | máx. 140 caracteres |

### `CadastroApoiador`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto | sim | mín. 2 caracteres; máx. 150 caracteres |
| `email` | e-mail | sim |  |
| `senha` | texto | sim | mín. 8 caracteres |
| `tipo_conta` | `apoiador` | sim |  |
| `cnpj` | texto | sim |  |
| `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` | sim |  |
| `endereco` | texto | sim | mín. 3 caracteres; máx. 255 caracteres |
| `latitude` | número (ou null) | não | ≥ -90; ≤ 90 |
| `longitude` | número (ou null) | não | ≥ -180; ≤ 180 |

### `CadastroTutor`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nome` | texto | sim | mín. 2 caracteres; máx. 150 caracteres |
| `email` | e-mail | sim |  |
| `senha` | texto | sim | mín. 8 caracteres |
| `tipo_conta` | `tutor` | sim |  |
| `telefone` | texto (ou null) | não | máx. 20 caracteres |
| `cidade` | texto (ou null) | não | máx. 120 caracteres |

### `CandidatoOut`

Um candidato da busca: o sistema nunca afirma que é o animal, só mostra o grau de semelhança.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `tipo` | `avistamento` \| `animal` \| `animal_perdido` | sim |  |
| `id` | inteiro | sim |  |
| `rotulo` | texto | sim |  |
| `foto` | texto (ou null) | sim |  |
| `grau` | `alta` \| `media` \| `baixa` (ou null) | sim |  |
| `nota` | número (ou null) | sim |  |
| `distancia_km` | número | sim |  |
| `data` | data (AAAA-MM-DD) (ou null) | sim |  |
| `caminho` | texto | sim |  |

### `Contagem`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `chave` | texto | sim |  |
| `total` | inteiro | sim |  |

### `ContagemNotificacoes`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `nao_lidas` | inteiro | sim |  |

### `DecisaoDenuncia`

ignorado: improcedente · advertido: aviso ao abrigo · removido: anúncio sai do ar · banido: abrigo suspenso.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `decisao` | `ignorado` \| `advertido` \| `removido` \| `banido` | sim |  |
| `observacao` | texto (ou null) | não | máx. 500 caracteres; Enviada ao abrigo junto com o aviso |

### `DecisaoDoacao`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `status` | `confirmada` \| `recusada` | sim |  |

### `DecisaoInteresse`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `status` | `em_conversa` \| `aprovado` \| `recusado` | sim |  |

### `DenunciaIn`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `motivo` | texto | sim | mín. 10 caracteres; máx. 1000 caracteres; O que há de errado no anúncio |

### `DenunciaOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `animal_id` | inteiro | sim |  |
| `animal_nome` | texto | sim |  |
| `abrigo_id` | inteiro | sim |  |
| `nome_abrigo` | texto | sim |  |
| `denunciante_nome` | texto | sim |  |
| `motivo` | texto | sim |  |
| `status` | `pendente` \| `removido` \| `advertido` \| `banido` \| `ignorado` | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `resolvido_em` | data e hora (ISO 8601) (ou null) | sim |  |
| `denuncias_do_animal` | inteiro | sim |  |

### `DoacaoIn`

Três formas: para uma necessidade do mural (`necessidade_id`), avulsa de itens (`abrigo_id` + `item`) ou em
dinheiro (`abrigo_id` + `valor_centavos`, depois de fazer o PIX para a chave do abrigo).

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `necessidade_id` | inteiro (ou null) | não |  |
| `abrigo_id` | inteiro (ou null) | não |  |
| `item` | texto (ou null) | não | mín. 2 caracteres; máx. 200 caracteres |
| `quantidade` | inteiro | não | ≥ 1; ≤ 10000; padrão `1` |
| `valor_centavos` | inteiro (ou null) | não | ≥ 100; ≤ 10000000; R$ 50,00 = 5000; mínimo R$ 1,00 |

### `DoacaoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `apoiador_id` | inteiro | sim |  |
| `nome_apoiador` | texto | sim |  |
| `perfil_publico_doador` | sim/não | não | padrão `True` |
| `abrigo_id` | inteiro | sim |  |
| `nome_abrigo` | texto | sim |  |
| `necessidade_id` | inteiro (ou null) | sim |  |
| `item` | texto | sim |  |
| `quantidade` | inteiro | sim |  |
| `valor_centavos` | inteiro (ou null) | não |  |
| `status` | `aguardando_confirmacao` \| `confirmada` \| `recusada` | sim |  |
| `registrado_em` | data e hora (ISO 8601) | sim |  |
| `confirmado_em` | data e hora (ISO 8601) (ou null) | sim |  |
| `contato` | texto (ou null) | não |  |

### `EsqueciSenha`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `email` | e-mail | sim |  |

### `FotoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `url` | texto | sim |  |

### `InteresseAbrigoOut`

O que o abrigo vê: quem se interessou e como falar com a pessoa.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `animal_id` | inteiro | sim |  |
| `animal_nome` | texto | sim |  |
| `tutor_nome` | texto | sim |  |
| `tutor_email` | texto | sim |  |
| `tutor_telefone` | texto (ou null) | sim |  |
| `tutor_cidade` | texto (ou null) | sim |  |
| `status` | `aguardando` \| `em_conversa` \| `aprovado` \| `recusado` | sim |  |
| `mensagem` | texto (ou null) | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |

### `InteresseCreate`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `mensagem` | texto (ou null) | não | máx. 500 caracteres; Apresentação do adotante (opcional) |

### `InteresseTutorOut`

O que o adotante vê. O contato do abrigo só aparece depois do interesse registrado.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `animal_id` | inteiro | sim |  |
| `animal_nome` | texto | sim |  |
| `nome_abrigo` | texto | sim |  |
| `abrigo_telefone` | texto (ou null) | sim |  |
| `abrigo_endereco` | texto | sim |  |
| `status` | `aguardando` \| `em_conversa` \| `aprovado` \| `recusado` | sim |  |
| `mensagem` | texto (ou null) | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |

### `LinhaRelatorio`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `rotulo` | texto | sim |  |
| `valores` | lista de inteiro | sim |  |

### `LogOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `usuario_id` | inteiro | sim |  |
| `usuario_nome` | texto | sim |  |
| `usuario_email` | texto | sim |  |
| `tipo_conta` | texto | sim |  |
| `acao` | texto | sim |  |
| `rotulo` | texto | sim |  |
| `entidade_tipo` | texto | sim |  |
| `entidade_id` | inteiro | sim |  |
| `detalhes` | objeto | sim |  |

### `MetaMensalOut`

Meta de gastos do mês (RF-31): o que o abrigo precisa e quanto já foi confirmado no mês (fuso de Recife).

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `mes` | texto | sim |  |
| `valor_centavos` | inteiro | sim |  |
| `descricao` | texto (ou null) | sim |  |
| `arrecadado_centavos` | inteiro | sim |  |
| `doacoes_confirmadas` | inteiro | sim |  |

### `NecessidadeEdicao`

Tudo opcional: só muda o que vier. `status` reabre ou marca como atendida.

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `item` | texto (ou null) | não | mín. 2 caracteres; máx. 200 caracteres |
| `quantidade` | inteiro (ou null) | não | ≥ 1; ≤ 10000 |
| `urgencia` | `baixa` \| `media` \| `alta` (ou null) | não |  |
| `status` | `aberta` \| `atendida` (ou null) | não |  |

### `NecessidadeIn`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `item` | texto | sim | mín. 2 caracteres; máx. 200 caracteres; Ex.: ração para cão adulto (saco de 15 kg) |
| `quantidade` | inteiro | sim | ≥ 1; ≤ 10000 |
| `urgencia` | `baixa` \| `media` \| `alta` | não | padrão `media` |

### `NecessidadeOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `abrigo_id` | inteiro | sim |  |
| `nome_abrigo` | texto | sim |  |
| `item` | texto | sim |  |
| `quantidade` | inteiro | sim |  |
| `quantidade_recebida` | inteiro | sim |  |
| `urgencia` | `baixa` \| `media` \| `alta` | sim |  |
| `status` | `aberta` \| `atendida` | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `distancia_km` | número (ou null) | não |  |

### `NotificacaoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `mensagem` | texto | sim |  |
| `referencia_tipo` | texto (ou null) | sim |  |
| `referencia_id` | inteiro (ou null) | sim |  |
| `lida` | sim/não | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `destino` | texto (ou null) | sim |  |

### `PaginaLinhas`

Uma lista do relatório completa, em páginas (carregada só quando a pessoa pede para ver tudo).

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `total` | inteiro | sim |  |
| `colunas` | lista de texto | sim |  |
| `itens` | lista de [`LinhaRelatorio`](#linharelatorio) | sim |  |

### `PaginaLogs`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `total` | inteiro | sim |  |
| `itens` | lista de [`LogOut`](#logout) | sim |  |

### `PainelAdminOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `periodo` | [`Periodo`](#periodo) | sim |  |
| `contas` | lista de [`Contagem`](#contagem) | sim |  |
| `abrigos` | lista de [`Contagem`](#contagem) | sim |  |
| `animais` | lista de [`Contagem`](#contagem) | sim |  |
| `no_periodo` | objeto | sim |  |
| `agora` | objeto | sim |  |
| `serie_mensal` | lista de [`PontoMensal`](#pontomensal) | sim |  |
| `ultimas_acoes` | lista de [`LogOut`](#logout) | sim |  |

### `PerdidoIn`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `especie` | `cao` \| `gato` \| `outro` | sim |  |
| `porte` | `pequeno` \| `medio` \| `grande` | sim |  |
| `cor_predominante` | texto | sim | mín. 2 caracteres; máx. 60 caracteres |
| `pelagem` | texto (ou null) | não | máx. 60 caracteres |
| `sexo` | `macho` \| `femea` \| `indefinido` | não | padrão `indefinido` |
| `sinais_particulares` | texto (ou null) | não | máx. 500 caracteres |
| `latitude` | número | sim | ≥ -90; ≤ 90 |
| `longitude` | número | sim | ≥ -180; ≤ 180 |
| `fotos` | lista de arquivo (ou null) | não | De 1 a 5 fotos (JPEG, PNG ou WebP) |
| `raio_busca_km` | número | não | > 0; ≤ 100; padrão `5.0` |
| `data_desaparecimento` | data (AAAA-MM-DD) | sim |  |

### `PerdidoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `especie` | `cao` \| `gato` \| `outro` | sim |  |
| `porte` | texto | sim |  |
| `cor_predominante` | texto | sim |  |
| `pelagem` | texto (ou null) | sim |  |
| `sexo` | `macho` \| `femea` \| `indefinido` | sim |  |
| `sinais_particulares` | texto (ou null) | sim |  |
| `latitude` | número | sim |  |
| `longitude` | número | sim |  |
| `localizacao_aproximada` | sim/não | sim |  |
| `fotos` | lista de texto | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `distancia_km` | número (ou null) | não |  |
| `raio_busca_km` | número | sim |  |
| `data_desaparecimento` | data (AAAA-MM-DD) | sim |  |
| `resolvido` | sim/não | sim |  |

### `Periodo`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `de` | data (AAAA-MM-DD) | sim |  |
| `ate` | data (AAAA-MM-DD) | sim |  |

### `PontoMensal`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `mes` | texto | sim |  |
| `interesses` | inteiro | sim |  |
| `registros_reencontro` | inteiro | sim |  |
| `doacoes_confirmadas` | inteiro | sim |  |

### `PosicaoRanking`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `posicao` | inteiro | sim |  |
| `apoiador_id` | inteiro | sim |  |
| `nome` | texto | sim |  |
| `tipo_estabelecimento` | `petshop` \| `clinica` \| `distribuidora` \| `pessoa_fisica` | sim |  |
| `pontos` | número | sim |  |
| `pontos_volume` | número | sim |  |
| `pontos_regularidade` | número | sim |  |
| `doacoes_confirmadas` | inteiro | sim |  |
| `meses_seguidos` | inteiro | sim |  |
| `selo_ativo` | sim/não | sim |  |
| `perfil_publico` | sim/não | não | padrão `True` |

### `RedefinirSenha`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `token` | texto | sim | mín. 10 caracteres |
| `senha_nova` | texto | sim | mín. 8 caracteres |

### `RelatorioAbrigoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `periodo` | [`Periodo`](#periodo) | sim |  |
| `animais` | lista de [`Contagem`](#contagem) | sim |  |
| `interesses` | lista de [`Contagem`](#contagem) | sim |  |
| `adocoes_aprovadas` | inteiro | sim |  |
| `tempo_medio_adocao_dias` | número (ou null) | sim |  |
| `origem_interessados` | lista de [`Contagem`](#contagem) | sim |  |
| `doacoes` | lista de [`Contagem`](#contagem) | sim |  |
| `por_apoiador` | lista de [`ApoiadorDoAbrigo`](#apoiadordoabrigo) | sim |  |
| `por_item` | lista de [`Contagem`](#contagem) | sim |  |
| `totais_listas` | objeto | sim |  |
| `necessidades` | lista de [`Contagem`](#contagem) | sim |  |
| `serie_mensal` | lista de [`PontoMensal`](#pontomensal) | sim |  |

### `SemelhantesOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `comparacao_por_foto` | sim/não | sim |  |
| `motivo` | texto (ou null) | não |  |
| `registros_comparados` | inteiro | sim |  |
| `comparacoes` | inteiro | sim |  |
| `tempo_nucleo_ms` | número | sim |  |
| `tempo_total_ms` | número | sim |  |
| `modo` | texto | sim |  |
| `raio_km` | número | sim |  |
| `candidatos` | lista de [`CandidatoOut`](#candidatoout) | sim |  |

### `TokenOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `access_token` | texto | sim |  |
| `token_type` | texto | não | padrão `bearer` |
| `usuario` | [`UsuarioOut`](#usuarioout) | sim |  |

### `TrocaSenha`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `senha_atual` | texto | sim |  |
| `senha_nova` | texto | sim | mín. 8 caracteres |

### `TutorOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `telefone` | texto (ou null) | sim |  |
| `cidade` | texto (ou null) | sim |  |

### `UsuarioOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome` | texto | sim |  |
| `email` | texto | sim |  |
| `tipo_conta` | `tutor` \| `abrigo` \| `apoiador` \| `admin` | sim |  |
| `ativo` | sim/não | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `perfil` | [`TutorOut`](#tutorout) ou [`AbrigoOut`](#abrigoout) ou [`ApoiadorOut`](#apoiadorout) (ou null) | não |  |

### `UsuarioResumoOut`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `id` | inteiro | sim |  |
| `nome` | texto | sim |  |
| `email` | texto | sim |  |
| `tipo_conta` | texto | sim |  |
| `ativo` | sim/não | sim |  |
| `criado_em` | data e hora (ISO 8601) | sim |  |
| `detalhe` | texto (ou null) | sim |  |

### `ValidacaoAbrigo`

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `status` | `pendente` \| `aprovado` \| `rejeitado` | sim |  |
