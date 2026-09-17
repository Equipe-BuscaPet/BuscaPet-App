# Núcleo OpenCL — `/nucleo-opencl`

Serviço HTTP separado do backend web, responsável por toda a etapa
computacionalmente pesada do reencontro por similaridade visual (RF-19 a
RF-29). Escrito em **C** com a API oficial do OpenCL (`cl.h`), rodando em
**dispositivo CPU** via **PoCL** (runtime OpenCL por software — não exige GPU).

Implementação prevista para a Sprint 3 (janela crítica do projeto, ver
[`plano-sprints-equipe-3.md`](https://github.com/Equipe-BuscaPet/Docs/blob/main/planejamento/plano-sprints-equipe-3.md) no repositório `Docs`). Nesta Sprint 2 o que existe é o contrato de
API e a estrutura de pastas — o binário ainda não faz nada.

## Contrato de API (provisório — versionar no OpenAPI junto com o backend)

```
POST /comparar
Body: { "foto_url": string, "filtros": { "especie": string, "porte": string, "cor": string }, "candidatos": [{"id": int, "foto_url": string}] }
Resp: { "candidatos_ordenados": [{"id": int, "score": float, "grau_semelhanca": "alta"|"media"|"baixa"}] }

POST /extrair-descritor
Body: { "foto_url": string }
Resp: { "histograma_cor": [...], "textura": [...], "proporcoes": [...] }

GET /benchmark?n=1000&modo=opencl|sequencial
Resp: { "tempo_ms": float, "breakdown": {...} }
```

## Pipeline (escopo, seção 4.6)

| Etapa | O que faz | Por que paraleliza |
|---|---|---|
| Pré-processamento | normaliza tamanho/iluminação, recorta a região do animal | cada pixel é independente |
| Extração de descritores | histograma de cor, textura, proporções | milhões de vizinhanças independentes |
| Comparação em massa | distância entre a foto de busca e cada candidato | milhares de comparações independentes |
| Lote de monitoramento | cada nova foto × todas as buscas ativas | carga recorrente que cresce com o uso |

## Estrutura

```
nucleo-opencl/
  src/            # kernels .cl e código C do host
  Dockerfile      # base com PoCL instalado
```
