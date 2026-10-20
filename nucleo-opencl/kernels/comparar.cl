/*
 * comparar.cl — comparação em massa (RF-22, RF-25): cada item de trabalho
 * compara UMA consulta com UM candidato, independentemente de todos os outros.
 *
 *   dimensão 0 = candidato (n), dimensão 1 = consulta (m)   →   notas[m][n]
 *
 * Com m = 1 é a busca de um tutor; com m > 1 é o lote do monitoramento
 * (cada foto nova contra todas as buscas ativas). A fórmula é a mesma de
 * nota_semelhanca() em src/descritor.c — mudar uma exige mudar a outra.
 */
#pragma OPENCL FP_CONTRACT OFF /* sem fusão a*b+c: mesma conta, mesmo arredondamento que o C */

#define DIM 224
#define D_TEXTURA 208
#define D_PROPORCOES 218
#define N_PROPORCOES 5

/* Distância qui-quadrado entre histogramas que somam 1: vai de 0 (iguais) a 1. */
inline float qui_quadrado(__global const float *a, __global const float *b, int ini, int fim) {
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

__kernel void comparar(__global const float *consultas, __global const float *candidatos,
                       __global float *notas, const int n) {
    const int j = get_global_id(0);
    const int i = get_global_id(1);
    if (j >= n) return;
    __global const float *a = consultas + (size_t)i * DIM;
    __global const float *b = candidatos + (size_t)j * DIM;

    const float cor = qui_quadrado(a, b, 0, D_TEXTURA);
    const float textura = qui_quadrado(a, b, D_TEXTURA, D_PROPORCOES);
    float prop = 0.0f;
    for (int k = D_PROPORCOES; k < D_PROPORCOES + N_PROPORCOES; k++) prop += fabs(a[k] - b[k]);
    prop /= N_PROPORCOES;

    notas[(size_t)i * n + j] = 1.0f - (0.6f * cor + 0.3f * textura + 0.1f * prop);
}
