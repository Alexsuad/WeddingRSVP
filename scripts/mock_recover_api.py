# scripts/mock_recover_api.py  # Ubicación: carpeta de scripts ejecutables del proyecto.          # Comentario ruta/rol.

from fastapi import FastAPI, Response, status  # FastAPI para servidor; Response/status para construir respuestas.  # Imports FastAPI.
from pydantic import BaseModel                 # Pydantic para validar/parsear JSON entrante.                       # Import Pydantic.
from typing import Optional                    # Optional para campos opcionales en el modelo.                      # Import typing.
import uvicorn                                 # Uvicorn para ejecutar servidor ASGI local.                         # Import uvicorn.
from loguru import logger                      # Loguru para logs legibles.                                         # Import loguru.

app = FastAPI(title="Mock Recover API", version="1.0.0")  # Instancia la app con título/versión informativos.      # FastAPI app.

class RecoveryRequest(BaseModel):              # Esquema del body esperado por /api/recover-code.                   # Modelo request.
    email: Optional[str] = None                # Email opcional (string o None).                                    # Campo email.
    phone: Optional[str] = None                # Teléfono opcional (string o None).                                  # Campo phone.

@app.get("/health")                            # Endpoint simple para chequear estado del mock.                      # Ruta /health.
async def health():                            # Handler asíncrono.                                                  # Handler health.
    return {"ok": True}                        # Respuesta JSON indicando OK.                                        # Respuesta health.

@app.post("/api/recover-code")                 # Endpoint que emula el backend real.                                 # Ruta recover.
async def recover(req: RecoveryRequest) -> Response:  # Recibe el body validado y devuelve una Response.            # Handler recover.
    email = (req.email or "").strip().lower()  # Normaliza email (strip + lower); si None, cadena vacía.            # Normaliza email.
    phone = (req.phone or "").strip()          # Normaliza phone (solo strip); si None, cadena vacía.               # Normaliza phone.

    logger.info(f"[MOCK] /api/recover-code ← email='{email}' phone='{phone}'")  # Log de entrada con payload.       # Log entrada.

    if not email and not phone:                # Si faltan ambos campos...                                           # Validación mínima.
        body = '{"detail":"Debes proporcionar al menos un email o teléfono"}'   # Cuerpo JSON 400 breve.            # Cuerpo 400.
        return Response(content=body, media_type="application/json",
                        status_code=status.HTTP_400_BAD_REQUEST)                 # Devuelve 400 Bad Request.         # Respuesta 400.

    key = email or phone                       # Usa una referencia única (prioriza email, si no, teléfono).         # Clave de decisión.

    # Reglas de simulación según contenido de 'key':
    if any(token in key for token in ("ok", "success")):        # Si contiene tokens de éxito...                      # Regla 200.
        body = '{"message":"Si tu contacto está en nuestra lista de invitados, recibirás un mensaje en breve."}'     # Cuerpo 200.
        logger.info("[MOCK] → 200 OK")                          # Log OK.                                            # Log 200.
        return Response(content=body, media_type="application/json",
                        status_code=status.HTTP_200_OK)         # Devuelve 200 OK.                                   # Respuesta 200.

    if any(token in key for token in ("rl", "429", "rate")):    # Si contiene tokens de rate-limit...                 # Regla 429.
        body = '{"message":"Too Many Requests (mock)"}'         # Cuerpo mínimo 429.                                  # Cuerpo 429.
        headers = {"Retry-After": "45"}                         # Header estándar para indicar espera.                # Header 429.
        logger.warning("[MOCK] → 429 Too Many Requests (Retry-After=45)")  # Log advertencia.                         # Log 429.
        return Response(content=body, media_type="application/json",
                        headers=headers,
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS)      # Devuelve 429.                          # Respuesta 429.

    if any(token in key for token in ("bad", "400", "invalid")):  # Si contiene tokens de payload inválido...         # Regla 400.
        body = '{"detail":"Payload inválido (mock)"}'            # Cuerpo 400.                                       # Cuerpo 400.
        logger.warning("[MOCK] → 400 Bad Request")               # Log advertencia.                                  # Log 400.
        return Response(content=body, media_type="application/json",
                        status_code=status.HTTP_400_BAD_REQUEST) # Devuelve 400.                                     # Respuesta 400.

    body = '{"detail":"Mock server internal error"}'             # Cuerpo genérico para forzar ruta de error.        # Cuerpo 500.
    logger.error("[MOCK] → 500 Internal Server Error")           # Log error.                                        # Log 500.
    return Response(content=body, media_type="application/json",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)       # Devuelve 500.                          # Respuesta 500.

if __name__ == "__main__":                    # Ejecuta solo si se llama este archivo directamente.                    # Guard main.
    # Arranca uvicorn con el objeto 'app' directamente (no depende del nombre de paquete/ruta).                       # Nota ejecución.
    uvicorn.run(app, host="127.0.0.1", port=9000, reload=False, log_level="info")  # Servidor en localhost:9000.     # Run uvicorn.
