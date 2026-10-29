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
NUCLEO = src/descritor.c src/descritor.h $(COMUM)

.PHONY: all leve teste teste-leve limpar

all: $(BUILD)/spike $(BUILD)/nucleo-servidor $(BUILD)/teste-nucleo $(BUILD)/bench

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/spike: src/spike.c $(COMUM) | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/spike.c src/ocl.c $(LDLIBS_OCL)

$(BUILD)/nucleo-servidor: src/servidor.c $(NUCLEO) | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -pthread -o $@ src/servidor.c src/descritor.c src/ocl.c \
		-lmicrohttpd -lcjson $(LDLIBS_OCL)

$(BUILD)/teste-nucleo: src/teste_nucleo.c $(NUCLEO) | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/teste_nucleo.c src/descritor.c src/ocl.c $(LDLIBS_OCL)

$(BUILD)/bench: src/bench.c $(NUCLEO) | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/bench.c src/descritor.c src/ocl.c $(LDLIBS_OCL)

# Tamanhos escolhidos de propósito: 1 (caso mínimo), um primo (não é múltiplo
# de nenhum tamanho de grupo) e o padrão de ~4 milhões de elementos.
teste: $(BUILD)/spike $(BUILD)/teste-nucleo
	./$(BUILD)/spike 1
	./$(BUILD)/spike 1000003
	./$(BUILD)/spike
	./$(BUILD)/teste-nucleo

limpar:
	rm -rf $(BUILD)

# Build "leve": sem OpenCL (nem PoCL), só o servidor HTTP com a versão sequencial em C. Gera os mesmos
# descritores e as mesmas notas; serve para hospedagem gratuita com pouca memória (imagem ~100 MB).
leve: $(BUILD)/nucleo-servidor-leve $(BUILD)/teste-leve

$(BUILD)/nucleo-servidor-leve: src/servidor.c src/descritor.c src/descritor.h | $(BUILD)
	$(CC) $(CPPFLAGS) -USEM_OPENCL -DSEM_OPENCL $(CFLAGS) -pthread -o $@ src/servidor.c src/descritor.c 		-lmicrohttpd -lcjson -lm

$(BUILD)/teste-leve: src/teste_nucleo.c src/descritor.c src/descritor.h | $(BUILD)
	$(CC) $(CPPFLAGS) -DSEM_OPENCL $(CFLAGS) -o $@ src/teste_nucleo.c src/descritor.c -lm

teste-leve: $(BUILD)/teste-leve
	./$(BUILD)/teste-leve
