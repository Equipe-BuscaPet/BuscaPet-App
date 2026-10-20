/*
 * descritor.cl — pré-processamento e extração de descritores visuais (RF-21).
 *
 * Trabalha em LOTE: a dimensão 1 do NDRange é a imagem do lote, a dimensão 0 é
 * o pixel. Toda a conta é feita com inteiros, de propósito: assim a versão
 * paralela devolve exatamente os mesmos números que a sequencial em C
 * (src/descritor.c), e o teste de equivalência pode exigir igualdade bit a bit.
 *
 * Etapas (uma chamada de kernel cada, todas por pixel e independentes):
 *   1. redimensionar   foto de qualquer tamanho → 128×128 (bilinear em ponto fixo)
 *   2. somar_canais    soma de R, G, B da imagem inteira e da moldura (fundo)
 *   3. classificar     corrige a iluminação (cor e brilho), calcula o tom (HSV),
 *                      o cinza e separa o animal do fundo (máscara)
 *   4. lbp             textura: padrão binário local (LBP "riu2", 10 classes)
 *   5. histogramas     contagens por região/tom, textura e o retângulo do animal
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
 * (deslocamento, largura, altura) da imagem i. destino: LADO×LADO×3 por imagem. */
__kernel void redimensionar(__global const uchar *origem, __global const int *info,
                            __global uchar *destino) {
    const int p = get_global_id(0);
    const int img = get_global_id(1);
    if (p >= PIXELS) return;
    const int desloc = info[3 * img], w = info[3 * img + 1], h = info[3 * img + 2];
    const int x = p % LADO, y = p / LADO;

    /* centro do pixel de destino no espaço da origem, com 8 bits de fração */
    int fx = ((2 * x + 1) * w * 256) / (2 * LADO) - 128;
    int fy = ((2 * y + 1) * h * 256) / (2 * LADO) - 128;
    fx = max(fx, 0);
    fy = max(fy, 0);
    const int x0 = min(fx >> 8, w - 1), y0 = min(fy >> 8, h - 1);
    const int x1 = min(x0 + 1, w - 1), y1 = min(y0 + 1, h - 1);
    const int ax = fx & 255, ay = fy & 255;

    for (int c = 0; c < 3; c++) {
        const int p00 = origem[desloc + (y0 * w + x0) * 3 + c];
        const int p01 = origem[desloc + (y0 * w + x1) * 3 + c];
        const int p10 = origem[desloc + (y1 * w + x0) * 3 + c];
        const int p11 = origem[desloc + (y1 * w + x1) * 3 + c];
        const int cima = p00 * (256 - ax) + p01 * ax;
        const int baixo = p10 * (256 - ax) + p11 * ax;
        destino[(img * PIXELS + p) * 3 + c] = (uchar)((cima * (256 - ay) + baixo * ay + 32768) >> 16);
    }
}

/* ---------------------------------------------------------------- 2 */
/* Cada grupo de trabalho soma no próprio "rascunho" (memória local) e só no fim
 * faz uma atualização na memória global: menos disputa entre os núcleos. */
__kernel void somar_canais(__global const uchar *img128, __global int *somas) {
    __local int parcial[N_SOMAS];
    const int lid = get_local_id(0);
    if (lid < N_SOMAS) parcial[lid] = 0;
    barrier(CLK_LOCAL_MEM_FENCE);

    const int p = get_global_id(0);
    const int img = get_global_id(1);
    if (p < PIXELS) {
        const int x = p % LADO, y = p / LADO;
        __global const uchar *px = img128 + (img * PIXELS + p) * 3;
        atomic_add(&parcial[S_R], px[0]);
        atomic_add(&parcial[S_G], px[1]);
        atomic_add(&parcial[S_B], px[2]);
        if (x < MOLDURA || y < MOLDURA || x >= LADO - MOLDURA || y >= LADO - MOLDURA) {
            atomic_add(&parcial[S_BR], px[0]);
            atomic_add(&parcial[S_BG], px[1]);
            atomic_add(&parcial[S_BB], px[2]);
            atomic_inc(&parcial[S_BN]);
        }
    }
    barrier(CLK_LOCAL_MEM_FENCE);
    if (lid < N_SOMAS && parcial[lid] != 0) atomic_add(&somas[img * N_SOMAS + lid], parcial[lid]);
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

/* saída por pixel: tom (0..51), cinza (0..255) e máscara (1 = animal). */
__kernel void classificar(__global const uchar *img128, __global const int *somas,
                          __global uchar *tom, __global uchar *cinza, __global uchar *mascara) {
    const int p = get_global_id(0);
    const int img = get_global_id(1);
    if (p >= PIXELS) return;
    __global const int *s = somas + img * N_SOMAS;
    const int gr = ganho(s[S_R]), gg = ganho(s[S_G]), gb = ganho(s[S_B]);
    const int n = max(s[S_BN], 1);
    const int fr = min(255, ((s[S_BR] / n) * gr) >> 10);
    const int fg = min(255, ((s[S_BG] / n) * gg) >> 10);
    const int fb = min(255, ((s[S_BB] / n) * gb) >> 10);

    __global const uchar *px = img128 + (img * PIXELS + p) * 3;
    const int r = min(255, (px[0] * gr) >> 10);
    const int g = min(255, (px[1] * gg) >> 10);
    const int b = min(255, (px[2] * gb) >> 10);

    const int i = img * PIXELS + p;
    tom[i] = (uchar)classe_tom(r, g, b);
    cinza[i] = (uchar)((77 * r + 150 * g + 29 * b) >> 8);
    mascara[i] = (uchar)((abs(r - fr) + abs(g - fg) + abs(b - fb)) > LIMIAR_FUNDO);
}

/* ---------------------------------------------------------------- 4 */
/* LBP rotacionalmente invariante e "uniforme" (riu2), 8 vizinhos: conta quantos
 * vizinhos são ≥ ao centro (0..8) se o padrão tiver no máximo 2 transições; senão
 * classe 9 (padrão irregular). Bordas da imagem ficam com 255 (sem textura). */
__kernel void lbp(__global const uchar *cinza, __global uchar *classe) {
    const int p = get_global_id(0);
    const int img = get_global_id(1);
    if (p >= PIXELS) return;
    const int x = p % LADO, y = p / LADO;
    const int i = img * PIXELS + p;
    if (x == 0 || y == 0 || x == LADO - 1 || y == LADO - 1) {
        classe[i] = 255;
        return;
    }
    __global const uchar *c = cinza + img * PIXELS;
    const int centro = c[p];
    /* vizinhos em volta, no sentido horário a partir do canto superior esquerdo */
    const int dx[8] = {-1, 0, 1, 1, 1, 0, -1, -1};
    const int dy[8] = {-1, -1, -1, 0, 1, 1, 1, 0};
    int bits[8], uns = 0;
    for (int k = 0; k < 8; k++) {
        bits[k] = c[(y + dy[k]) * LADO + (x + dx[k])] >= centro;
        uns += bits[k];
    }
    int transicoes = 0;
    for (int k = 0; k < 8; k++) transicoes += bits[k] != bits[(k + 1) & 7];
    classe[i] = (uchar)(transicoes <= 2 ? uns : 9);
}

/* ---------------------------------------------------------------- 5 */
/* Contagens por imagem. Começam zeradas, exceto MIN_X/MIN_Y (= LADO) e
 * MAX_X/MAX_Y (= -1), preparados pelo host. */
__kernel void histogramas(__global const uchar *tom, __global const uchar *classe_lbp,
                          __global const uchar *mascara, __global int *estat) {
    const int p = get_global_id(0);
    const int img = get_global_id(1);
    if (p >= PIXELS) return;
    const int x = p % LADO, y = p / LADO;
    const int i = img * PIXELS + p;
    __global int *e = estat + img * N_ESTAT;
    const int regiao = (y >= LADO / 2) * 2 + (x >= LADO / 2);
    const int t = regiao * TONS + tom[i];
    const int animal = mascara[i];
    const int l = classe_lbp[i];

    atomic_inc(&e[E_COR_TODOS + t]);
    if (l != 255) atomic_inc(&e[E_LBP_TODOS + l]);
    if (animal) {
        atomic_inc(&e[E_COR_ANIMAL + t]);
        if (l != 255) atomic_inc(&e[E_LBP_ANIMAL + l]);
        atomic_inc(&e[E_N_ANIMAL]);
        atomic_add(&e[E_SOMA_X], x);
        atomic_add(&e[E_SOMA_Y], y);
        atomic_min(&e[E_MIN_X], x);
        atomic_max(&e[E_MAX_X], x);
        atomic_min(&e[E_MIN_Y], y);
        atomic_max(&e[E_MAX_Y], y);
    }
}
