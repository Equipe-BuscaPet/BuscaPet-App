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
```
