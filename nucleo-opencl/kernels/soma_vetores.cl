/*
 * soma_vetores.cl — kernel do spike (gate da Sprint 1 do plano interno).
 *
 * Cada work-item (uma "linha de execução" do OpenCL) soma UMA posição:
 * c[i] = a[i] + b[i]. Não há dependência entre posições, então todas podem
 * rodar ao mesmo tempo — é o exemplo mínimo de paralelismo de dados.
 *
 * O teste `n` existe porque o runtime pode lançar mais work-items do que
 * elementos (arredondamento do tamanho global); os excedentes não fazem nada.
 */
__kernel void soma_vetores(__global const float *a,
                           __global const float *b,
                           __global float *c,
                           const uint n)
{
    const size_t i = get_global_id(0);
    if (i < n) {
        c[i] = a[i] + b[i];
    }
}
