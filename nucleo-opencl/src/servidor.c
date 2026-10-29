/*
 * servidor.c — serviço HTTP do núcleo OpenCL (porta 8001 por padrão).
 *
 * O backend (FastAPI) nunca executa OpenCL: ele chama este serviço via HTTP
 * (decisão de arquitetura da equipe). Este arquivo cuida só do HTTP; o cálculo
 * fica em src/descritor.c e nos kernels.
 *
 * Rotas:
 *   GET  /saude               estado do serviço e o dispositivo OpenCL em uso
 *   POST /extrair-descritor   {largura, altura, pixels: RGB em base64} → descritor (RF-21)
 *   POST /comparar            consultas × candidatos → notas e grau, ordenados (RF-22, RF-25)
 *   GET  /benchmark           sequencial × OpenCL, com tempos por etapa (RF-29)
 *
 * As requisições são atendidas uma por vez (uma thread de atendimento): a
 * fila do OpenCL não é compartilhada entre threads e cada pedido já usa todos
 * os núcleos da CPU sozinho.
 *
 * Bibliotecas: libmicrohttpd (servidor HTTP do projeto GNU) e cJSON.
 */
#include "descritor.h"

#include <cjson/cJSON.h>
#include <math.h>
#include <microhttpd.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VERSAO "0.2.0"
#define CORPO_MAXIMO (24u * 1024 * 1024) /* uma foto de 2048×2048 em base64 cabe com folga */
#define MAX_CANDIDATOS 200000
#define MAX_CONSULTAS 50

typedef struct {
#ifndef SEM_OPENCL
    NucleoOcl ocl;
#endif
    Nucleo nucleo;
    char *json_saude; /* montado uma vez na partida: o dispositivo não muda */
} Estado;

typedef struct {
    char *dados;
    size_t tam;
    int grande_demais;
} Pedido;

/* ------------------------------------------------------------ respostas */

static enum MHD_Result enviar_json(struct MHD_Connection *con, unsigned int status, const char *json) {
    struct MHD_Response *resp =
        MHD_create_response_from_buffer(strlen(json), (void *)json, MHD_RESPMEM_MUST_COPY);
    MHD_add_response_header(resp, "Content-Type", "application/json; charset=utf-8");
    enum MHD_Result r = MHD_queue_response(con, status, resp);
    MHD_destroy_response(resp);
    return r;
}

static enum MHD_Result enviar_objeto(struct MHD_Connection *con, unsigned int status, cJSON *obj) {
    char *texto = cJSON_PrintUnformatted(obj);
    enum MHD_Result r = enviar_json(con, status, texto);
    cJSON_free(texto);
    cJSON_Delete(obj);
    return r;
}

static enum MHD_Result enviar_erro(struct MHD_Connection *con, unsigned int status, const char *detalhe) {
    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddStringToObject(raiz, "detail", detalhe); /* mesmo campo que o FastAPI usa */
    return enviar_objeto(con, status, raiz);
}

static cJSON *json_tempos(const Tempos *t) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddNumberToObject(o, "envio_ms", t->envio_ms);
    cJSON_AddNumberToObject(o, "kernel_ms", t->kernel_ms);
    cJSON_AddNumberToObject(o, "retorno_ms", t->retorno_ms);
    cJSON_AddNumberToObject(o, "total_ms", t->total_ms);
    return o;
}

/* ------------------------------------------------------------ /saude */

#ifdef SEM_OPENCL
/* Build leve: o mesmo formato de resposta, mas avisando que não há OpenCL (a API só lê "dispositivo"). */
static char *montar_json_saude(void) {
    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddStringToObject(raiz, "servico", "nucleo-opencl");
    cJSON_AddStringToObject(raiz, "versao", VERSAO);
    cJSON_AddStringToObject(raiz, "status", "ok");
    cJSON_AddStringToObject(raiz, "versao_descritor", VERSAO_DESCRITOR);
    cJSON_AddNumberToObject(raiz, "dimensao_descritor", DIM);
    cJSON_AddStringToObject(raiz, "modo", "leve");
    cJSON *o = cJSON_AddObjectToObject(raiz, "opencl");
    cJSON_AddStringToObject(o, "plataforma", "nenhuma (build leve)");
    cJSON_AddStringToObject(o, "versao", "-");
    cJSON_AddStringToObject(o, "dispositivo", "CPU sequencial (sem OpenCL)");
    cJSON_AddStringToObject(o, "tipo", "CPU");
    cJSON_AddNumberToObject(o, "unidades_computo", 1);
    cJSON_AddNumberToObject(o, "memoria_global_mb", 0);
    char *texto = cJSON_PrintUnformatted(raiz);
    cJSON_Delete(raiz);
    return texto;
}
#else
static char *montar_json_saude(const NucleoOcl *ocl) {
    char plataforma[256], versao_ocl[256], dispositivo[256];
    ocl_info_plataforma(ocl->plataforma, CL_PLATFORM_NAME, plataforma, sizeof(plataforma));
    ocl_info_plataforma(ocl->plataforma, CL_PLATFORM_VERSION, versao_ocl, sizeof(versao_ocl));
    ocl_info_dispositivo(ocl->dispositivo, CL_DEVICE_NAME, dispositivo, sizeof(dispositivo));

    cl_device_type tipo = 0;
    cl_uint unidades = 0;
    cl_ulong memoria = 0;
    clGetDeviceInfo(ocl->dispositivo, CL_DEVICE_TYPE, sizeof(tipo), &tipo, NULL);
    clGetDeviceInfo(ocl->dispositivo, CL_DEVICE_MAX_COMPUTE_UNITS, sizeof(unidades), &unidades, NULL);
    clGetDeviceInfo(ocl->dispositivo, CL_DEVICE_GLOBAL_MEM_SIZE, sizeof(memoria), &memoria, NULL);

    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddStringToObject(raiz, "servico", "nucleo-opencl");
    cJSON_AddStringToObject(raiz, "versao", VERSAO);
    cJSON_AddStringToObject(raiz, "status", "ok");
    cJSON_AddStringToObject(raiz, "versao_descritor", VERSAO_DESCRITOR);
    cJSON_AddNumberToObject(raiz, "dimensao_descritor", DIM);
    cJSON *o = cJSON_AddObjectToObject(raiz, "opencl");
    cJSON_AddStringToObject(o, "plataforma", plataforma);
    cJSON_AddStringToObject(o, "versao", versao_ocl);
    cJSON_AddStringToObject(o, "dispositivo", dispositivo);
    cJSON_AddStringToObject(o, "tipo", (tipo & CL_DEVICE_TYPE_GPU) ? "GPU"
                                      : (tipo & CL_DEVICE_TYPE_CPU) ? "CPU" : "outro");
    cJSON_AddNumberToObject(o, "unidades_computo", unidades);
    cJSON_AddNumberToObject(o, "memoria_global_mb", (double)(memoria / (1024 * 1024)));

    char *texto = cJSON_PrintUnformatted(raiz);
    cJSON_Delete(raiz);
    return texto;
}

#endif /* SEM_OPENCL */

/* ------------------------------------------------------------ /extrair-descritor */

static int valor_base64(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

/* Decodifica base64 (padrão, com ou sem "="). Devolve o tamanho ou -1 se inválido. */
static long decodificar_base64(const char *txt, uint8_t **saida) {
    const size_t n = strlen(txt);
    uint8_t *buf = malloc(n / 4 * 3 + 3);
    long tam = 0;
    int acumulado = 0, bits = 0;
    for (size_t i = 0; i < n; i++) {
        if (txt[i] == '=') break;
        const int v = valor_base64(txt[i]);
        if (v < 0) {
            free(buf);
            return -1;
        }
        acumulado = (acumulado << 6) | v;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            buf[tam++] = (uint8_t)((acumulado >> bits) & 0xFF);
        }
    }
    *saida = buf;
    return tam;
}

static enum MHD_Result rota_extrair(Estado *e, struct MHD_Connection *con, cJSON *corpo) {
    const cJSON *jw = cJSON_GetObjectItem(corpo, "largura"), *jh = cJSON_GetObjectItem(corpo, "altura");
    const cJSON *jp = cJSON_GetObjectItem(corpo, "pixels");
    if (!cJSON_IsNumber(jw) || !cJSON_IsNumber(jh) || !cJSON_IsString(jp))
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "Envie largura, altura e pixels (RGB em base64).");
    const int w = jw->valueint, h = jh->valueint;
    if (w < 1 || h < 1 || w > LADO_MAXIMO || h > LADO_MAXIMO)
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "Largura e altura precisam estar entre 1 e 2048.");
    uint8_t *rgb = NULL;
    const long tam = decodificar_base64(jp->valuestring, &rgb);
    if (tam != (long)w * h * 3) {
        free(rgb);
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "Os pixels não batem com largura × altura × 3 (RGB).");
    }
    Imagem img = {rgb, w, h};
    float d[DIM];
    Tempos t;
    descritor_opencl(&e->nucleo, &img, 1, d, &t);
    free(rgb);

    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddItemToObject(raiz, "descritor", cJSON_CreateFloatArray(d, DIM));
    cJSON_AddStringToObject(raiz, "versao", VERSAO_DESCRITOR);
    cJSON_AddItemToObject(raiz, "tempos", json_tempos(&t));
    return enviar_objeto(con, MHD_HTTP_OK, raiz);
}

/* ------------------------------------------------------------ /comparar */

/* Lê um descritor do JSON; 0 se tiver o tamanho certo e só números. */
static int ler_descritor(const cJSON *arr, float *saida) {
    if (!cJSON_IsArray(arr) || cJSON_GetArraySize(arr) != DIM) return -1;
    int k = 0;
    const cJSON *v;
    cJSON_ArrayForEach(v, arr) {
        if (!cJSON_IsNumber(v)) return -1;
        saida[k++] = (float)v->valuedouble;
    }
    return 0;
}

typedef struct {
    int id;
    float nota;
} Par;

static int por_nota(const void *a, const void *b) {
    const Par *x = a, *y = b;
    if (x->nota != y->nota) return x->nota < y->nota ? 1 : -1;
    return (x->id > y->id) - (x->id < y->id); /* empate: menor id primeiro, ordem estável */
}

static enum MHD_Result rota_comparar(Estado *e, struct MHD_Connection *con, cJSON *corpo) {
    const cJSON *jcons = cJSON_GetObjectItem(corpo, "consultas"), *jcand = cJSON_GetObjectItem(corpo, "candidatos");
    const cJSON *jmodo = cJSON_GetObjectItem(corpo, "modo");
    const int sequencial = cJSON_IsString(jmodo) && strcmp(jmodo->valuestring, "sequencial") == 0;
    if (!cJSON_IsArray(jcons) || !cJSON_IsArray(jcand))
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "Envie consultas (lista de descritores) e candidatos ({id, descritor}).");
    const int m = cJSON_GetArraySize(jcons), n = cJSON_GetArraySize(jcand);
    if (m < 1 || m > MAX_CONSULTAS || n > MAX_CANDIDATOS)
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "Envie de 1 a 50 consultas e até 200.000 candidatos.");

    float *cons = malloc(sizeof(float) * DIM * (size_t)m), *cand = malloc(sizeof(float) * DIM * (size_t)(n ? n : 1));
    int *ids = malloc(sizeof(int) * (size_t)(n ? n : 1));
    int i = 0, invalido = 0;
    const cJSON *item;
    cJSON_ArrayForEach(item, jcons) invalido |= ler_descritor(item, cons + (size_t)i++ * DIM);
    i = 0;
    cJSON_ArrayForEach(item, jcand) {
        const cJSON *jid = cJSON_GetObjectItem(item, "id");
        invalido |= !cJSON_IsNumber(jid) || ler_descritor(cJSON_GetObjectItem(item, "descritor"), cand + (size_t)i * DIM);
        ids[i++] = jid ? jid->valueint : 0;
    }
    if (invalido) {
        free(cons);
        free(cand);
        free(ids);
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "Cada descritor precisa ter 224 números (versão v1).");
    }

    float *notas = malloc(sizeof(float) * (size_t)m * (n ? n : 1));
    Tempos t = {0};
    if (n > 0) {
        if (sequencial) comparar_sequencial(cons, m, cand, n, notas, &t);
        else comparar_opencl(&e->nucleo, cons, m, cand, n, notas, &t);
    }

    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddStringToObject(raiz, "modo", sequencial ? "sequencial" : "opencl");
    cJSON *resultados = cJSON_AddArrayToObject(raiz, "resultados");
    Par *pares = malloc(sizeof(Par) * (size_t)(n ? n : 1));
    for (int c = 0; c < m; c++) {
        for (int j = 0; j < n; j++) pares[j] = (Par){ids[j], notas[(size_t)c * n + j]};
        qsort(pares, (size_t)n, sizeof(Par), por_nota);
        cJSON *lista = cJSON_CreateArray();
        for (int j = 0; j < n; j++) {
            cJSON *o = cJSON_CreateObject();
            cJSON_AddNumberToObject(o, "id", pares[j].id);
            cJSON_AddNumberToObject(o, "nota", pares[j].nota);
            cJSON_AddStringToObject(o, "grau", grau_semelhanca(pares[j].nota));
            cJSON_AddItemToArray(lista, o);
        }
        cJSON_AddItemToArray(resultados, lista);
    }
    cJSON_AddItemToObject(raiz, "tempos", json_tempos(&t));
    free(pares);
    free(cons);
    free(cand);
    free(ids);
    free(notas);
    return enviar_objeto(con, MHD_HTTP_OK, raiz);
}

/* ------------------------------------------------------------ /benchmark */

static unsigned semente_bench = 2026;
static float aleatorio01(void) {
    semente_bench = semente_bench * 1103515245u + 12345u;
    return (float)((semente_bench >> 8) & 0xFFFF) / 65535.0f;
}

static void descritores_aleatorios(float *d, int n) {
    for (int i = 0; i < n; i++) {
        float *v = d + (size_t)i * DIM, sc = 0, st = 0;
        memset(v, 0, sizeof(float) * DIM);
        for (int k = D_COR; k < D_TEXTURA; k++) sc += v[k] = aleatorio01() < 0.2f ? aleatorio01() : 0;
        for (int k = D_TEXTURA; k < D_PROPORCOES; k++) st += v[k] = aleatorio01();
        for (int k = D_COR; k < D_TEXTURA; k++) v[k] /= sc > 0 ? sc : 1;
        for (int k = D_TEXTURA; k < D_PROPORCOES; k++) v[k] /= st > 0 ? st : 1;
        for (int k = D_PROPORCOES; k < D_PROPORCOES + 5; k++) v[k] = aleatorio01();
    }
}

/* GET /benchmark?etapa=busca|lote|extracao&n=1000 — roda as duas versões
 * (com 1 aquecimento e média de 3) e confere se dão o mesmo resultado. */
#ifdef SEM_OPENCL
static enum MHD_Result rota_benchmark(Estado *e, struct MHD_Connection *con) {
    (void)e;
    return enviar_erro(con, MHD_HTTP_NOT_IMPLEMENTED, "Benchmark indisponível: este núcleo foi compilado sem OpenCL (build leve).");
}

#else
static enum MHD_Result rota_benchmark(Estado *e, struct MHD_Connection *con) {
    const char *etapa = MHD_lookup_connection_value(con, MHD_GET_ARGUMENT_KIND, "etapa");
    const char *n_txt = MHD_lookup_connection_value(con, MHD_GET_ARGUMENT_KIND, "n");
    if (!etapa) etapa = "busca";
    const int n = n_txt ? atoi(n_txt) : 1000;
    const int busca = strcmp(etapa, "busca") == 0, lote = strcmp(etapa, "lote") == 0;
    const int extracao = strcmp(etapa, "extracao") == 0;
    if (!busca && !lote && !extracao)
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, "etapa precisa ser busca, lote ou extracao.");
    const int limite = extracao ? 2000 : busca ? 200000 : 20000;
    if (n < 1 || n > limite) {
        char msg[96];
        snprintf(msg, sizeof(msg), "Para a etapa %s, n vai de 1 a %d.", etapa, limite);
        return enviar_erro(con, MHD_HTTP_UNPROCESSABLE_CONTENT, msg);
    }

    const int REP = 3;
    Tempos s = {0}, o = {0}, t;
    int iguais = 1;
    double comparacoes = 0;
    if (extracao) {
        Imagem *imgs = malloc(sizeof(Imagem) * (size_t)n);
        for (int i = 0; i < n; i++) {
            uint8_t *rgb = malloc(320 * 240 * 3);
            for (int k = 0; k < 320 * 240 * 3; k++) rgb[k] = (uint8_t)(aleatorio01() * 255);
            imgs[i] = (Imagem){rgb, 320, 240};
        }
        float *ds = malloc(sizeof(float) * DIM * (size_t)n), *dp = malloc(sizeof(float) * DIM * (size_t)n);
        descritor_opencl(&e->nucleo, imgs, n, dp, &t);
        for (int r = 0; r < REP; r++) {
            descritor_sequencial(imgs, n, ds, &t);
            s.envio_ms += t.envio_ms / REP, s.kernel_ms += t.kernel_ms / REP, s.retorno_ms += t.retorno_ms / REP, s.total_ms += t.total_ms / REP;
            descritor_opencl(&e->nucleo, imgs, n, dp, &t);
            o.envio_ms += t.envio_ms / REP, o.kernel_ms += t.kernel_ms / REP, o.retorno_ms += t.retorno_ms / REP, o.total_ms += t.total_ms / REP;
        }
        iguais = memcmp(ds, dp, sizeof(float) * DIM * (size_t)n) == 0;
        for (int i = 0; i < n; i++) free((void *)imgs[i].rgb);
        free(imgs);
        free(ds);
        free(dp);
    } else {
        const int m = busca ? 1 : 100;
        float *cons = malloc(sizeof(float) * DIM * (size_t)m), *cand = malloc(sizeof(float) * DIM * (size_t)n);
        descritores_aleatorios(cons, m);
        descritores_aleatorios(cand, n);
        float *ns = malloc(sizeof(float) * (size_t)m * n), *np = malloc(sizeof(float) * (size_t)m * n);
        comparar_opencl(&e->nucleo, cons, m, cand, n, np, &t);
        for (int r = 0; r < REP; r++) {
            comparar_sequencial(cons, m, cand, n, ns, &t);
            s.envio_ms += t.envio_ms / REP, s.kernel_ms += t.kernel_ms / REP, s.retorno_ms += t.retorno_ms / REP, s.total_ms += t.total_ms / REP;
            comparar_opencl(&e->nucleo, cons, m, cand, n, np, &t);
            o.envio_ms += t.envio_ms / REP, o.kernel_ms += t.kernel_ms / REP, o.retorno_ms += t.retorno_ms / REP, o.total_ms += t.total_ms / REP;
        }
        for (size_t k = 0; k < (size_t)m * n; k++) iguais &= fabsf(ns[k] - np[k]) <= 1e-5f;
        comparacoes = (double)m * n;
        free(cons);
        free(cand);
        free(ns);
        free(np);
    }

    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddStringToObject(raiz, "etapa", etapa);
    cJSON_AddNumberToObject(raiz, "n", n);
    if (lote) cJSON_AddNumberToObject(raiz, "consultas", 100);
    cJSON_AddItemToObject(raiz, "sequencial", json_tempos(&s));
    cJSON_AddItemToObject(raiz, "opencl", json_tempos(&o));
    cJSON_AddNumberToObject(raiz, "speedup", o.total_ms > 0 ? s.total_ms / o.total_ms : 0);
    cJSON_AddNumberToObject(raiz, "speedup_kernel", o.kernel_ms > 0 ? s.kernel_ms / o.kernel_ms : 0);
    if (comparacoes > 0) {
        cJSON_AddNumberToObject(raiz, "comparacoes_por_s_sequencial", comparacoes / (s.total_ms / 1000));
        cJSON_AddNumberToObject(raiz, "comparacoes_por_s_opencl", comparacoes / (o.total_ms / 1000));
    }
    cJSON_AddBoolToObject(raiz, "resultados_iguais", iguais);
    cJSON_AddNumberToObject(raiz, "repeticoes", REP);
    return enviar_objeto(con, MHD_HTTP_OK, raiz);
}

#endif /* SEM_OPENCL */

/* ------------------------------------------------------------ roteamento */

static void fim_pedido(void *cls, struct MHD_Connection *con, void **estado_req,
                       enum MHD_RequestTerminationCode motivo) {
    (void)cls;
    (void)con;
    (void)motivo;
    Pedido *p = *estado_req;
    if (p) {
        free(p->dados);
        free(p);
    }
    *estado_req = NULL;
}

static enum MHD_Result responder(void *cls, struct MHD_Connection *con, const char *url,
                                 const char *metodo, const char *versao, const char *dados,
                                 size_t *tam_dados, void **estado_req) {
    (void)versao;
    Estado *estado = cls;

    /* A libmicrohttpd chama esta função várias vezes por requisição: na primeira
     * criamos o acumulador do corpo; nas seguintes chegam os pedaços do corpo;
     * na última (*tam_dados == 0) respondemos. */
    if (*estado_req == NULL) {
        *estado_req = calloc(1, sizeof(Pedido));
        return MHD_YES;
    }
    Pedido *p = *estado_req;
    if (*tam_dados != 0) {
        if (p->tam + *tam_dados > CORPO_MAXIMO) {
            p->grande_demais = 1;
        } else {
            char *novo = realloc(p->dados, p->tam + *tam_dados + 1);
            if (!novo) {
                p->grande_demais = 1;
            } else {
                p->dados = novo;
                memcpy(p->dados + p->tam, dados, *tam_dados);
                p->tam += *tam_dados;
                p->dados[p->tam] = '\0';
            }
        }
        *tam_dados = 0;
        return MHD_YES;
    }

    const int get = strcmp(metodo, "GET") == 0, post = strcmp(metodo, "POST") == 0;
    const double inicio = agora_ms();
    unsigned int status = 0;
    enum MHD_Result r;
    if (strcmp(url, "/saude") == 0) {
        status = get ? MHD_HTTP_OK : MHD_HTTP_METHOD_NOT_ALLOWED;
        r = get ? enviar_json(con, status, estado->json_saude) : enviar_erro(con, status, "Use GET em /saude.");
    } else if (strcmp(url, "/benchmark") == 0) {
        status = get ? MHD_HTTP_OK : MHD_HTTP_METHOD_NOT_ALLOWED;
        r = get ? rota_benchmark(estado, con) : enviar_erro(con, status, "Use GET em /benchmark.");
    } else if (strcmp(url, "/extrair-descritor") == 0 || strcmp(url, "/comparar") == 0) {
        cJSON *corpo = NULL;
        if (!post) {
            status = MHD_HTTP_METHOD_NOT_ALLOWED;
            r = enviar_erro(con, status, "Use POST nesta rota.");
        } else if (p->grande_demais) {
            status = MHD_HTTP_CONTENT_TOO_LARGE;
            r = enviar_erro(con, status, "Corpo grande demais (limite de 24 MB).");
        } else if (!p->dados || !(corpo = cJSON_Parse(p->dados))) {
            status = MHD_HTTP_BAD_REQUEST;
            r = enviar_erro(con, status, "Corpo precisa ser um JSON válido.");
        } else {
            status = MHD_HTTP_OK; /* o status real vai no log só como "respondido" */
            r = strcmp(url, "/comparar") == 0 ? rota_comparar(estado, con, corpo) : rota_extrair(estado, con, corpo);
        }
        cJSON_Delete(corpo);
    } else {
        status = MHD_HTTP_NOT_FOUND;
        r = enviar_erro(con, status, "Rota não encontrada.");
    }
    printf("%s %s -> %u (%.1f ms)\n", metodo, url, status, agora_ms() - inicio);
    fflush(stdout);
    return r;
}

int main(void) {
    const char *porta_txt = getenv("PORTA");
    const int porta = porta_txt ? atoi(porta_txt) : 8001;

    Estado estado;
#ifdef SEM_OPENCL
    estado.json_saude = montar_json_saude();
#else
    if (ocl_iniciar(&estado.ocl, 1) != 0) return EXIT_FAILURE; /* sem OpenCL, não sobe */
    nucleo_preparar(&estado.nucleo, &estado.ocl);                /* compila os kernels uma vez */
    estado.json_saude = montar_json_saude(&estado.ocl);
#endif

    /* Bloqueia SIGINT/SIGTERM antes de criar as threads do servidor, para que
     * só a thread principal os receba (via sigwait) e o encerramento seja limpo
     * quando o Docker parar o container. */
    sigset_t sinais;
    sigemptyset(&sinais);
    sigaddset(&sinais, SIGINT);
    sigaddset(&sinais, SIGTERM);
    pthread_sigmask(SIG_BLOCK, &sinais, NULL);

    struct MHD_Daemon *daemon =
        MHD_start_daemon(MHD_USE_INTERNAL_POLLING_THREAD | MHD_USE_ERROR_LOG, (uint16_t)porta, NULL, NULL,
                         &responder, &estado, MHD_OPTION_NOTIFY_COMPLETED, &fim_pedido, NULL,
                         MHD_OPTION_CONNECTION_TIMEOUT, (unsigned int)120, MHD_OPTION_END);
    if (!daemon) {
        fprintf(stderr, "[nucleo] não consegui abrir a porta %d.\n", porta);
        return EXIT_FAILURE;
    }
    printf("[nucleo] ouvindo na porta %d — %s\n", porta, estado.json_saude);
    fflush(stdout);

    int sinal;
    sigwait(&sinais, &sinal);
    printf("[nucleo] sinal %d recebido, encerrando.\n", sinal);

    MHD_stop_daemon(daemon);
    cJSON_free(estado.json_saude);
#ifndef SEM_OPENCL
    nucleo_liberar(&estado.nucleo);
    ocl_encerrar(&estado.ocl);
#endif
    return EXIT_SUCCESS;
}
