/*
 * descritor.cl — pré-processamento e extração de descritores visuais (RF-21).
 *
 * Trabalha em LOTE: a dimensão 1 do NDRange é a imagem do lote, a dimensão 0 é
 * o pixel. Toda a conta é feita com inteiros, de propósito: assim a versão
 * paralela devolve exatamente os mesmos números que a sequencial em C
 * (src/descritor.c), e o teste de equivalência pode exigir igualdade bit a bit.
 *
 * Etapas (três kernels; cada item de trabalho cuida de LINHAS, não de pixels):
 *   1. redimensionar   foto de qualquer tamanho → 128×128 (bilinear em ponto fixo)
 *   2. somar_canais    soma de R, G, B da imagem inteira e da moldura (fundo)
 *   3. descrever       para um bloco de 8 linhas: corrige a iluminação (cor e
 *                      brilho), calcula o tom (HSV), o cinza, separa o animal do
 *                      fundo, a textura (LBP "riu2") e conta tudo num histograma
 *                      particular, somado ao da imagem só no fim
 *
 * Por que linhas e não pixels: na CPU, 16 mil itens de trabalho minúsculos por
 * foto, todos disputando os mesmos contadores, custam mais que a própria conta
 * (medido: o kernel de histogramas por pixel levava 40 ms para 100 fotos e não
 * ganhava do sequencial). Com blocos, cada núcleo faz bastante conta seguida e a
 * disputa acontece uma vez por bloco.
 *
 * As constantes abaixo são as mesmas de src/descritor.h (o host passa -D na
 * compilação para garantir isso).
 */

#ifndef LADO
#define LADO 128
#endif
#define PIXELS (LADO * LADO)
#define MOLDURA 6          /* faixa da borda usada para estimar a cor do fundo */
#define LIMIAR_FUNDO 60    /* distância |ΔR|+|ΔG|+|ΔB| a partir da qual o pixel é do animal */
#define TONS 52            /* 12 matizes × 2 saturações × 2 brilhos + 4 tons de cinza */
#define REGIOES 4
#define CLASSES_LBP 10
#define LINHAS_BLOCO 8
#define BLOCOS (LADO / LINHAS_BLOCO)

/* Posições do vetor de somas (por imagem). */
#define S_R 0
#define S_G 1
#define S_B 2
#define S_BR 3
#define S_BG 4
#define S_BB 5
#define S_BN 6
#define N_SOMAS 8

/* Estatísticas inteiras por imagem (layout igual ao de src/descritor.h). */
#define E_COR_ANIMAL 0                                   /* REGIOES*TONS */
#define E_COR_TODOS (E_COR_ANIMAL + REGIOES * TONS)      /* REGIOES*TONS */
#define E_LBP_ANIMAL (E_COR_TODOS + REGIOES * TONS)      /* CLASSES_LBP */
#define E_LBP_TODOS (E_LBP_ANIMAL + CLASSES_LBP)         /* CLASSES_LBP */
#define E_N_ANIMAL (E_LBP_TODOS + CLASSES_LBP)
#define E_SOMA_X (E_N_ANIMAL + 1)
#define E_SOMA_Y (E_SOMA_X + 1)
#define E_MIN_X (E_SOMA_Y + 1)
#define E_MAX_X (E_MIN_X + 1)
#define E_MIN_Y (E_MAX_X + 1)
#define E_MAX_Y (E_MIN_Y + 1)
#define N_ESTAT (E_MAX_Y + 1)

/* ---------------------------------------------------------------- 1 */
/* origem: bytes RGB de todas as imagens, uma atrás da outra; info[i] =
 * (deslocamento, largura, altura) da imagem i. destino: LADO×LADO×3 por imagem.
 * NDRange: (linha, imagem). */
__kernel void redimensionar(__global const uchar *origem, __global const int *info,
                            __global uchar *destino) {
    const int y = get_global_id(0);
    const int img = get_global_id(1);
    if (y >= LADO) return;
    const int desloc = info[3 * img], w = info[3 * img + 1], h = info[3 * img + 2];
    __global const uchar *o = origem + desloc;

    int fy = ((2 * y + 1) * h * 256) / (2 * LADO) - 128;
    fy = max(fy, 0);
    const int y0 = min(fy >> 8, h - 1), y1 = min(y0 + 1, h - 1), ay = fy & 255;
    for (int x = 0; x < LADO; x++) {
        /* centro do pixel de destino no espaço da origem, com 8 bits de fração */
        int fx = ((2 * x + 1) * w * 256) / (2 * LADO) - 128;
        fx = max(fx, 0);
        const int x0 = min(fx >> 8, w - 1), x1 = min(x0 + 1, w - 1), ax = fx & 255;
        for (int c = 0; c < 3; c++) {
            const int p00 = o[(y0 * w + x0) * 3 + c], p01 = o[(y0 * w + x1) * 3 + c];
            const int p10 = o[(y1 * w + x0) * 3 + c], p11 = o[(y1 * w + x1) * 3 + c];
            const int cima = p00 * (256 - ax) + p01 * ax, baixo = p10 * (256 - ax) + p11 * ax;
            destino[((img * LADO + y) * LADO + x) * 3 + c] = (uchar)((cima * (256 - ay) + baixo * ay + 32768) >> 16);
        }
    }
}

/* ---------------------------------------------------------------- 2 */
/* NDRange: (linha, imagem). Cada linha soma no particular e soma no global uma vez. */
__kernel void somar_canais(__global const uchar *img128, __global int *somas) {
    const int y = get_global_id(0);
    const int img = get_global_id(1);
    if (y >= LADO) return;
    __global const uchar *px = img128 + (img * LADO + y) * LADO * 3;
    int s[7] = {0, 0, 0, 0, 0, 0, 0};
    const int linha_moldura = y < MOLDURA || y >= LADO - MOLDURA;
    for (int x = 0; x < LADO; x++, px += 3) {
        s[S_R] += px[0];
        s[S_G] += px[1];
        s[S_B] += px[2];
        if (linha_moldura || x < MOLDURA || x >= LADO - MOLDURA) {
            s[S_BR] += px[0];
            s[S_BG] += px[1];
            s[S_BB] += px[2];
            s[S_BN]++;
        }
    }
    for (int k = 0; k < 7; k++)
        if (s[k]) atomic_add(&somas[img * N_SOMAS + k], s[k]);
}

/* ---------------------------------------------------------------- 3 */
/* Ganho em ponto fixo (1024 = 1,0), limitado a 4,0: leva a média de cada canal
 * para o cinza médio (128). Corrige o tom da luz (gray-world) e o brilho da foto
 * ao mesmo tempo — a mesma cena, mais clara ou mais escura, dá o mesmo descritor. */
inline int ganho(long soma_canal) {
    if (soma_canal == 0) return 1024;
    return (int)min((long)4096, (128L * 1024 * PIXELS) / soma_canal);
}

/* Tom: 48 classes coloridas (12 matizes × 2 saturações × 2 brilhos) e, se a cor
 * é quase cinza (pouca saturação), 4 classes de cinza pelo brilho. */
inline int classe_tom(int r, int g, int b) {
    const int mx = max(r, max(g, b)), mn = min(r, min(g, b)), delta = mx - mn;
    const int s = mx == 0 ? 0 : (delta * 255) / mx;
    if (s < 40) return 48 + (mx * 4) / 256;
    int h;
    if (mx == r) h = (60 * (g - b)) / delta;
    else if (mx == g) h = 120 + (60 * (b - r)) / delta;
    else h = 240 + (60 * (r - g)) / delta;
    if (h < 0) h += 360;
    const int hb = (h * 12) / 360, sb = s < 128 ? 0 : 1, vb = mx < 128 ? 0 : 1;
    return (hb * 2 + sb) * 2 + vb;
}

/* NDRange: (bloco de LINHAS_BLOCO linhas, imagem). As contagens globais começam
 * zeradas, exceto MIN_X/MIN_Y (= LADO) e MAX_X/MAX_Y (= -1), preparados pelo host. */
__kernel void descrever(__global const uchar *img128, __global const int *somas, __global int *estat) {
    const int bloco = get_global_id(0);
    const int img = get_global_id(1);
    if (bloco >= BLOCOS) return;
    const int y0 = bloco * LINHAS_BLOCO;

    __global const int *s = somas + img * N_SOMAS;
    const int gr = ganho(s[S_R]), gg = ganho(s[S_G]), gb = ganho(s[S_B]);
    const int n = max(s[S_BN], 1);
    const int fr = min(255, ((s[S_BR] / n) * gr) >> 10);
    const int fg = min(255, ((s[S_BG] / n) * gg) >> 10);
    const int fb = min(255, ((s[S_BB] / n) * gb) >> 10);

    /* cinza das linhas do bloco + 1 linha acima e 1 abaixo (vizinhos do LBP) */
    uchar cinza[LINHAS_BLOCO + 2][LADO];
    uchar tom[LINHAS_BLOCO][LADO], animal[LINHAS_BLOCO][LADO];
    for (int dy = -1; dy <= LINHAS_BLOCO; dy++) {
        const int y = y0 + dy;
        if (y < 0 || y >= LADO) continue;
        __global const uchar *px = img128 + (img * LADO + y) * LADO * 3;
        for (int x = 0; x < LADO; x++, px += 3) {
            const int r = min(255, (px[0] * gr) >> 10);
            const int g = min(255, (px[1] * gg) >> 10);
            const int b = min(255, (px[2] * gb) >> 10);
            cinza[dy + 1][x] = (uchar)((77 * r + 150 * g + 29 * b) >> 8);
            if (dy >= 0 && dy < LINHAS_BLOCO) {
                tom[dy][x] = (uchar)classe_tom(r, g, b);
                animal[dy][x] = (uchar)((abs(r - fr) + abs(g - fg) + abs(b - fb)) > LIMIAR_FUNDO);
            }
        }
    }

    int h[N_ESTAT];
    for (int k = 0; k < N_ESTAT; k++) h[k] = 0;
    h[E_MIN_X] = LADO;
    h[E_MAX_X] = -1;
    h[E_MIN_Y] = LADO;
    h[E_MAX_Y] = -1;
    /* vizinhos em volta, no sentido horário a partir do canto superior esquerdo */
    const int dxs[8] = {-1, 0, 1, 1, 1, 0, -1, -1};
    const int dys[8] = {-1, -1, -1, 0, 1, 1, 1, 0};
    for (int dy = 0; dy < LINHAS_BLOCO; dy++) {
        const int y = y0 + dy;
        for (int x = 0; x < LADO; x++) {
            /* LBP rotacionalmente invariante e "uniforme" (riu2), 8 vizinhos: conta
             * quantos vizinhos são ≥ ao centro (0..8) se o padrão tiver no máximo 2
             * transições; senão classe 9. Pixels da borda da foto não têm textura. */
            int l = 255;
            if (x > 0 && y > 0 && x < LADO - 1 && y < LADO - 1) {
                const int centro = cinza[dy + 1][x];
                int bits[8], uns = 0, transicoes = 0;
                for (int k = 0; k < 8; k++) {
                    bits[k] = cinza[dy + 1 + dys[k]][x + dxs[k]] >= centro;
                    uns += bits[k];
                }
                for (int k = 0; k < 8; k++) transicoes += bits[k] != bits[(k + 1) & 7];
                l = transicoes <= 2 ? uns : 9;
            }
            const int t = ((y >= LADO / 2) * 2 + (x >= LADO / 2)) * TONS + tom[dy][x];
            h[E_COR_TODOS + t]++;
            if (l != 255) h[E_LBP_TODOS + l]++;
            if (animal[dy][x]) {
                h[E_COR_ANIMAL + t]++;
                if (l != 255) h[E_LBP_ANIMAL + l]++;
                h[E_N_ANIMAL]++;
                h[E_SOMA_X] += x;
                h[E_SOMA_Y] += y;
                h[E_MIN_X] = min(h[E_MIN_X], x);
                h[E_MAX_X] = max(h[E_MAX_X], x);
                h[E_MIN_Y] = min(h[E_MIN_Y], y);
                h[E_MAX_Y] = max(h[E_MAX_Y], y);
            }
        }
    }

    __global int *e = estat + img * N_ESTAT;
    for (int k = 0; k < N_ESTAT; k++) {
        if (k == E_MIN_X || k == E_MIN_Y) atomic_min(&e[k], h[k]);
        else if (k == E_MAX_X || k == E_MAX_Y) atomic_max(&e[k], h[k]);
        else if (h[k] != 0) atomic_add(&e[k], h[k]);
    }
}
