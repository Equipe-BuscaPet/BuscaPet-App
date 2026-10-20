#include "ocl.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void ocl_falhar(cl_int codigo, const char *contexto, const char *arquivo, int linha) {
    fprintf(stderr, "[nucleo] erro OpenCL em %s (%s:%d): %s (%d)\n",
            contexto, arquivo, linha, ocl_erro(codigo), (int)codigo);
    exit(EXIT_FAILURE);
}

int ocl_iniciar(NucleoOcl *ocl, int profiling) {
    memset(ocl, 0, sizeof(*ocl));

    cl_uint n_plataformas = 0;
    cl_int err = clGetPlatformIDs(0, NULL, &n_plataformas);
    if (err != CL_SUCCESS || n_plataformas == 0) {
        fprintf(stderr, "[nucleo] nenhuma plataforma OpenCL encontrada (%s). "
                        "O PoCL está instalado? Rode `clinfo` para conferir.\n", ocl_erro(err));
        return -1;
    }

    cl_platform_id plataformas[8];
    if (n_plataformas > 8) n_plataformas = 8;
    OCL_CHECAR(clGetPlatformIDs(n_plataformas, plataformas, NULL), "listar plataformas");

    /* Primeira plataforma que tiver algum dispositivo. */
    for (cl_uint i = 0; i < n_plataformas; i++) {
        cl_device_id d;
        if (clGetDeviceIDs(plataformas[i], CL_DEVICE_TYPE_ALL, 1, &d, NULL) == CL_SUCCESS) {
            ocl->plataforma = plataformas[i];
            ocl->dispositivo = d;
            break;
        }
    }
    if (!ocl->dispositivo) {
        fprintf(stderr, "[nucleo] há plataforma OpenCL, mas nenhum dispositivo disponível.\n");
        return -1;
    }

    ocl->contexto = clCreateContext(NULL, 1, &ocl->dispositivo, NULL, NULL, &err);
    OCL_CHECAR(err, "criar contexto");

    cl_command_queue_properties props = profiling ? CL_QUEUE_PROFILING_ENABLE : 0;
    ocl->fila = clCreateCommandQueue(ocl->contexto, ocl->dispositivo, props, &err);
    OCL_CHECAR(err, "criar fila de comandos");
    return 0;
}

void ocl_encerrar(NucleoOcl *ocl) {
    if (ocl->fila) clReleaseCommandQueue(ocl->fila);
    if (ocl->contexto) clReleaseContext(ocl->contexto);
    memset(ocl, 0, sizeof(*ocl));
}

static char *ler_arquivo(const char *caminho) {
    FILE *f = fopen(caminho, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long tam = ftell(f);
    rewind(f);
    char *texto = malloc((size_t)tam + 1);
    if (texto && fread(texto, 1, (size_t)tam, f) != (size_t)tam) {
        free(texto);
        texto = NULL;
    }
    if (texto) texto[tam] = '\0';
    fclose(f);
    return texto;
}

cl_program ocl_compilar(NucleoOcl *ocl, const char *arquivo) {
    const char *pasta = getenv("NUCLEO_KERNELS");
    if (!pasta || !*pasta) pasta = "kernels";

    char caminho[512];
    snprintf(caminho, sizeof(caminho), "%s/%s", pasta, arquivo);
    char *fonte = ler_arquivo(caminho);
    if (!fonte) {
        fprintf(stderr, "[nucleo] não consegui ler o kernel %s "
                        "(ajuste NUCLEO_KERNELS para a pasta dos .cl).\n", caminho);
        exit(EXIT_FAILURE);
    }

    cl_int err;
    const char *fontes[] = {fonte};
    cl_program programa = clCreateProgramWithSource(ocl->contexto, 1, fontes, NULL, &err);
    free(fonte);
    OCL_CHECAR(err, "criar programa");

    err = clBuildProgram(programa, 1, &ocl->dispositivo, "-cl-std=CL1.2", NULL, NULL);
    if (err != CL_SUCCESS) {
        size_t tam_log = 0;
        clGetProgramBuildInfo(programa, ocl->dispositivo, CL_PROGRAM_BUILD_LOG, 0, NULL, &tam_log);
        char *log = malloc(tam_log + 1);
        clGetProgramBuildInfo(programa, ocl->dispositivo, CL_PROGRAM_BUILD_LOG, tam_log, log, NULL);
        log[tam_log] = '\0';
        fprintf(stderr, "[nucleo] falha ao compilar %s:\n%s\n", caminho, log);
        free(log);
        exit(EXIT_FAILURE);
    }
    return programa;
}

double ocl_duracao_ms(cl_event evento) {
    cl_ulong inicio = 0, fim = 0;
    OCL_CHECAR(clGetEventProfilingInfo(evento, CL_PROFILING_COMMAND_START, sizeof(inicio), &inicio, NULL),
               "ler início do evento");
    OCL_CHECAR(clGetEventProfilingInfo(evento, CL_PROFILING_COMMAND_END, sizeof(fim), &fim, NULL),
               "ler fim do evento");
    return (double)(fim - inicio) / 1e6; /* nanossegundos → milissegundos */
}

void ocl_info_dispositivo(cl_device_id d, cl_device_info campo, char *buf, size_t tam) {
    if (clGetDeviceInfo(d, campo, tam, buf, NULL) != CL_SUCCESS) snprintf(buf, tam, "?");
}

void ocl_info_plataforma(cl_platform_id p, cl_platform_info campo, char *buf, size_t tam) {
    if (clGetPlatformInfo(p, campo, tam, buf, NULL) != CL_SUCCESS) snprintf(buf, tam, "?");
}

const char *ocl_erro(cl_int codigo) {
    switch (codigo) {
#define CASO(c) case c: return #c
        CASO(CL_SUCCESS);
        CASO(CL_DEVICE_NOT_FOUND);
        CASO(CL_DEVICE_NOT_AVAILABLE);
        CASO(CL_COMPILER_NOT_AVAILABLE);
        CASO(CL_MEM_OBJECT_ALLOCATION_FAILURE);
        CASO(CL_OUT_OF_RESOURCES);
        CASO(CL_OUT_OF_HOST_MEMORY);
        CASO(CL_PROFILING_INFO_NOT_AVAILABLE);
        CASO(CL_BUILD_PROGRAM_FAILURE);
        CASO(CL_INVALID_VALUE);
        CASO(CL_INVALID_PLATFORM);
        CASO(CL_INVALID_DEVICE);
        CASO(CL_INVALID_CONTEXT);
        CASO(CL_INVALID_COMMAND_QUEUE);
        CASO(CL_INVALID_MEM_OBJECT);
        CASO(CL_INVALID_PROGRAM);
        CASO(CL_INVALID_PROGRAM_EXECUTABLE);
        CASO(CL_INVALID_KERNEL_NAME);
        CASO(CL_INVALID_KERNEL);
        CASO(CL_INVALID_ARG_INDEX);
        CASO(CL_INVALID_ARG_VALUE);
        CASO(CL_INVALID_ARG_SIZE);
        CASO(CL_INVALID_KERNEL_ARGS);
        CASO(CL_INVALID_WORK_DIMENSION);
        CASO(CL_INVALID_WORK_GROUP_SIZE);
        CASO(CL_INVALID_WORK_ITEM_SIZE);
        CASO(CL_INVALID_GLOBAL_WORK_SIZE);
        CASO(CL_INVALID_EVENT);
        CASO(CL_INVALID_BUFFER_SIZE);
#undef CASO
    case -1001: /* CL_PLATFORM_NOT_FOUND_KHR, definido em cl_ext.h */
        return "CL_PLATFORM_NOT_FOUND_KHR (nenhum driver OpenCL instalado)";
    default:
        return "erro OpenCL desconhecido";
    }
}
