"""Recebimento e armazenamento das fotos do reencontro — RF-19 e RF-20.

Toda foto enviada é aberta e regravada pelo servidor antes de ser guardada:
- confirma que é mesmo uma imagem (JPEG, PNG ou WebP), e não um arquivo qualquer renomeado;
- corrige a rotação de foto de celular (tag EXIF de orientação) e reduz o maior lado para LADO_MAXIMO;
- grava um JPEG novo **sem metadados**: foto de celular costuma carregar a coordenada GPS de onde foi
  tirada (muitas vezes a casa de quem enviou), e o escopo (seção 9) proíbe expor o endereço de quem registra;
- o nome do arquivo é aleatório (uuid), sem nada que identifique o autor.

O arquivo fica em `settings.pasta_fotos` (padrão) ou, com `ARMAZENAMENTO_FOTOS=banco`, na tabela
`fotos_arquivos` (hospedagem gratuita, onde o disco é apagado a cada reinício). Em qualquer caso é servido por
`GET /fotos/{nome}`; o resto da API só usa `salvar`, `ler` e `apagar`.
"""
import io
import re
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.animal import FotoArquivo

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


def _no_banco() -> bool:
    return settings.armazenamento_fotos == "banco"


def salvar(jpeg: bytes) -> str:
    """Grava a foto já processada e devolve o nome do arquivo (aleatório)."""
    nome = f"{uuid.uuid4().hex}.jpg"
    if _no_banco():
        with SessionLocal() as db:  # sessão própria: a foto fica gravada mesmo antes de o registro ser confirmado
            db.add(FotoArquivo(nome=nome, conteudo=jpeg))
            db.commit()
        return nome
    pasta = Path(settings.pasta_fotos)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_bytes(jpeg)
    return nome


def ler(nome: str) -> bytes | None:
    """Bytes da foto, ou None se o nome não for de uma foto nossa (evita ler fora da pasta) ou ela não existir."""
    if not NOME_VALIDO.match(nome):
        return None
    if _no_banco():
        with SessionLocal() as db:
            arquivo = db.get(FotoArquivo, nome)
            return arquivo.conteudo if arquivo else None
    arquivo = Path(settings.pasta_fotos) / nome
    return arquivo.read_bytes() if arquivo.is_file() else None


def url_publica(nome: str) -> str:
    return f"/fotos/{nome}"


def nome_da_url(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def apagar(nomes: list[str]) -> None:
    for nome in nomes:
        if not NOME_VALIDO.match(nome):
            continue
        if _no_banco():
            with SessionLocal() as db:
                arquivo = db.get(FotoArquivo, nome)
                if arquivo:
                    db.delete(arquivo)
                    db.commit()
        else:
            (Path(settings.pasta_fotos) / nome).unlink(missing_ok=True)
