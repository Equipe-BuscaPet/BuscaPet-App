/*
 * ocl.h — utilidades de OpenCL compartilhadas pelos programas do núcleo.
 *
 * Esconde a parte repetitiva da API do OpenCL (escolher dispositivo, criar
 * contexto e fila, compilar kernel, traduzir códigos de erro) para que cada
 * programa (spike, servidor, kernels do reencontro) cuide só do seu cálculo.
 */
#ifndef NUCLEO_OCL_H
#define NUCLEO_OCL_H

#include <CL/cl.h>
#include <stddef.h>

/* Tudo o que um programa precisa para enfileirar trabalho no dispositivo. */
typedef struct {
    cl_platform_id plataforma;
    cl_device_id dispositivo;
    cl_context contexto;
    cl_command_queue fila;
} NucleoOcl;

/* Escolhe o primeiro dispositivo disponível (no container: a CPU via PoCL),
 * cria contexto e fila. Com profiling = 1 a fila mede o tempo de cada comando.
 * Devolve 0 em caso de sucesso; em erro, explica o motivo em stderr. */
int ocl_iniciar(NucleoOcl *ocl, int profiling);
void ocl_encerrar(NucleoOcl *ocl);

/* Lê kernels/<arquivo> (pasta trocável pela variável NUCLEO_KERNELS) e compila.
 * Em erro de compilação, imprime o log do compilador do OpenCL. */
cl_program ocl_compilar(NucleoOcl *ocl, const char *arquivo);

/* Duração de um comando já concluído, em milissegundos (exige profiling). */
double ocl_duracao_ms(cl_event evento);

/* Texto legível de um código de erro do OpenCL (ex.: "CL_OUT_OF_RESOURCES"). */
const char *ocl_erro(cl_int codigo);

/* Atalhos para ler informações em texto do dispositivo e da plataforma. */
void ocl_info_dispositivo(cl_device_id d, cl_device_info campo, char *buf, size_t tam);
void ocl_info_plataforma(cl_platform_id p, cl_platform_info campo, char *buf, size_t tam);

/* Aborta o programa com uma mensagem clara se `codigo` não for CL_SUCCESS. */
#define OCL_CHECAR(codigo, contexto)                                          \
    do {                                                                      \
        cl_int ocl_c_ = (codigo);                                             \
        if (ocl_c_ != CL_SUCCESS) ocl_falhar(ocl_c_, (contexto), __FILE__, __LINE__); \
    } while (0)

void ocl_falhar(cl_int codigo, const char *contexto, const char *arquivo, int linha);

#endif
