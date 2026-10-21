# Núcleo OpenCL — `/nucleo-opencl`

Serviço HTTP separado do backend web, responsável por toda a etapa computacionalmente pesada do
reencontro por similaridade visual (RF-21 a RF-29). Escrito em **C** com a API oficial do OpenCL
(`CL/cl.h`) e roda em **dispositivo CPU** via **PoCL** (runtime OpenCL por software, que não exige GPU).
O backend nunca executa OpenCL: ele chama este serviço via HTTP (`NUCLEO_OPENCL_URL`), em `api/app/core/nucleo.py`.

## Estado atual

| Item | Situação |
|---|---|
| Spike: kernel `soma_vetores` + teste de equivalência | ✅ |
| Serviço HTTP (`libmicrohttpd` + `cJSON`) | ✅ `GET /saude`, `POST /extrair-descritor`, `POST /comparar`, `GET /benchmark` |
| Pré-processamento e descritores (RF-21): tamanho, iluminação, recorte do animal, cor, textura, proporções | ✅ sequencial + OpenCL, **iguais bit a bit** |
| Comparação em massa (RF-22, RF-25): 1 × N (busca) e M × N (monitoramento) | ✅ sequencial + OpenCL, mesmo ranking |
| Modo comparativo de desempenho (RF-29) | ✅ `GET /benchmark`, `bench curva`, `bench moer` |
| Build em Docker que só gera a imagem se todos os testes passarem | ✅ |
| CI: compila, testa, sobe o serviço e roda a API contra ele com fotos reais | ✅ |

## Como rodar

Só é preciso ter o Docker. Compilador C, PoCL e bibliotecas ficam todos dentro da imagem, e por isso o
resultado é igual em qualquer máquina do time e na CI.

```bash
# a partir da raiz do BuscaPet-App
docker compose up -d --build nucleo-opencl
curl localhost:8001/saude
```

Para a API usar o núcleo rodando fora do Docker Compose (desenvolvimento local), defina no `api/.env`:
`NUCLEO_OPENCL_URL=http://127.0.0.1:8001`. Fotos enviadas com o núcleo desligado ficam sem descritor; depois
rode `python -m app.scripts.indexar_fotos` (ou o botão da administração) para calcular os que faltam.

## Teste visual: ver os núcleos trabalhando

1. Abra o **Gerenciador de Tarefas** → **Desempenho** → **CPU** → botão direito no gráfico →
   **Alterar gráfico para → Processadores lógicos** (um gráfico por núcleo).
2. Rode (20 segundos em cada modo):

```bash
docker compose run --rm nucleo-opencl ./bench moer 20
```

No modo **sequencial** só um núcleo fica cheio; no **OpenCL** todos sobem juntos. O processo que aparece é o
da máquina virtual do Docker (`Vmmem` no Windows). Resultado na máquina de referência (i5-2400, 4 núcleos):
**1,06 milhão → 3,26 milhões de comparações por segundo (3,1×)**.

> No Git Bash do Windows, ao montar pastas com `docker run -v`, use `MSYS_NO_PATHCONV=1` na frente do comando:
> sem isso o Git Bash troca `/src` por `C:/Program Files/Git/src`.

## O pipeline

Cada foto vira um **descritor** de 224 números (versão `v1`). Toda a conta é feita com inteiros até o fim, de
propósito: assim a versão paralela devolve exatamente os mesmos números que a sequencial.

| Etapa | Kernel | O que faz |
|---|---|---|
| Pré-processamento | `redimensionar` | qualquer tamanho → 128×128 (bilinear em ponto fixo) |
| | `somar_canais` | médias de R, G, B da foto e da moldura (cor do fundo) |
| Descritores | `descrever` | corrige a iluminação (cor e brilho), separa o animal do fundo, histograma de **cor** (52 tons × 4 regiões), **textura** da pelagem (LBP, 10 classes) e **proporções** do animal |
| Comparação | `comparar` | qui-quadrado entre histogramas + diferença de proporções → nota de 0 a 1 → grau **alta** (≥ 0,75), **média** (≥ 0,55) ou **baixa** |

O sistema nunca afirma que encontrou o animal: a nota só ordena os candidatos (escopo, seção 4.3).

**Decisões de desempenho** (cada uma medida antes e depois):
- **Itens de trabalho por bloco de 8 linhas, não por pixel.** Por pixel, 16 mil itens minúsculos por foto
  disputavam os mesmos contadores e o OpenCL não ganhava do sequencial; por bloco, cada item faz bastante conta
  e a disputa acontece uma vez por bloco.
- **Sem cópia (zero-copy, `CL_MEM_USE_HOST_PTR`).** Como o dispositivo é a própria CPU, o kernel lê os dados
  direto da memória do programa. Copiar 90 MB de candidatos por busca era o que dominava o tempo antes.
- **Aquecimento na partida.** O PoCL termina de compilar cada kernel no primeiro uso (~0,5 s); o servidor faz
  isso ao subir, para a primeira busca de verdade não ficar lenta.

## Benchmark (RF-29)

Curva de escala de 20/10/2026 (`bench curva`, média de 3 execuções após 1 de aquecimento, i5-2400, 4 núcleos;
CSV completo em [`bench/curva-2026-10-20-i5-2400.csv`](bench/curva-2026-10-20-i5-2400.csv)):

| Etapa | n | Sequencial (ms) | OpenCL (ms) | Speedup |
|---|---:|---:|---:|---:|
| Busca: 1 foto × n candidatos | 1.000 | 1,1 | 1,5 | 0,7× |
| | 10.000 | 14,0 | 4,3 | 3,2× |
| | 100.000 | 104,3 | 31,9 | **3,3×** |
| Lote: 100 fotos novas × n buscas ativas | 1.000 | 101,9 | 25,5 | 4,0× |
| | 10.000 | 1.030,3 | 269,2 | **3,8×** |
| Extração: n fotos 320×240 | 10 | 11,9 | 7,5 | 1,6× |
| | 1.000 | 1.165,9 | 554,5 | **2,1×** (kernel 3,1×) |

**Leitura (Lei de Amdahl):** com poucos registros o OpenCL perde, porque o custo fixo de enfileirar o trabalho
domina; o ganho cresce com o volume e chega perto do número de núcleos (4), mas não passa dele, e sobra sempre
uma parte serial (juntar as fotos, montar o descritor, ordenar). Na extração, a parte serial é maior, e por isso
o total (2,1×) fica abaixo do kernel (3,1×). O RF-29 também está na API: `GET /admin/nucleo/benchmark`.

## Testes

`make teste` (executado no `docker build` e na CI):

| Teste | O que garante |
|---|---|
| `spike` com N = 1, 1.000.003 (primo) e 4.194.304 | OpenCL funcionando, sem erro de borda |
| `teste-nucleo`: equivalência dos descritores | sequencial × OpenCL **iguais bit a bit** em fotos de 1×1, 3×2, 37×501, 128×128, 640×480 e 1024×768, uma a uma e em lote |
| `teste-nucleo`: equivalência da comparação | 3 × 1.003 notas com diferença ≤ 1e-5 e o mesmo ranking |
| `teste-nucleo`: comportamento | mesma cena em outro tamanho ou com 40% menos luz = alta; outro animal = baixa |

Na API, `api/tests/test_nucleo_real.py` (rodado na CI com o serviço no ar) manda fotos reais: o mesmo cão,
espelhado, mais escuro e recortado, sai em primeiro e "alta"; o gato sai "baixa"; OpenCL e sequencial dão o
mesmo ranking.

**Regra para todo kernel novo:** ele só entra quando a saída paralela bater com a versão sequencial.

## Contrato de API

```
GET  /saude
     → {servico, versao, status, versao_descritor, dimensao_descritor, opencl: {plataforma, dispositivo, unidades_computo, ...}}

POST /extrair-descritor   {"largura": int, "altura": int, "pixels": "<RGB em base64>"}   (até 2048×2048)
     → {"descritor": [224 números], "versao": "v1", "tempos": {envio_ms, kernel_ms, retorno_ms, total_ms}}

POST /comparar            {"consultas": [[224]...], "candidatos": [{"id": int, "descritor": [224]}], "modo": "opencl"|"sequencial"}
     → {"modo", "resultados": [[{"id", "nota", "grau"}...] por consulta, do mais parecido ao menos], "tempos"}

GET  /benchmark?etapa=busca|lote|extracao&n=1000
     → {etapa, n, sequencial: {tempos}, opencl: {tempos}, speedup, speedup_kernel, resultados_iguais, comparacoes_por_s_*}
```

A API abre a foto com o Pillow e manda os pixels (no máximo 512 px de lado; o núcleo reduz para 128×128):
assim o núcleo não precisa decodificar JPEG nem buscar arquivos. Erros seguem o formato do FastAPI:
`{"detail": "mensagem"}`, com `400`, `404`, `405`, `413` e `422`.

## Estrutura

```
nucleo-opencl/
  kernels/
    soma_vetores.cl   kernel do spike
    descritor.cl      pré-processamento e descritores (redimensionar, somar_canais, descrever)
    comparar.cl       comparação em massa
  src/
    ocl.c / ocl.h     utilidades: escolher dispositivo, compilar kernel, medir tempo, traduzir erros
    descritor.c / .h  as duas versões (sequencial e OpenCL) de cada etapa
    servidor.c        serviço HTTP (porta 8001, variável PORTA)
    teste_nucleo.c    testes de equivalência e de comportamento
    bench.c           benchmark: curva de escala (CSV) e o "teste visual"
    spike.c           teste de equivalência do spike + medição de tempos
  bench/              resultados do benchmark (CSV), um arquivo por máquina
  Makefile            make · make teste · make limpar
  Dockerfile          estágio 1 compila e testa; estágio 2 leva só os binários (usuário sem root)
```

Variáveis de ambiente: `PORTA` (padrão `8001`), `NUCLEO_KERNELS` (pasta dos `.cl`, padrão `kernels`),
`POCL_CACHE_DIR` (cache dos kernels já compilados) e `NUCLEO_PERFIL=1` (imprime o tempo de cada kernel).

A imagem final tem ~850 MB porque o PoCL traz o LLVM/Clang: ele compila os kernels `.cl` na hora em que o
serviço sobe. É o preço de não depender de GPU.
