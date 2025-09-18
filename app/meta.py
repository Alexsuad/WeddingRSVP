# app/routers/meta.py  # Router de metadatos para el frontend.

from fastapi import APIRouter  # Importa el enrutador de FastAPI para definir rutas simples.
from typing import Dict, List  # Tipado para claridad en la respuesta.

router = APIRouter(prefix="/api/meta", tags=["meta"])  # Crea un router con prefijo /api/meta.

@router.get("/options")  # Define el endpoint GET /api/meta/options.
def get_meta_options() -> Dict[str, List[str]]:  # Firma que devuelve un dict con listas de strings.
    return {  # Retorna un diccionario con catálogos simples.
        "allergy_suggestions": [  # Lista de sugerencias de alergias que el frontend puede mostrar.
            "Gluten",  # Sugerencia 1.
            "Lácteos",  # Sugerencia 2.
            "Frutos secos",  # Sugerencia 3.
            "Mariscos",  # Sugerencia 4.
            "Huevos",  # Sugerencia 5.
            "Soja",  # Sugerencia 6.
        ],  # Fin de la lista.
        # Nota: Ya no exponemos opciones de menú porque hay un único servicio (adulto/niño implícito).
    }  # Fin del dict.
