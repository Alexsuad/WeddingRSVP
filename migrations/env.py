#migrations/env.py
from logging.config import fileConfig
import os
import sys

from alembic import context

# ---- Asegurar que podamos importar el paquete "app" ----
# (asume que "migrations" está en la raíz del proyecto junto a "app/")
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importa tu engine y Base desde el proyecto
from app.db import engine, Base  # <-- requiere que app/db.py exporte 'engine' y 'Base'

# Alembic Config (lee alembic.ini para logging, etc.)
config = context.config

# Logging de Alembic (opcional)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de tus modelos para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Modo 'offline': configura el contexto con una URL (tomada del engine real).
    No crea Engine/DBAPI; emite SQL al output.
    """
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,      # detecta cambios de tipos
        compare_server_default=True,  # detecta defaults en servidor
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo 'online': usa directamente tu Engine real y ejecuta contra la BD.
    """
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
