# app/routers/admin.py
# =============================================================================
# 👑 Rutas de administración: Importación en lote de invitados (upsert)
# - Protegido con API Key mediante dependencia `require_admin`
# - Recibe un payload con invitados validados (ImportGuestsPayload)
# - Realiza upsert por email/phone (si existen)
# - Devuelve resumen: created / updated / skipped / errors
# =============================================================================

from fastapi import APIRouter, Depends                           # Importa router y dependencias de FastAPI.
from sqlalchemy.orm import Session                                # Importa el tipo de sesión de SQLAlchemy.
from typing import List, Optional                                  # Tipos para anotaciones.
import re                                                          # Regex para normalizar teléfonos.

import app.schemas as schemas                                      # 🔁 Import robusto del módulo completo de schemas.
from app.core.security import require_admin                        # Dep. que valida x-api-key == ADMIN_API_KEY.
from app.db import get_db                                          # Proveedor de Session por request.

from app.models import Guest                                       # ORM del invitado.
from app.crud import guests_crud                                   # CRUD con helpers get_by_email/phone/create/commit.

router = APIRouter(prefix="/api/admin", tags=["admin"])            # Define el router con prefijo /api/admin.

# ------------------------------ Helpers locales -------------------------------

def _normalize_email(email: Optional[str]) -> Optional[str]:
    """Devuelve el email en minúsculas y sin espacios, o None si queda vacío."""
    if not email:
        return None
    e = email.strip().lower()
    return e or None

def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Deja solo dígitos y '+' en el teléfono, o None si queda vacío."""
    if not phone:
        return None
    digits = re.sub(r"[^\d+]", "", phone.strip())
    return digits or None

# --------------------------------- Endpoint -----------------------------------

@router.post(
    "/import-guests",                                              # Ruta del endpoint.
    response_model=schemas.ImportGuestsResult,                     # 🔁 Respuesta tipada del módulo schemas.
    dependencies=[Depends(require_admin)],                         # Protege con API Key de admin.
)
def import_guests(payload: schemas.ImportGuestsPayload,            # 🔁 Request tipado del módulo schemas.
                  db: Session = Depends(get_db)):                  # Inyección de sesión de BD.
    """
    Importación en lote con upsert por email/phone (si existen).
    - Para cada ítem:
        1) Busca invitado existente por email (normalizado) o phone (normalizado).
        2) Si existe → actualiza campos principales (sin sobreescribir opcionales con None).
        3) Si no existe → crea nuevo Guest.
    - Nunca aborta el lote por un error de fila: acumula en `errors`.
    """
    created = 0                                                    # Contador de creados.
    updated = 0                                                    # Contador de actualizados.
    skipped = 0                                                    # Contador de filas saltadas por error.
    errors: List[str] = []                                         # Lista de errores por fila.

    for idx, item in enumerate(payload.items, start=1):            # Itera sobre cada invitado del payload.
        try:
            norm_email = _normalize_email(item.email)              # Normaliza email.
            norm_phone = _normalize_phone(item.phone)              # Normaliza teléfono.

            existing: Optional[Guest] = None                       # Inicializa variable de existente.
            if norm_email:                                         # Si hay email normalizado...
                existing = guests_crud.get_by_email(db, norm_email)# ...busca por email.
            if not existing and norm_phone:                        # Si no encontró y hay teléfono...
                existing = guests_crud.get_by_phone(db, norm_phone)# ...busca por teléfono.

            if existing:                                           # Si existe registro...
                existing.full_name = item.full_name                # Actualiza nombre.
                existing.language = item.language                  # Actualiza idioma.
                existing.max_accomp = item.max_accomp              # Actualiza máximo acompañantes.
                existing.invite_type = item.invite_type            # Actualiza tipo de invitación.
                if item.side is not None:                          # Actualiza side si vino.
                    existing.side = item.side
                if item.relationship is not None:                  # Actualiza relación si vino.
                    existing.relationship = item.relationship
                if item.group_id is not None:                      # Actualiza group_id si vino.
                    existing.group_id = item.group_id
                if norm_email:                                     # Actualiza email si vino.
                    existing.email = norm_email
                if norm_phone:                                     # Actualiza teléfono si vino.
                    existing.phone = norm_phone

                try:
                    guests_crud.commit(db, existing)               # Usa tu helper commit si existe.
                except AttributeError:
                    db.add(existing)                               # Fallback: añade a la sesión.
                    db.commit()                                    # Confirma cambios.
                    db.refresh(existing)                           # Refresca desde DB.

                updated += 1                                       # Incrementa contador de updates.

            else:                                                  # Si no existe, crea nuevo registro...
                _ = guests_crud.create(                            # Usa tu helper create para persistir.
                    db,
                    full_name=item.full_name,
                    email=norm_email,
                    phone=norm_phone,
                    language=item.language,
                    max_accomp=item.max_accomp,
                    invite_type=item.invite_type,
                    side=item.side,
                    relationship=item.relationship,
                    group_id=item.group_id,
                )
                try:
                    db.flush()                                     # Asegura INSERT antes de contar (opcional).
                except Exception:
                    pass
                created += 1                                       # Incrementa contador de creaciones.

        except Exception as e:                                     # Si algo falla en esta fila...
            skipped += 1                                           # Cuenta como saltada.
            errors.append(f"Row {idx}: {e}")                       # Guarda el error legible.

    return schemas.ImportGuestsResult(                             # Devuelve resumen del lote.
        created=created, updated=updated, skipped=skipped, errors=errors
    )
