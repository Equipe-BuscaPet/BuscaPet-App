# Núcleo OpenCL do BuscaPet — imagem em dois estágios.
#
# PoCL é um runtime OpenCL por software: roda os kernels na CPU, sem depender
# de GPU nem de driver específico, igual nas máquinas do time, na CI e no deploy.

# ---------- Estágio 1: compilar e testar ----------
FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ocl-icd-opencl-dev \
        pocl-opencl-icd \
        libmicrohttpd-dev \
        libcjson-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY Makefile ./
COPY src/ ./src/
COPY kernels/ ./kernels/

# O build só termina se o teste de equivalência passar: uma imagem com kernel
# errado nunca chega a ser gerada.
ENV POCL_CACHE_DIR=/tmp/pocl
RUN make && make teste

# ---------- Estágio 2: imagem final, só o necessário para rodar ----------
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ocl-icd-libopencl1 \
        pocl-opencl-icd \
        libmicrohttpd12 \
        libcjson1 \
        clinfo \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home nucleo

WORKDIR /app
COPY --from=build /src/build/nucleo-servidor /src/build/spike /src/build/bench /src/build/teste-nucleo ./
COPY kernels/ ./kernels/

ENV PORTA=8001 \
    NUCLEO_KERNELS=/app/kernels \
    POCL_CACHE_DIR=/tmp/pocl

USER nucleo
EXPOSE 8001
CMD ["./nucleo-servidor"]
