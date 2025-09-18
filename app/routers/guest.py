# app/routers/guest.py  # Ruta del archivo que define el router de endpoints del invitado.                   # Comentario: indica la ubicación del módulo.

# =================================================================================                                                                # Separador visual de sección.
# 👤 Router: Endpoints del Invitado (perfil y RSVP)                                                                                                 # Título descriptivo del módulo.
# ---------------------------------------------------------------------------------                                                                 # Separador.
# Este módulo expone las rutas PROTEGIDAS (requieren JWT) para:                                                                                     # Explicación del propósito.
# - Obtener el perfil del invitado autenticado (/me).                                                                                               # Lista de endpoints.
# - Actualizar la confirmación de asistencia (RSVP) del invitado (/me/rsvp).                                                                        # Lista de endpoints.
# =================================================================================                                                                # Fin encabezado.

# 🐍 Importaciones estándar y de terceros                                                                                                          # Sección de importaciones.
# ---------------------------------------------------------------------------------                                                                 # Separador.
from datetime import datetime  # Para sellos de tiempo en confirmaciones y validaciones.                                                           # Import: datetime para tiempos.
from typing import Optional    # Para anotar tipos opcionales en dependencias/helpers.                                                             # Import: Optional para tipado.
import os                      # Para leer variables de entorno (RSVP_DEADLINE).                                                                   # Import: os para env.
from loguru import logger      # Logger para observabilidad de errores                                                                            # Import: loguru logger.

from fastapi import APIRouter, Depends, HTTPException, status  # API Router y utilidades de FastAPI.                                               # Import: FastAPI core.
from fastapi.security import OAuth2PasswordBearer              # Esquema Bearer para extraer el token.                                            # Import: OAuth2 bearer.
from sqlalchemy.orm import Session                             # Sesión de SQLAlchemy para acceso a BD.                                           # Import: Session ORM.

# 🧩 Importaciones internas del proyecto                                                                                                           # Sección de imports internos.
# ---------------------------------------------------------------------------------                                                                 # Separador.
from app.db import SessionLocal                # Fábrica de sesiones de BD.                                                                        # Import: SessionLocal.
from app import models, schemas, auth, mailer  # Modelos ORM, Schemas Pydantic, utilidades de autenticación y mailer.                           # Import: modelos, schemas, auth, mailer.
from app.models import InviteTypeEnum          # Enum para diferenciar ceremonia vs ceremonia+recepción.                                          # Import: enum de invitación.

# 🧍‍♂️ Helper para enmascarar correos electrónicos                                                                                                  # Helper: enmascarar email.
# ---------------------------------------------------------------------------------                                                                 # Separador.
def _mask_email(addr: str | None) -> str:      # Función para enmascarar emails en logs.                                                          # Define _mask_email.
    if not addr:                               # Si no hay email, retorna placeholder.                                                            # Caso None.
        return "<no-email>"                    # Placeholder para email ausente.                                                                  # Retorno placeholder.
    addr = addr.strip()                        # Limpia espacios en blanco.                                                                       # Limpia string.
    if "@" not in addr or len(addr) < 3:       # Si no tiene @ o es muy corto, enmascara parcialmente.                                            # Validación formato.
        return addr[:2] + "***"                # Enmascara con asteriscos.                                                                        # Retorno enmascarado.
    name, dom = addr.split("@", 1)             # Divide en nombre y dominio.                                                                       # Split email.
    return (name[:2] + "***@" + dom)           # Retorna nombre parcialmente enmascarado + dominio.                                                # Retorno final.

# 🧭 Configuración del router                                                                                                                                                     
# ---------------------------------------------------------------------------------                                                                 # Separador.
router = APIRouter(                            # Crea un router modular de FastAPI.                                                               # Construcción del router.
    prefix="/api/guest",                       # Prefijo común para todas las rutas de este archivo.                                              # Prefijo /api/guest.
    tags=["guest"],                            # Etiqueta para agrupar rutas en la documentación /docs.                                            # Tag 'guest'.
)                                              # Cierra la construcción del router.                                                                # Fin router.

# 🔐 Esquema OAuth2 para extraer el token Bearer en /docs                                                                                         # Sección de seguridad.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")  # El login real es JSON en /api/login.                                               # Esquema bearer para Swagger.

# 🛠️ Dependencias comunes                                                                                                                                                           
# ---------------------------------------------------------------------------------                                                                 # Separador.
def get_db() -> Session:                       # Dependencia que entrega una sesión de BD por request.                                            # Define get_db.
    db = SessionLocal()                        # Crea una nueva sesión de SQLAlchemy.                                                             # Instancia sesión.
    try:                                       # Garantiza cierre con try/finalmente.                                                             # Bloque try.
        yield db                               # Entrega la sesión a la ruta que la requiera.                                                     # Yield sesión.
    finally:                                   # Al finalizar la request (éxito o error)...                                                        # Bloque finally.
        db.close()                             # Cierra la sesión y libera recursos.                                                              # Cierra sesión.

def get_current_guest(                         # Dependencia para autenticar y obtener al invitado actual.                                        # Define get_current_guest.
    token: str = Depends(oauth2_scheme),       # Extrae el token Bearer del encabezado Authorization.                                             # Dependencia: token.
    db: Session = Depends(get_db),             # Inyecta una sesión de BD.                                                                        # Dependencia: db sesión.
) -> models.Guest:                             # Devuelve una instancia ORM de Guest.                                                             # Tipo de retorno ORM.
    credentials_exception = HTTPException(     # Excepción estándar de credenciales inválidas.                                                    # Prepara excepción 401.
        status_code=status.HTTP_401_UNAUTHORIZED,  # HTTP 401 (no autorizado).                                                                    # Código 401.
        detail="No se pudieron validar las credenciales",  # Mensaje genérico.                                                                   # Mensaje error.
        headers={"WWW-Authenticate": "Bearer"},            # Indica esquema esperado.                                                             # Cabecera WWW-Authenticate.
    )                                         # Cierra construcción de la excepción.                                                               # Fin excepción.

    payload = auth.verify_access_token(token)  # Verifica el JWT y devuelve payload o None.                                                       # Verifica token.
    if payload is None:                        # Si el token es inválido o expiró...                                                              # Condición sin payload.
        raise credentials_exception            # Lanza 401.                                                                                       # Lanza excepción.

    guest_code = payload.get("sub")            # Extrae el claim 'sub' (guest_code).                                                              # Lee 'sub'.
    if not guest_code:                         # Si no existe el claim esperado...                                                                 # Validación 'sub'.
        raise credentials_exception            # Lanza 401.                                                                                       # Excepción.

    guest = db.query(models.Guest).filter(     # Busca en la BD al invitado correspondiente.                                                      # Query ORM.
        models.Guest.guest_code == guest_code  # Filtro por guest_code.                                                                           # Filtro igualdad.
    ).first()                                  # Toma el primer resultado.                                                                         # Obtiene 1 fila.
    if not guest:                              # Si no se encuentra el invitado...                                                                # Comprobación None.
        raise credentials_exception            # Lanza 401.                                                                                       # Excepción.

    return guest                               # Devuelve el invitado autenticado.                                                                # Retorno ORM.

# =================================================================================                                                                 # Separador.
# 📄 GET /api/guest/me — Perfil del invitado autenticado                                                                                           # Sección endpoint GET /me.
# ---------------------------------------------------------------------------------                                                                 # Separador.
@router.get("/me", response_model=schemas.GuestWithCompanionsResponse)  # Define ruta GET con response_model tipado.                               # Decorador FastAPI.
def get_my_profile(                            # Endpoint: devuelve el perfil del invitado.                                                       # Define función handler.
    current_guest: models.Guest = Depends(get_current_guest),  # Invitado autenticado.                                                            # Dependencia invitado actual.
):                                             # Cierra firma de la función.                                                                      # Fin firma.
    # --- Campos calculados para UI (no alteran el modelo en BD) ---                                                                             # Bloque de campos derivados.
    is_full_invite: bool = (current_guest.invite_type == InviteTypeEnum.full)  # True si la invitación es 'full' (Ceremonia + Recepción).       # Calcula booleano.
    invite_scope_label: str = "ceremony+reception" if is_full_invite else "reception-only"  # Etiqueta canónica para UI según el booleano.       # Define etiqueta.

    # --- Construcción de la respuesta con los campos extra ---                                                                                   # Bloque de respuesta tipada.
    resp = schemas.GuestWithCompanionsResponse.model_validate(current_guest)  # Transforma ORM → schema respetando from_attributes.               # Model validate.
    resp.invited_to_ceremony = is_full_invite                                  # Inserta el booleano calculado en el schema de salida.            # Set campo 1.
    resp.invite_scope = invite_scope_label                                     # Inserta la etiqueta calculada en el schema de salida.            # Set campo 2.
    return resp                                                                 # Devuelve el schema extendido (incluye companions).               # Return final.

# =================================================================================                                                                 # Separador.
# 📝 POST /api/guest/me/rsvp — Actualizar confirmación de asistencia                                                                                 # Sección endpoint POST /me/rsvp.
# ---------------------------------------------------------------------------------                                                                 # Separador.
@router.post("/me/rsvp", response_model=schemas.GuestWithCompanionsResponse)  # Define ruta POST con response_model tipado.                        # Decorador FastAPI.
def update_my_rsvp(                            # Endpoint: actualiza la confirmación de asistencia.                                               # Define función handler.
    payload: schemas.RSVPUpdateRequest,        # Datos recibidos del cliente (attending, companions...).                                          # Body payload tipado.
    db: Session = Depends(get_db),             # Sesión de BD.                                                                                    # Dependencia DB.
    current_guest: models.Guest = Depends(get_current_guest),  # Invitado autenticado.                                                            # Dependencia invitado.
):                                             # Cierra firma de la función.                                                                      # Fin firma.
    # ⏳ 1) Validar fecha límite de RSVP desde variables de entorno.                                                                              # Paso 1: validar deadline.
    deadline_str = os.getenv("RSVP_DEADLINE", "2026-01-20")  # Lee la fecha límite (ISO) con un valor por defecto seguro.                        # Lee env.
    try:                                                     # Intenta parsear la fecha en formato ISO.                                           # Try parse.
        deadline = datetime.fromisoformat(deadline_str)      # Convierte la cadena ISO a datetime naive.                                          # Parse ISO.
    except Exception:                                        # Si el formato es inválido o falla el parseo...                                     # Except parse.
        deadline = datetime.fromisoformat("2099-12-31")      # Usa una fecha futura para no bloquear por error de configuración.                  # Fallback fecha.

    if datetime.utcnow() > deadline:                         # Compara hora actual UTC vs fecha límite.                                           # Comparación tiempo.
        raise HTTPException(                                 # Si ya pasó, rechaza la operación con 400.                                          # Lanza 400.
            status_code=status.HTTP_400_BAD_REQUEST,         # Código 400 (bad request).                                                          # Código HTTP.
            detail="La fecha límite para confirmar la asistencia ya ha pasado.",  # Mensaje claro para el cliente.                               # Mensaje.
        )                                                    # Cierra la excepción.                                                                # Fin raise.

    # 🚫 2) Si el invitado NO asistirá, limpiar datos dependientes.
    if not payload.attending:
        current_guest.confirmed = False
        current_guest.confirmed_at = datetime.utcnow()
        current_guest.menu_choice = None
        current_guest.allergies = None
        current_guest.needs_accommodation = bool(payload.needs_accommodation)
        current_guest.needs_transport = bool(payload.needs_transport)
        current_guest.companions.clear()
        current_guest.num_adults = 0
        current_guest.num_children = 0
        # ✅ NUEVO: guardar notas (aunque no asista)
        current_guest.notes = (payload.notes or None)

        db.commit()
        db.refresh(current_guest)

        logger.info(
            "RSVP: declinado | guest_id=%s | code=%s | email=%s",
            current_guest.id, current_guest.guest_code, _mask_email(current_guest.email)
        )

        try:
            if current_guest.email:
                summary = {
                    "guest_name": current_guest.full_name or "",
                    "invite_scope": "ceremony+reception" if current_guest.invite_type == InviteTypeEnum.full else "reception-only",
                    "attending": False,
                    "companions": [],  # al declinar, no hay acompañantes
                    "allergies": "",
                    "notes": None,
                }
                ok = mailer.send_confirmation_email(
                    to_email=current_guest.email,
                    language=(current_guest.language.value if current_guest.language else "en"),
                    summary=summary,
                )
                if ok:
                    logger.info("RSVP: email de confirmación ENVIADO | guest_id=%s | email=%s",
                                current_guest.id, _mask_email(current_guest.email))
                else:
                    logger.error("RSVP: email de confirmación FALLÓ (ret False) | guest_id=%s | email=%s",
                                 current_guest.id, _mask_email(current_guest.email))
        except Exception as e:
            logger.error("RSVP: error enviando email de confirmación (declinó) | guest_id=%s | err=%s",
                         current_guest.id, e)

        # --- Construir respuesta con campos calculados, igual que en /me ---
        is_full_invite: bool = (current_guest.invite_type == InviteTypeEnum.full)
        invite_scope_label: str = "ceremony+reception" if is_full_invite else "reception-only"
        resp = schemas.GuestWithCompanionsResponse.model_validate(current_guest)
        resp.invited_to_ceremony = is_full_invite
        resp.invite_scope = invite_scope_label
        return resp

    # ✅ 3) Si asistirá, validar reglas de negocio.                                                                                              # Paso 3: validaciones.
    if len(payload.companions) > (current_guest.max_accomp or 0):  # Verifica que no supere el máximo permitido de acompañantes.                 # Regla de cupo.
        raise HTTPException(status_code=400, detail="Has superado el número máximo de acompañantes permitido.")  # Error claro.                # Lanza 400.

    requires_menu = (current_guest.invite_type == InviteTypeEnum.full)  # El menú del titular solo aplica si invitación es FULL.                # Flag menú.
    if requires_menu and not (payload.menu_choice and payload.menu_choice.strip()):  # Si requiere menú pero no se envió uno válido...           # Validación menú.
        raise HTTPException(status_code=400, detail="Debes escoger un menú para el titular.")  # Error si falta menú.                           # Lanza 400.

    # 👪 4) Calcular totales de adultos y niños.                                                                                                 # Paso 4: conteo.
    titular_adult = 1                                               # El titular cuenta como un adulto.                                            # Titular = 1 adulto.
    adults = titular_adult + sum(1 for c in payload.companions if not c.is_child)  # Adultos = titular + acompañantes adultos.                   # Calcula adultos.
    children = sum(1 for c in payload.companions if c.is_child)    # Niños = suma de acompañantes marcados como niño.                             # Calcula niños.

    # 📝 5) Persistir datos del titular.                                                                                                          # Paso 5: persistir titular.
    current_guest.confirmed = True                                  # Marca confirmación como True.                                                # Confirma asistencia.
    current_guest.confirmed_at = datetime.utcnow()                  # Sella tiempo de confirmación.                                                # Timestamp.
    current_guest.menu_choice = (payload.menu_choice or None) if requires_menu else None  # Guarda menú si aplica; si no, None.                  # Guarda menú.
    current_guest.allergies = (payload.allergies or None)           # Guarda alergias (o None si vacío).                                           # Guarda alergias.
    current_guest.needs_accommodation = bool(payload.needs_accommodation)  # Guarda necesidad de alojamiento.                                     # Guarda alojamiento.
    current_guest.needs_transport = bool(payload.needs_transport)          # Guarda necesidad de transporte.                                      # Guarda transporte.
    # ✅ NUEVO: guardar notas del titular
    current_guest.notes = (payload.notes or None)

    # 🔁 6) Reemplazar la lista de acompañantes.                                                                                                  # Paso 6: companions.
    current_guest.companions.clear()                                # Limpia la lista existente para reemplazarla.                                 # Limpia lista.
    for c in payload.companions:                                    # Itera por cada acompañante recibido en el payload.                          # Loop companions.
        current_guest.companions.append(                            # Agrega un nuevo registro Companion al invitado actual.                      # Append companion.
            models.Companion(                                       # Instancia el modelo Companion.                                               # Construye modelo.
                guest_id=current_guest.id,                          # Relaciona el companion con el invitado actual.                               # FK guest_id.
                name=c.name.strip(),                                # Guarda nombre del acompañante (sin espacios extra).                          # Nombre limpio.
                is_child=bool(c.is_child),                          # Guarda si es niño/niña.                                                       # Flag niño.
                menu_choice=(c.menu_choice or None) if requires_menu else None,  # Menú del acompañante si aplica; si no, None.                   # Menú acomp.
                allergies=(c.allergies or None),                    # Alergias del acompañante (o None si vacío).                                  # Alergias acomp.
            )
        )

    # 🔢 7) Actualizar contadores y guardar cambios.                                                                                              # Paso 7: contadores + commit.
    current_guest.num_adults = adults                                # Actualiza el total de adultos.                                              # Set adultos.
    current_guest.num_children = children                            # Actualiza el total de niños.                                                # Set niños.
    db.commit()                                                      # Persiste todos los cambios (titular + acompañantes + contadores).           # Commit BD.
    db.refresh(current_guest)                                        # Refresca el objeto ORM con datos confirmados.                               # Refresh ORM.

    logger.info(
        "RSVP: confirmado | guest_id=%s | code=%s | email=%s | adults=%s | children=%s",
        current_guest.id, current_guest.guest_code, _mask_email(current_guest.email),
        current_guest.num_adults, current_guest.num_children
    )

    try:
        if current_guest.email:
            summary = {
                "guest_name": current_guest.full_name or "",
                "invite_scope": "ceremony+reception" if current_guest.invite_type == InviteTypeEnum.full else "reception-only",
                "attending": True,
                "companions": [
                    {"name": c.name or "", "label": ("child" if c.is_child else "adult"), "allergens": c.allergies or ""}
                    for c in (current_guest.companions or [])
                ],
                "allergies": current_guest.allergies or "",
                "notes": (current_guest.notes or None),
            }
            ok = mailer.send_confirmation_email(
                to_email=current_guest.email,
                language=(current_guest.language.value if current_guest.language else "en"),
                summary=summary,
            )
            if ok:
                logger.info("RSVP: email de confirmación ENVIADO | guest_id=%s | email=%s",
                            current_guest.id, _mask_email(current_guest.email))
            else:
                logger.error("RSVP: email de confirmación FALLÓ (ret False) | guest_id=%s | email=%s",
                             current_guest.id, _mask_email(current_guest.email))
    except Exception as e:
        logger.error("RSVP: error enviando email de confirmación (asiste) | guest_id=%s | err=%s",
                     current_guest.id, e)

    # --- Construir respuesta con campos calculados, igual que en /me ---                                                                         # Respuesta consistente.
    is_full_invite: bool = (current_guest.invite_type == InviteTypeEnum.full)          # Recalcula si la invitación es 'full'.                  # Booleano invitación.
    invite_scope_label: str = "ceremony+reception" if is_full_invite else "reception-only"  # Etiqueta canónica.                                 # Etiqueta alcance.
    resp = schemas.GuestWithCompanionsResponse.model_validate(current_guest)           # Transforma ORM → schema.                               # Model validate.
    resp.invited_to_ceremony = is_full_invite                                          # Inserta booleano calculado.                            # Set campo 1.
    resp.invite_scope = invite_scope_label                                             # Inserta etiqueta calculada.                            # Set campo 2.
    return resp                                                                         # Devuelve schema coherente.                             # Return final.