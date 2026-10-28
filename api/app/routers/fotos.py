"""Entrega pública das fotos do reencontro (as gravadas por app/core/fotos.py)."""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.core import fotos as armazenamento

router = APIRouter(prefix="/fotos", tags=["reencontro"])


@router.get("/{nome}", response_class=Response)
def baixar(nome: str) -> Response:
    """Arquivo da foto (JPEG, sem metadados). O nome é aleatório e o conteúdo não muda, por isso fica em cache por 7 dias."""
    conteudo = armazenamento.ler(nome)
    if conteudo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto não encontrada.")
    # O nome é aleatório e o conteúdo nunca muda: o navegador pode guardar a foto por muito tempo.
    return Response(conteudo, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800, immutable"})
