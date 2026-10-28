/*
 * descritor.c — extração de descritores e comparação, sequencial e OpenCL.
 *
 * A versão sequencial repete, laço por laço, o que cada kernel de
 * kernels/descritor.cl e kernels/comparar.cl faz para um pixel ou um par.
 * Mudou a conta de um lado, mude do outro: o `make teste` confere.
 */
#include "descritor.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define E_COR_ANIMAL 0
#define E_COR_TODOS (E_COR_ANIMAL + REGIOES * TONS)
#define E_LBP_ANIMAL (E_COR_TODOS + REGIOES * TONS)
#define E_LBP_TODOS (E_LBP_ANIMAL + CLASSES_LBP)
#define E_N_ANIMAL (E_LBP_TODOS + CLASSES_LBP)
#define E_SOMA_X (E_N_ANIMAL + 1)
#define E_SOMA_Y (E_SOMA_X + 1)
#define E_MIN_X (E_SOMA_Y + 1)
#define E_MAX_X (E_MIN_X + 1)
#define E_MIN_Y (E_MAX_X + 1)
#define E_MAX_Y (E_MIN_Y + 1)

#define N_PROPORCOES 5
#define MINIMO_ANIMAL (PIXELS / 20) /* 5% da foto */

double agora_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e3 + (double)t.tv_nsec / 1e6;
}

static int min_i(int a, int b) { return a < b ? a : b; }
static int max_i(int a, int b) { return a > b ? a : b; }

/* ===================================================== parte comum */

static void zerar_estatisticas(int *e) {
    memset(e, 0, N_ESTAT * sizeof(int));
    e[E_MIN_X] = LADO;
    e[E_MAX_X] = -1;
    e[E_MIN_Y] = LADO;
    e[E_MAX_Y] = -1;
}

void descritor_de_estatisticas(const int *e, float *d) {
    memset(d, 0, DIM * sizeof(float));
    const int usar_animal = e[E_N_ANIMAL] >= MINIMO_ANIMAL;
    const int *cor = e + (usar_animal ? E_COR_ANIMAL : E_COR_TODOS);
    const int *lbp = e + (usar_animal ? E_LBP_ANIMAL : E_LBP_TODOS);

    long total_cor = 0, total_lbp = 0;
    for (int k = 0; k < REGIOES * TONS; k++) total_cor += cor[k];
    for (int k = 0; k < CLASSES_LBP; k++) total_lbp += lbp[k];
    for (int k = 0; k < REGIOES * TONS; k++) d[D_COR + k] = total_cor ? (float)cor[k] / (float)total_cor : 0.0f;
    for (int k = 0; k < CLASSES_LBP; k++) d[D_TEXTURA + k] = total_lbp ? (float)lbp[k] / (float)total_lbp : 0.0f;

    float *p = d + D_PROPORCOES;
    if (usar_animal) {
        const int largura = e[E_MAX_X] - e[E_MIN_X] + 1, altura = e[E_MAX_Y] - e[E_MIN_Y] + 1;
        p[0] = (float)largura / (float)(largura + altura);
        p[1] = (float)e[E_N_ANIMAL] / (float)(largura * altura);
        p[2] = (float)e[E_N_ANIMAL] / (float)PIXELS;
        p[3] = ((float)e[E_SOMA_X] / (float)e[E_N_ANIMAL]) / (float)LADO;
        p[4] = ((float)e[E_SOMA_Y] / (float)e[E_N_ANIMAL]) / (float)LADO;
    } else { /* sem recorte confiável: a foto inteira, centralizada */
        p[0] = 0.5f;
        p[1] = 1.0f;
        p[2] = 1.0f;
        p[3] = 0.5f;
        p[4] = 0.5f;
    }
}

static float qui_quadrado(const float *a, const float *b, int ini, int fim) {
    float d = 0.0f;
    for (int k = ini; k < fim; k++) {
        const float s = a[k] + b[k];
        if (s > 0.0f) {
            const float dif = a[k] - b[k];
            d += dif * dif / s;
        }
    }
    return 0.5f * d;
}

float nota_semelhanca(const float *a, const float *b) {
    const float cor = qui_quadrado(a, b, 0, D_TEXTURA);
    const float textura = qui_quadrado(a, b, D_TEXTURA, D_PROPORCOES);
    float prop = 0.0f;
    for (int k = D_PROPORCOES; k < D_PROPORCOES + N_PROPORCOES; k++) prop += fabsf(a[k] - b[k]);
    prop /= N_PROPORCOES;
    return 1.0f - (0.6f * cor + 0.3f * textura + 0.1f * prop);
}

const char *grau_semelhanca(float nota) {
    if (nota >= 0.75f) return "alta";
    if (nota >= 0.55f) return "media";
    return "baixa";
}

/* ===================================================== versão sequencial */

static int ganho(long soma_canal) {
    if (soma_canal == 0) return 1024;
    const long g = (128L * 1024 * PIXELS) / soma_canal;
    return (int)(g < 4096 ? g : 4096);
}

static int classe_tom(int r, int g, int b) {
    const int mx = max_i(r, max_i(g, b)), mn = min_i(r, min_i(g, b)), delta = mx - mn;
    const int s = mx == 0 ? 0 : (delta * 255) / mx;
    if (s < 40) return 48 + (mx * 4) / 256;
    int h;
    if (mx == r) h = (60 * (g - b)) / delta;
    else if (mx == g) h = 120 + (60 * (b - r)) / delta;
    else h = 240 + (60 * (r - g)) / delta;
    if (h < 0) h += 360;
    const int hb = (h * 12) / 360, sb = s < 128 ? 0 : 1, vb = mx < 128 ? 0 : 1;
    return (hb * 2 + sb) * 2 + vb;
}

static void uma_imagem_sequencial(const Imagem *im, uint8_t *img128, uint8_t *tom, uint8_t *cinza,
                                  uint8_t *mascara, uint8_t *classe, int *e) {
    const int w = im->largura, h = im->altura;
    /* 1. redimensionar */
    for (int p = 0; p < PIXELS; p++) {
        const int x = p % LADO, y = p / LADO;
        int fx = ((2 * x + 1) * w * 256) / (2 * LADO) - 128;
        int fy = ((2 * y + 1) * h * 256) / (2 * LADO) - 128;
        fx = max_i(fx, 0);
        fy = max_i(fy, 0);
        const int x0 = min_i(fx >> 8, w - 1), y0 = min_i(fy >> 8, h - 1);
        const int x1 = min_i(x0 + 1, w - 1), y1 = min_i(y0 + 1, h - 1);
        const int ax = fx & 255, ay = fy & 255;
        for (int c = 0; c < 3; c++) {
            const int p00 = im->rgb[(y0 * w + x0) * 3 + c], p01 = im->rgb[(y0 * w + x1) * 3 + c];
            const int p10 = im->rgb[(y1 * w + x0) * 3 + c], p11 = im->rgb[(y1 * w + x1) * 3 + c];
            const int cima = p00 * (256 - ax) + p01 * ax, baixo = p10 * (256 - ax) + p11 * ax;
            img128[p * 3 + c] = (uint8_t)((cima * (256 - ay) + baixo * ay + 32768) >> 16);
        }
    }
    /* 2. somar canais (imagem inteira e moldura) */
    int s[N_SOMAS] = {0};
    for (int p = 0; p < PIXELS; p++) {
        const int x = p % LADO, y = p / LADO;
        const uint8_t *px = img128 + p * 3;
        s[0] += px[0];
        s[1] += px[1];
        s[2] += px[2];
        if (x < MOLDURA || y < MOLDURA || x >= LADO - MOLDURA || y >= LADO - MOLDURA) {
            s[3] += px[0];
            s[4] += px[1];
            s[5] += px[2];
            s[6]++;
        }
    }
    /* 3. classificar */
    const int gr = ganho(s[0]), gg = ganho(s[1]), gb = ganho(s[2]);
    const int n = max_i(s[6], 1);
    const int fr = min_i(255, ((s[3] / n) * gr) >> 10);
    const int fg = min_i(255, ((s[4] / n) * gg) >> 10);
    const int fb = min_i(255, ((s[5] / n) * gb) >> 10);
    for (int p = 0; p < PIXELS; p++) {
        const uint8_t *px = img128 + p * 3;
        const int r = min_i(255, (px[0] * gr) >> 10);
        const int g = min_i(255, (px[1] * gg) >> 10);
        const int b = min_i(255, (px[2] * gb) >> 10);
        tom[p] = (uint8_t)classe_tom(r, g, b);
        cinza[p] = (uint8_t)((77 * r + 150 * g + 29 * b) >> 8);
        mascara[p] = (uint8_t)((abs(r - fr) + abs(g - fg) + abs(b - fb)) > LIMIAR_FUNDO);
    }
    /* 4. LBP */
    static const int dx[8] = {-1, 0, 1, 1, 1, 0, -1, -1};
    static const int dy[8] = {-1, -1, -1, 0, 1, 1, 1, 0};
    for (int p = 0; p < PIXELS; p++) {
        const int x = p % LADO, y = p / LADO;
        if (x == 0 || y == 0 || x == LADO - 1 || y == LADO - 1) {
            classe[p] = 255;
            continue;
        }
        const int centro = cinza[p];
        int bits[8], uns = 0;
        for (int k = 0; k < 8; k++) {
            bits[k] = cinza[(y + dy[k]) * LADO + (x + dx[k])] >= centro;
            uns += bits[k];
        }
        int transicoes = 0;
        for (int k = 0; k < 8; k++) transicoes += bits[k] != bits[(k + 1) & 7];
        classe[p] = (uint8_t)(transicoes <= 2 ? uns : 9);
    }
    /* 5. histogramas */
    zerar_estatisticas(e);
    for (int p = 0; p < PIXELS; p++) {
        const int x = p % LADO, y = p / LADO;
        const int t = ((y >= LADO / 2) * 2 + (x >= LADO / 2)) * TONS + tom[p];
        const int l = classe[p];
        e[E_COR_TODOS + t]++;
        if (l != 255) e[E_LBP_TODOS + l]++;
        if (mascara[p]) {
            e[E_COR_ANIMAL + t]++;
            if (l != 255) e[E_LBP_ANIMAL + l]++;
            e[E_N_ANIMAL]++;
            e[E_SOMA_X] += x;
            e[E_SOMA_Y] += y;
            e[E_MIN_X] = min_i(e[E_MIN_X], x);
            e[E_MAX_X] = max_i(e[E_MAX_X], x);
            e[E_MIN_Y] = min_i(e[E_MIN_Y], y);
            e[E_MAX_Y] = max_i(e[E_MAX_Y], y);
        }
    }
}

void descritor_sequencial(const Imagem *imgs, int n, float *saida, Tempos *t) {
    const double inicio = agora_ms();
    uint8_t *img128 = malloc(PIXELS * 3), *tom = malloc(PIXELS), *cinza = malloc(PIXELS);
    uint8_t *mascara = malloc(PIXELS), *classe = malloc(PIXELS);
    int e[N_ESTAT];
    for (int i = 0; i < n; i++) {
        uma_imagem_sequencial(&imgs[i], img128, tom, cinza, mascara, classe, e);
        descritor_de_estatisticas(e, saida + (size_t)i * DIM);
    }
    free(img128);
    free(tom);
    free(cinza);
    free(mascara);
    free(classe);
    if (t) {
        memset(t, 0, sizeof(*t));
        t->kernel_ms = t->total_ms = agora_ms() - inicio;
    }
}

void comparar_sequencial(const float *consultas, int m, const float *candidatos, int n, float *notas,
                         Tempos *t) {
    const double inicio = agora_ms();
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++)
            notas[(size_t)i * n + j] = nota_semelhanca(consultas + (size_t)i * DIM, candidatos + (size_t)j * DIM);
    if (t) {
        memset(t, 0, sizeof(*t));
        t->kernel_ms = t->total_ms = agora_ms() - inicio;
    }
}

#ifndef SEM_OPENCL
/* ===================================================== versão OpenCL */

int nucleo_preparar(Nucleo *nc, NucleoOcl *ocl) {
    cl_int err;
    nc->ocl = ocl;
    nc->prog_descritor = ocl_compilar(ocl, "descritor.cl");
    nc->prog_comparar = ocl_compilar(ocl, "comparar.cl");
    nc->k_redimensionar = clCreateKernel(nc->prog_descritor, "redimensionar", &err);
    OCL_CHECAR(err, "kernel redimensionar");
    nc->k_somar = clCreateKernel(nc->prog_descritor, "somar_canais", &err);
    OCL_CHECAR(err, "kernel somar_canais");
    nc->k_descrever = clCreateKernel(nc->prog_descritor, "descrever", &err);
    OCL_CHECAR(err, "kernel descrever");
    nc->k_comparar = clCreateKernel(nc->prog_comparar, "comparar", &err);
    OCL_CHECAR(err, "kernel comparar");
    return 0;
}

void nucleo_liberar(Nucleo *nc) {
    clReleaseKernel(nc->k_redimensionar);
    clReleaseKernel(nc->k_somar);
    clReleaseKernel(nc->k_descrever);
    clReleaseKernel(nc->k_comparar);
    clReleaseProgram(nc->prog_descritor);
    clReleaseProgram(nc->prog_comparar);
}

static cl_mem criar(Nucleo *nc, cl_mem_flags flags, size_t bytes, const char *nome) {
    cl_int err;
    cl_mem m = clCreateBuffer(nc->ocl->contexto, flags, bytes ? bytes : 1, NULL, &err);
    OCL_CHECAR(err, nome);
    return m;
}

static void arg(cl_kernel k, cl_uint i, size_t tam, const void *v) {
    OCL_CHECAR(clSetKernelArg(k, i, tam, v), "argumento do kernel");
}

/* início do primeiro e fim do último comando: o tempo de uma etapa inteira */
static double intervalo_ms(cl_event primeiro, cl_event ultimo) {
    cl_ulong ini = 0, fim = 0;
    OCL_CHECAR(clGetEventProfilingInfo(primeiro, CL_PROFILING_COMMAND_START, sizeof(ini), &ini, NULL), "evento");
    OCL_CHECAR(clGetEventProfilingInfo(ultimo, CL_PROFILING_COMMAND_END, sizeof(fim), &fim, NULL), "evento");
    return (double)(fim - ini) / 1e6;
}

void descritor_opencl(Nucleo *nc, const Imagem *imgs, int n, float *saida, Tempos *t) {
    if (n <= 0) {
        if (t) memset(t, 0, sizeof(*t));
        return;
    }
    const double inicio = agora_ms();
    cl_command_queue fila = nc->ocl->fila;

    /* entrada: todas as fotos num buffer só, com (deslocamento, largura, altura) de cada uma */
    size_t total = 0;
    int *info = malloc(sizeof(int) * 3 * (size_t)n);
    for (int i = 0; i < n; i++) {
        info[3 * i] = (int)total;
        info[3 * i + 1] = imgs[i].largura;
        info[3 * i + 2] = imgs[i].altura;
        total += (size_t)imgs[i].largura * imgs[i].altura * 3;
    }
    uint8_t *origem = malloc(total ? total : 1);
    for (int i = 0; i < n; i++)
        memcpy(origem + info[3 * i], imgs[i].rgb, (size_t)imgs[i].largura * imgs[i].altura * 3);
    int *estat = malloc(sizeof(int) * N_ESTAT * (size_t)n);
    for (int i = 0; i < n; i++) zerar_estatisticas(estat + (size_t)i * N_ESTAT);

    /* as fotos já estão na memória do programa: o kernel lê de lá, sem cópia (ver comparar_opencl) */
    cl_int err;
    cl_mem d_origem = clCreateBuffer(nc->ocl->contexto, CL_MEM_READ_ONLY | CL_MEM_USE_HOST_PTR, total ? total : 1, origem, &err);
    OCL_CHECAR(err, "buffer origem");
    cl_mem d_info = criar(nc, CL_MEM_READ_ONLY, sizeof(int) * 3 * (size_t)n, "buffer info");
    cl_mem d_img = criar(nc, CL_MEM_READ_WRITE, (size_t)n * PIXELS * 3, "buffer 128x128");
    cl_mem d_somas = criar(nc, CL_MEM_READ_WRITE, sizeof(int) * N_SOMAS * (size_t)n, "buffer somas");
    cl_mem d_estat = criar(nc, CL_MEM_READ_WRITE, sizeof(int) * N_ESTAT * (size_t)n, "buffer estat");

    cl_event ev_envio[3], ev_k[3], ev_retorno;
    const int zero = 0;
    OCL_CHECAR(clEnqueueWriteBuffer(fila, d_info, CL_FALSE, 0, sizeof(int) * 3 * (size_t)n, info, 0, NULL, &ev_envio[0]), "enviar info");
    OCL_CHECAR(clEnqueueFillBuffer(fila, d_somas, &zero, sizeof(int), 0, sizeof(int) * N_SOMAS * (size_t)n, 0, NULL, &ev_envio[1]), "zerar somas");
    OCL_CHECAR(clEnqueueWriteBuffer(fila, d_estat, CL_FALSE, 0, sizeof(int) * N_ESTAT * (size_t)n, estat, 0, NULL, &ev_envio[2]), "enviar estat");

    const size_t por_linha[2] = {LADO, (size_t)n}, por_bloco[2] = {LADO / 8, (size_t)n};
    arg(nc->k_redimensionar, 0, sizeof(cl_mem), &d_origem);
    arg(nc->k_redimensionar, 1, sizeof(cl_mem), &d_info);
    arg(nc->k_redimensionar, 2, sizeof(cl_mem), &d_img);
    OCL_CHECAR(clEnqueueNDRangeKernel(fila, nc->k_redimensionar, 2, NULL, por_linha, NULL, 0, NULL, &ev_k[0]), "redimensionar");
    arg(nc->k_somar, 0, sizeof(cl_mem), &d_img);
    arg(nc->k_somar, 1, sizeof(cl_mem), &d_somas);
    OCL_CHECAR(clEnqueueNDRangeKernel(fila, nc->k_somar, 2, NULL, por_linha, NULL, 0, NULL, &ev_k[1]), "somar_canais");
    arg(nc->k_descrever, 0, sizeof(cl_mem), &d_img);
    arg(nc->k_descrever, 1, sizeof(cl_mem), &d_somas);
    arg(nc->k_descrever, 2, sizeof(cl_mem), &d_estat);
    OCL_CHECAR(clEnqueueNDRangeKernel(fila, nc->k_descrever, 2, NULL, por_bloco, NULL, 0, NULL, &ev_k[2]), "descrever");
    OCL_CHECAR(clEnqueueReadBuffer(fila, d_estat, CL_TRUE, 0, sizeof(int) * N_ESTAT * (size_t)n, estat, 0, NULL, &ev_retorno), "ler estat");

    for (int i = 0; i < n; i++) descritor_de_estatisticas(estat + (size_t)i * N_ESTAT, saida + (size_t)i * DIM);

    if (getenv("NUCLEO_PERFIL")) { /* diagnóstico: tempo de cada kernel */
        const char *nomes[] = {"redimensionar", "somar_canais", "descrever"};
        for (int k = 0; k < 3; k++) fprintf(stderr, "  %-14s %8.3f ms\n", nomes[k], ocl_duracao_ms(ev_k[k]));
    }
    if (t) {
        t->envio_ms = intervalo_ms(ev_envio[0], ev_envio[2]);
        t->kernel_ms = intervalo_ms(ev_k[0], ev_k[2]);
        t->retorno_ms = ocl_duracao_ms(ev_retorno);
        t->total_ms = agora_ms() - inicio;
    }
    for (int k = 0; k < 3; k++) clReleaseEvent(ev_envio[k]);
    for (int k = 0; k < 3; k++) clReleaseEvent(ev_k[k]);
    clReleaseEvent(ev_retorno);
    cl_mem bufs[] = {d_origem, d_info, d_img, d_somas, d_estat};
    for (size_t k = 0; k < sizeof(bufs) / sizeof(bufs[0]); k++) clReleaseMemObject(bufs[k]);
    free(origem);
    free(info);
    free(estat);
}

/* Os descritores ficam na memória do próprio programa e o kernel lê direto de
 * lá (CL_MEM_USE_HOST_PTR): como o "dispositivo" é a própria CPU (PoCL), copiar
 * 90 MB de candidatos a cada busca seria puro desperdício — era o que dominava o
 * tempo antes desta otimização. Em GPU, o mesmo código faria a cópia sozinho. */
void comparar_opencl(Nucleo *nc, const float *consultas, int m, const float *candidatos, int n, float *notas,
                     Tempos *t) {
    if (n <= 0 || m <= 0) {
        if (t) memset(t, 0, sizeof(*t));
        return;
    }
    const double inicio = agora_ms();
    cl_command_queue fila = nc->ocl->fila;
    const size_t b_cons = sizeof(float) * DIM * (size_t)m, b_cand = sizeof(float) * DIM * (size_t)n;
    const size_t b_notas = sizeof(float) * (size_t)m * n;
    cl_int err;
    const double ini_envio = agora_ms();
    cl_mem d_cons = clCreateBuffer(nc->ocl->contexto, CL_MEM_READ_ONLY | CL_MEM_USE_HOST_PTR, b_cons, (void *)consultas, &err);
    OCL_CHECAR(err, "buffer consultas");
    cl_mem d_cand = clCreateBuffer(nc->ocl->contexto, CL_MEM_READ_ONLY | CL_MEM_USE_HOST_PTR, b_cand, (void *)candidatos, &err);
    OCL_CHECAR(err, "buffer candidatos");
    cl_mem d_notas = clCreateBuffer(nc->ocl->contexto, CL_MEM_WRITE_ONLY | CL_MEM_USE_HOST_PTR, b_notas, notas, &err);
    OCL_CHECAR(err, "buffer notas");
    const double envio_ms = agora_ms() - ini_envio;

    cl_event ev_k, ev_r;
    arg(nc->k_comparar, 0, sizeof(cl_mem), &d_cons);
    arg(nc->k_comparar, 1, sizeof(cl_mem), &d_cand);
    arg(nc->k_comparar, 2, sizeof(cl_mem), &d_notas);
    arg(nc->k_comparar, 3, sizeof(int), &n);
    const size_t global[2] = {(size_t)n, (size_t)m};
    OCL_CHECAR(clEnqueueNDRangeKernel(fila, nc->k_comparar, 2, NULL, global, NULL, 0, NULL, &ev_k), "comparar");
    /* "ler" um buffer que já mora na memória do programa: só garante que terminou */
    float *mapa = clEnqueueMapBuffer(fila, d_notas, CL_TRUE, CL_MAP_READ, 0, b_notas, 0, NULL, &ev_r, &err);
    OCL_CHECAR(err, "ler notas");
    OCL_CHECAR(clEnqueueUnmapMemObject(fila, d_notas, mapa, 0, NULL, NULL), "devolver notas");
    OCL_CHECAR(clFinish(fila), "terminar fila");

    if (t) {
        t->envio_ms = envio_ms;
        t->kernel_ms = ocl_duracao_ms(ev_k);
        t->retorno_ms = ocl_duracao_ms(ev_r);
        t->total_ms = agora_ms() - inicio;
    }
    clReleaseEvent(ev_k);
    clReleaseEvent(ev_r);
    clReleaseMemObject(d_cons);
    clReleaseMemObject(d_cand);
    clReleaseMemObject(d_notas);
}
#endif /* SEM_OPENCL */
