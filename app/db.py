# app/db.py                                                                                   # Indica la ruta y nombre del archivo (informativo para el lector).

# =================================================================================            # Separador visual de sección.
# 🗄️ CONFIGURACIÓN Y CONEXIÓN A LA BASE DE DATOS                                              # Título explicativo de la sección.
# ---------------------------------------------------------------------------------            # Línea de separación.
# Este módulo centraliza la configuración de la conexión a la base de datos                    # Explica el propósito del módulo.
# utilizando SQLAlchemy.                                                                       # Continúa la explicación.
#                                                                                              # Línea en blanco intencional.
# Se implementa una lógica para asegurar que todas las partes de la aplicación                 # Describe la lógica de ruta absoluta.
# (FastAPI, Streamlit, scripts) apunten a un único archivo de base de datos                    # Aclara qué componentes se benefician.
# utilizando una ruta absoluta, evitando la creación de bases de datos duplicadas.             # Beneficio de la ruta absoluta.
# =================================================================================            # Fin del encabezado.

# 🐍 Importaciones de Módulos                                                                  # Título de sección de imports.
# ---------------------------------------------------------------------------------            # Separador de sección.
import os                                                                                      # `os`: para leer variables de entorno y construir rutas absolutas.
from sqlalchemy import create_engine                                                           # `create_engine`: crea el motor de conexión a la BD.
from sqlalchemy.orm import sessionmaker, declarative_base                                      # `sessionmaker`: fabrica sesiones; `declarative_base`: base ORM.
from loguru import logger                                                                      # ✅ Importa logger para escribir trazas (añadido para loguear la BD).

# 📍 LÓGICA DE RUTA ABSOLUTA PARA LA BASE DE DATOS                                             # Título de sección de configuración de URL.
# ---------------------------------------------------------------------------------            # Separador de sección.
DATABASE_URL_ENV = os.getenv("DATABASE_URL")                                                   # Lee la URL de BD desde variables de entorno (si existe).

if DATABASE_URL_ENV:                                                                           # Si la variable de entorno está definida...
    DATABASE_URL = DATABASE_URL_ENV                                                            # ...úsala directamente como cadena de conexión.
else:                                                                                          # De lo contrario (no hay env)...
    current_dir = os.path.dirname(os.path.abspath(__file__))                                   # 1) Obtiene la ruta absoluta del directorio de este archivo.
    project_root = os.path.abspath(os.path.join(current_dir, ".."))                            # 2) Sube un nivel para llegar a la raíz del proyecto.
    db_path = os.path.join(project_root, "wedding.db")                                         # 3) Construye la ruta absoluta del archivo SQLite `wedding.db`.
    DATABASE_URL = f"sqlite:///{db_path}"                                                      # 4) Formatea la URL SQLAlchemy para ruta absoluta en SQLite.

# 🏭 CREACIÓN DEL MOTOR Y LA FÁBRICA DE SESIONES                                               # Título de sección de engine y sesión.
# ---------------------------------------------------------------------------------            # Separador de sección.
engine = create_engine(                                                                        # Crea el motor de SQLAlchemy contra la URL resuelta.
    DATABASE_URL,                                                                              # Pasa la URL de la base de datos (absoluta o de entorno).
    connect_args={"check_same_thread": False}                                                  # Para SQLite: permite acceso multi-hilo (requerido por FastAPI).
)                                                                                              # Cierra la creación del engine.

SessionLocal = sessionmaker(                                                                   # Crea la fábrica de sesiones asociada al engine.
    autocommit=False,                                                                          # Desactiva autocommit: control manual de commits.
    autoflush=False,                                                                           # Desactiva autoflush: evita flush implícitos inesperados.
    bind=engine                                                                                # Asocia la sesión al engine configurado.
)                                                                                              # Cierra la creación de la fábrica de sesiones.

Base = declarative_base()                                                                       # Crea la clase base del ORM para modelos (mapear tablas).

def get_db():                                                                                  # Define una dependencia para inyectar sesiones por petición.
    db = SessionLocal()                                                                         # Crea una nueva sesión ligada al engine.
    try:                                                                                        # Bloque try/finally para asegurar el cierre de la sesión.
        yield db                                                                                # Entrega la sesión al código que la consuma (endpoint/servicio).
    finally:                                                                                    # Al finalizar el uso de la sesión...
        db.close()                                                                              # ...cierra la sesión liberando recursos/conexiones.

# =================================================================================            # Separador de nueva sección añadida.
# 🔎 UTILIDAD: LOGUEAR LA RUTA REAL DE LA BASE DE DATOS EN STARTUP                             # Título claro de la utilidad de diagnóstico.
# ---------------------------------------------------------------------------------            # Separador de sección.
def log_db_path_on_startup() -> None:                                                          # Define una función que imprime la BD en uso al arrancar.
    try:                                                                                       # Protege el log para no impedir el arranque por errores.
        url = engine.url                                                                        # Obtiene el objeto URL del engine (describe la conexión actual).
        db_file = getattr(url, "database", None)                                                # Extrae la ruta del archivo físico (solo aplica a SQLite).
        abs_path = os.path.abspath(db_file) if db_file else "<memory/other>"                    # Resuelve a ruta absoluta (o marca si no hay archivo).
        logger.info("DB in use → {} (abs={})", db_file, abs_path)                               # Escribe en logs la ruta cruda y la absoluta (diagnóstico).
    except Exception as e:                                                                      # Si ocurre cualquier excepción durante el proceso...
        logger.warning("No pude resolver la ruta de la BD: {}", e)                              # ...lo reporta como warning sin romper el servicio.
