# app/db.py

# =================================================================================
# 🗄️ CONFIGURACIÓN Y CONEXIÓN A LA BASE DE DATOS
# ---------------------------------------------------------------------------------
# Este módulo centraliza la configuración de la conexión a la base de datos
# utilizando SQLAlchemy.
#
# Se implementa una lógica para asegurar que todas las partes de la aplicación
# (FastAPI, Streamlit, scripts) apunten a un único archivo de base de datos
# utilizando una ruta absoluta, evitando la creación de bases de datos duplicadas.
# =================================================================================


# 🐍 Importaciones de Módulos
# ---------------------------------------------------------------------------------
# `os`: Para interactuar con el sistema operativo, específicamente para construir
#      rutas de archivos de manera robusta.
import os
# `create_engine`: La función de SQLAlchemy para establecer la conexión con la BD.
from sqlalchemy import create_engine
# `sessionmaker`: Para crear "fábricas" de sesiones que gestionan las conversaciones
#                 con la base de datos.
# `declarative_base`: Para crear la clase Base de la que heredarán todos nuestros
#                     modelos ORM.
from sqlalchemy.orm import sessionmaker, declarative_base


# 📍 LÓGICA DE RUTA ABSOLUTA PARA LA BASE DE DATOS
# ---------------------------------------------------------------------------------
# Esta sección garantiza que siempre se use el mismo archivo `wedding.db`.

# Se intenta leer la URL de la base de datos desde una variable de entorno.
# Esto da flexibilidad para configurar una base de datos diferente (como PostgreSQL) en producción.
DATABASE_URL_ENV = os.getenv("DATABASE_URL")

# Si se encuentra una URL en las variables de entorno, se utiliza esa.
if DATABASE_URL_ENV:
    DATABASE_URL = DATABASE_URL_ENV
else:
    # Si no se encuentra, se construye una ruta absoluta al archivo `wedding.db`
    # que debe estar en la carpeta raíz del proyecto.
    
    # 1. Se obtiene la ruta del directorio donde se encuentra este archivo (`app/`).
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 2. Se sube un nivel para llegar a la raíz del proyecto (`backend_starter/`).
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    # 3. Se construye la ruta completa al archivo de la base de datos.
    db_path = os.path.join(project_root, "wedding.db")
    # 4. Se formatea la ruta en el formato de URL de conexión que SQLAlchemy espera para SQLite.
    #    `sqlite:///` indica una ruta de archivo absoluta.
    DATABASE_URL = f"sqlite:///{db_path}"


# 🏭 CREACIÓN DEL MOTOR Y LA FÁBRICA DE SESIONES
# ---------------------------------------------------------------------------------

# Se crea el "motor" de SQLAlchemy, que es el punto de entrada a la base de datos.
# `connect_args={"check_same_thread": False}`: Es una configuración específica para
# SQLite que permite que sea utilizado por múltiples hilos, algo necesario para FastAPI.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Se crea una "fábrica" de sesiones (`SessionLocal`). Cada vez que necesitemos hablar
# con la base de datos, pediremos una nueva sesión a esta fábrica.
# `autocommit=False`, `autoflush=False`: Asegura que tengamos control manual sobre
# cuándo se guardan los cambios.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Se crea la clase `Base`. Todos nuestros modelos (como `Guest` y `Task`)
# heredarán de esta clase, permitiendo que SQLAlchemy los descubra y los mapee
# a tablas en la base de datos.
Base = declarative_base()



def get_db():                              # Define una dependencia para inyectar sesiones de BD por petición.
    db = SessionLocal()                    # Crea una nueva sesión ligada al engine configurado.
    try:                                   # Abre un bloque try para garantizar cierre correcto.
        yield db                           # Entrega la sesión al endpoint que la consuma.
    finally:                               # Al finalizar la petición...
        db.close()                         # Cierra la sesión para liberar conexiones/recursos.
