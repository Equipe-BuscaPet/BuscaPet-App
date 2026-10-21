"""Recebimento e armazenamento das fotos do reencontro — RF-19 e RF-20.

Toda foto enviada é aberta e regravada pelo servidor antes de ser guardada:
- confirma que é mesmo uma imagem (JPEG, PNG ou WebP), e não um arquivo qualquer renomeado;
- corrige a rotação de foto de celular (tag EXIF de orientação) e reduz o maior lado para LADO_MAXIMO;
- grava um JPEG novo **sem metadados**: foto de celular costuma carregar a coordenada GPS de onde foi
  tirada (muitas vezes a casa de quem enviou), e o escopo (seção 9) proíbe expor o endereço de quem registra;
- o nome do arquivo é aleatório (uuid), sem nada que identifique o autor.

O arquivo fica em `settings.pasta_fotos` e é servido por `GET /fotos/{nome}`. Ao publicar (deploy), a
pasta pode ser trocada por um storage externo sem mudar o resto da API.
"""
import io
import re
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

FORMATOS_ACEITOS = {"JPEG", "PNG", "WEBP"}
LADO_MAXIMO = 1280
PIXELS_MAXIMOS = 40_000_000  # ~40 megapixels: acima disso é suspeito (imagem-bomba) e não é foto de celular
MAX_FOTOS = 5
NOME_VALIDO = re.compile(r"^[0-9a-f]{32}\.jpg$")


class FotoInvalida(ValueError):
    """Mensagem pronta para mostrar à pessoa (em português)."""


def tamanho_maximo_bytes() -> int:
    return settings.foto_tamanho_max_mb * 1024 * 1024


def processar(conteudo: bytes) -> bytes:
    """Valida e normaliza uma foto. Devolve os bytes do JPEG final, sem metadados."""
    if len(conteudo) > tamanho_maximo_bytes():
        raise FotoInvalida(f"cada foto pode ter no máximo {settings.foto_tamanho_max_mb} MB.")
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        if imagem.format not in FORMATOS_ACEITOS:
            raise FotoInvalida("envie fotos em JPEG, PNG ou WebP.")
        if imagem.width * imagem.height > PIXELS_MAXIMOS:
            raise FotoInvalida("a foto tem resolução grande demais.")
        imagem = ImageOps.exif_transpose(imagem)  # também carrega os pixels: arquivo corrompido falha aqui
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise FotoInvalida("o arquivo enviado não é uma imagem válida.")

    imagem = imagem.convert("RGB")  # PNG com transparência e WebP viram RGB comum
    imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85, optimize=True)  # sem exif=...: nenhum metadado é copiado
    return saida.getvalue()


def salvar(jpeg: bytes) -> str:
    """Grava a foto já processada e devolve o nome do arquivo (aleatório)."""
    pasta = Path(settings.pasta_fotos)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{uuid.uuid4().hex}.jpg"
    (pasta / nome).write_bytes(jpeg)
    return nome


def caminho(nome: str) -> Path | None:
    """Caminho do arquivo no disco, ou None se o nome não for de uma foto nossa (evita ler fora da pasta)."""
    if not NOME_VALIDO.match(nome):
        return None
    arquivo = Path(settings.pasta_fotos) / nome
    return arquivo if arquivo.is_file() else None


def url_publica(nome: str) -> str:
    return f"/fotos/{nome}"


def nome_da_url(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def apagar(nomes: list[str]) -> None:
    for nome in nomes:
        arquivo = caminho(nome)
        if arquivo:
            arquivo.unlink(missing_ok=True)
