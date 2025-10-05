# app/db.py
# =================================================================================
# 🗄️ CONFIGURACIÓN Y CONEXIÓN A LA BASE DE DATOS
# ---------------------------------------------------------------------------------
# Este módulo centraliza la configuración de la conexión a la base de datos
# utilizando SQLAlchemy, con lógica condicional para soportar tanto
# SQLite (desarrollo) como PostgreSQL (producción).
# =================================================================================

# --- Importaciones de Módulos ---
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from loguru import logger

# --- Lógica de URL de la Base de Datos ---
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

if DATABASE_URL_ENV:
    # Si la variable de entorno está definida (ej. en Railway), se usa directamente.
    DATABASE_URL = DATABASE_URL_ENV
else:
    # Si no, se construye una ruta absoluta al archivo wedding.db en la raíz del proyecto.
    # (Esta lógica es más robusta para ejecuciones locales).
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    db_path = os.path.join(project_root, "wedding.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# --- Creación del Engine con Lógica Condicional y Resiliencia ---
engine = None

if DATABASE_URL.startswith("sqlite"):
    # Para SQLite: se necesita `check_same_thread` y se añade `pool_pre_ping`.
    logger.info("DB in use → SQLite")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    # Para PostgreSQL (y otros): NO se usa `check_same_thread` y se añade `pool_pre_ping`.
    logger.info("DB in use → PostgreSQL (o no-SQLite)")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

# --- Fábrica de Sesiones y Base Declarativa ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependencia de FastAPI para inyectar una sesión de BD por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================================================================================
# 🔎 UTILIDAD: LOGUEAR LA RUTA REAL DE LA BASE DE DATOS EN STARTUP
# =================================================================================
def log_db_path_on_startup() -> None:
    """Escribe en los logs qué motor de base de datos se está utilizando al arrancar."""
    try:
        url = engine.url
        logger.info("DB driver in use → {}", url.drivername)
        if url.drivername == "sqlite":
            db_file = getattr(url, "database", None)
            abs_path = os.path.abspath(db_file) if db_file else "<memory>"
            logger.info("DB path → {} (abs={})", db_file, abs_path)
    except Exception as e:
        logger.warning("No se pudo resolver la información de la BD: {}", e)