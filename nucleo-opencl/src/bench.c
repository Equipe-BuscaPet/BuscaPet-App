/*
 * bench.c — benchmark do núcleo (RF-29): sequencial × OpenCL.
 *
 *   bench curva            curva de escala em CSV (etapa, n, modo, tempos em ms)
 *   bench moer [SEGUNDOS]  "teste visual": roda o lote de comparação sem parar,
 *                          primeiro sequencial e depois em OpenCL, para ver no
 *                          Gerenciador de Tarefas 1 núcleo × todos os núcleos
 *
 * Etapas medidas (notas técnicas, seção 4):
 *   busca     1 foto buscada contra N candidatos (o que o tutor faz)
 *   extracao  N fotos 320×240 viram descritores (cadastro em massa / reindexação)
 *   lote      100 fotos novas contra N buscas ativas (monitoramento contínuo, RF-25)
 * Cada ponto é a média de 3 execuções, depois de 1 de aquecimento.
 */
#include "descritor.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned semente = 2026;
static float aleatorio01(void) {
    semente = semente * 1103515245u + 12345u;
    return (float)((semente >> 8) & 0xFFFF) / 65535.0f;
}

/* descritores sintéticos com a mesma forma dos reais (histogramas que somam 1) */
static float *descritores_aleatorios(int n) {
    float *d = malloc(sizeof(float) * DIM * (size_t)n);
    for (int i = 0; i < n; i++) {
        float *v = d + (size_t)i * DIM, sc = 0, st = 0;
        for (int k = 0; k < DIM; k++) v[k] = 0;
        for (int k = D_COR; k < D_TEXTURA; k++) sc += v[k] = aleatorio01() < 0.2f ? aleatorio01() : 0;
        for (int k = D_TEXTURA; k < D_PROPORCOES; k++) st += v[k] = aleatorio01();
        for (int k = D_COR; k < D_TEXTURA; k++) v[k] /= sc > 0 ? sc : 1;
        for (int k = D_TEXTURA; k < D_PROPORCOES; k++) v[k] /= st > 0 ? st : 1;
        for (int k = D_PROPORCOES; k < D_PROPORCOES + 5; k++) v[k] = aleatorio01();
    }
    return d;
}

static Imagem *fotos_aleatorias(int n, int w, int h) {
    Imagem *imgs = malloc(sizeof(Imagem) * (size_t)n);
    for (int i = 0; i < n; i++) {
        uint8_t *rgb = malloc((size_t)w * h * 3);
        for (size_t k = 0; k < (size_t)w * h * 3; k++) rgb[k] = (uint8_t)(aleatorio01() * 255);
        imgs[i] = (Imagem){rgb, w, h};
    }
    return imgs;
}

static void media(Tempos *acc, const Tempos *t, int vezes) {
    acc->envio_ms += t->envio_ms / vezes;
    acc->kernel_ms += t->kernel_ms / vezes;
    acc->retorno_ms += t->retorno_ms / vezes;
    acc->total_ms += t->total_ms / vezes;
}

static void linha(const char *etapa, int n, const char *modo, const Tempos *t) {
    printf("%s,%d,%s,%.3f,%.3f,%.3f,%.3f\n", etapa, n, modo, t->envio_ms, t->kernel_ms, t->retorno_ms, t->total_ms);
    fflush(stdout);
}

static void curva(Nucleo *nc) {
    printf("etapa,n,modo,envio_ms,kernel_ms,retorno_ms,total_ms\n");
    const int REP = 3;
    const int ns_busca[] = {10, 100, 1000, 10000, 100000};
    for (size_t a = 0; a < sizeof(ns_busca) / sizeof(int); a++) {
        const int n = ns_busca[a];
        float *cons = descritores_aleatorios(1), *cand = descritores_aleatorios(n), *notas = malloc(sizeof(float) * n);
        Tempos t, s = {0}, o = {0};
        comparar_sequencial(cons, 1, cand, n, notas, &t);
        comparar_opencl(nc, cons, 1, cand, n, notas, &t);
        for (int r = 0; r < REP; r++) {
            comparar_sequencial(cons, 1, cand, n, notas, &t);
            media(&s, &t, REP);
            comparar_opencl(nc, cons, 1, cand, n, notas, &t);
            media(&o, &t, REP);
        }
        linha("busca", n, "sequencial", &s);
        linha("busca", n, "opencl", &o);
        free(cons);
        free(cand);
        free(notas);
    }
    const int ns_extr[] = {1, 10, 100, 1000};
    for (size_t a = 0; a < sizeof(ns_extr) / sizeof(int); a++) {
        const int n = ns_extr[a];
        Imagem *imgs = fotos_aleatorias(n, 320, 240);
        float *d = malloc(sizeof(float) * DIM * (size_t)n);
        Tempos t, s = {0}, o = {0};
        descritor_opencl(nc, imgs, n, d, &t);
        for (int r = 0; r < REP; r++) {
            descritor_sequencial(imgs, n, d, &t);
            media(&s, &t, REP);
            descritor_opencl(nc, imgs, n, d, &t);
            media(&o, &t, REP);
        }
        linha("extracao", n, "sequencial", &s);
        linha("extracao", n, "opencl", &o);
        for (int i = 0; i < n; i++) free((void *)imgs[i].rgb);
        free(imgs);
        free(d);
    }
    const int m = 100, ns_lote[] = {10, 100, 1000, 10000};
    float *novas = descritores_aleatorios(m);
    for (size_t a = 0; a < sizeof(ns_lote) / sizeof(int); a++) {
        const int n = ns_lote[a];
        float *ativas = descritores_aleatorios(n), *notas = malloc(sizeof(float) * (size_t)m * n);
        Tempos t, s = {0}, o = {0};
        comparar_opencl(nc, novas, m, ativas, n, notas, &t);
        for (int r = 0; r < REP; r++) {
            comparar_sequencial(novas, m, ativas, n, notas, &t);
            media(&s, &t, REP);
            comparar_opencl(nc, novas, m, ativas, n, notas, &t);
            media(&o, &t, REP);
        }
        linha("lote", n, "sequencial", &s);
        linha("lote", n, "opencl", &o);
        free(ativas);
        free(notas);
    }
    free(novas);
}

static void moer(Nucleo *nc, double segundos) {
    const int m = 200, n = 10000;
    float *novas = descritores_aleatorios(m), *ativas = descritores_aleatorios(n);
    float *notas = malloc(sizeof(float) * (size_t)m * n);
    const char *modos[] = {"SEQUENCIAL (1 núcleo)", "OPENCL (todos os núcleos)"};
    for (int modo = 0; modo < 2; modo++) {
        printf("\n=== %s: lote de %d fotos novas × %d buscas ativas, por %.0f s ===\n", modos[modo], m, n, segundos);
        fflush(stdout);
        const double inicio = agora_ms();
        double ultimo = inicio;
        long comparacoes = 0, desde_ultimo = 0;
        while (agora_ms() - inicio < segundos * 1000) {
            if (modo == 0) comparar_sequencial(novas, m, ativas, n, notas, NULL);
            else comparar_opencl(nc, novas, m, ativas, n, notas, NULL);
            comparacoes += (long)m * n;
            desde_ultimo += (long)m * n;
            const double agora = agora_ms();
            if (agora - ultimo >= 1000) {
                printf("  %5.1f s  %8.2f milhões de comparações/s\n", (agora - inicio) / 1000,
                       desde_ultimo / ((agora - ultimo) / 1000) / 1e6);
                fflush(stdout);
                ultimo = agora;
                desde_ultimo = 0;
            }
        }
        printf("  média: %.2f milhões de comparações/s\n", comparacoes / ((agora_ms() - inicio) / 1000) / 1e6);
    }
    free(novas);
    free(ativas);
    free(notas);
}

int main(int argc, char **argv) {
    const char *modo = argc > 1 ? argv[1] : "curva";
    NucleoOcl ocl;
    if (ocl_iniciar(&ocl, 1) != 0) return 1;
    Nucleo nc;
    nucleo_preparar(&nc, &ocl);
    if (strcmp(modo, "moer") == 0) moer(&nc, argc > 2 ? atof(argv[2]) : 15);
    else curva(&nc);
    nucleo_liberar(&nc);
    ocl_encerrar(&ocl);
    return 0;
}
