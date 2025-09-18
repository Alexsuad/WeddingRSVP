# app/utils/rate_limit.py                                                                                      # Ruta del archivo (nuevo).

# =================================================================================                               # Separador visual.
# 🚦 Rate limit ligero en memoria                                                                                # Título.
# ---------------------------------------------------------------------------------                               # Separador.
# - Implementa una ventana deslizante en memoria por clave (IP + ruta).                                          # Descripción.
# - Útil para entornos single-process (Streamlit/uvicorn simple).                                                # Alcance.
# - Para despliegues multiinstancia usa Redis/Upstash o un reverse-proxy (NGINX, Cloudflare).                    # Nota prod.
# =================================================================================                               # Fin encabezado.

import os                                              # Para leer variables de entorno (.env).                     # Import OS.
import time                                            # Para obtener timestamps con time.time().                   # Import time.
from collections import deque                          # Deque eficiente para pops en cola.                         # Import deque.
from typing import Dict                                # Tipado para dict.                                          # Import typing.
from loguru import logger                              # Logger para trazas.                                         # Import logger.

# Estructura en memoria: clave → deque de timestamps (segundos)                                                   # Explicación estructura.
_BUCKETS: Dict[str, deque] = {}                        # Diccionario global de cubos por clave.                      # Estado global.

def _now() -> float:                                   # Helper: devuelve tiempo actual en segundos (float).        # Helper now.
    return time.time()                                 # Retorna epoch seconds.                                      # Retorno.

def is_allowed(key: str, max_req: int, window_s: int) -> bool:
    """Devuelve True si la acción está permitida para 'key' según (max_req/window_s)."""                           # Docstring.
    if max_req <= 0:                                    # Si el límite es 0 o negativo...                            # Chequeo rápido.
        return True                                     # ...no rate-limiteamos.                                     # Sin límite.

    bucket = _BUCKETS.get(key)                         # Obtiene o crea el deque para la clave.                     # Busca cubo.
    if bucket is None:                                 # Si no existe...                                             # Condicional.
        bucket = deque()                               # ...crea un deque vacío.                                     # Crea deque.
        _BUCKETS[key] = bucket                         # ...y lo guarda.                                             # Guarda cubo.

    now = _now()                                       # Timestamp actual.                                           # now.

    # Purga timestamps fuera de la ventana [now - window_s, now].                                                  # Comentario purga.
    cutoff = now - window_s                            # Límite inferior de la ventana.                              # cutoff.
    while bucket and bucket[0] <= cutoff:              # Mientras haya elementos viejos al frente...                 # Loop purga.
        bucket.popleft()                               # ...elimínalos.                                              # Pop left.

    if len(bucket) >= max_req:                         # Si ya alcanzó el máximo dentro de ventana...                # Chequeo límite.
        logger.warning(f"Rate limit hit for key='{key}' ({len(bucket)}/{max_req} in {window_s}s)")  # Log aviso.    # Log.
        return False                                   # Deniega.                                                    # Deniega.

    bucket.append(now)                                 # Registra el intento actual.                                 # Push timestamp.
    return True                                        # Permite.                                                    # Permite.

def get_limits_from_env(prefix: str, default_max: int, default_window: int) -> tuple[int, int]:
    """Lee MAX y WINDOW en segundos desde env: {prefix}_MAX, {prefix}_WINDOW; aplica defaults si no están."""       # Docstring.
    try:                                              # Intenta parsear enteros desde env.                           # Try parse.
        max_req = int(os.getenv(f"{prefix}_MAX", str(default_max)))         # Límite de solicitudes.               # MAX.
        window = int(os.getenv(f"{prefix}_WINDOW", str(default_window)))    # Tamaño de ventana en segundos.       # WINDOW.
    except ValueError:                                 # Si hay valores inválidos...                                  # Except.
        max_req, window = default_max, default_window  # ...usa los defaults.                                        # Defaults.
    return max_req, window                             # Devuelve tupla (max, window).                                # Retorno.
