# Imagem com PoCL (runtime OpenCL por software) — permite rodar o núcleo em
# CPU, sem depender de GPU/driver específico, igual nas três máquinas do time.
# Implementação do serviço (main.c, kernels .cl) é trabalho da Sprint 3.
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    ocl-icd-opencl-dev \
    pocl-opencl-icd \
    clinfo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/ ./src/

# Placeholder — substituir pelo binário real na Sprint 3 (compilar main.c
# linkando -lOpenCL e servindo a API HTTP enxuta do contrato em README.md)
CMD ["clinfo"]
