# Frontend

Interface web do BuscaPet em **React + Vite**. Consome a API do backend (`api/`,
contrato em `http://localhost:8000/docs`). Protótipo e identidade visual em
[`sprints/sprint-2/05-prototipos.md`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/blob/main/sprints/sprint-2/05-prototipos.md)
(repositório `BuscaPet-Docs`).

## Telas

| Rota | Quem acessa | O que faz |
|---|---|---|
| `/` | todos | Catálogo de animais para adoção, com busca e filtros |
| `/mapa` | todos | Mapa de abrigos, com distância a partir da posição da pessoa |
| `/animais/:id` | todos | Ficha completa do animal e registro de interesse de adoção |
| `/reencontro` | todos | **Perdidos e achados**: animais perdidos e avistados na rua, com filtros e "perto de mim" (RF-19/20) |
| `/reencontro/perdidos/:id`, `/reencontro/avistamentos/:id` | todos | Detalhe do registro: galeria, características e mapa da região aproximada |
| `/perdi` | todos preenchem; **tutor** publica | Assistente "Perdi meu animal" em 5 etapas (RF-19) |
| `/encontrei` | todos preenchem; **qualquer conta** publica | Assistente "Encontrei um animal" em 5 etapas (RF-20) |
| `/meus-registros` | tutor, abrigo, apoiador | Os próprios registros de perdido/avistamento, com exclusão |
| `/interesses` | tutor | Interesses de adoção que a pessoa registrou |
| `/interessados` | abrigo | Interessados nos animais do abrigo, com a decisão de cada caso |
| `/painel` | abrigo | CRUD dos animais do abrigo (opera na hora; o selo Verificado é dado pelo administrador) |
| `/admin` | administrador | Verificação de abrigos (dar ou retirar o selo, suspender) |
| `/login`, `/cadastro` | visitante | Login único e cadastro de tutor, abrigo ou apoiador |

### Assistente "Perdi" / "Encontrei"

Segue o protótipo da Sprint 2 (escopo §4.2): **Fotos → Características → Local e data → Revisar → Resultados**.

- **Visitante preenche tudo** e só entra na hora de publicar, com um login na própria etapa de revisão, sem perder
  as fotos (CONTEXTO §8, ponto 5).
- Fotos: de 1 a 5, JPEG/PNG/WebP até 8 MB, com pré-visualização e arrastar-e-soltar. A API remove os metadados
  (inclusive o GPS da foto de celular).
- Local marcado no mapa ou pela localização do aparelho. Em público o ponto aparece **aproximado** (perdido ~1 km,
  avistamento ~100 m); só o autor vê o ponto exato.
- **Resultados:** enquanto o núcleo OpenCL não compara as fotos, a tela mostra registros **reais** da outra base
  (perdido → avistamentos; avistamento → perdidos), da mesma espécie e perto do local, por distância, com um aviso
  claro de que a comparação por foto está em construção. Nenhum dado é inventado.

O controle de perfil também vale no menu: cada tipo de conta só vê os links a que
tem direito. A regra de verdade fica na API; a interface só reflete.

## Rodando

Precisa do Node 20+ e da API rodando (ver o README da raiz).

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

A URL da API vem de `VITE_API_URL` e, se não existir, usa `http://localhost:8000`.
Para apontar para outra API: `VITE_API_URL=http://meu-servidor:8000 npm run dev`.

`npm run build` gera a versão de produção em `dist/`.

## Testes de ponta a ponta (Playwright)

```bash
npm run e2e            # roda tudo (sobe API e interface se precisar)
npm run e2e:ver        # modo visual, passo a passo
npm run e2e:relatorio  # relatório HTML da última execução
```

| Arquivo | Cobre |
|---|---|
| `e2e/navegacao.spec.js` | catálogo, menu, página inexistente, rota protegida → login → volta, retorno do login só para dentro do site, menu do celular |
| `e2e/autenticacao.spec.js` | cadastro pela interface, senha errada, menu por perfil e bloqueio de página, sair |
| `e2e/adocao.spec.js` | tutor registra interesse e o abrigo vê o interessado; visitante é convidado a entrar |
| `e2e/reencontro.spec.js` | assistente "Perdi" completo (validações, login na revisão, fotos mantidas, data sem erro de fuso), arquivo que não é imagem, aviso para abrigo, "Encontrei" achando o perdido próximo, abas da lista, privacidade do local, exclusão |
| `e2e/apoio.js` | cria contas e registros pela API, com e-mail único por teste |

Dois projetos: `computador` (todos os testes) e `celular` (Pixel 7, só os marcados com `@celular`). O fuso do navegador
é `America/Recife`. Falhas guardam captura, vídeo e *trace* em `test-results/` (fora do Git).

> Requer Playwright 1.56 ou mais novo no Node 24: a versão 1.48 trava ao carregar os testes.

## Estrutura

```
src/
  api.js        cliente da API (token, erros em português, envio de fotos em multipart)
  auth.jsx      contexto de login: usuário atual, entrar, sair
  rotulos.js    textos em português para os valores da API
  App.jsx       cabeçalho, rotas e proteção por tipo de conta
  pages/        uma tela por arquivo
  componentes/  peças reaproveitadas entre telas (assistente do reencontro, seletor de fotos,
                seletor de local no mapa, cartão de registro)
  styles.css    paleta e componentes (modo claro e escuro)
e2e/            testes de ponta a ponta (Playwright); fotos de teste em e2e/fixtures/
playwright.config.js   projetos computador/celular, servidores que o teste sobe sozinho
```
