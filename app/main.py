# app/main.py  # Ruta y nombre del archivo principal de la API.

# =================================================================================
# 🧠 NÚCLEO DE LA APLICACIÓN API (FastAPI)
# ---------------------------------------------------------------------------------
# - Crea la instancia de FastAPI
# - Configura CORS
# - Inicializa la BD y crea tablas
# - Registra routers modulares (auth, guest, meta, admin)
# =================================================================================

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


# ✅ AJUSTE: Carga explícita y log de verificación al arranque
from pathlib import Path
from loguru import logger

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

logger.info(
    "[BOOT] DRY_RUN={} | EMAIL_FROM={} | SG_KEY_SET={}",
    os.getenv("DRY_RUN"),
    os.getenv("EMAIL_FROM"),
    "yes" if os.getenv("SENDGRID_API_KEY") else "no"
)

# 2) Importaciones internas del proyecto (ya con .env cargado)
from app.db import engine
from app import models
from app.routers import auth_routes, guest, admin         # Importa solo routers reales.
from app import meta                                      # Importa meta desde app/meta.py (ubicación real)

# 3) Instancia FastAPI
app = FastAPI(
    title="API para la Boda de Daniela & Cristian",
    description="Backend para gestionar RSVP, login y lógica de invitados",
    version="6.0.0",
)

# 4) Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://suarezsiicawedding.com",       # WordPress (producción)
        "https://rsvp.suarezsiicawedding.com",  # Streamlit (producción)
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5) Creación de tablas (migración mínima)
models.Base.metadata.create_all(bind=engine)

# 6) Registro de routers (montaje de endpoints)
#    ⚠️ Importante: NO repetir prefijos aquí si los routers ya los tienen definidos.
#       - auth_routes: expone /api/login, /api/recover-code (prefijo en el propio router)
#       - guest:       expone /api/guest/...
#       - meta:        expone /api/meta/...
#       - admin:       expone /api/admin/... (protegido por require_admin)
app.include_router(auth_routes.router)
app.include_router(guest.router)
app.include_router(meta.router)
app.include_router(admin.router)  # ✅ ahora sí, con la app creada y junto al resto

# (Opcional) punto de salud simple:
# from fastapi import status
# @app.get("/health", status_code=status.HTTP_204_NO_CONTENT)
# def health(): return None
