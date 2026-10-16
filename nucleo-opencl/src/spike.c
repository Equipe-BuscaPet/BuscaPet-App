/*
 * spike.c — prova de que o OpenCL funciona no ambiente do time (Sprint 1).
 *
 * Soma dois vetores de N floats de duas formas, na CPU de forma sequencial
 * (referência) e via OpenCL, e então:
 *   1. confere se as duas respostas são iguais (teste de equivalência);
 *   2. mede SEPARADAMENTE o envio dos dados (host→device), o kernel e o
 *      retorno (device→host), como pede o plano.
 *
 * Uso: spike [N]        (padrão: 4.194.304 elementos)
 * Saída com código 0 se a equivalência passar, 1 se falhar — é isso que o
 * `make teste` e a CI verificam.
 */
#include "ocl.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N_PADRAO (1u << 22)

static double agora_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e3 + (double)t.tv_nsec / 1e6;
}

static void soma_sequencial(const float *a, const float *b, float *c, cl_uint n) {
    for (cl_uint i = 0; i < n; i++) c[i] = a[i] + b[i];
}

typedef struct {
    double envio_ms, kernel_ms, retorno_ms, total_ms;
} TemposOcl;

static TemposOcl soma_opencl(NucleoOcl *ocl, cl_kernel kernel,
                             const float *a, const float *b, float *c, cl_uint n) {
    const size_t bytes = (size_t)n * sizeof(float);
    cl_int err;
    cl_mem da = clCreateBuffer(ocl->contexto, CL_MEM_READ_ONLY, bytes, NULL, &err);
    OCL_CHECAR(err, "criar buffer a");
    cl_mem db = clCreateBuffer(ocl->contexto, CL_MEM_READ_ONLY, bytes, NULL, &err);
    OCL_CHECAR(err, "criar buffer b");
    cl_mem dc = clCreateBuffer(ocl->contexto, CL_MEM_WRITE_ONLY, bytes, NULL, &err);
    OCL_CHECAR(err, "criar buffer c");

    const double inicio = agora_ms();
    cl_event ev_a, ev_b, ev_kernel, ev_c;
    OCL_CHECAR(clEnqueueWriteBuffer(ocl->fila, da, CL_FALSE, 0, bytes, a, 0, NULL, &ev_a), "enviar a");
    OCL_CHECAR(clEnqueueWriteBuffer(ocl->fila, db, CL_FALSE, 0, bytes, b, 0, NULL, &ev_b), "enviar b");

    OCL_CHECAR(clSetKernelArg(kernel, 0, sizeof(cl_mem), &da), "argumento a");
    OCL_CHECAR(clSetKernelArg(kernel, 1, sizeof(cl_mem), &db), "argumento b");
    OCL_CHECAR(clSetKernelArg(kernel, 2, sizeof(cl_mem), &dc), "argumento c");
    OCL_CHECAR(clSetKernelArg(kernel, 3, sizeof(cl_uint), &n), "argumento n");

    const size_t global = n;
    OCL_CHECAR(clEnqueueNDRangeKernel(ocl->fila, kernel, 1, NULL, &global, NULL, 0, NULL, &ev_kernel),
               "executar kernel");
    OCL_CHECAR(clEnqueueReadBuffer(ocl->fila, dc, CL_TRUE, 0, bytes, c, 0, NULL, &ev_c), "ler c");

    TemposOcl t;
    t.total_ms = agora_ms() - inicio;
    t.envio_ms = ocl_duracao_ms(ev_a) + ocl_duracao_ms(ev_b);
    t.kernel_ms = ocl_duracao_ms(ev_kernel);
    t.retorno_ms = ocl_duracao_ms(ev_c);

    clReleaseEvent(ev_a);
    clReleaseEvent(ev_b);
    clReleaseEvent(ev_kernel);
    clReleaseEvent(ev_c);
    clReleaseMemObject(da);
    clReleaseMemObject(db);
    clReleaseMemObject(dc);
    return t;
}

/* Quantas posições batem com a referência (tolerância relativa de 1e-6). */
static cl_uint conferir(const float *ref, const float *obtido, cl_uint n) {
    cl_uint iguais = 0;
    for (cl_uint i = 0; i < n; i++) {
        const float tol = 1e-6f * fmaxf(1.0f, fabsf(ref[i]));
        if (fabsf(ref[i] - obtido[i]) <= tol) iguais++;
    }
    return iguais;
}

int main(int argc, char **argv) {
    cl_uint n = N_PADRAO;
    if (argc > 1) {
        long v = strtol(argv[1], NULL, 10);
        if (v <= 0 || v > (1L << 28)) {
            fprintf(stderr, "uso: %s [N]   (1 <= N <= 268435456)\n", argv[0]);
            return 2;
        }
        n = (cl_uint)v;
    }

    float *a = malloc((size_t)n * sizeof(float));
    float *b = malloc((size_t)n * sizeof(float));
    float *ref = malloc((size_t)n * sizeof(float));
    float *res = malloc((size_t)n * sizeof(float));
    if (!a || !b || !ref || !res) {
        fprintf(stderr, "memória insuficiente para N = %u\n", n);
        return 2;
    }
    for (cl_uint i = 0; i < n; i++) { /* valores determinísticos e variados */
        a[i] = (float)(i % 1000) * 0.5f;
        b[i] = (float)((i * 7u) % 1000) * 0.25f;
    }

    NucleoOcl ocl;
    if (ocl_iniciar(&ocl, 1) != 0) return 2;
    cl_program programa = ocl_compilar(&ocl, "soma_vetores.cl");
    cl_int err;
    cl_kernel kernel = clCreateKernel(programa, "soma_vetores", &err);
    OCL_CHECAR(err, "criar kernel");

    const double t0 = agora_ms();
    soma_sequencial(a, b, ref, n);
    const double seq_ms = agora_ms() - t0;

    soma_opencl(&ocl, kernel, a, b, res, n); /* aquecimento: 1ª execução paga custos únicos */
    TemposOcl t = soma_opencl(&ocl, kernel, a, b, res, n);
    const cl_uint iguais = conferir(ref, res, n);

    char dispositivo[256], plataforma[256];
    ocl_info_dispositivo(ocl.dispositivo, CL_DEVICE_NAME, dispositivo, sizeof(dispositivo));
    ocl_info_plataforma(ocl.plataforma, CL_PLATFORM_NAME, plataforma, sizeof(plataforma));

    printf("BuscaPet - spike OpenCL (soma de vetores)\n");
    printf("Plataforma : %s\n", plataforma);
    printf("Dispositivo: %s\n", dispositivo);
    printf("N          : %u elementos (%.1f MB por vetor)\n\n", n, n * sizeof(float) / 1048576.0);
    printf("%-34s %12s\n", "Etapa", "Tempo (ms)");
    printf("%-34s %12.3f\n", "CPU sequencial (referencia)", seq_ms);
    printf("%-34s %12.3f\n", "OpenCL - envio (host -> device)", t.envio_ms);
    printf("%-34s %12.3f\n", "OpenCL - kernel", t.kernel_ms);
    printf("%-34s %12.3f\n", "OpenCL - retorno (device -> host)", t.retorno_ms);
    printf("%-34s %12.3f\n\n", "OpenCL - total de ponta a ponta", t.total_ms);

    const int ok = iguais == n;
    printf("Equivalencia: %s (%u de %u posicoes iguais)\n", ok ? "OK" : "FALHOU", iguais, n);

    clReleaseKernel(kernel);
    clReleaseProgram(programa);
    ocl_encerrar(&ocl);
    free(a);
    free(b);
    free(ref);
    free(res);
    return ok ? 0 : 1;
}
