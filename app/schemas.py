# app/schemas.py  # Ruta y nombre del archivo de esquemas (Pydantic).                               # Indica dónde va este archivo en el proyecto.

# =================================================================================
# 📦 Schemas (MODELOS DE DATOS Pydantic)
# ---------------------------------------------------------------------------------
# Este archivo define los modelos de datos usados por la API, basados en Pydantic.
# - Validan la entrada y salida de datos (tipos, reglas de negocio).
# - Serializan/parsean objetos ORM a respuestas JSON (from_attributes=True).
# - Usan Pydantic v2: model_validator/field_validator y ConfigDict.
# =================================================================================

from datetime import datetime                                                                 # Importa tipo de fecha/hora para timestamps.
from typing import Optional, List, Literal                                                    # Importa tipos para anotar opcionales, listas y literales.

from pydantic import (                                                                        # Importa utilidades principales de Pydantic v2.
    BaseModel,                                                                                # Clase base para definir modelos.
    EmailStr,                                                                                 # Tipo de email con validación de formato.
    field_validator,                                                                          # Decorador para validación a nivel de campo.
    model_validator,                                                                          # Decorador para validación a nivel de modelo.
    ConfigDict,                                                                               # Configuración del modelo (equivalente a class Config).
    Field,                                                                                    # Declaración de campos con metadata y defaults.
)

# Enums desde el ORM                                                                          # Importa enums definidos en tu capa ORM (SQLAlchemy).
from app.models import LanguageEnum, SideEnum, InviteTypeEnum

LanguageLiteral = Literal["es", "en", "ro"]                                                   # Define el conjunto de valores válidos para 'lang'.

# =================================================================================
# 🧰 Utilidades de normalización
# =================================================================================
def _normalize_phone(raw: Optional[str]) -> Optional[str]:                                    # Normaliza teléfonos entrantes.
    """Devuelve el teléfono solo con dígitos y '+', o None si queda vacío."""                 # Documenta el objetivo del helper.
    if not raw:                                                                               # Si no hay valor...
        return None                                                                           # ...retorna None directamente.
    import re                                                                                 # Importa regex localmente (evita coste global).
    digits = re.sub(r"[^\d+]", "", raw.strip())                                               # Elimina cualquier cosa que no sea dígito o '+'.
    return digits or None                                                                     # Devuelve la cadena resultante o None si quedó vacía.

# =================================================================================
# 👤 Invitados principales (grupo familiar)
# =================================================================================
class GuestBase(BaseModel):                                                                   # Modelo base para invitados (compartido entre requests/responses).
    guest_code: str                                                                           # Código único del invitado (clave pública).
    full_name: str                                                                            # Nombre completo del invitado.
    email: Optional[EmailStr] = None                                                          # Email del invitado (opcional).
    phone: Optional[str] = None                                                               # Teléfono del invitado (opcional, normalizado aparte).
    is_primary: Optional[bool] = False                                                        # Marca si es el contacto principal del grupo.
    group_id: Optional[str] = None                                                            # Identificador de grupo/familia (si aplica).
    side: Optional[SideEnum] = None                                                           # Lado de la boda (bride/groom) si se usa.
    relationship: Optional[str] = None                                                        # Relación con la pareja (texto libre).
    language: Optional[LanguageEnum] = None                                                   # 🔁 Idioma preferido (opcional para no forzar EN por defecto).
    invite_type: InviteTypeEnum = InviteTypeEnum.full                                         # Tipo de invitación (full/reception-only).
    max_accomp: int = Field(default=0, ge=0)                                                  # Máximo de acompañantes permitidos (>=0).

    confirmed: Optional[bool] = None                                                          # Confirmación de asistencia (puede ser None si no ha respondido).
    confirmed_at: Optional[datetime] = None                                                   # Fecha/hora de confirmación (si existe).
    num_adults: int = 0                                                                       # Número de adultos confirmados (si aplica).
    num_children: int = 0                                                                     # Número de niños confirmados (si aplica).
    menu_choice: Optional[str] = None                                                         # Opción de menú (si aplica).
    allergies: Optional[str] = None                                                           # Alergias o restricciones (texto libre).
    needs_accommodation: bool = False                                                         # Si necesita alojamiento (bandera booleana).
    needs_transport: bool = False                                                             # Si necesita transporte (bandera booleana).

    model_config = ConfigDict(from_attributes=True)                                           # Permite construir desde objetos ORM (atributos).

class GuestCreate(GuestBase):                                                                 # Modelo para crear invitados (admin/import).
    @model_validator(mode="after")                                                            # Validador que se ejecuta tras el parseo del modelo.
    def _check_contact(self):                                                                 # Asegura que haya al menos un medio de contacto.
        if (self.email is None) and (self.phone is None):                                     # Verifica que email/phone no estén ambos vacíos.
            raise ValueError("Debes proporcionar al menos email o teléfono.")                 # Error claro si faltan ambos.
        self.phone = _normalize_phone(self.phone)                                             # Normaliza teléfono si vino.
        return self                                                                           # Devuelve la instancia validada.

class GuestResponse(GuestBase):                                                               # Modelo de respuesta pública del invitado (protegida).
    id: int                                                                                   # Identificador interno del invitado (DB).
    created_at: datetime                                                                      # Fecha de creación del registro.
    updated_at: datetime                                                                      # Fecha de última actualización del registro.
    invited_to_ceremony: bool | None = None                                                   # Campo calculado: asiste a ceremonia (lo rellena el router).
    invite_scope: str | None = None                                                           # Campo calculado: 'ceremony+reception' o 'reception-only'.
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)                     # ⬅️ Exporta enums por su value ("es","en","ro").

# =================================================================================
# 👥 Acompañantes
# =================================================================================
class CompanionIn(BaseModel):                                                                 # Modelo de entrada para acompañantes (desde el invitado).
    name: str                                                                                 # Nombre del acompañante.
    is_child: bool                                                                            # Marca si el acompañante es niño.
    menu_choice: Optional[str] = None                                                         # Opción de menú del acompañante (opcional).
    allergies: Optional[str] = None                                                           # Alergias del acompañante (opcional).

    @field_validator("name")                                                                  # Validador a nivel de campo para 'name'.
    @classmethod                                                                              # Define como método de clase (requerido por Pydantic).
    def _non_empty(cls, v: str) -> str:                                                       # Rechaza nombres vacíos.
        v = (v or "").strip()                                                                 # Limpia espacios alrededor.
        if not v:                                                                             # Si quedó vacío...
            raise ValueError("El nombre del acompañante es obligatorio.")                     # ...lanza error entendible.
        return v                                                                              # Devuelve el nombre limpio.

    @field_validator("allergies")                                                             # Validador para 'allergies'.
    @classmethod                                                                              # Método de clase.
    def _clean_allergies(cls, v: Optional[str]) -> Optional[str]:                             # Limpia y normaliza alergias.
        v = (v or "").strip()                                                                 # Elimina espacios incidentales.
        return v or None                                                                      # Devuelve None si quedó vacío.

class CompanionOut(CompanionIn):                                                              # Modelo de salida para acompañantes (mismo shape que entrada).
    model_config = ConfigDict(from_attributes=True)                                                                                    # No añade campos extra (permite extender si se requiere).

# =================================================================================
# 🔐 Login / Token / Recuperación
# =================================================================================
class LoginRequest(BaseModel):                                                                # Modelo para login clásico (guest_code + email/phone).
    guest_code: str                                                                           # Código de invitado (obligatorio).
    email: Optional[EmailStr] = None                                                          # Email (opcional).
    phone: Optional[str] = None                                                               # Teléfono (opcional).

    @model_validator(mode="after")                                                            # Validador post-parsing.
    def _check_email_or_phone(self):                                                          # Exige al menos un contacto válido además del código.
        self.email = (self.email or None)                                                     # Normaliza email nulo.
        self.phone = _normalize_phone(self.phone)                                             # Normaliza teléfono si vino.
        if (self.email is None) and (self.phone is None):                                     # Si ambos están ausentes...
            raise ValueError("Debes proporcionar email o teléfono para iniciar sesión.")      # ...lanza error claro.
        self.guest_code = (self.guest_code or "").strip()                                     # Asegura que el código no esté vacío/espaciado.
        if not self.guest_code:                                                               # Si el código quedó vacío...
            raise ValueError("guest_code es obligatorio.")                                    # ...lanza error.
        return self                                                                           # Devuelve el modelo validado.

class Token(BaseModel):                                                                       # Modelo de respuesta para /login y /magic-login.
    access_token: str                                                                         # JWT de acceso.
    token_type: str                                                                           # Tipo de token (normalmente "bearer").

class RecoveryRequest(BaseModel):                                                             # Modelo para recuperar el código por email/teléfono.
    email: Optional[EmailStr] = None                                                          # Email opcional.
    phone: Optional[str] = None                                                               # Teléfono opcional.
    lang: Optional[str] = None                                                                # 🆕 Idioma sugerido por el cliente (se pasará al resolver).

    @model_validator(mode="after")                                                            # Validador post-parsing.
    def _check_contact(self):                                                                 # Exige al menos un contacto.
        self.phone = _normalize_phone(self.phone)                                             # Normaliza teléfono si vino.
        if (self.email is None) and (self.phone is None):                                     # Si no hay ninguno...
            raise ValueError("Debes indicar email o teléfono para recuperar tu código.")      # ...lanza error claro.
        return self                                                                           # Devuelve instancia validada.

# =================================================================================
# 🔗 Magic Link (Request / Login)
# =================================================================================
class RequestAccessPayload(BaseModel):                                                        # Payload para solicitar acceso (código o magic link).
    full_name: str = Field(..., min_length=3, max_length=120)                                 # Nombre completo (validación mínima).
    phone_last4: str = Field(..., min_length=4, max_length=4)                                 # Últimos 4 del teléfono (exactamente 4).
    email: EmailStr                                                                           # Correo a donde se enviará el acceso.
    consent: bool = True                                                                      # Consentimiento para comunicaciones (GDPR-friendly).
    lang: Optional[LanguageLiteral] = None                                                    # 🆕 Idioma canónico del payload (opcional, sin default).
    preferred_language: Optional[LanguageLiteral] = Field(                                    # 🆕 Alias de compat. para clientes que envían este nombre.
        default=None,                                                                         #    No imponemos idioma por defecto desde el schema.
        alias="preferred_language",                                                           #    Permite recibir 'preferred_language' y mapearlo a 'lang'.
    )                                                                                         # Fin de definición del alias.

    @model_validator(mode="after")                                                            # Validador post-parsing.
    def _merge_lang_alias(self):                                                              # Fusiona alias → campo canónico.
        self.lang = (self.lang or self.preferred_language or None)                            # Si 'lang' no vino, usa 'preferred_language'.
        return self                                                                           # Devuelve la instancia validada.

    @field_validator("phone_last4")                                                           # Validador específico del campo phone_last4.
    @classmethod                                                                              # Método de clase.
    def _only_digits_len4(cls, v: str) -> str:                                                # Enforce: 4 dígitos exactos.
        v = (v or "").strip()                                                                 # Limpia espacios.
        if not (len(v) == 4 and v.isdigit()):                                                 # Comprueba longitud 4 y que sean dígitos.
            raise ValueError("phone_last4 debe tener exactamente 4 dígitos numéricos.")       # Error claro si no cumple.
        return v                                                                              # Devuelve valor válido.

class MagicLoginPayload(BaseModel):                                                           # Payload para canjear token mágico por access token.
    token: str                                                                                # Token firmado (JWT corto) recibido por email.

# =================================================================================
# 📋 Actualización de RSVP por el invitado
# =================================================================================
class RSVPUpdateRequest(BaseModel):                                                           # Modelo para actualizar la respuesta RSVP del invitado.
    attending: bool                                                                           # Indica si asiste (el router mapeará a 'confirmed').
    menu_choice: Optional[str] = None                                                         # Opción de menú (opcional).
    allergies: Optional[str] = None                                                           # Alergias/restricciones (texto libre).
    notes: Optional[str] = Field(default=None, max_length=500)                                # Notas opcionales, limitadas a 500 caracteres.
    needs_accommodation: bool = False                                                         # Bandera: necesita alojamiento.
    needs_transport: bool = False                                                             # Bandera: necesita transporte.
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    companions: List[CompanionIn] = Field(default_factory=list)                               # Lista de acompañantes (vacía por defecto).

    @model_validator(mode="after")                                                            # Validador post-parsing.
    def _sanitize_fields(self):                                                               # Limpia/trunca campos libres para evitar excesos.
        self.allergies = ((self.allergies or "").strip() or None)                             # Normaliza alergias a None si vacío.
        if self.notes:                                                                        # Si hay notas...
            self.notes = self.notes.strip()[:500]                                             # ...trunca a 500 chars como máximo.
        else:                                                                                 # Si no hay notas...
            self.notes = None                                                                 # ...deja como None.
        return self                                                                           # Devuelve instancia validada.

# =================================================================================
# 🧾 Guest + Companions (respuesta protegida)
# =================================================================================
class GuestWithCompanionsResponse(GuestResponse):                                             # Respuesta que incluye invitado + acompañantes.
    companions: List[CompanionOut] = Field(default_factory=list)                              # Lista de acompañantes (vacía por defecto).
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)                     # ⬅️ Exporta enums por su value en JSON.

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
    side: Optional[SideEnum] = None
    relationship: Optional[str] = None
    group_id: Optional[str] = None

    @model_validator(mode="after")
    def _normalize_and_optional_rules(self):
        self.phone = _normalize_phone(self.phone)
        if (self.email is None) and (self.phone is None):
             raise ValueError("Cada invitado debe tener al menos email o teléfono.")
        self.full_name = (self.full_name or "").strip()
        if not self.full_name:
            raise ValueError("full_name no puede estar vacío.")
        return self

class ImportGuestsPayload(BaseModel):
    items: List[ImportGuestIn]

    @model_validator(mode="before")
    @classmethod
    def _accept_rows_alias(cls, data):
        if isinstance(data, dict):
            if "rows" in data and "items" not in data:
                data = {**data, "items": data["rows"]}
        return data

class ImportGuestsResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: List[str] = Field(default_factory=list)
