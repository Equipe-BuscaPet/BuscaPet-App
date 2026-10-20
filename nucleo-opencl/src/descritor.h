/*
 * descritor.h — descritores visuais (RF-21) e comparação em massa (RF-22, RF-25),
 * cada um em duas versões: sequencial em C e paralela em OpenCL.
 *
 * As duas versões existem para o modo comparativo do RF-29 e para o teste de
 * equivalência (src/teste_nucleo.c): a extração precisa dar exatamente os
 * mesmos números nas duas, e a comparação, o mesmo ranking.
 *
 * Descritor (DIM floats por foto, versão "v1"):
 *   [0, 208)    cor: 4 regiões (quadrantes) × 52 tons, só pixels do animal, soma 1
 *   [208, 218)  textura: 10 classes de LBP, só pixels do animal, soma 1
 *   [218, 223)  proporções do animal: largura/(largura+altura), preenchimento do
 *               retângulo, área na foto, centro x, centro y (todos entre 0 e 1)
 *   223         zero (alinhamento)
 * Se o "animal" ocupar menos de 5% da foto (fundo parecido com o animal, foto
 * muito fechada), a foto inteira é usada.
 */
#ifndef NUCLEO_DESCRITOR_H
#define NUCLEO_DESCRITOR_H

#include "ocl.h"

#include <stdint.h>

#define LADO 128
#define PIXELS (LADO * LADO)
#define MOLDURA 6
#define LIMIAR_FUNDO 60
#define TONS 52
#define REGIOES 4
#define CLASSES_LBP 10
#define N_SOMAS 8
#define N_ESTAT (2 * REGIOES * TONS + 2 * CLASSES_LBP + 7)

#define D_COR 0
#define D_TEXTURA (REGIOES * TONS)
#define D_PROPORCOES (D_TEXTURA + CLASSES_LBP)
#define DIM 224
#define VERSAO_DESCRITOR "v1"

#define LADO_MAXIMO 2048 /* maior largura/altura aceita na entrada */

/* Uma foto em RGB (3 bytes por pixel, linha a linha). */
typedef struct {
    const uint8_t *rgb;
    int largura, altura;
} Imagem;

/* Tempos de cada etapa, em milissegundos. No OpenCL, envio/kernel/retorno vêm
 * dos eventos da fila (profiling); na versão sequencial, só "kernel" é usado. */
typedef struct {
    double envio_ms, kernel_ms, retorno_ms, total_ms;
} Tempos;

/* ---- versão sequencial (referência) ---- */
void descritor_sequencial(const Imagem *imgs, int n, float *saida, Tempos *t);
void comparar_sequencial(const float *consultas, int m, const float *candidatos, int n,
                         float *notas, Tempos *t);

/* ---- versão OpenCL ---- */
typedef struct {
    NucleoOcl *ocl;
    cl_program prog_descritor, prog_comparar;
    cl_kernel k_redimensionar, k_somar, k_descrever, k_comparar;
} Nucleo;

int nucleo_preparar(Nucleo *nc, NucleoOcl *ocl); /* compila os kernels; 0 = ok */
void nucleo_liberar(Nucleo *nc);
void descritor_opencl(Nucleo *nc, const Imagem *imgs, int n, float *saida, Tempos *t);
void comparar_opencl(Nucleo *nc, const float *consultas, int m, const float *candidatos, int n,
                     float *notas, Tempos *t);

/* Monta o descritor a partir das contagens inteiras (comum às duas versões). */
void descritor_de_estatisticas(const int *estat, float *saida);

/* Nota de semelhança entre dois descritores, de 0 (nada a ver) a 1 (iguais). */
float nota_semelhanca(const float *a, const float *b);

/* "alta", "media" ou "baixa" (o escopo pede grau qualitativo, não porcentagem). */
const char *grau_semelhanca(float nota);

double agora_ms(void);

#endif
