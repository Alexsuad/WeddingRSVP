# app/main.py                                                                                   # Ruta y nombre del archivo principal de la API.

# ================================================================
# 🧱 MODO MANTENIMIENTO (Control temporal desde variable de entorno)
# ================================================================

import os

# Si la variable MAINTENANCE_MODE=1 está activa, se crea una app mínima
if os.getenv("MAINTENANCE_MODE") == "1":
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from loguru import logger

    app = FastAPI(title="API en mantenimiento")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    async def maintenance_page(path: str):
        """Responde a cualquier ruta y método con mensaje neutro de mantenimiento."""
        return JSONResponse(
            status_code=503,
            content={
                "status": "offline",
                "message": "🌙 El sistema está en mantenimiento. Vuelve más tarde."
            }
        )

    # Importante: detener el resto del archivo para no cargar endpoints reales
    logger.warning("🚧 API arrancada en MODO MANTENIMIENTO. Todos los endpoints reales están desactivados.")
    # El raise SystemExit no es la forma más limpia de detener la ejecución en un contexto de servidor.
    # En su lugar, el código se estructura para que el resto del archivo no se ejecute.
else:
    # =================================================================================             # Separador visual de sección.
    # 🧠 NÚCLEO DE LA APLICACIÓN API (FastAPI)                                                      # Título de la sección principal.
    # ---------------------------------------------------------------------------------             # Separador de sección.
    # - Crea la instancia de FastAPI                                                                # Lista responsabilidades del módulo.
    # - Configura CORS                                                                              # Continua la lista.
    # - Registra routers modulares (auth, guest, meta, admin)                                      # Continua la lista.
    # =================================================================================             # Fin del encabezado.

    from fastapi import FastAPI                                                                     # Importa FastAPI para crear la aplicación.
    from fastapi.middleware.cors import CORSMiddleware                                              # Importa middleware CORS para orígenes permitidos.
    from dotenv import load_dotenv                                                                  # Importa load_dotenv para cargar variables desde .env.

    from pathlib import Path                                                                        # Importa Path para manipular rutas de archivos.
    from loguru import logger                                                                       # Importa logger para escribir trazas al arrancar.

    env_path = Path('.') / '.env'                                                                   # Construye la ruta al archivo .env en el directorio actual.
    load_dotenv(dotenv_path=env_path)                                                               # Carga las variables de entorno desde el archivo .env.

    logger.info(                                                                                    # Log informativo de variables clave para verificar configuración.
        "[BOOT] DRY_RUN={} | EMAIL_FROM={} | SG_KEY_SET={}",                                        # Plantilla del mensaje con placeholders.
        os.getenv("DRY_RUN"),                                                                        # Valor de DRY_RUN del entorno (simulación de envíos).
        os.getenv("EMAIL_FROM"),                                                                     # Remitente configurado para correos.
        "yes" if os.getenv("SENDGRID_API_KEY") else "no"                                             # Indica si hay API key de SendGrid cargada.
    )                                                                                                # Cierra la llamada de log.

    from app.db import engine                                                                       # Importa el engine para inicializar tablas.
    from app import models                                                                          # Importa modelos ORM (definen las tablas).
    from app.routers import auth_routes, guest, admin                                               # Importa routers reales de la aplicación.
    from app import meta                                                                            # Importa el router/meta de información general.
    from app.db import log_db_path_on_startup                                                       # ✅ Importa la utilidad para loguear la ruta real de la BD.

    app = FastAPI(                                                                                  # Crea la instancia de la aplicación FastAPI.
        title="API para la Boda de Jenny & Cristian",                                             # Título de la API (documentación OpenAPI).
        description="Backend para gestionar RSVP, login y lógica de invitados",                     # Descripción corta de la API.
        version="6.0.0",                                                                            # Versión de la API (para control de cambios).
    )                                                                                                # Cierra la creación de la app.

    app.add_middleware(                                                                             # Registra el middleware de CORS en la app.
        CORSMiddleware,                                                                              # Especifica el tipo de middleware (CORS).
        allow_origins=[                                                                              # Lista de orígenes permitidos (frontends conocidos).
            "https://suarezsiicawedding.com",                                                        # WordPress (producción).
            "https://rsvp.suarezsiicawedding.com",                                                   # Streamlit (producción).
            "http://localhost:3000",                                                                 # Front local (dev).
            "http://127.0.0.1:3000",                                                                 # Front local por IP loopback.
            "http://localhost:8501",                                                                 # Streamlit local (dev).
            "http://127.0.0.1:8501",                                                                 # Streamlit local por IP loopback.
        ],                                                                                           # Cierra la lista de orígenes permitidos.
        allow_credentials=True,                                                                      # Permite el envío de credenciales (cookies/autenticación).
        allow_methods=["*"],                                                                         # Permite todos los métodos HTTP (GET/POST/etc.).
        allow_headers=["*"],                                                                         # Permite todos los headers (autenticación personalizados, etc.).
    )                                                                                                # Cierra la configuración del middleware CORS.

    # #############################################################################################
    # ### INICIO DE LA CORRECCIÓN: Eliminar `create_all`                                        ###
    # #############################################################################################
    # Esta línea se elimina porque la gestión del esquema de la BD en producción debe ser
    # manejada exclusivamente por Alembic, que ya se ejecuta en el `Procfile`.
    # models.Base.metadata.create_all(bind=engine)
    # #############################################################################################
    # ### FIN DE LA CORRECCIÓN                                                                  ###
    # #############################################################################################

    @app.on_event("startup")                                                                         # Registra un hook que se ejecuta cuando la app arranca.
    def _startup_db_trace() -> None:                                                                 # Define la función a ejecutar en el evento de startup.
        log_db_path_on_startup()                                                                     # ✅ Llama a la utilidad que imprime la ruta real de la BD.

    app.include_router(auth_routes.router)                                                           # Monta el router de autenticación bajo sus propios prefijos.
    app.include_router(guest.router)                                                                 # Monta el router de invitados (gestión de guest).
    app.include_router(meta.router)                                                                  # Monta el router meta (información de la API).
    app.include_router(admin.router)                                                                 # Monta el router admin (endpoints protegidos por API key).