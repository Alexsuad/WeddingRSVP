# app/routers/admin.py
# =============================================================================
# 👑 Rutas de administración: Importación en lote de invitados (upsert)
# - Protegido con API Key mediante dependencia `require_admin`
# - Recibe un payload con invitados validados (ImportGuestsPayload)
# - Realiza upsert por email/phone (si existen)
# - Devuelve resumen: created / updated / skipped / errors
# =============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import re

# ⬇️ OJO: estos schemas están en app/schemas.py (no en un submódulo)
from app.schemas import ImportGuestsPayload, ImportGuestsResult
from app.core.security import require_admin       # Dep. que valida x-api-key == ADMIN_API_KEY
from app.db import get_db                         # Session por request

# Modelos/CRUD del dominio (ajusta import caminos si difieren en tu proyecto)
from app.models import Guest                      # ORM de invitado
from app.crud import guests_crud                  # CRUD con helpers get_by_email/phone/create/commit


# ⚠️ IMPORTANTE:
# - Este router ya tiene prefix="/api/admin".
# - En app/main.py, al incluirlo, NO vuelvas a poner el mismo prefix o te quedará duplicado:
#       app.include_router(admin.router)   # ✅
#       app.include_router(admin.router, prefix="/api/admin")  # ❌ NO repetir


router = APIRouter(prefix="/api/admin", tags=["admin"])


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
    "/import-guests",
    response_model=ImportGuestsResult,
    dependencies=[Depends(require_admin)],   # protege con API Key de admin
)
def import_guests(payload: ImportGuestsPayload, db: Session = Depends(get_db)):
    """
    Importación en lote con upsert por email/phone (si existen).
    - Para cada ítem:
        1) Busca invitado existente por email (normalizado) o phone (normalizado).
        2) Si existe → actualiza campos principales (sin sobreescribir opcionales con None).
        3) Si no existe → crea nuevo Guest.
    - Nunca aborta el lote por un error de fila: acumula en `errors`.
    """
    created = 0
    updated = 0
    skipped = 0
    errors: List[str] = []

    for idx, item in enumerate(payload.items, start=1):
        try:
            # Normaliza email/phone (aunque Pydantic ya validó formatos, aquí igualamos criterios de búsqueda)
            norm_email = _normalize_email(item.email)
            norm_phone = _normalize_phone(item.phone)

            # 1) Buscar existente por email, luego por phone (si no se encontró por email)
            existing: Optional[Guest] = None
            if norm_email:
                existing = guests_crud.get_by_email(db, norm_email)
            if not existing and norm_phone:
                existing = guests_crud.get_by_phone(db, norm_phone)

            if existing:
                # 2) UPDATE (upsert): actualiza campos principales SIEMPRE;
                #    opcionales solo si vienen no-None, para no pisar datos con None involuntario.
                existing.full_name = item.full_name
                existing.language = item.language
                existing.max_accomp = item.max_accomp
                existing.invite_type = item.invite_type

                if item.side is not None:
                    existing.side = item.side
                if item.relationship is not None:
                    existing.relationship = item.relationship
                if item.group_id is not None:
                    existing.group_id = item.group_id

                # Email/phone: solo actualiza si vienen (y normalizados)
                if norm_email:
                    existing.email = norm_email
                if norm_phone:
                    existing.phone = norm_phone

                # Commit usando tu CRUD; si tu CRUD no tiene commit(obj), usamos fallback
                try:
                    guests_crud.commit(db, existing)   # tu helper (si existe)
                except AttributeError:
                    db.add(existing)
                    db.commit()
                    db.refresh(existing)

                updated += 1

            else:
                # 3) CREATE (upsert)
                # Si tu `guests_crud.create` espera un diccionario o un schema, ajusta aquí.
                obj = guests_crud.create(
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
                # Si tu CRUD no hace commit interno, asegura persistencia:
                try:
                    db.flush()   # opcional: asegura INSERT antes de contar
                except Exception:
                    pass

                created += 1

        except Exception as e:
            # Nunca abortamos el lote: registramos el error y continuamos
            skipped += 1
            errors.append(f"Row {idx}: {e}")

    # No hacemos db.commit() final a propósito: asumimos que CRUD maneja commit por fila
    # (si quieres un commit por lote, podríamos envolver el for en un bloque de transacción).
    return ImportGuestsResult(created=created, updated=updated, skipped=skipped, errors=errors)
