# app/routers/auth_routes.py                                                        # Ruta y nombre del archivo del router de autenticación.

# =================================================================================  # Separador visual para la cabecera del módulo.
# 🔑 ROUTER DE AUTENTICACIÓN Y RECUPERACIÓN DE CÓDIGOS                              # Describe el propósito del módulo.
# ---------------------------------------------------------------------------------  # Línea divisoria.
# - Login de invitados mediante guest_code + (email o teléfono).                    # Lista funcionalidades actuales.
# - Recuperación de código con respuesta neutra, envío de email si hay match.      # Explica recover-code.
# - Aplica rate-limit por IP en /api/login y /api/recover-code.                     # Indica rate limiting existente.
# - 🔗 NUEVO: request-access (Magic Link o Código) y magic-login.                   # Anuncia endpoints nuevos compatibles con 7.2.
# =================================================================================  # Fin de cabecera.

from fastapi import APIRouter, Depends, HTTPException, Request, status             # Importa utilidades de FastAPI (router, dependencias, errores).
from sqlalchemy.orm import Session                                                # Tipo de sesión de SQLAlchemy para operaciones con BD.
import time                                                                       # Para medir duración de operaciones (logs de búsqueda).
from loguru import logger                                                         # Logger de Loguru para trazas claras.
import os                                                                         # Para leer variables de entorno (.env).

# Importaciones internas del proyecto
from app import models, schemas, auth, mailer                                     # Modulos internos: modelos, esquemas, auth (tokens), mailer.
from app.db import SessionLocal                                                   # Fábrica de sesiones de BD (get_db manual).
from app.rate_limit import is_allowed, get_limits_from_env                        # Helpers para rate limit configurable por entorno.
from app.crud.guests_crud import (                                                # CRUD específico del flujo Magic Link / búsqueda robusta.
    find_guest_for_magic,                                                         # Búsqueda por nombre + últimos 4 del teléfono + email.
    set_magic_link,                                                               # Persistencia de token mágico y expiración.
    consume_magic_link,                                                           # Consumo atómico del token mágico (un uso).
)                                                                                 # Fin import múltiple.
from app.utils.i18n import resolve_lang                                           # 🆕 Importa el cerebro i18n centralizado.

router = APIRouter(                                                               # Crea un router de FastAPI para agrupar rutas relacionadas.
    prefix="/api",                                                                # Prefijo común para todas las rutas de este módulo.
    tags=["auth"],                                                                # Tag para documentación OpenAPI (agrupa endpoints).
)                                                                                 # Cierra la construcción del router.

# --- Dependencia de BD (mantiene compatibilidad con tu proyecto actual) ---
def get_db():                                                                     # Define la dependencia que provee una sesión de BD por request.
    db = SessionLocal()                                                           # Crea una nueva sesión usando la fábrica SessionLocal.
    try:                                                                          # Abre un bloque try/finally para garantizar el cierre.
        yield db                                                                  # Cede la sesión a la ruta que la consuma.
    finally:                                                                      # Al finalizar el manejo de la request...
        db.close()                                                                # ...cierra la sesión para evitar fugas de conexiones.

# --- Configuración de rate limit desde .env (con defaults sensatos) ---
LOGIN_MAX, LOGIN_WINDOW = get_limits_from_env("LOGIN_RL", default_max=5, default_window=60)          # Límite login.
RECOVER_MAX, RECOVER_WINDOW = get_limits_from_env("RECOVER_RL", default_max=3, default_window=120)   # Límite recover.
REQUEST_MAX, REQUEST_WINDOW = get_limits_from_env("REQUEST_RL", default_max=RECOVER_MAX, default_window=RECOVER_WINDOW)  # Límite request-access.

# --- Configuración de URLs y expiraciones desde entorno ---
RSVP_URL = os.getenv("RSVP_URL", "https://rsvp.suarezsiicawedding.com")           # URL pública del formulario (se usa en el Magic Link).
MAGIC_EXPIRE_MIN = int(os.getenv("MAGIC_LINK_EXPIRE_MINUTES", "15"))              # Minutos de expiración del Magic Link (por defecto 15).
ACCESS_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))           # Minutos de expiración del access token (login clásico/mágico).
SEND_ACCESS_MODE = os.getenv("SEND_ACCESS_MODE", "code").strip().lower()          # Modo de acceso desde .env: 'code' (7.2) o 'magic' (clásico).

# =================================================================================
# ✅ Helper para obtener la IP real del cliente (proxy/CDN)
# =================================================================================
def _client_ip(request: Request) -> str:                                           # Helper para extraer IP del cliente (considerando proxies).
    """
    Extrae la IP real del cliente, considerando la cabecera X-Forwarded-For
    comúnmente usada por proxies, balanceadores de carga y CDNs.                 # Docstring: qué hace y por qué.
    """                                                                          # Fin de docstring.
    xff = request.headers.get("x-forwarded-for")                                 # Lee la cabecera X-Forwarded-For si existe.
    if xff:                                                                      # Si la cabecera está presente...
        return xff.split(",")[0].strip()                                         # ...toma la primera IP (cliente original) y la limpia.
    return request.client.host or "unknown"                                      # Si no hay XFF, devuelve la IP de la conexión o 'unknown'.

# =================================================================================
# 🚪 ENDPOINT DE LOGIN (clásico)
# =================================================================================
@router.post("/login", response_model=schemas.Token)                               # Declara la ruta POST /api/login con respuesta tipada (Token).
def login_for_access_token(                                                        # Define la función manejadora del endpoint de login.
    form_data: schemas.LoginRequest,                                               # Payload Pydantic: guest_code + (email o teléfono).
    request: Request,                                                              # Objeto Request para leer headers/IP.
    db: Session = Depends(get_db),                                                 # Inyección de sesión de base de datos.
):                                                                                 # Cierra la firma de la función.
    """
    Login flexible para invitados:
    - Siempre requiere guest_code.
    - Debe coincidir email o teléfono (mínimo uno).
    - Si pasa la validación → devuelve un token JWT.
    - Aplica rate-limit por IP para mitigar fuerza bruta.                         # Docstring: describe la lógica del endpoint.
    """                                                                           # Fin de docstring.
    client_ip = _client_ip(request)                                               # Obtiene la IP real del cliente (considerando XFF).
    rl_key = f"login:{client_ip}"                                                 # Construye clave de rate-limit por IP para este endpoint.
    if not is_allowed(rl_key, LOGIN_MAX, LOGIN_WINDOW):                           # Verifica si se excedió el límite de intentos.
        raise HTTPException(                                                      # Lanza una excepción HTTP 429 si está rate-limited.
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,                        # Código 429 Too Many Requests.
            detail="Too many attempts. Please try again later.",                  # Mensaje genérico (no revela lógica interna).
            headers={"Retry-After": str(LOGIN_WINDOW)},                           # Header sugerido para reintento.
        )                                                                         # Fin de raise.

    guest = db.query(models.Guest).filter(models.Guest.guest_code == form_data.guest_code).first()  # Busca invitado por guest_code exacto.

    if not guest or not (                                                         # Si no existe invitado o no coincide contacto...
        (form_data.email and guest.email == form_data.email) or                   # ...por email exacto (normalizado por schema)...
        (form_data.phone and guest.phone == form_data.phone)                      # ...o por teléfono exacto (normalizado por schema)...
    ):                                                                            # Fin de condición de validación.
        logger.info(f"Login failed for code='{form_data.guest_code}' ip={client_ip}")  # Loguea intento fallido (auditoría).
        raise HTTPException(                                                      # Lanza 401 Unauthorized por credenciales inválidas.
            status_code=status.HTTP_401_UNAUTHORIZED,                             # Código 401.
            detail="Código de invitado, email o teléfono incorrectos",            # Mensaje neutro (no revela cuál campo falló).
        )                                                                         # Fin de raise.

    access_token = auth.create_access_token(subject=guest.guest_code)             # Genera access token (JWT) con subject=guest_code.
    logger.info(f"Login success for code='{guest.guest_code}' ip={client_ip}")    # Loguea acceso exitoso con guest_code e IP.
    return {"access_token": access_token, "token_type": "bearer"}                 # Devuelve el token y su tipo (Bearer) según schema.

# =================================================================================
# 📩 ENDPOINT DE RECUPERACIÓN DE CÓDIGO (respuesta neutra)
# =================================================================================
@router.post("/recover-code")                                                     # Declara la ruta POST /api/recover-code.
def recover_code(                                                                 # Define la función manejadora del endpoint de recuperación.
    recovery_data: schemas.RecoveryRequest,                                       # Payload Pydantic: email o phone (mínimo uno) + lang (opcional).
    request: Request,                                                             # Objeto Request (para IP/rate-limit/headers).
    db: Session = Depends(get_db),                                                # Inyección de sesión de BD.
):                                                                                # Cierra la firma.
    """
    Permite a un invitado recuperar su código de acceso si lo olvidó.
    - Acepta email o teléfono (mínimo uno).
    - Aplica rate-limit por IP.
    - Respuesta SIEMPRE genérica (200) para no revelar existencia.
    - Si hay match con un invitado con email → envía correo con el código.       # Docstring que resume el comportamiento.
    """                                                                           # Fin de docstring.
    client_ip = _client_ip(request)                                               # Obtiene IP del cliente.
    rl_key = f"recover:{client_ip}"                                               # Clave de rate-limit para este endpoint.
    if not is_allowed(rl_key, RECOVER_MAX, RECOVER_WINDOW):                       # Verifica si excedió el límite.
        logger.warning(f"Recover rate-limited ip={client_ip}")                    # Loguea que fue rate-limited (auditoría).
        return {"message": "Demasiados intentos. Intenta más tarde."}             # Respuesta 200 neutra para no facilitar enumeración.

    if not recovery_data.email and not recovery_data.phone:                       # Valida que haya al menos un contacto.
        logger.info(f"Recover bad request ip={client_ip} (no email/phone)")       # Loguea mala petición (sin datos).
        raise HTTPException(                                                      # Lanza 400 por solicitud inválida.
            status_code=status.HTTP_400_BAD_REQUEST,                              # Código 400.
            detail="Debes proporcionar al menos un email o teléfono"              # Mensaje claro para el cliente.
        )                                                                         # Fin de raise.

    guest = None                                                                  # Inicializa variable de invitado.
    if recovery_data.email:                                                       # Si proporcionó email...
        guest = db.query(models.Guest).filter(models.Guest.email == recovery_data.email).first()  # Busca por email exacto.
    if not guest and recovery_data.phone:                                         # Si no encontró por email y hay teléfono...
        guest = db.query(models.Guest).filter(models.Guest.phone == recovery_data.phone).first()  # Busca por teléfono exacto.

    if guest and guest.email:                                                     # Si hay match y el invitado tiene email...
        # --- Resolver idioma para recover-code (consistente con request-access) ---
        accept_lang = request.headers.get("Accept-Language")                      # Lee encabezado 'Accept-Language' del cliente (si existe).
        lang_from_guest = getattr(getattr(guest, "language", None), "value", getattr(guest, "language", None))  # Idioma en DB (Enum->value o str).
        final_lang = resolve_lang(                                                # Llama al resolvedor central de i18n.
            payload_lang=getattr(recovery_data, "lang", None),                    # 1) Usa 'lang' si vino en payload del recover.
            guest_lang=lang_from_guest,                                           # 2) Idioma guardado del invitado.
            accept_language_header=accept_lang,                                   # 3) Header Accept-Language del cliente (opcional).
            email=guest.email,                                                    # 4) Heurística por TLD si aplica (.es/.ro).
            default="es",                                                         # 5) Fallback consistente del proyecto (ES).
        )                                                                         # Fin de llamada al resolver.

        logger.info("RECOVER → Idioma resuelto para id={} : {}", getattr(guest, "id", None), final_lang)  # Log de trazabilidad.

        try:                                                                      # Intenta enviar usando el mailer i18n unificado.
            _ = mailer.send_guest_code_email(                                     # Reutiliza el mismo helper que en request-access (consistente).
                to_email=guest.email,                                             # Destinatario.
                guest_name=(guest.full_name or ""),                               # Nombre del invitado (el mailer escapará si es HTML).
                guest_code=guest.guest_code,                                      # Código que se reenvía.
                language=final_lang,                                              # Idioma resuelto consistentemente.
            )                                                                      # Fin de llamada al mailer.
            logger.info("Recover mail sent to={} ip={}", guest.email, client_ip)   # Log éxito de envío.
        except Exception as e:                                                    # Si algo falla en el envío...
            logger.exception("Recover mail FAILED to={} : {}", guest.email, e)     # Log de error (manteniendo respuesta neutra).
    else:                                                                         # Si no hay match o el invitado no tiene email...
        logger.info(f"Recover requested ip={client_ip} (no match or no email)")   # Log informativo (respuesta seguirá neutra).

    return {"message": "Si tu contacto está en nuestra lista de invitados, recibirás un mensaje en breve."}  # Respuesta neutra 200.

# =================================================================================
# ✉️ NUEVO: REQUEST-ACCESS (solicitar acceso: Magic Link o Código según .env)
# =================================================================================
@router.post("/request-access")                                                   # Declara la ruta POST /api/request-access.
def request_access(                                                               # Define la función manejadora del endpoint.
    payload: schemas.RequestAccessPayload,                                        # Payload Pydantic: full_name, phone_last4, email, consent, lang/alias.
    request: Request,                                                             # Objeto Request (para IP y rate limit).
    db: Session = Depends(get_db),                                                # Inyección de sesión de BD.
):                                                                                # Cierra la firma.
    # --- Rate limiting ---
    client_ip = _client_ip(request)                                               # Obtiene IP real del cliente.
    rl_key = f"request_access:{client_ip}"                                        # Construye clave para rate-limit por IP.
    if not is_allowed(rl_key, REQUEST_MAX, REQUEST_WINDOW):                       # Verifica si excedió su cuota en la ventana.
        raise HTTPException(                                                      # Lanza 429 Too Many Requests si aplica.
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,                        # Código 429.
            detail={"ok": False, "error": "rate_limited"},                        # Detalle mínimo (no revela existencia de datos).
            headers={"Retry-After": str(REQUEST_WINDOW)},                         # Indica en segundos cuándo reintentar.
        )                                                                         # Fin del raise.

    # --- Matching invitado (respuesta SIEMPRE genérica, con logs extendidos) ---
    start_time = time.monotonic()                                                 # Inicia cronómetro para medir duración de la búsqueda.
    _masked_email = "<empty>" if not payload.email else (                         # Prepara versión enmascarada del email para logs.
        (payload.email[:2] + "***@" + payload.email.split("@", 1)[1])             # Si tiene dominio, muestra 2 letras + *** + dominio.
        if "@" in payload.email else (payload.email[:2] + "***")                  # Si no hay '@', muestra 2 letras + ***.
    )                                                                              # Cierra construcción del email enmascarado.

    logger.info(                                                                   # Log de entrada con contexto de la búsqueda (sin PII completa).
        "RSVP/ACCESS → Buscando invitado | name='{}' | last4='{}' | email='{}' | lang_pref='{}'",
        payload.full_name,                                                         # Nombre recibido tal cual en el payload.
        payload.phone_last4,                                                       # Últimos 4 dígitos del teléfono recibidos.
        _masked_email,                                                             # Email enmascarado.
        getattr(payload, "lang", None),                                            # Idioma preferido indicado por el cliente (si lo hay).
    )                                                                              # Fin del log de entrada.

    guest = find_guest_for_magic(                                                 # Invoca el CRUD que hace la búsqueda robusta.
        db,                                                                        # Pasa la sesión de BD activa.
        payload.full_name,                                                         # Pasa el nombre completo del payload.
        payload.phone_last4,                                                       # Pasa los últimos 4 del teléfono del payload.
        (payload.email or ""),                                                     # Evita pasar "None" como texto.
    )                                                                              # Fin de la llamada al CRUD.

    # --- BLOQUE ÚNICO DE PERSISTENCIA: actualiza email/consent ANTES de enviar el correo ---
    if guest:                                                                      # Si hubo match de invitado...
        email_in = ((payload.email) or "").strip().lower()                         # Normaliza el email entrante a minúsculas.
        consent_in = bool(getattr(payload, "consent", False))                      # Normaliza el consentimiento a booleano.
        stored_email = (guest.email or "").strip().lower()                         # Obtiene el email guardado (o vacío) normalizado.
        updated = False                                                             # Flag para saber si hay cambios que persistir.

        if email_in and email_in != stored_email:                                  # Si hay email nuevo y distinto del guardado...
            guest.email = email_in                                                 # ...asigna el nuevo email al registro.
            updated = True                                                         # ...marca que hay cambios.

        if hasattr(guest, "consent") and getattr(guest, "consent", None) != consent_in:  # Si el modelo tiene 'consent' y cambia...
            guest.consent = consent_in                                             # ...actualiza el consentimiento.
            updated = True                                                         # ...marca que hay cambios.

        if updated:                                                                 # Solo si hubo cambios...
            try:                                                                    # Protege la transacción.
                db.add(guest)                                                       # Asegura que el objeto está en la sesión.
                db.commit()                                                         # Persiste los cambios en la base de datos.
                db.refresh(guest)                                                   # Refresca el objeto para lecturas consistentes.
                logger.info("RSVP/ACCESS → Datos actualizados (email/consent) guest_id={}", guest.id)  # Traza de éxito de actualización.
            except Exception as e:                                                  # En caso de error de DB...
                db.rollback()                                                       # Revierte la transacción.
                logger.exception("RSVP/ACCESS → Error actualizando email/consent guest_id={} : {}", guest.id, e)  # Log de error.

    elapsed = int((time.monotonic() - start_time) * 1000)                          # Calcula duración total de la búsqueda en ms.

    if guest:                                                                       # Si se encontró un invitado que hace match...
        _digits = "".join([c for c in (guest.phone or "") if c.isdigit()])         # Extrae dígitos del teléfono guardado en DB.
        g_last4 = _digits[-4:] if _digits else ""                                  # Obtiene los últimos 4 del teléfono guardado (si existe).
        _guest_masked = "<empty>" if not getattr(guest, "email", None) else (      # Enmascara el email de la DB (no exponer PII completa).
            (guest.email[:2] + "***@" + guest.email.split("@", 1)[1])              # Dos letras + *** + dominio si hay '@'.
            if "@" in guest.email else (guest.email[:2] + "***")                   # Dos letras + *** si no hay '@'.
        )                                                                           # Cierra construcción de email enmascarado.
        logger.info(                                                                # Log de hallazgo con datos mínimos y tiempo.
            "RSVP/ACCESS → Invitado encontrado | id={} | name='{}' | last4='{}' | email='{}' | lang_guest='{}' | t={}ms",
            getattr(guest, "id", None),                                             # ID del invitado en la DB (si existe).
            guest.full_name,                                                        # Nombre tal como está en la DB.
            g_last4,                                                                # Últimos 4 del teléfono de la DB.
            _guest_masked,                                                          # Email enmascarado del invitado en la DB.
            getattr(getattr(guest, "language", None), "value", getattr(guest, "language", None)),  # Idioma (Enum->value o str).
            elapsed,                                                                # Duración total de la búsqueda (ms).
        )                                                                           # Fin del log.
    else:                                                                           # Si no hubo match...
        logger.warning(                                                             # Log de advertencia con el contexto que no matcheó.
            "RSVP/ACCESS → SIN MATCH | name='{}' | last4='{}' | email='{}' | t={}ms",
            payload.full_name,                                                      # Nombre solicitado (tal cual llegó).
            payload.phone_last4,                                                    # Últimos 4 solicitados.
            _masked_email,                                                          # Email enmascarado solicitado.
            elapsed,                                                                # Duración de la búsqueda (ms).
        )                                                                           # Fin del log.

    generic = {                                                                     # Prepara respuesta genérica (no filtra existencia).
        "ok": True,                                                                 # Indica que la solicitud fue aceptada.
        "message": "If the data matched, you'll receive an email shortly",          # Mensaje neutro para evitar enumeración.
        "expires_in_sec": MAGIC_EXPIRE_MIN * 60,                                    # Incluye expiración en segundos para el cliente.
    }                                                                               # Fin del diccionario de respuesta.

    if not guest:                                                                   # Si no hubo match en la búsqueda...
       raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No se encontró una invitación con los datos proporcionados. Por favor, verifica la información."
    )                                                             # Devuelve la respuesta genérica 200 (no revela nada).

    # --- Envío conmutado según SEND_ACCESS_MODE (code|magic) ---
    to_email = (payload.email or "").strip()                                        # Normaliza destino tomando el email del payload.
    if not to_email:                                                                # Si no hay email destino...
        logger.info("RSVP/ACCESS → sin email en payload; no se envía correo (id={})", getattr(guest, "id", None))  # Log informativo.
        return generic                                                              # Devuelve respuesta genérica (anti-enumeración).

    # --- Generar y persistir token mágico SOLO cuando el modo es 'magic' ---
    if SEND_ACCESS_MODE == "magic":                                                 # Si el modo es 'magic'...
        token = auth.create_magic_token(guest_code=guest.guest_code, email=to_email)  # Crea token 'magic' (JWT corto) solo en modo magic.
        set_magic_link(db, guest, token, ttl_minutes=MAGIC_EXPIRE_MIN)              # Persiste el token para canjearlo luego.

    # --- Resolver idioma de forma consistente usando el cerebro i18n ---
    lang_from_guest = getattr(getattr(guest, "language", None), "value", getattr(guest, "language", None))  # Idioma de DB (Enum->value o str).
    accept_lang = request.headers.get("Accept-Language")                            # Lee encabezado 'Accept-Language' del cliente (si existe).
    resolved_lang = resolve_lang(                                                   # Llama al resolvedor centralizado de i18n.
        payload_lang=getattr(payload, "lang", None),                                # 1) Usa 'lang' canónico del payload (o None si no vino).
        guest_lang=lang_from_guest,                                                 # 2) Idioma preferido persistido en la DB (si existe).
        accept_language_header=accept_lang,                                         # 3) Header 'Accept-Language' del navegador/cliente (opcional).
        email=(payload.email or ""),                                                # 4) Heurística por TLD (.es/.ro) si aplica.
        default="es",                                                               # 5) Fallback consistente del proyecto (ES).
    )                                                                               # Fin de llamada al resolver.
    logger.info(                                                                     # Deja trazabilidad del idioma resuelto.
        "RSVP/ACCESS → Idioma resuelto email='{}' : '{}' (payload='{}', guest='{}')",
        _masked_email,                                                               # Email enmascarado del destinatario.
        resolved_lang,                                                               # Idioma final que se usará.
        getattr(payload, "lang", None),                                              # Idioma que llegó en payload (si alguno).
        lang_from_guest,                                                             # Idioma guardado en DB (si alguno).
    )                                                                                # Fin del log.

    # (solo para 'magic') construir la URL con el token
    if SEND_ACCESS_MODE == "magic":                                                 # Si el modo elegido es 'magic'...
        magic_url = f"{RSVP_URL}?token={token}"                                     # ...construye la URL con el token.

    if SEND_ACCESS_MODE == "code":                                                  # Si .env pide el flujo 7.2 (código por email)...
        try:                                                                        # Protege para no romper la respuesta aunque falle el correo.
            _ = mailer.send_guest_code_email(                                       # Llama al mailer que manda el guest_code.
                to_email=to_email,                                                  # Destinatario tomado del payload del formulario.
                guest_name=(guest.full_name or ""),                                 # Pasa el nombre crudo; el mailer lo escapará si es HTML.
                guest_code=guest.guest_code,                                        # Código único (se usará en la pantalla de login).
                language=resolved_lang                                              # Idioma i18n resuelto arriba.
            )                                                                       # Fin de llamada.
            logger.info("RSVP/CODE → guest_code enviado | id={} | code='{}'", getattr(guest, "id", None), guest.guest_code)  # Éxito.
        except Exception as e:                                                      # Si algo falla al enviar...
            logger.exception("RSVP/CODE → error enviando guest_code: {}", e)        # Log de excepción; respuesta seguirá neutra.
    else:                                                                           # Si el modo NO es 'code', usamos el flujo clásico 'magic'...
        try:                                                                        # Protege igualmente el envío.
            _ = mailer.send_magic_link_email(                                       # Mailer de Magic Link ya implementado.
                to_email=to_email,                                                  # Destinatario.
                language=resolved_lang,                                             # Idioma i18n resuelto.
                magic_url=magic_url                                                 # URL con token para el canje en /magic-login.
            )                                                                       # Fin de llamada.
            logger.info("RSVP/MAGIC → magic link enviado | id={}", getattr(guest, "id", None))  # Trazamos éxito sin exponer el token.
        except Exception as e:                                                      # Si falla...
            logger.exception("RSVP/MAGIC → error enviando magic link: {}", e)       # Registra la excepción; respuesta seguirá neutra.

    # --- Respuesta del endpoint (anti-enumeración, retrocompatibilidad) ---
    return generic                                                                  # Devuelve la misma respuesta tanto si hay match como si no.

# =================================================================================
# 🔓 NUEVO: MAGIC-LOGIN (canjea token mágico por access token)
# =================================================================================
@router.post("/magic-login", response_model=schemas.Token)                          # Declara la ruta POST /api/magic-login con schema de respuesta Token.
def magic_login(                                                                    # Define la función manejadora del canje de token mágico.
    payload: schemas.MagicLoginPayload,                                             # Payload Pydantic: 'token' (JWT tipo 'magic').
    db: Session = Depends(get_db),                                                  # Inyección de sesión de BD.
):                                                                                  # Cierra la firma.
    try:                                                                            # Intenta decodificar y validar el token 'magic'.
        auth.decode_magic_token(payload.token)                                      # Verifica firma, expiración y que el type sea 'magic'.
    except Exception:                                                               # Si la verificación falla (firma/exp/estructura)...
        raise HTTPException(                                                        # Lanza 401 Unauthorized.
            status_code=status.HTTP_401_UNAUTHORIZED,                               # Código 401.
            detail={"ok": False, "error": "invalid_token"},                         # Respuesta JSON mínima.
        )                                                                            # Fin de raise.

    guest = consume_magic_link(db, payload.token)                                   # Consume el token (marca usado) y obtiene el invitado.
    if not guest:                                                                   # Si no existe, ya fue usado o expiró...
        raise HTTPException(                                                        # Lanza 401 Unauthorized.
            status_code=status.HTTP_401_UNAUTHORIZED,                               # Código 401.
            detail={"ok": False, "error": "invalid_or_used_token"},                 # Mensaje JSON mínimo.
        )                                                                            # Fin de raise.

    access_token = auth.create_access_token(subject=guest.guest_code)               # Emite un access token normal (type='access').
    return {                                                                        # Construye respuesta estándar de login.
        "access_token": access_token,                                               # Token de sesión JWT.
        "token_type": "bearer",                                                     # Tipo de token (Bearer).
    }                                                                               # Fin del objeto de respuesta.
