"""Calcula o descritor visual (RF-21) de todas as fotos que ainda não têm — por exemplo, as dos dados de
demonstração ou as enviadas enquanto o núcleo estava fora do ar.

    python -m app.scripts.indexar_fotos          (precisa do núcleo no ar: NUCLEO_OPENCL_URL)
"""
from sqlalchemy import select

from app.core import nucleo
from app.db.session import SessionLocal
from app.models.animal import Foto
from app.models.reencontro import DescritorVisual


def main() -> None:
    print("núcleo:", nucleo.saude()["opencl"]["dispositivo"])
    with SessionLocal() as db:
        sem = list(db.scalars(
            select(Foto).outerjoin(DescritorVisual, DescritorVisual.foto_id == Foto.id).where(DescritorVisual.id.is_(None))
        ))
        feitas = nucleo.indexar(db, sem, repassar_falha=True)
        print(f"{feitas} de {len(sem)} fotos sem descritor foram indexadas.")


if __name__ == "__main__":
    main()
