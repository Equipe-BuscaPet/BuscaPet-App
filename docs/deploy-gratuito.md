# Publicação gratuita (MVP) — Vercel + Render + Supabase

Custo zero, sem cartão. O sistema completo (com o núcleo OpenCL e o benchmark) continua rodando **localmente**
(`iniciar-demo.ps1`); a versão online é o MVP.

| Peça | Onde | O que roda |
|---|---|---|
| Interface (React) | Vercel (Hobby) | `frontend/` |
| API + núcleo leve | Render (free) | `deploy/Dockerfile.render`: a API e o núcleo em C **sem OpenCL**, dois processos no mesmo contêiner |
| Banco | Supabase (free) | Postgres; também guarda os JPEGs das fotos (tabela `fotos_arquivos`) |

**Por que o núcleo vai junto da API?** O plano gratuito do Render dá ~750 h/mês no total: sustenta *um* serviço
sempre ligado. Dois serviços dormiriam, e o primeiro acesso a um serviço dormindo leva ~50 s. O núcleo continua
sendo um serviço HTTP separado (processo próprio, `127.0.0.1:8001`); só a embalagem é uma. O núcleo leve usa a
versão sequencial em C, que dá os mesmos descritores e as mesmas notas que a OpenCL (o teste de equivalência
roda no build). Sem o ganho de velocidade e sem `/admin/nucleo/benchmark` (responde 503).

**Por que as fotos no banco?** O disco do Render free é apagado a cada reinício. Com `ARMAZENAMENTO_FOTOS=banco`
(já definido na imagem) o JPEG vai para o Postgres. As fotos têm ~8 kB cada nas demonstrações e ~100–200 kB
reais; o Supabase free dá 500 MB.

## O que a API dorme e o que não
A API do Render free **dorme após 15 min sem acesso** e a primeira requisição depois disso leva ~30–50 s.
Antes de uma apresentação, abra o site uns 2 minutos antes. (Um monitor gratuito, como o UptimeRobot, chamando
`/health` a cada 5 min mantém a API acordada; as 750 h cobrem um serviço o mês todo.)

O Supabase free **pausa o projeto após ~1 semana sem uso**: reative no painel antes da apresentação.

## Passo a passo

### 1. Supabase (banco)
Use o projeto que já existe. Copie a connection string do **Session pooler** (porta 5432). Ela é a `DATABASE_URL`.
As migrações (inclusive a 0006) rodam sozinhas na partida da API (`alembic upgrade head`).

### 2. Render (API + núcleo)
1. Em render.com, entre com o GitHub → **New → Blueprint** → escolha o repositório `BuscaPet-App`
   (o `render.yaml` da raiz descreve tudo).
2. Preencha as variáveis que ele pedir:
   - `DATABASE_URL`: a do Supabase.
   - `CORS_ORIGINS`: a URL da Vercel em JSON, ex.: `["https://buscapet.vercel.app"]` (se ainda não souber,
     deixe `["*"]`... não: preencha depois do passo 3 e faça *Manual Deploy*).
   - `URL_INTERFACE`: a URL da Vercel, sem barra no fim.
3. `JWT_SECRET` é gerado pelo Render. O deploy leva alguns minutos; confira `https://<nome>.onrender.com/health/db`.

### 3. Vercel (interface)
1. Em vercel.com → **Add New → Project** → o mesmo repositório.
2. **Root Directory:** `frontend`. Framework: Vite (detectado).
3. **Environment Variable:** `VITE_API_URL` = a URL da API no Render (sem barra no fim).
4. Deploy. Volte ao Render e ajuste `CORS_ORIGINS` e `URL_INTERFACE` com a URL final da Vercel.

### 4. Depois de no ar
```
# no Shell do Render (ou local, com DATABASE_URL apontando para o Supabase e ARMAZENAMENTO_FOTOS=banco):
python -m app.scripts.criar_admin
python -m app.scripts.indexar_fotos     # calcula o descritor das fotos que ficaram sem
```
O `popular_demo` recusa bancos remotos de propósito; para ter dados de demonstração online, veja a decisão
registrada no diário do projeto.

## Custos e limites (verificados em out/2026 — confirmar antes de decidir)
Vercel Hobby, Render free e Supabase free não pedem cartão. Se um limite for estourado, o serviço para ou
dorme; não há cobrança automática no plano gratuito.
