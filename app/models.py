# app/models.py  # Define la ruta y nombre del archivo del módulo de modelos.

# =================================================================================
# 🏛️ DEFINICIÓN DE LOS MODELOS DE LA BASE DE DATOS (ORM)
# ---------------------------------------------------------------------------------
# Este archivo define la estructura de las tablas de nuestra base de datos
# utilizando SQLAlchemy ORM.
# Implementa:
# - Enums para consistencia (idioma, lado, tipo de invitación, estado de tareas).
# - Restricción CHECK para exigir email o teléfono (al menos uno obligatorio).
# - email/phone únicos si existen (nullable=True permite flexibilidad).
# - Tabla Companion para modelar acompañantes por grupo familiar.
# =================================================================================

# 🐍 Importaciones de Python y SQLAlchemy
# ---------------------------------------------------------------------------------
from datetime import datetime  # Importa datetime para sellos de tiempo.
import enum  # Importa enum para crear enumeraciones tipadas.

from sqlalchemy import (  # Importa utilidades de SQLAlchemy para definir tablas y columnas.
    Column,  # Clase para declarar columnas.
    Integer,  # Tipo entero para IDs y contadores.
    String,  # Tipo texto para nombres y códigos.
    Boolean,  # Tipo booleano para flags.
    DateTime,  # Tipo fecha/hora para auditoría y confirmaciones.
    ForeignKey,  # Clave foránea para relaciones entre tablas.
    func,  # Funciones SQL (ej. now()).
    Enum as SQLAlchemyEnum,  # Enum de SQLAlchemy para mapear enumeraciones.
    CheckConstraint,  # Restricción CHECK a nivel de tabla.
    Index, # ✅ AJUSTE B (Opcional): Importado para el índice compuesto.
)
from sqlalchemy.orm import relationship as orm_relationship  # Importa relationship para relaciones ORM.

from app.db import Base  # Importa la clase Base declarativa del proyecto (metadatos ORM).

# 🗂️ ENUMS PARA CONSISTENCIA DE DATOS
# ---------------------------------------------------------------------------------
class LanguageEnum(str, enum.Enum):  # Enum para idioma preferido del invitado.
    es = "es"  # Español.
    ro = "ro"  # Rumano.
    en = "en"  # Inglés.

class SideEnum(str, enum.Enum):  # Enum para lado/familia (opcional para métricas).
    bride = "bride"  # Lado de la novia.
    groom = "groom"  # Lado del novio.

class InviteTypeEnum(str, enum.Enum):  # Enum para tipo de invitación (segmentación clave).
    ceremony = "ceremony"          # Invitado solo a ceremonia.
    full = "full"                  # ✅ Alineado con schemas/frontend (antes: "ceremony+reception")

class TaskStatusEnum(str, enum.Enum):  # Enum para estado de tareas del planner (dashboard).
    pending = "pending"  # Tarea pendiente.
    in_progress = "in_progress"  # Tarea en progreso.
    completed = "completed"  # Tarea completada.

# 🤵👰 MODELO DE INVITADOS PRINCIPALES (TABLA 'guests')
# ---------------------------------------------------------------------------------
class Guest(Base):  # Define el modelo ORM de invitados principales (grupo familiar).
    __tablename__ = "guests"  # Nombre de la tabla en la base de datos.

    # =================================================================================
    # ✅ AJUSTE B (Opcional): Restricciones de tabla con índice compuesto.
    # ---------------------------------------------------------------------------------
    __table_args__ = (
        CheckConstraint(
            "(email IS NOT NULL) OR (phone IS NOT NULL)",  # Mantiene el CHECK existente (email OR phone).
            name="ck_guests_email_or_phone_required",
        ),
        # (Descomenta la siguiente línea si quieres activar el índice compuesto para mejorar el rendimiento de los filtros del dashboard)
        # Index('ix_guests_confirmed_invite', 'confirmed', 'invite_type'),
    )
    # =================================================================================

    # --- Columnas Principales ---
    id = Column(Integer, primary_key=True, index=True)
    # ✅ AJUSTE B (Opcional): Longitudes de String acotadas.
    guest_code = Column(String(64), unique=True, index=True, nullable=False)
    full_name = Column(String(120), index=True, nullable=False)

    # --- Columnas de Contacto (Flexibles + Únicas) ---
    # ✅ AJUSTE B (Opcional): Longitudes de String acotadas.
    email = Column(String(254), unique=True, index=True, nullable=True)
    phone = Column(String(32), unique=True, index=True, nullable=True)

    # --- Segmentación y Metadatos ---
    is_primary = Column(Boolean, default=False)
    group_id = Column(String, index=True, nullable=True)
    side = Column(SQLAlchemyEnum(SideEnum), nullable=True)
    relationship = Column(String(120), nullable=True) # ✅ AJUSTE B (Opcional): Longitud añadida.
    
    # ✅ AJUSTE A: Default de idioma alineado a 'en' para coherencia con el sistema.
    language = Column(SQLAlchemyEnum(LanguageEnum), default=LanguageEnum.en, nullable=False)

    # --- Segmento de Invitación y Cupos ---
    invite_type = Column(SQLAlchemyEnum(InviteTypeEnum), nullable=False, default=InviteTypeEnum.full)
    max_accomp = Column(Integer, default=0, nullable=False)

    # --- Estado de RSVP y Resumen por Grupo ---
    confirmed = Column(Boolean, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    num_adults = Column(Integer, default=0, nullable=False)
    num_children = Column(Integer, default=0, nullable=False)

    # --- Preferencias del Titular (si hay recepción) ---
    menu_choice = Column(String, nullable=True)
    allergies = Column(String, nullable=True)
    notes = Column(String(500), nullable=True)  # Comentarios/observaciones del RSVP (opcional).
    needs_accommodation = Column(Boolean, default=False, nullable=False)
    needs_transport = Column(Boolean, default=False, nullable=False)

    # --- Auditoría y Recordatorios ---
    last_reminder_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Columnas para el flujo de Magic Link ---
    # ✅ AJUSTE B (Opcional): Longitud de String acotada.
    magic_link_token = Column(String(512), nullable=True, index=True)
    magic_link_sent_at = Column(DateTime, nullable=True)
    magic_link_expires_at = Column(DateTime, nullable=True)
    magic_link_used_at = Column(DateTime, nullable=True)

    # --- Relación con Acompañantes ---
    companions = orm_relationship(
        "Companion",
        cascade="all, delete-orphan",
        back_populates="guest",
        lazy="selectin",
    )

# 👥 MODELO DE ACOMPAÑANTES (TABLA 'companions')
# ---------------------------------------------------------------------------------
class Companion(Base):
    __tablename__ = "companions"

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    is_child = Column(Boolean, default=False, nullable=False)
    menu_choice = Column(String, nullable=True)
    allergies = Column(String, nullable=True)

    guest = orm_relationship(
        "Guest",
        back_populates="companions",
    )

# 📝 MODELO DE TAREAS (TABLA 'tasks')
# ---------------------------------------------------------------------------------
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    assigned_to = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(TaskStatusEnum), default=TaskStatusEnum.pending, nullable=False)
    is_subtask = Column(Boolean, default=False, nullable=False)
    parent_task_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)