/*
 * servidor.c — serviço HTTP do núcleo OpenCL (porta 8001 por padrão).
 *
 * O backend (FastAPI) nunca executa OpenCL: ele chama este serviço via HTTP
 * (decisão fechada no CONTEXTO §5). Este arquivo cuida só do HTTP; o cálculo
 * fica nos kernels e nos módulos de cada etapa do pipeline.
 *
 * Rotas implementadas:
 *   GET /saude   estado do serviço e qual dispositivo OpenCL ele está usando
 * Rotas do contrato que ainda virão (README): POST /extrair-descritor,
 * POST /comparar, GET /benchmark. Por enquanto respondem 501 (não implementado).
 *
 * Bibliotecas: libmicrohttpd (servidor HTTP do projeto GNU) e cJSON.
 */
#include "ocl.h"

#include <cjson/cJSON.h>
#include <microhttpd.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VERSAO "0.1.0"

typedef struct {
    NucleoOcl ocl;
    char *json_saude; /* montado uma vez na partida: o dispositivo não muda */
} Estado;

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

static enum MHD_Result enviar_json(struct MHD_Connection *con, unsigned int status, const char *json) {
    struct MHD_Response *resp =
        MHD_create_response_from_buffer(strlen(json), (void *)json, MHD_RESPMEM_MUST_COPY);
    MHD_add_response_header(resp, "Content-Type", "application/json; charset=utf-8");
    enum MHD_Result r = MHD_queue_response(con, status, resp);
    MHD_destroy_response(resp);
    return r;
}

static enum MHD_Result enviar_erro(struct MHD_Connection *con, unsigned int status, const char *detalhe) {
    cJSON *raiz = cJSON_CreateObject();
    cJSON_AddStringToObject(raiz, "detail", detalhe); /* mesmo campo que o FastAPI usa */
    char *texto = cJSON_PrintUnformatted(raiz);
    enum MHD_Result r = enviar_json(con, status, texto);
    cJSON_free(texto);
    cJSON_Delete(raiz);
    return r;
}

static int eh_rota_futura(const char *url) {
    return strcmp(url, "/extrair-descritor") == 0 || strcmp(url, "/comparar") == 0 ||
           strcmp(url, "/benchmark") == 0;
}

static enum MHD_Result responder(void *cls, struct MHD_Connection *con, const char *url,
                                 const char *metodo, const char *versao, const char *dados,
                                 size_t *tam_dados, void **estado_req) {
    (void)versao;
    (void)dados;
    Estado *estado = cls;

    /* A libmicrohttpd chama esta função mais de uma vez por requisição; na
     * primeira só marcamos que ela começou (padrão da biblioteca). */
    static int marcador;
    if (*estado_req == NULL) {
        *estado_req = &marcador;
        return MHD_YES;
    }
    if (*tam_dados != 0) { /* corpo ignorado por enquanto: nenhuma rota lê corpo */
        *tam_dados = 0;
        return MHD_YES;
    }

    unsigned int status;
    enum MHD_Result r;
    if (strcmp(url, "/saude") == 0) {
        if (strcmp(metodo, "GET") == 0) {
            status = MHD_HTTP_OK;
            r = enviar_json(con, status, estado->json_saude);
        } else {
            status = MHD_HTTP_METHOD_NOT_ALLOWED;
            r = enviar_erro(con, status, "Use GET em /saude.");
        }
    } else if (eh_rota_futura(url)) {
        status = MHD_HTTP_NOT_IMPLEMENTED;
        r = enviar_erro(con, status, "Rota prevista no contrato, ainda não implementada.");
    } else {
        status = MHD_HTTP_NOT_FOUND;
        r = enviar_erro(con, status, "Rota não encontrada.");
    }
    printf("%s %s -> %u\n", metodo, url, status);
    fflush(stdout);
    return r;
}

int main(void) {
    const char *porta_txt = getenv("PORTA");
    const int porta = porta_txt ? atoi(porta_txt) : 8001;

    Estado estado;
    if (ocl_iniciar(&estado.ocl, 0) != 0) return EXIT_FAILURE; /* sem OpenCL, não sobe */
    estado.json_saude = montar_json_saude(&estado.ocl);

    /* Bloqueia SIGINT/SIGTERM antes de criar as threads do servidor, para que
     * só a thread principal os receba (via sigwait) e o encerramento seja limpo
     * quando o Docker parar o container. */
    sigset_t sinais;
    sigemptyset(&sinais);
    sigaddset(&sinais, SIGINT);
    sigaddset(&sinais, SIGTERM);
    pthread_sigmask(SIG_BLOCK, &sinais, NULL);

    struct MHD_Daemon *daemon =
        MHD_start_daemon(MHD_USE_INTERNAL_POLLING_THREAD | MHD_USE_ERROR_LOG, (uint16_t)porta, NULL,
                         NULL, &responder, &estado, MHD_OPTION_END);
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
    ocl_encerrar(&estado.ocl);
    return EXIT_SUCCESS;
}
