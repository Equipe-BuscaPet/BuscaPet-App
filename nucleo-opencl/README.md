# Núcleo OpenCL — `/nucleo-opencl`

Serviço HTTP separado do backend web, responsável por toda a etapa computacionalmente pesada do
reencontro por similaridade visual (RF-19 a RF-29). Escrito em **C** com a API oficial do OpenCL
(`CL/cl.h`) e roda em **dispositivo CPU** via **PoCL** (runtime OpenCL por software, que não exige GPU).
O backend nunca executa OpenCL: ele chama este serviço via HTTP (`NUCLEO_OPENCL_URL`).

## Estado atual

| Item | Situação |
|---|---|
| Spike: kernel `soma_vetores` + teste de equivalência (gate da Sprint 1 do plano interno) | ✅ |
| Serviço HTTP (`libmicrohttpd` + `cJSON`) com `GET /saude` | ✅ |
| Build em Docker multi-stage que só gera a imagem se o teste passar | ✅ |
| Job `nucleo-opencl` na CI (compila, testa, sobe o serviço e consulta `/saude`) | ✅ |
| Pré-processamento e extração de descritores (sequencial + kernels) | ⏳ Sprint 3, semana 6 |
| `POST /comparar`, `POST /extrair-descritor`, `GET /benchmark` | ⏳ respondem `501` por enquanto |

## Como rodar

Só é preciso ter o Docker. Compilador C, PoCL e bibliotecas ficam todos dentro da imagem, e por isso o
resultado é igual em qualquer máquina do time e na CI.

```bash
# a partir da raiz do BuscaPet-App
docker compose up -d --build nucleo-opencl
curl localhost:8001/saude
```

Resposta (na máquina de referência do time, um i5-2400 com 4 núcleos):

```json
{"servico":"nucleo-opencl","versao":"0.1.0","status":"ok",
 "opencl":{"plataforma":"Portable Computing Language","versao":"OpenCL 3.0 PoCL 3.1+debian ...",
           "dispositivo":"pthread-sandybridge-Intel(R) Core(TM) i5-2400 CPU @ 3.10GHz",
           "tipo":"CPU","unidades_computo":4,"memoria_global_mb":2183}}
```

Para rodar o spike à mão, com o tamanho que quiser:

```bash
docker compose run --rm nucleo-opencl ./spike 10000000
```

## O spike e o que ele mede

O `spike` soma dois vetores de N números de duas formas, uma **sequencial na CPU** (referência) e outra
**via OpenCL**, e confere se as respostas são iguais posição por posição. Os tempos do OpenCL vêm dos
eventos de *profiling* da fila e são medidos separadamente: o envio dos dados (host → device), o kernel e
o retorno (device → host).

Medição de 16/10/2026, i5-2400, N = 4.194.304 (16 MB por vetor):

| Etapa | Tempo (ms) |
|---|---:|
| CPU sequencial (referência) | 16,9 |
| OpenCL: envio (host → device) | 29,1 |
| OpenCL: kernel | 8,9 |
| OpenCL: retorno (device → host) | 4,6 |
| OpenCL: total de ponta a ponta | 43,5 |

**Leitura honesta:** o kernel em si foi ~1,9× mais rápido que o laço sequencial, mas o total ficou
mais lento, porque somar vetores faz só **uma** conta por número transferido e a cópia dos dados domina o
tempo. É exatamente o efeito que a Lei de Amdahl prevê. O ganho real aparece quando há muito cálculo por
dado transferido, como nas etapas de descritores e de comparação em massa abaixo. Medir a transferência à
parte desde o spike é o que vai permitir mostrar isso no benchmark do RF-29.

## Testes

`make teste` (executado automaticamente no `docker build` e na CI) roda o spike com três tamanhos:

| N | Por quê |
|---|---|
| 1 | caso mínimo |
| 1.000.003 | número primo: não é múltiplo de nenhum tamanho de grupo de trabalho, então pega erro de borda |
| 4.194.304 | volume realista |

**Regra para todo kernel novo** (plano interno, semana 6): ele só entra quando a saída paralela bater com a
versão sequencial no `make teste`.

## Estrutura

```
nucleo-opencl/
  kernels/            código OpenCL C (.cl), compilado em tempo de execução pelo PoCL
    soma_vetores.cl   kernel do spike
  src/
    ocl.c / ocl.h     utilidades: escolher dispositivo, compilar kernel, medir tempo, traduzir erros
    spike.c           teste de equivalência + medição de tempos
    servidor.c        serviço HTTP (porta 8001, variável PORTA)
  Makefile            make · make teste · make limpar
  Dockerfile          estágio 1 compila e testa; estágio 2 leva só os binários (usuário sem root)
```

Variáveis de ambiente: `PORTA` (padrão `8001`), `NUCLEO_KERNELS` (pasta dos `.cl`, padrão `kernels`) e
`POCL_CACHE_DIR` (cache dos kernels já compilados pelo PoCL).

A imagem final tem ~850 MB porque o PoCL traz o LLVM/Clang: ele compila os kernels `.cl` na hora em que o
serviço sobe. É o preço de não depender de GPU.

## Contrato de API (provisório — versionar no OpenAPI junto com o backend)

```
GET /saude                                                   ✅ implementado
Resp: { "servico", "versao", "status", "opencl": { "plataforma", "versao", "dispositivo", "tipo", ... } }

POST /comparar                                               ⏳ 501
Body: { "foto_url": string, "filtros": { "especie": string, "porte": string, "cor": string }, "candidatos": [{"id": int, "foto_url": string}] }
Resp: { "candidatos_ordenados": [{"id": int, "score": float, "grau_semelhanca": "alta"|"media"|"baixa"}] }

POST /extrair-descritor                                      ⏳ 501
Body: { "foto_url": string }
Resp: { "histograma_cor": [...], "textura": [...], "proporcoes": [...] }

GET /benchmark?n=1000&modo=opencl|sequencial                 ⏳ 501
Resp: { "tempo_ms": float, "breakdown": {...} }
```

Erros seguem o formato do FastAPI: `{"detail": "mensagem"}`, com `404` (rota inexistente), `405` (método
errado) e `501` (rota prevista e ainda não implementada).

## Pipeline (escopo, seção 4.6)

| Etapa | O que faz | Por que paraleliza |
|---|---|---|
| Pré-processamento | normaliza tamanho/iluminação, recorta a região do animal | cada pixel é independente |
| Extração de descritores | histograma de cor, textura, proporções | milhões de vizinhanças independentes |
| Comparação em massa | distância entre a foto de busca e cada candidato | milhares de comparações independentes |
| Lote de monitoramento | cada nova foto × todas as buscas ativas | carga recorrente que cresce com o uso |

Planejamento completo em
[`plano-sprints-equipe-3.md`](https://github.com/Equipe-BuscaPet/BuscaPet-Docs/blob/main/planejamento/plano-sprints-equipe-3.md)
(repositório `BuscaPet-Docs`).
