# app/routers/meta.py  # Router de metadatos para el frontend.

from fastapi import APIRouter  # Importa el enrutador de FastAPI para definir rutas simples.
from typing import Dict, List  # Tipado para claridad en la respuesta.

router = APIRouter(prefix="/api/meta", tags=["meta"])  # Crea un router con prefijo /api/meta.

@router.get("/options")
def get_meta_options() -> Dict[str, List[str]]:
    """
    Devuelve listas de CÓDIGOS (neutros) para que el frontend traduzca con t().
    Mantiene compatibilidad: expone 'allergens' y también 'allergy_suggestions'.
    """
    allergens_codes = ["gluten", "dairy", "nuts", "seafood", "eggs", "soy"]
    return {
        "allergens": allergens_codes,
        "allergy_suggestions": allergens_codes,  # alias legacy para no romper fronts viejos
        # Si necesitas más catálogos, agrégalos como códigos: attendance/menu/etc.
    }
