# Frontend

Interface web do BuscaPet em **React + Vite**. Consome a API do backend (`api/`,
contrato em `http://localhost:8000/docs`). Protótipo e identidade visual em
[`sprints/sprint-2/05-prototipos.md`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/blob/main/sprints/sprint-2/05-prototipos.md)
(repositório `BuscaPet-Docs`).

## Telas da Sprint 3

| Rota | Quem acessa | O que faz |
|---|---|---|
| `/` | todos | Catálogo de animais para adoção, com busca e filtros |
| `/mapa` | todos | Mapa de abrigos, com distância a partir da posição da pessoa |
| `/animais/:id` | todos | Ficha completa do animal |
| `/login` | visitante | Login único para todos os perfis |
| `/cadastro` | visitante | Cadastro de tutor, abrigo ou apoiador |
| `/painel` | abrigo | CRUD de animais (liberado só depois de aprovado pelo administrador) |
| `/admin` | administrador | Fila de validação de abrigos (aprovar ou rejeitar) |

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
  api.js        cliente da API (token, erros em português)
  auth.jsx      contexto de login: usuário atual, entrar, sair
  rotulos.js    textos em português para os valores da API
  App.jsx       cabeçalho, rotas e proteção por tipo de conta
  pages/        uma tela por arquivo
  styles.css    paleta e componentes (modo claro e escuro)
```
