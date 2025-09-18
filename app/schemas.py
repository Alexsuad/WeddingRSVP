# app/schemas.py  # Ruta y nombre del archivo de esquemas (Pydantic).

# =================================================================================
# 📦 Schemas (MODELOS DE DATOS Pydantic)
# ---------------------------------------------------------------------------------
# Este archivo define los modelos de datos usados por la API, basados en Pydantic.
# - Validan la entrada y salida de datos (tipos, reglas de negocio).
# - Serializan/parsean objetos ORM a respuestas JSON (from_attributes=True).
# - Usan Pydantic v2: model_validator/field_validator y ConfigDict.
# =================================================================================

from datetime import datetime
from typing import Optional, List

from pydantic import (
    BaseModel,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict,
    Field,  # <- Usaremos Field también para default_factory
)

# Enums desde el ORM
from app.models import LanguageEnum, SideEnum, InviteTypeEnum

# =================================================================================
# 🧰 Utilidades de normalización
# =================================================================================
def _normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Devuelve el teléfono solo con dígitos y '+', o None si queda vacío."""
    if not raw:
        return None
    import re
    digits = re.sub(r"[^\d+]", "", raw.strip())
    return digits or None

# =================================================================================
# 👤 Invitados principales (grupo familiar)
# =================================================================================
class GuestBase(BaseModel):
    guest_code: str
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_primary: Optional[bool] = False
    group_id: Optional[str] = None
    side: Optional[SideEnum] = None
    relationship: Optional[str] = None
    language: LanguageEnum = LanguageEnum.en
    invite_type: InviteTypeEnum = InviteTypeEnum.full
    max_accomp: int = Field(default=0, ge=0)  # Define el máximo de acompañantes con valor por defecto 0 y restricción ge=0 para impedir negativos.

    confirmed: Optional[bool] = None
    confirmed_at: Optional[datetime] = None
    num_adults: int = 0
    num_children: int = 0
    menu_choice: Optional[str] = None
    allergies: Optional[str] = None
    needs_accommodation: bool = False
    needs_transport: bool = False

    model_config = ConfigDict(from_attributes=True)

class GuestCreate(GuestBase):
    @model_validator(mode="after")
    def _check_contact(self):
        if (self.email is None) and (self.phone is None):
            raise ValueError("Debes proporcionar al menos email o teléfono.")
        self.phone = _normalize_phone(self.phone)
        return self

class GuestResponse(GuestBase):
    id: int
    created_at: datetime
    updated_at: datetime
    invited_to_ceremony: bool | None = None  # Campo calculado: True si invite_type == full; se rellena en el router.
    invite_scope: str | None = None          # Campo calculado: 'ceremony+reception' o 'reception-only'; se rellena en el router.
    
    model_config = ConfigDict(from_attributes=True)

# =================================================================================
# 👥 Acompañantes
# =================================================================================
class CompanionIn(BaseModel):
    name: str
    is_child: bool
    menu_choice: Optional[str] = None
    allergies: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("El nombre del acompañante es obligatorio.")
        return v

    @field_validator("allergies")
    @classmethod
    def _clean_allergies(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip()
        return v or None

class CompanionOut(CompanionIn):
    pass

# =================================================================================
# 🔐 Login / Token / Recuperación
# =================================================================================
class LoginRequest(BaseModel):
    guest_code: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    @model_validator(mode="after")
    def _check_email_or_phone(self):
        self.email = (self.email or None)
        self.phone = _normalize_phone(self.phone)
        if (self.email is None) and (self.phone is None):
            raise ValueError("Debes proporcionar email o teléfono para iniciar sesión.")
        self.guest_code = (self.guest_code or "").strip()
        if not self.guest_code:
            raise ValueError("guest_code es obligatorio.")
        return self

class Token(BaseModel):
    access_token: str
    token_type: str

class RecoveryRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    @model_validator(mode="after")
    def _check_contact(self):
        self.phone = _normalize_phone(self.phone)
        if (self.email is None) and (self.phone is None):
            raise ValueError("Debes indicar email o teléfono para recuperar tu código.")
        return self

# =================================================================================
# 🔗 Magic Link (Request / Login)  # Sección específica para el flujo de Magic Link.
# =================================================================================


class RequestAccessPayload(BaseModel):  # Define el payload para solicitar acceso vía Magic Link.
    full_name: str = Field(..., min_length=3, max_length=120)  # Nombre completo tal como en la invitación (validación básica).
    phone_last4: str = Field(..., min_length=4, max_length=4)  # Últimos 4 dígitos del teléfono (exactamente 4).
    email: EmailStr  # Correo donde se enviará el enlace mágico (valida formato de email).
    consent: bool = True  # Bandera de consentimiento para comunicaciones (buena práctica GDPR).
    preferred_language: str = "en"  # Idioma preferido para el correo (en|es|ro); default alineado al sistema.

    @field_validator("phone_last4")  # Validador de campo específico para phone_last4.
    @classmethod  # Declara método de clase para el validador.
    def _only_digits_len4(cls, v: str) -> str:  # Enforce: solo dígitos y longitud 4.
        v = (v or "").strip()  # Limpia espacios alrededor.
        if not (len(v) == 4 and v.isdigit()):  # Comprueba longitud exacta 4 y que sean solo dígitos.
            raise ValueError("phone_last4 debe tener exactamente 4 dígitos numéricos.")  # Mensaje de error claro.
        return v  # Devuelve el valor normalizado si pasó la validación.

class MagicLoginPayload(BaseModel):  # Define el payload para canjear el enlace mágico por un access_token.
    token: str  # Token firmado (JWT corto) recibido por correo; el backend lo validará y emitirá un access_token.


# =================================================================================
# 📋 Actualización de RSVP por el invitado
# =================================================================================
class RSVPUpdateRequest(BaseModel):
    attending: bool
    menu_choice: Optional[str] = None
    allergies: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    needs_accommodation: bool = False
    needs_transport: bool = False
    companions: List[CompanionIn] = Field(default_factory=list)  # <- FIX

    @model_validator(mode="after")
    def _sanitize_fields(self):
        self.allergies = ((self.allergies or "").strip() or None)
        if self.notes:
            self.notes = self.notes.strip()[:500]  # Trunca a 500 caracteres
        else:
            self.notes = None
        return self


# =================================================================================
# 🧾 Guest + Companions (respuesta protegida)
# =================================================================================
class GuestWithCompanionsResponse(GuestResponse):
    companions: List[CompanionOut] = Field(default_factory=list)  # <- FIX

    model_config = ConfigDict(from_attributes=True)

# =================================================================================
# 📥 Schemas de Importación de Invitados (Admin)
# =================================================================================
class ImportGuestIn(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    language: LanguageEnum
    max_accomp: int = Field(ge=0)
    invite_type: InviteTypeEnum
    side: Optional[SideEnum] = None          # "bride" | "groom" | None
    relationship: Optional[str] = None
    group_id: Optional[str] = None

    @model_validator(mode="after")
    def _normalize_and_optional_rules(self):
        # Normaliza teléfono
        self.phone = _normalize_phone(self.phone)
        # (Opcional) Si quieres también exigir email o phone aquí, descomenta:
        if (self.email is None) and (self.phone is None):
             raise ValueError("Cada invitado debe tener al menos email o teléfono.")
        # Normaliza nombre
        self.full_name = (self.full_name or "").strip()
        if not self.full_name:
            raise ValueError("full_name no puede estar vacío.")
        return self

class ImportGuestsPayload(BaseModel):                                                     # Define el payload estándar para importación de invitados (usando la clave 'items').
    items: List[ImportGuestIn]                                                            # Lista canónica de ítems que el backend procesará para crear/actualizar invitados.

    @model_validator(mode="before")                                                       # Declara un validador que se ejecuta antes del parseo a campos tipados (modo 'before').
    @classmethod                                                                          # Indica que el validador es un método de clase (no de instancia).
    def _accept_rows_alias(cls, data):                                                    # Define un normalizador para aceptar 'rows' como alias de 'items'.
        if isinstance(data, dict):                                                        # Verifica que el payload recibido sea un diccionario (estructura JSON típica).
            if "rows" in data and "items" not in data:                                    # Si el cliente mandó 'rows' y no incluyó 'items'...
                data = {**data, "items": data["rows"]}                                    # Copia el contenido de 'rows' a 'items' para compatibilidad retro.
        return data                                                                        # Devuelve los datos (posiblemente normalizados) para que Pydantic continúe el parseo.

class ImportGuestsResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: List[str] = Field(default_factory=list)
