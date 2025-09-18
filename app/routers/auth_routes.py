# app/routers/auth_routes.py  # Ruta y nombre del archivo del router de autenticación.  # Indica el archivo objetivo.

# =================================================================================  # Separador visual para la cabecera del módulo.
# 🔑 ROUTER DE AUTENTICACIÓN Y RECUPERACIÓN DE CÓDIGOS                              # Describe el propósito del módulo.
# ---------------------------------------------------------------------------------  # Línea divisoria.
# - Login de invitados mediante guest_code + (email o teléfono).                    # Lista funcionalidades actuales.
# - Recuperación de código con respuesta neutra, envío de email si hay match.      # Explica recover-code.
# - Aplica rate-limit por IP en /api/login y /api/recover-code.                     # Indica rate limiting existente.
# - 🔗 NUEVO: request-access (Magic Link o Código) y magic-login.                   # Anuncia endpoints nuevos compatibles con 7.2.
# =================================================================================  # Fin de cabecera.

from fastapi import APIRouter, Depends, HTTPException, Request, status  # Importa utilidades de FastAPI (router, dependencias, excepciones y estados).
from sqlalchemy.orm import Session                                       # Importa el tipo de sesión de SQLAlchemy para operaciones con BD.
import time                                                              # Importa time para medir duración de operaciones (logs de búsqueda).
from loguru import logger                                                # Importa logger de Loguru para trazas claras.
import os                                                                # Importa os para leer variables de entorno (.env).
import html                                                                # para html.escape en el envío del guest_name



# Importaciones internas del proyecto
from app import models, schemas, auth, mailer                            # Importa módulos internos: modelos, esquemas Pydantic, auth (tokens), y mailer.
from app.db import SessionLocal                                          # Importa fábrica de sesiones de BD para inyección manual (get_db).
from app.rate_limit import is_allowed, get_limits_from_env               # Importa helpers para rate limit configurable por entorno.
from app.crud.guests_crud import (                                       # Importa funciones CRUD específicas del flujo Magic Link.
    find_guest_for_magic,                                                # Búsqueda robusta por nombre + últimos 4 del teléfono + email.
    set_magic_link,                                                      # Persistencia de token mágico y expiración.
    consume_magic_link,                                                  # Consumo atómico del token mágico (un uso).
)                                                                        # Cierra importación múltiple.

router = APIRouter(                                                      # Crea un router de FastAPI para agrupar rutas relacionadas.
    prefix="/api",                                                       # Prefijo común para todas las rutas de este módulo.
    tags=["auth"],                                                       # Tag para documentación OpenAPI (agrupa endpoints).
)                                                                        # Cierra la construcción del router.

# --- Dependencia de BD (mantiene compatibilidad con tu proyecto actual) ---
def get_db():                                                            # Define la dependencia que provee una sesión de BD por request.
    db = SessionLocal()                                                  # Crea una nueva sesión usando la fábrica SessionLocal.
    try:                                                                 # Abre un bloque try/finally para garantizar el cierre.
        yield db                                                         # Cede la sesión a la ruta que la consuma.
    finally:                                                             # Al finalizar el manejo de la request...
        db.close()                                                       # ...cierra la sesión para evitar fugas de conexiones.

# --- Configuración de rate limit desde .env (con defaults sensatos) ---
LOGIN_MAX, LOGIN_WINDOW = get_limits_from_env("LOGIN_RL", default_max=5, default_window=60)       # Lee límites para login (intentos/ventana).
RECOVER_MAX, RECOVER_WINDOW = get_limits_from_env("RECOVER_RL", default_max=3, default_window=120)  # Lee límites para recover-code.
REQUEST_MAX, REQUEST_WINDOW = get_limits_from_env("REQUEST_RL", default_max=RECOVER_MAX, default_window=RECOVER_WINDOW)  # Reusa defaults para request-access.

# --- Configuración de URLs y expiraciones desde entorno ---
RSVP_URL = os.getenv("RSVP_URL", "https://rsvp.suarezsiicawedding.com")   # URL pública del formulario (se usa en el Magic Link).
MAGIC_EXPIRE_MIN = int(os.getenv("MAGIC_LINK_EXPIRE_MINUTES", "15"))      # Minutos de expiración del Magic Link (por defecto 15).
ACCESS_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))   # Minutos de expiración del access token (para el login clásico/mágico).
SEND_ACCESS_MODE = os.getenv("SEND_ACCESS_MODE", "code").strip().lower()  # Modo de acceso desde .env: 'code' (7.2) o 'magic' (clásico).

# =================================================================================  # Separador para helpers.
# ✅ Helper para obtener la IP real del cliente (proxy/CDN)                          # Explica la finalidad del helper.
# =================================================================================  # Fin de separador.
def _client_ip(request: Request) -> str:                                  # Define helper para extraer IP del cliente (considerando proxies).
    """
    Extrae la IP real del cliente, considerando la cabecera X-Forwarded-For
    comúnmente usada por proxies, balanceadores de carga y CDNs.          # Docstring: qué hace y por qué.
    """                                                                   # Fin de docstring.
    xff = request.headers.get("x-forwarded-for")                          # Lee la cabecera X-Forwarded-For si existe.
    if xff:                                                               # Si la cabecera está presente...
        return xff.split(",")[0].strip()                                  # ...toma la primera IP (cliente original) y la limpia.
    return request.client.host or "unknown"                               # Si no hay XFF, devuelve la IP de la conexión o 'unknown'.

# =================================================================================  # Separador para endpoint de login.
# 🚪 ENDPOINT DE LOGIN (clásico)                                                     # Título descriptivo del endpoint.
# =================================================================================  # Fin de separador.
@router.post("/login", response_model=schemas.Token)                       # Declara la ruta POST /api/login con respuesta tipada (Token).
def login_for_access_token(                                                # Define la función manejadora del endpoint de login.
    form_data: schemas.LoginRequest,                                       # Payload Pydantic: guest_code + (email o teléfono).
    request: Request,                                                      # Objeto Request para leer headers/IP.
    db: Session = Depends(get_db),                                         # Inyección de sesión de base de datos.
):                                                                         # Cierra la firma de la función.
    """
    Login flexible para invitados:
    - Siempre requiere guest_code.
    - Debe coincidir email o teléfono (mínimo uno).
    - Si pasa la validación → devuelve un token JWT.
    - Aplica rate-limit por IP para mitigar fuerza bruta.                 # Docstring: describe la lógica del endpoint.
    """                                                                   # Fin de docstring.
    client_ip = _client_ip(request)                                        # Obtiene la IP real del cliente (considerando XFF).
    rl_key = f"login:{client_ip}"                                          # Construye clave de rate-limit por IP para este endpoint.
    if not is_allowed(rl_key, LOGIN_MAX, LOGIN_WINDOW):                    # Verifica si se excedió el límite de intentos.
        raise HTTPException(                                               # Lanza una excepción HTTP 429 si está rate-limited.
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,                 # Código 429 Too Many Requests.
            detail="Too many attempts. Please try again later.",           # Mensaje genérico (no revela lógica interna).
            headers={"Retry-After": str(LOGIN_WINDOW)},                    # Header sugerido para reintento.
        )                                                                  # Fin de raise.

    guest = db.query(models.Guest).filter(models.Guest.guest_code == form_data.guest_code).first()  # Busca invitado por guest_code exacto.

    if not guest or not (                                                  # Si no existe invitado o no coincide contacto...
        (form_data.email and guest.email == form_data.email) or            # ...por email exacto (normalizado por schema)...
        (form_data.phone and guest.phone == form_data.phone)               # ...o por teléfono exacto (normalizado por schema)...
    ):                                                                     # Fin de condición de validación.
        logger.info(f"Login failed for code='{form_data.guest_code}' ip={client_ip}")  # Loguea intento fallido (auditoría).
        raise HTTPException(                                               # Lanza 401 Unauthorized por credenciales inválidas.
            status_code=status.HTTP_401_UNAUTHORIZED,                      # Código 401.
            detail="Código de invitado, email o teléfono incorrectos",     # Mensaje neutro (no revela cuál campo falló).
        )                                                                  # Fin de raise.

    access_token = auth.create_access_token(subject=guest.guest_code)      # Genera access token (JWT) con subject=guest_code.
    logger.info(f"Login success for code='{guest.guest_code}' ip={client_ip}")  # Loguea acceso exitoso con guest_code e IP.
    return {"access_token": access_token, "token_type": "bearer"}          # Devuelve el token y su tipo (Bearer) según schema.

# =================================================================================  # Separador para endpoint de recuperación.
# 📩 ENDPOINT DE RECUPERACIÓN DE CÓDIGO (respuesta neutra)                           # Título explicativo del endpoint.
# =================================================================================  # Fin de separador.
@router.post("/recover-code")                                              # Declara la ruta POST /api/recover-code.
def recover_code(                                                          # Define la función manejadora del endpoint de recuperación.
    recovery_data: schemas.RecoveryRequest,                                # Payload Pydantic: email o phone (mínimo uno).
    request: Request,                                                      # Objeto Request (para IP/rate-limit).
    db: Session = Depends(get_db),                                         # Inyección de sesión de BD.
):                                                                         # Cierra la firma.
    """
    Permite a un invitado recuperar su código de acceso si lo olvidó.
    - Acepta email o teléfono (mínimo uno).
    - Aplica rate-limit por IP.
    - Respuesta SIEMPRE genérica (200) para no revelar existencia.
    - Si hay match con un invitado con email → envía correo con el código.  # Docstring que resume el comportamiento.
    """                                                                     # Fin de docstring.
    client_ip = _client_ip(request)                                        # Obtiene IP del cliente.
    rl_key = f"recover:{client_ip}"                                        # Clave de rate-limit para este endpoint.
    if not is_allowed(rl_key, RECOVER_MAX, RECOVER_WINDOW):                # Verifica si excedió el límite.
        logger.warning(f"Recover rate-limited ip={client_ip}")             # Loguea que fue rate-limited (auditoría).
        return {"message": "Demasiados intentos. Intenta más tarde."}      # Respuesta 200 neutra para no facilitar enumeración.

    if not recovery_data.email and not recovery_data.phone:                # Valida que haya al menos un contacto.
        logger.info(f"Recover bad request ip={client_ip} (no email/phone)")# Loguea mala petición (sin datos).
        raise HTTPException(                                               # Lanza 400 por solicitud inválida.
            status_code=status.HTTP_400_BAD_REQUEST,                       # Código 400.
            detail="Debes proporcionar al menos un email o teléfono"       # Mensaje claro para el cliente.
        )                                                                  # Fin de raise.

    guest = None                                                           # Inicializa variable de invitado.
    if recovery_data.email:                                                # Si proporcionó email...
        guest = db.query(models.Guest).filter(models.Guest.email == recovery_data.email).first()  # Busca por email exacto.
    if not guest and recovery_data.phone:                                  # Si no encontró por email y hay teléfono...
        guest = db.query(models.Guest).filter(models.Guest.phone == recovery_data.phone).first()  # Busca por teléfono exacto.

    if guest and guest.email:                                              # Si hay match y el invitado tiene email...
        lang = (guest.language.value if getattr(guest, "language", None) else "es") or "es"  # Determina idioma con fallback preferente a 'es'.
        subject = {                                                        # Tabla de subjects por idioma.
            "es": "Tu código de invitación",
            "ro": "Codul tău de invitație",
            "en": "Your invitation code",
        }.get(lang, "Your invitation code")                                # Fallback a EN si el idioma no está contemplado.

        body = {                                                           # Tabla de cuerpos de correo por idioma.
            "es": f"Hola {guest.full_name},\n\nTu código de invitación es: {guest.guest_code}\n\nSi no solicitaste este mensaje, puedes ignorarlo.\n\nDaniela & Cristian",
            "ro": f"Bună {guest.full_name},\n\nCodul tău de invitație este: {guest.guest_code}\n\nDacă nu ai solicitat acest mesaj, îl poți ignora.\n\nDaniela & Cristian",
            "en": f"Hi {guest.full_name},\n\nYour invitation code is: {guest.guest_code}\n\nIf you didn’t request this, you can ignore this email.\n\nDaniela & Cristian",
        }.get(lang, f"Hi {guest.full_name},\n\nYour invitation code is: {guest.guest_code}\n\nBest,\nDaniela & Cristian")  # Fallback si idioma desconocido.

        try:                                                               # Protege el envío con try/except para capturar errores.
            sent = mailer.send_email(to_email=guest.email, subject=subject, body=body)  # Envío texto plano (respeta DRY_RUN en mailer).
            if sent:                                                       # Si el envío reporta éxito...
                logger.info(f"Recover mail sent to={guest.email} ip={client_ip}")  # Loguea éxito de envío.
            else:                                                          # Si el envío reporta fallo...
                logger.error(f"Recover mail FAILED to={guest.email} ip={client_ip}")  # Loguea fallo de envío.
        except Exception as e:                                             # Si hubo excepción inesperada durante el envío...
            logger.exception(f"Unhandled error sending recover email to={guest.email}: {e}")  # Log detallado de la excepción.
    else:                                                                  # Si no hay match o el invitado no tiene email...
        logger.info(f"Recover requested ip={client_ip} (no match or no email)")  # Log informativo (respuesta seguirá neutra).

    return {"message": "Si tu contacto está en nuestra lista de invitados, recibirás un mensaje en breve."}  # Respuesta neutra 200.

# =================================================================================  # Separador para el endpoint de Request Access.
# ✉️ NUEVO: REQUEST-ACCESS (solicitar acceso: Magic Link o Código según .env)        # Título descriptivo.
# =================================================================================  # Fin de separador.
@router.post("/request-access")                                            # Declara la ruta POST /api/request-access.
def request_access(                                                        # Define la función manejadora del endpoint.
    payload: schemas.RequestAccessPayload,                                 # Payload Pydantic: full_name, phone_last4, email, consent, preferred_language.
    request: Request,                                                      # Objeto Request (para IP y rate limit).
    db: Session = Depends(get_db),                                         # Inyección de sesión de BD.
):                                                                         # Cierra la firma.
    # --- Rate limiting ---
    client_ip = _client_ip(request)                                        # Obtiene IP real del cliente.
    rl_key = f"request_access:{client_ip}"                                 # Construye clave para rate-limit por IP.
    if not is_allowed(rl_key, REQUEST_MAX, REQUEST_WINDOW):                # Verifica si excedió su cuota en la ventana.
        raise HTTPException(                                               # Lanza 429 Too Many Requests si aplica.
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,                 # Código 429.
            detail={"ok": False, "error": "rate_limited"},                 # Detalle mínimo (no revela existencia de datos).
            headers={"Retry-After": str(REQUEST_WINDOW)},                  # Indica en segundos cuándo reintentar.
        )                                                                  # Fin del raise.

    # --- Matching invitado (respuesta SIEMPRE genérica, con logs extendidos) ---
    start_time = time.monotonic()                                          # Inicia cronómetro para medir duración de la búsqueda.
    _masked_email = "<empty>" if not payload.email else (                  # Prepara versión enmascarada del email para logs.
        (payload.email[:2] + "***@" + payload.email.split("@", 1)[1])      # Si el email tiene dominio, muestra 2 letras + *** + dominio.
        if "@" in payload.email else (payload.email[:2] + "***")           # Si no hay '@', muestra solo 2 letras + ***.
    )                                                                       # Cierra construcción del email enmascarado.

    logger.info(                                                            # Log de entrada con contexto de la búsqueda.
        "RSVP/ACCESS → Buscando invitado | name='%s' | last4='%s' | email='%s' | lang_pref='%s'",  # Mensaje parametrizado.
        payload.full_name,                                                 # Nombre recibido tal cual en el payload.
        payload.phone_last4,                                               # Últimos 4 dígitos del teléfono recibidos.
        _masked_email,                                                     # Email enmascarado (evita PII completa en logs).
        getattr(payload, "preferred_language", None),                      # Idioma preferido indicado por el cliente (si lo hay).
    )                                                                       # Fin del log de entrada.

    guest = find_guest_for_magic(                                          # Invoca el CRUD que hace la búsqueda robusta.
        db,                                                                # Pasa la sesión de BD activa.
        payload.full_name,                                                 # Pasa el nombre completo del payload.
        payload.phone_last4,                                               # Pasa los últimos 4 del teléfono del payload.
        str(payload.email),                                                # Pasa el email destino como cadena.
    )                                                                       # Fin de la llamada al CRUD.

    elapsed = int((time.monotonic() - start_time) * 1000)                  # Calcula duración total de la búsqueda en milisegundos.

    if guest:                                                              # Si se encontró un invitado que hace match...
        _digits = "".join([c for c in (guest.phone or "") if c.isdigit()]) # Extrae dígitos del teléfono guardado en DB.
        g_last4 = _digits[-4:] if _digits else ""                          # Obtiene los últimos 4 del teléfono guardado (si existe).
        _guest_masked = "<empty>" if not getattr(guest, "email", None) else (  # Enmascara el email de la DB para no exponer PII completa.
            (guest.email[:2] + "***@" + guest.email.split("@", 1)[1])      # Si tiene dominio, muestra 2 letras + *** + dominio.
            if "@" in guest.email else (guest.email[:2] + "***")           # Si no hay '@', muestra solo 2 letras + ***.
        )                                                                   # Cierra construcción de email enmascarado.
        logger.info(                                                        # Log de hallazgo con datos mínimos y tiempo.
            "RSVP/ACCESS → Invitado encontrado | id=%s | name='%s' | last4='%s' | email='%s' | lang_guest='%s' | t=%sms",
            getattr(guest, "id", None),                                     # ID del invitado en la DB (si existe).
            guest.full_name,                                                # Nombre tal como está en la DB.
            g_last4,                                                        # Últimos 4 del teléfono de la DB (verificación cruzada).
            _guest_masked,                                                  # Email enmascarado del invitado en la DB.
            getattr(getattr(guest, "language", None), "value", getattr(guest, "language", None)),  # Idioma del invitado (Enum->value o str).
            elapsed,                                                        # Duración total de la búsqueda (ms).
        )                                                                   # Fin del log de hallazgo.
    else:                                                                  # Si no hubo match...
        logger.warning(                                                     # Log de advertencia con el contexto que no matcheó.
            "RSVP/ACCESS → SIN MATCH | name='%s' | last4='%s' | email='%s' | t=%sms",
            payload.full_name,                                              # Nombre solicitado (tal cual llegó).
            payload.phone_last4,                                            # Últimos 4 solicitados.
            _masked_email,                                                  # Email enmascarado solicitado.
            elapsed,                                                        # Duración de la búsqueda (ms).
        )                                                                   # Fin del log de sin match.

    generic = {                                                            # Prepara respuesta genérica (no filtra existencia).
        "ok": True,                                                        # Indica que la solicitud fue aceptada.
        "message": "If the data matched, you'll receive an email shortly",                      # Mensaje neutro para evitar enumeración.
        "expires_in_sec": MAGIC_EXPIRE_MIN * 60,                           # Incluye expiración en segundos para el cliente.
    }                                                                      # Fin del diccionario de respuesta.

    if not guest:                                                          # Si no hubo match en la búsqueda...
        return generic                                                     # Devuelve la respuesta genérica 200 (no revela nada).
    
    # --- Generar y persistir token mágico SOLO cuando el modo es 'magic' ---
    if SEND_ACCESS_MODE == "magic":
        token = auth.create_magic_token(guest_code=guest.guest_code, email=str(payload.email))  # Crea token 'magic' (JWT corto) solo en modo magic.
        set_magic_link(db, guest, token, ttl_minutes=MAGIC_EXPIRE_MIN)  # Persiste el token para poder canjearlo luego.

    # --- Preparativos comunes al envío ---
    resolved_lang = (
        payload.preferred_language
        or (getattr(guest, "language", None) and guest.language.value)
        or "en"
    )

    # (solo para 'magic') construir la URL con el token
    if SEND_ACCESS_MODE == "magic":
        magic_url = f"{RSVP_URL}?token={token}"



    logger.info(                                                           # Deja trazabilidad del idioma final que usaremos.
        "RSVP/ACCESS → Idioma resuelto email='%s': '%s' (payload='%s', guest='%s')",
        _masked_email,                                                     # Email destino enmascarado.
        resolved_lang,                                                     # Idioma que se usará realmente.
        payload.preferred_language,                                        # Idioma que venía del cliente (si envió).
        getattr(getattr(guest, 'language', None), 'value', getattr(guest, 'language', None)),  # Idioma guardado en DB (Enum->value o str).
    )                                                                      # Fin del log.

    # --- Envío conmutado según SEND_ACCESS_MODE (code|magic) ---
    if SEND_ACCESS_MODE == "code":                                         # Si .env pide el flujo 7.2 (código por email)...
        try:                                                               # Protegemos para no romper la respuesta aunque falle el correo.
            _ = mailer.send_guest_code_email(                              # Llamamos al nuevo mailer que manda el guest_code.
                to_email=str(payload.email),                               # Destinatario tomado del payload del formulario.
                guest_name=html.escape(guest.full_name or ""),                                # Nombre del invitado para personalizar saludo.
                guest_code=guest.guest_code,                               # Código único (se usará en la pantalla de login).
                language=resolved_lang                                     # Idioma i18n resuelto arriba.
            )                                                              # Fin de llamada.
            logger.info("RSVP/CODE → guest_code enviado | id=%s | code='%s'", getattr(guest, "id", None), guest.guest_code)  # Traza de éxito.
        except Exception as e:                                             # Si algo falla al enviar...
            logger.exception("RSVP/CODE → error enviando guest_code: %s", e)  # Registramos la excepción; respuesta seguirá neutra.
    else:                                                                  # Si el modo NO es 'code', usamos el flujo clásico 'magic'...
        try:                                                               # Protegemos igualmente el envío.
            _ = mailer.send_magic_link_email(                              # Mailer de Magic Link que ya tenías implementado.
                to_email=str(payload.email),                               # Destinatario.
                language=resolved_lang,                                    # Idioma i18n resuelto.
                magic_url=magic_url                                        # URL con token para el canje en /magic-login.
            )                                                              # Fin de llamada.
            logger.info("RSVP/MAGIC → magic link enviado | id=%s", getattr(guest, "id", None))  # Trazamos éxito sin exponer el token.
        except Exception as e:                                             # Si falla...
            logger.exception("RSVP/MAGIC → error enviando magic link: %s", e)  # Registramos excepción; respuesta seguirá neutra.

    # --- Respuesta del endpoint (anti-enumeración, retrocompatibilidad) ---
    return generic                                                         # Devolvemos la misma respuesta tanto si hay match como si no.

# =================================================================================  # Separador para endpoint de canje de token mágico.
# 🔓 NUEVO: MAGIC-LOGIN (canjea token mágico por access token)                        # Título descriptivo.
# =================================================================================  # Fin de separador.
@router.post("/magic-login", response_model=schemas.Token)                 # Declara la ruta POST /api/magic-login con schema de respuesta Token.
def magic_login(                                                           # Define la función manejadora del canje de token mágico.
    payload: schemas.MagicLoginPayload,                                    # Payload Pydantic: 'token' (JWT tipo 'magic').
    db: Session = Depends(get_db),                                         # Inyección de sesión de BD.
):                                                                         # Cierra la firma.
    try:                                                                   # Intenta decodificar y validar el token 'magic'.
        auth.decode_magic_token(payload.token)                             # Verifica firma, expiración y que el type sea 'magic'.
    except Exception:                                                      # Si la verificación falla (firma/exp/estructura)...
        raise HTTPException(                                               # Lanza 401 Unauthorized.
            status_code=status.HTTP_401_UNAUTHORIZED,                      # Código 401.
            detail={"ok": False, "error": "invalid_token"},                # Respuesta JSON mínima.
        )                                                                  # Fin de raise.

    guest = consume_magic_link(db, payload.token)                          # Consume el token (marca usado) y obtiene el invitado.
    if not guest:                                                          # Si no existe, ya fue usado o expiró...
        raise HTTPException(                                               # Lanza 401 Unauthorized.
            status_code=status.HTTP_401_UNAUTHORIZED,                      # Código 401.
            detail={"ok": False, "error": "invalid_or_used_token"},        # Mensaje JSON mínimo.
        )                                                                  # Fin de raise.

    access_token = auth.create_access_token(subject=guest.guest_code)      # Emite un access token normal (type='access') con subject=guest_code.
    return {                                                               # Construye respuesta estándar de login.
        "access_token": access_token,                                      # Token de sesión JWT.
        "token_type": "bearer",                                            # Tipo de token (Bearer).
        # "expires_in_sec": ACCESS_EXPIRE_MIN * 60,                        # (Opcional) Incluye expiración si tu schemas.Token lo contempla.
    }                                                                       # Fin del objeto de respuesta.
