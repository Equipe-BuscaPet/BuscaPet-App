"""Entrega pública das fotos do reencontro (as gravadas por app/core/fotos.py)."""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core import fotos as armazenamento

router = APIRouter(prefix="/fotos", tags=["reencontro"])


@router.get("/{nome}", response_class=FileResponse)
def baixar(nome: str) -> FileResponse:
    arquivo = armazenamento.caminho(nome)
    if arquivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto não encontrada.")
    # O nome é aleatório e o conteúdo nunca muda: o navegador pode guardar a foto por muito tempo.
    return FileResponse(arquivo, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800, immutable"})
