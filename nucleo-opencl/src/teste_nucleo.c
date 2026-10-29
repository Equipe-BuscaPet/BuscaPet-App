/*
 * teste_nucleo.c — testes do pipeline de descritores e da comparação.
 *
 * 1. Equivalência (regra do plano: kernel só entra se bater com o sequencial):
 *    - descritores: OpenCL × sequencial IGUAIS bit a bit, em fotos de tamanhos
 *      estranhos (1×1, 3×2, 37×501, ...) e num lote misturado;
 *    - comparação: notas com diferença ≤ 1e-5 e o mesmo ranking.
 * 2. Comportamento (o descritor serve para o que promete):
 *    - a mesma foto em outro tamanho ou com outra iluminação continua "alta";
 *    - um animal de outra cor e outro formato fica "baixa".
 *
 * As fotos são sintéticas (geradas aqui, com semente fixa): um "animal" (elipse
 * com pelagem listrada ou malhada) sobre um fundo liso com ruído.
 * Saída 0 se tudo passar, 1 se algo falhar.
 */
#include "descritor.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int falhas = 0;

#define CONFERIR(cond, ...)                         \
    do {                                            \
        if (cond) {                                 \
            printf("  ok    ");                     \
        } else {                                    \
            printf("  FALHA ");                     \
            falhas++;                               \
        }                                           \
        printf(__VA_ARGS__);                        \
        printf("\n");                               \
    } while (0)

static unsigned semente = 12345;
static int aleatorio(int maximo) { /* gerador simples e repetível */
    semente = semente * 1103515245u + 12345u;
    return (int)((semente >> 16) % (unsigned)maximo);
}

typedef struct {
    int fundo[3], pelo[3], mancha[3];
    float cx, cy, rx, ry; /* elipse em frações da foto */
    int listras;          /* 1 = listras, 0 = manchas */
    float luz;            /* multiplica o brilho (iluminação) */
} Cena;

static uint8_t *desenhar(const Cena *c, int w, int h) {
    uint8_t *rgb = malloc((size_t)w * h * 3);
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            const float u = (x + 0.5f) / w, v = (y + 0.5f) / h;
            const float du = (u - c->cx) / c->rx, dv = (v - c->cy) / c->ry;
            const int *cor = c->fundo;
            if (du * du + dv * dv <= 1.0f) {
                const int padrao = c->listras ? ((int)(u * 24) % 2) : (((int)(u * 10) + (int)(v * 10)) % 3 == 0);
                cor = padrao ? c->mancha : c->pelo;
            }
            for (int k = 0; k < 3; k++) {
                int val = (int)(cor[k] * c->luz) + aleatorio(9) - 4;
                rgb[((size_t)y * w + x) * 3 + k] = (uint8_t)(val < 0 ? 0 : val > 255 ? 255 : val);
            }
        }
    }
    return rgb;
}

static const Cena CARAMELO = {{200, 205, 195}, {196, 124, 52}, {230, 190, 140}, 0.5f, 0.55f, 0.32f, 0.22f, 0, 1.0f};
static const Cena PRETO_E_BRANCO = {{90, 140, 70}, {25, 25, 28}, {240, 240, 240}, 0.45f, 0.5f, 0.2f, 0.35f, 1, 1.0f};

static void teste_equivalencia_descritores(Nucleo *nc) {
    printf("Equivalência dos descritores (OpenCL × sequencial, bit a bit)\n");
    const int tamanhos[][2] = {{1, 1}, {3, 2}, {37, 501}, {128, 128}, {640, 480}, {1024, 768}};
    const int qtd = sizeof(tamanhos) / sizeof(tamanhos[0]);
    Imagem imgs[2 * 6];
    uint8_t *buffers[2 * 6];
    for (int i = 0; i < qtd; i++) {
        for (int k = 0; k < 2; k++) {
            Cena c = k ? PRETO_E_BRANCO : CARAMELO;
            const int w = tamanhos[i][0], h = tamanhos[i][1];
            buffers[2 * i + k] = desenhar(&c, w, h);
            imgs[2 * i + k] = (Imagem){buffers[2 * i + k], w, h};
        }
    }
    const int n = 2 * qtd;
    float *seq = malloc(sizeof(float) * DIM * n), *par = malloc(sizeof(float) * DIM * n);
    descritor_sequencial(imgs, n, seq, NULL);
    for (int i = 0; i < n; i++) { /* uma foto por vez... */
        descritor_opencl(nc, &imgs[i], 1, par + (size_t)i * DIM, NULL);
        CONFERIR(memcmp(seq + (size_t)i * DIM, par + (size_t)i * DIM, sizeof(float) * DIM) == 0,
                 "foto %dx%d (%s)", imgs[i].largura, imgs[i].altura, i % 2 ? "preto e branco" : "caramelo");
    }
    memset(par, 0, sizeof(float) * DIM * n); /* ...e todas num lote só */
    descritor_opencl(nc, imgs, n, par, NULL);
    CONFERIR(memcmp(seq, par, sizeof(float) * DIM * n) == 0, "lote com as %d fotos de tamanhos diferentes", n);

    float soma = 0.0f;
    for (int k = 0; k < D_TEXTURA; k++) soma += seq[DIM * 4 + k];
    CONFERIR(fabsf(soma - 1.0f) < 1e-4f, "histograma de cor soma 1 (%.5f)", soma);
    for (int i = 0; i < n; i++) free(buffers[i]);
    free(seq);
    free(par);
}

static void teste_equivalencia_comparacao(Nucleo *nc) {
    printf("Equivalência da comparação (OpenCL × sequencial)\n");
    const int n = 1003, m = 3; /* 1003 é primo: não divide nenhum tamanho de grupo */
    Imagem *imgs = malloc(sizeof(Imagem) * n);
    uint8_t **bufs = malloc(sizeof(uint8_t *) * n);
    for (int i = 0; i < n; i++) {
        Cena c = (i % 2) ? PRETO_E_BRANCO : CARAMELO;
        for (int k = 0; k < 3; k++) c.pelo[k] = (c.pelo[k] + aleatorio(120)) % 256;
        c.cx = 0.3f + aleatorio(40) / 100.0f;
        c.rx = 0.15f + aleatorio(20) / 100.0f;
        bufs[i] = desenhar(&c, 64, 48);
        imgs[i] = (Imagem){bufs[i], 64, 48};
    }
    float *desc = malloc(sizeof(float) * DIM * n);
    descritor_opencl(nc, imgs, n, desc, NULL);
    float *seq = malloc(sizeof(float) * m * n), *par = malloc(sizeof(float) * m * n);
    comparar_sequencial(desc, m, desc, n, seq, NULL);
    comparar_opencl(nc, desc, m, desc, n, par, NULL);

    float maior = 0.0f;
    int ranking_igual = 1;
    for (int i = 0; i < m; i++) {
        int melhor_s = 0, melhor_p = 0;
        for (int j = 0; j < n; j++) {
            const float d = fabsf(seq[(size_t)i * n + j] - par[(size_t)i * n + j]);
            if (d > maior) maior = d;
            if (seq[(size_t)i * n + j] > seq[(size_t)i * n + melhor_s]) melhor_s = j;
            if (par[(size_t)i * n + j] > par[(size_t)i * n + melhor_p]) melhor_p = j;
        }
        ranking_igual &= melhor_s == melhor_p && melhor_s == i; /* o mais parecido é ela mesma */
        /* ordem completa: cada par de vizinhos na ordem sequencial mantém a ordem no OpenCL */
        for (int j = 0; j + 1 < n; j++) {
            const float a_s = seq[(size_t)i * n + j], b_s = seq[(size_t)i * n + j + 1];
            const float a_p = par[(size_t)i * n + j], b_p = par[(size_t)i * n + j + 1];
            if (fabsf(a_s - b_s) > 1e-5f && ((a_s > b_s) != (a_p > b_p))) ranking_igual = 0;
        }
    }
    CONFERIR(maior <= 1e-5f, "%d × %d notas, maior diferença %.2e (limite 1e-5)", m, n, maior);
    CONFERIR(ranking_igual, "mesmo ranking nas duas versões (e cada foto é a mais parecida consigo mesma)");
    for (int i = 0; i < n; i++) free(bufs[i]);
    free(bufs);
    free(imgs);
    free(desc);
    free(seq);
    free(par);
}

static float nota_entre(Nucleo *nc, const Cena *a, int wa, int ha, const Cena *b, int wb, int hb) {
    uint8_t *pa = desenhar(a, wa, ha), *pb = desenhar(b, wb, hb);
    Imagem imgs[2] = {{pa, wa, ha}, {pb, wb, hb}};
    float d[2 * DIM], nota;
    descritor_opencl(nc, imgs, 2, d, NULL);
    comparar_opencl(nc, d, 1, d + DIM, 1, &nota, NULL);
    free(pa);
    free(pb);
    return nota;
}

static void teste_comportamento(Nucleo *nc) {
    printf("Comportamento do descritor\n");
    Cena escura = CARAMELO;
    escura.luz = 0.6f;
    Cena outro_caramelo = CARAMELO;
    outro_caramelo.cx = 0.42f;
    outro_caramelo.rx = 0.28f;
    float s;
    s = nota_entre(nc, &CARAMELO, 640, 480, &CARAMELO, 640, 480);
    CONFERIR(s > 0.99f, "mesma cena, mesma resolução: %.3f (%s)", s, grau_semelhanca(s));
    s = nota_entre(nc, &CARAMELO, 1024, 768, &CARAMELO, 320, 240);
    CONFERIR(strcmp(grau_semelhanca(s), "alta") == 0, "mesma cena em outro tamanho: %.3f (%s)", s, grau_semelhanca(s));
    s = nota_entre(nc, &CARAMELO, 640, 480, &escura, 640, 480);
    CONFERIR(strcmp(grau_semelhanca(s), "alta") == 0, "mesma cena com 40%% menos luz: %.3f (%s)", s, grau_semelhanca(s));
    s = nota_entre(nc, &CARAMELO, 640, 480, &outro_caramelo, 640, 480);
    CONFERIR(strcmp(grau_semelhanca(s), "baixa") != 0, "outro animal caramelo, posição diferente: %.3f (%s)", s, grau_semelhanca(s));
    s = nota_entre(nc, &CARAMELO, 640, 480, &PRETO_E_BRANCO, 640, 480);
    CONFERIR(strcmp(grau_semelhanca(s), "baixa") == 0, "animal preto e branco listrado: %.3f (%s)", s, grau_semelhanca(s));
}

int main(void) {
    Nucleo nc;
#ifndef SEM_OPENCL
    NucleoOcl ocl;
    if (ocl_iniciar(&ocl, 1) != 0) return 1;
    nucleo_preparar(&nc, &ocl);
#endif
    teste_equivalencia_descritores(&nc);
    teste_equivalencia_comparacao(&nc);
    teste_comportamento(&nc);
#ifndef SEM_OPENCL
    nucleo_liberar(&nc);
    ocl_encerrar(&ocl);
#endif
    printf(falhas ? "\n%d teste(s) FALHARAM\n" : "\nTodos os testes passaram\n", falhas);
    return falhas ? 1 : 0;
}
