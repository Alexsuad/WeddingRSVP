# create_db.py

# =================================================================================
# 🏗️ SCRIPT DE CREACIÓN DE LA BASE DE DATOS
# ---------------------------------------------------------------------------------
# Este script inicializa la base de datos y crea todas las tablas definidas
# en los modelos de la aplicación. Debe ejecutarse una sola vez al configurar
# el proyecto o después de realizar cambios en los modelos.
# =================================================================================

# Se importa el motor de la base de datos y la clase Base declarativa.
from app.db import engine, Base

# --- CORRECCIÓN CRÍTICA ---
# Se importan todos los modelos de `app/models.py`.
# Esta línea es esencial. Al importar los modelos, estos se "registran" en los
# metadatos del objeto `Base`. Sin esta importación, `Base` no sabría
# qué tablas tiene que crear.
from app import models


def create_database_tables():
    """
    Crea todas las tablas en la base de datos que están asociadas con `Base`.
    """
    print("Creando tablas en la base de datos...")
    # `Base.metadata.create_all` ahora tiene la información de las tablas `Guest` y `Task`.
    Base.metadata.create_all(bind=engine)
    print("✔️ Base de datos y tablas creadas correctamente.")


if __name__ == "__main__":
    create_database_tables()