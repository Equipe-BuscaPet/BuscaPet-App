# Núcleo OpenCL — compilação e testes.
# Feito para rodar dentro da imagem Docker (ver Dockerfile), onde PoCL,
# libmicrohttpd e cJSON já estão instalados. Alvos principais:
#   make          compila tudo em build/
#   make teste    roda o teste de equivalência sequencial x OpenCL
#   make limpar   apaga build/

CC       ?= gcc
CFLAGS   ?= -O2 -std=c11 -Wall -Wextra -Wpedantic
CPPFLAGS += -D_POSIX_C_SOURCE=200809L -DCL_TARGET_OPENCL_VERSION=120 -Isrc
LDLIBS_OCL = -lOpenCL -lm

BUILD = build
COMUM = src/ocl.c src/ocl.h

.PHONY: all teste limpar

all: $(BUILD)/spike $(BUILD)/nucleo-servidor

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/spike: src/spike.c $(COMUM) | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/spike.c src/ocl.c $(LDLIBS_OCL)

$(BUILD)/nucleo-servidor: src/servidor.c $(COMUM) | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -pthread -o $@ src/servidor.c src/ocl.c \
		-lmicrohttpd -lcjson $(LDLIBS_OCL)

# Tamanhos escolhidos de propósito: 1 (caso mínimo), um primo (não é múltiplo
# de nenhum tamanho de grupo) e o padrão de ~4 milhões de elementos.
teste: $(BUILD)/spike
	./$(BUILD)/spike 1
	./$(BUILD)/spike 1000003
	./$(BUILD)/spike

limpar:
	rm -rf $(BUILD)
