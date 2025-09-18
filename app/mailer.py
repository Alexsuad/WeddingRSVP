# app/mailer.py  # Ruta y nombre del archivo.                                               # Indica el nombre del módulo y su ubicación.

# =================================================================================
# 📧 MÓDULO DE ENVÍO DE CORREOS (con soporte HTML)                                   # Describe propósito del módulo.
# ---------------------------------------------------------------------------------
# Centraliza envío por SendGrid, plantillas (texto y HTML), formato de fechas        # Explica funciones principales.
# y alertas. Incluye helpers para recordatorios, recuperación y Magic Link.          # Indica funcionalidades cubiertas.
# =================================================================================

# 🐍 Importaciones
import os                                                                              # Acceso a variables de entorno (.env).
from enum import Enum                                                                  # Soporte para tipos Enum (idioma/segmento).
from datetime import datetime                                                          # Tipo de fecha para formateo de deadline.
import json                                                                            # Serialización JSON para payloads/leer plantillas.
import requests                                                                        # HTTP simple para webhook opcional.
from functools import lru_cache                                                        # Cache de lectura i18n para evitar I/O repetido.
from loguru import logger                                                              # Logger estructurado para trazas legibles.
from sendgrid import SendGridAPIClient                                                 # Cliente oficial de SendGrid para envío de correos.
from sendgrid.helpers.mail import Mail, From                                           # Clases para construir correos y remitente con nombre.
from pathlib import Path                                                               # Manejo de rutas de archivos de forma robusta.

# =================================================================================
# ✅ Configuración unificada al inicio del archivo.                                     # Sección de configuración.
# ---------------------------------------------------------------------------------
# Se centraliza la lectura de variables de entorno y se valida credenciales            # Razón del bloque.
# solo si DRY_RUN=0 (evita fallos en dev/CI).                                          # Comportamiento en pruebas/producción.
# =================================================================================
SUPPORTED_LANGS = ("en", "es", "ro")                                                  # Lista centralizada de idiomas soportados.
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"                                            # Activa simulación por defecto (seguro en dev/CI).
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")                                  # Clave de SendGrid (puede faltar en DRY_RUN).
FROM_EMAIL = os.getenv("EMAIL_FROM", "")                                              # Remitente del correo (puede faltar en DRY_RUN).
RSVP_URL = os.getenv("RSVP_URL", "")                                                  # URL pública del formulario RSVP (opcional en correos).
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Daniela & Cristian")             # Nombre visible del remitente.
TEMPLATES_DIR = (Path(__file__).parent / "templates" / "emails").resolve()            # Ruta a plantillas relativa a este archivo.
PUBLIC_LOGIN_URL = os.getenv("PUBLIC_LOGIN_URL", "").strip()                            # Lee la URL pública de la página de Login desde .env; cadena vacía si no existe.


# Valida configuración crítica solo si NO estamos en modo simulación.                 # Validación condicional.
if not DRY_RUN:                                                                       # Si se quiere envío real...
    if not SENDGRID_API_KEY:                                                          # Verifica existencia API Key.
        raise RuntimeError("Falta SENDGRID_API_KEY para envíos reales.")              # Falla temprano con mensaje claro.
    if not FROM_EMAIL:                                                                # Verifica remitente por defecto.
        raise RuntimeError("Falta EMAIL_FROM para envíos reales.")                    # Falla temprano con mensaje claro.

# =================================================================================
# 📢 Webhook de alertas (opcional)                                                     # Sección de webhook opcional.
# =================================================================================
def send_alert_webhook(title: str, message: str) -> None:                             # Función para notificar errores por webhook.
    """Envía alerta a webhook si ALERT_WEBHOOK_URL está definido; silencioso si no."""# Docstring descriptivo.
    url = os.getenv("ALERT_WEBHOOK_URL")                                              # Lee la URL del webhook desde el entorno.
    if not url:                                                                       # Si no hay URL configurada...
        return                                                                        # No hace nada (opcionalidad real).
    try:                                                                              # Intenta envío del webhook.
        payload = {"text": f"{title}\n{message}"}                                     # Construye payload simple (Slack/Teams compatible).
        headers = {"Content-Type": "application/json"}                                # Define cabeceras JSON.
        requests.post(url, data=json.dumps(payload), headers=headers, timeout=5)      # Envía POST con timeout de 5s.
    except Exception as e:                                                            # Captura cualquier error.
        logger.error(f"No se pudo notificar alerta por webhook: {e}")                # Loguea el error.

# =================================================================================
# 🗓️ Internacionalización de fechas (sin depender del locale del sistema)             # Sección i18n fechas.
# =================================================================================
_MONTHS_ES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]  # Meses ES.
_MONTHS_RO = ["ianuarie","februarie","martie","aprilie","mai","iunie","iulie","august","septembrie","octombrie","noiembrie","decembrie"]  # Meses RO.
_MONTHS_EN = ["January","February","March","April","May","June","July","August","September","October","November","December"]   # Meses EN.

def format_deadline(deadline_dt: datetime, lang_code: str) -> str:                    # Función para formatear fecha límite por idioma.
    """Devuelve la fecha límite en texto legible según idioma."""                     # Docstring claro.
    m = deadline_dt.month - 1                                                         # Índice de mes (base 0).
    d = deadline_dt.day                                                               # Día del mes.
    y = deadline_dt.year                                                              # Año numérico.
    if lang_code == "es":                                                             # Caso español...
        return f"{d} de {_MONTHS_ES[m]} de {y}"                                       # Ejemplo: '12 de mayo de 2026'.
    if lang_code == "ro":                                                             # Caso rumano...
        return f"{d} {_MONTHS_RO[m]} {y}"                                            # Ejemplo: '12 mai 2026'.
    return f"{_MONTHS_EN[m]} {d}, {y}"                                                # Por defecto inglés: 'May 12, 2026'.

# =================================================================================
# 📨 Asuntos por tipo de correo e idioma (i18n)                                        # Sección de subjects.
# =================================================================================
SUBJECTS = {                                                                          # Diccionario de asuntos por tipo de correo.
    "reminder": {                                                                     # Asuntos para recordatorios RSVP.
        "es": "Recordatorio: Confirma tu asistencia a nuestra boda",                  # Español.
        "ro": "Memento: Confirmă-ți prezența la nunta noastră",                       # Rumano.
        "en": "Reminder: Please RSVP for our wedding",                                # Inglés.
    },
    "recovery": {                                                                     # Asuntos para recuperación de código.
        "es": "Recuperación de código de invitado",                                   # Español.
        "ro": "Recuperare cod invitat",                                               # Rumano.
        "en": "Guest code recovery",                                                  # Inglés.
    },
}                                                                                     # Cierra SUBJECTS base.

SUBJECTS.setdefault("magic_link", {                                                   # Asegura clave para enlace mágico.
    "es": "Tu enlace mágico para confirmar asistencia",                               # Asunto en español.
    "ro": "Linkul tău magic pentru confirmare",                                       # Asunto en rumano.
    "en": "Your magic link to confirm attendance",                                    # Asunto en inglés.
})                                                                                    # Cierre setdefault.

# =================================================================================
# 🧾 Plantillas de texto plano (i18n)                                                  # Sección de plantillas de texto.
# =================================================================================
TEMPLATES = {                                                                         # Diccionario de plantillas por idioma.
    "es": {                                                                           # Español.
        "reminder_both": (                                                            # Recordatorio ceremonia + recepción.
            "Hola {name},\n\n"
            "Este es un amable recordatorio para que confirmes tu asistencia a nuestra ceremonia y recepción.\n"
            "La fecha límite para confirmar es el {deadline}.\n\n"
            "{cta}\n\n"
            "¡Esperamos verte allí!\n\n"
            "Un abrazo,\nDaniela & Cristian"
        ),
        "reminder_reception": (                                                       # Recordatorio solo recepción.
            "Hola {name},\n\n"
            "Este es un amable recordatorio para que confirmes tu asistencia a nuestra recepción.\n"
            "La fecha límite para confirmar es el {deadline}.\n\n"
            "{cta}\n\n"
            "¡Nos encantaría celebrar contigo!\n\n"
            "Un abrazo,\nDaniela & Cristian"
        ),
        "recovery": (                                                                 # Recuperación de código.
            "Hola {name},\n\n"
            "Has solicitado recuperar tu código de invitado.\n"
            "Tu código es: {guest_code}\n\n"
            "Puedes usarlo junto con tu email o teléfono para iniciar sesión en el formulario.\n"
            "{cta}\n\n"
            "Si no solicitaste este mensaje, puedes ignorarlo.\n\n"
            "Un abrazo,\nDaniela & Cristian"
        ),
        "cta": "👉 Confirma aquí: {url}",                                             # CTA de texto con URL.
    },
    "ro": {                                                                           # Rumano (completo).
        "reminder_both": (
            "Bună {name},\n\n"
            "Acesta este un memento prietenos pentru a confirma participarea la ceremonia și recepție.\n"
            "Data limită pentru confirmare este {deadline}.\n\n"
            "{cta}\n\n"
            "Sperăm să te vedem acolo!\n\n"
            "Cu drag,\nDaniela & Cristian"
        ),
        "reminder_reception": (
            "Bună {name},\n\n"
            "Acesta este un memento prietenos pentru a confirma participarea la recepția noastră.\n"
            "Data limită pentru confirmare este {deadline}.\n\n"
            "{cta}\n\n"
            "Ne-ar plăcea să sărbătorim cu tine!\n\n"
            "Cu drag,\nDaniela & Cristian"
        ),
        "recovery": (
            "Bună {name},\n\n"
            "Ai solicitat recuperarea codului tău de invitat.\n"
            "Codul tău este: {guest_code}\n\n"
            "Îl poți folosi împreună cu emailul sau telefonul pentru autentificare în formular.\n"
            "{cta}\n\n"
            "Dacă nu ai solicitat acest mesaj, îl poți ignora.\n\n"
            "Cu drag,\nDaniela & Cristian"
        ),
        "cta": "👉 Confirmă aici: {url}",                                             # CTA de texto con URL.
    },
    "en": {                                                                           # Inglés (completo).
        "reminder_both": (
            "Hi {name},\n\n"
            "This is a friendly reminder to confirm your attendance for our ceremony and reception.\n"
            "The deadline to RSVP is {deadline}.\n\n"
            "{cta}\n\n"
            "We hope to see you there!\n\n"
            "Best,\nDaniela & Cristian"
        ),
        "reminder_reception": (
            "Hi {name},\n\n"
            "This is a friendly reminder to confirm your attendance for our reception.\n"
            "The deadline to RSVP is {deadline}.\n\n"
            "{cta}\n\n"
            "We would love to celebrate with you!\n\n"
            "Best,\nDaniela & Cristian"
        ),
        "recovery": (
            "Hi {name},\n\n"
            "You requested to recover your guest code.\n"
            "Your code is: {guest_code}\n\n"
            "Use it along with your email or phone to log in to the form.\n"
            "{cta}\n\n"
            "If you did not request this, you can ignore this message.\n\n"
            "Best,\nDaniela & Cristian"
        ),
        "cta": "👉 Confirm here: {url}",                                              # CTA de texto con URL.
    },
}                                                                                     # Cierra TEMPLATES.

# =================================================================================
# 🌐 Plantillas HTML (i18n con tolerancia de nombres)                                  # Sección de HTML y JSON i18n.
# =================================================================================
LANG_CONTENT_FILES = {                                                                # Mapa idioma → lista de archivos JSON candidatos.
    "en": ["wedding_en.json", "email_en.json"],                                       # Prioriza wedding_*, luego email_* para EN.
    "es": ["wedding_es.json", "email_es.json"],                                       # Prioriza wedding_*, luego email_* para ES.
    "ro": ["wedding_ro.json", "email_ro.json"],                                       # Prioriza wedding_*, luego email_* para RO.
}                                                                                     # Cierra mapa.

@lru_cache(maxsize=8)                                                                 # Cachea la lectura por idioma (reduce I/O).
def _load_language_content(lang_code: str) -> dict:                                   # Carga JSON por idioma con fallback.
    """
    Carga el JSON (title, message, cta_label, footer_text) según idioma,
    probando múltiples nombres; si ninguno existe/parsea, retorna fallback seguro.
    """                                                                               # Docstring de función.
    code = lang_code if lang_code in LANG_CONTENT_FILES else "en"                     # Normaliza idioma a soportado o EN.
    for filename in LANG_CONTENT_FILES[code]:                                         # Itera por nombres candidatos.
        json_path = TEMPLATES_DIR / filename                                          # Construye ruta absoluta.
        if json_path.exists():                                                        # Si el archivo existe...
            try:                                                                      # Intenta parsear el JSON.
                data = json.loads(json_path.read_text(encoding="utf-8"))             # Lee y parsea con UTF-8.
                logger.debug(f"[mailer] i18n file loaded: {filename} (lang={code})")  # Log para depuración (qué archivo se usó).
                return data                                                           # Devuelve contenido.
            except Exception as e:                                                    # Ante error de parseo...
                logger.error(f"Error al parsear '{filename}': {e}")                  # Registra el problema y prueba siguiente.
    logger.error(f"No se encontró archivo de contenido válido para '{code}'. Usando fallback.")  # Logea ausencia total.
    return {                                                                          # Fallback mínimo en inglés.
        "title": "Message",
        "message": "",
        "cta_label": "Open",
        "footer_text": "This email was sent automatically. If you don’t recognize this invitation, ignore it."
    }

def _build_email_html(lang_code: str, cta_url: str) -> str:                           # Ensambla HTML final desde plantilla y contenido.
    """Ensambla HTML usando plantilla base + contenido i18n + URL de CTA."""          # Docstring descriptivo.
    template_path = TEMPLATES_DIR / "wedding_email_template.html"                     # Ruta al HTML base.
    if template_path.exists():                                                        # Si la plantilla base existe...
        template_html = template_path.read_text(encoding="utf-8")                     # Lee el HTML base.
    else:                                                                             # Si no existe la plantilla...
        template_html = (                                                             # Usa HTML mínimo con placeholders.
            "<html lang='{{html_lang}}'><body>"
            "<h1>{{title}}</h1><p>{{message}}</p>"
            "<p><a href='{{cta_url}}'>{{cta_label}}</a></p>"
            "<p style='font-size:12px;color:#888'>{{footer_text}}</p>"
            "</body></html>"
        )
    content = _load_language_content(lang_code)                                       # Carga textos del idioma.
    html = template_html.replace("{{html_lang}}", lang_code)                          # Inserta atributo lang.
    html = html.replace("{{title}}", content.get("title", ""))                        # Inserta título.
    html = html.replace("{{message}}", content.get("message", ""))                    # Inserta cuerpo del mensaje.
    html = html.replace("{{cta_label}}", content.get("cta_label", "Open"))            # Inserta etiqueta del botón.
    html = html.replace("{{cta_url}}", cta_url or "#")                                # Inserta URL del botón (fallback '#').
    html = html.replace("{{footer_text}}", content.get("footer_text", ""))            # Inserta texto del pie.
    return html                                                                       # Devuelve HTML final.

# =================================================================================
# ✉️ Envío de emails (HTML y texto)                                                     # Funciones de envío básico.
# =================================================================================

def send_email_html(to_email: str, subject: str, html_body: str, text_fallback: str = "") -> bool:  # Firma de envío HTML.
    """Envía correo HTML con SendGrid, con logging detallado y observabilidad."""                       # Docstring mejorado.

    # ✅ AJUSTE: "Chivato" en tiempo de ejecución para depuración.                                      # Comentario de bloque.
    DRY_RUN_NOW = os.getenv("DRY_RUN", "1") == "1"                                                     # Lee DRY_RUN en el momento del envío.
    FROM_EMAIL_NOW = os.getenv("EMAIL_FROM", "")                                                      # Lee el remitente configurado en .env.
    API_KEY_NOW = os.getenv("SENDGRID_API_KEY", "")                                                   # Lee la API key en tiempo de ejecución.
    API_KEY_EXISTS = bool(API_KEY_NOW)                                                                # Evalúa si la API key existe (bool).

    logger.debug(                                                                                    # Log de depuración previo al envío.
        "Mailer check -> DRY_RUN={} | FROM={} | SG_KEY_SET={}",                                       # Mensaje claro y no sensible.
        DRY_RUN_NOW,                                                                                 # Muestra si está en simulación (True) o real (False).
        FROM_EMAIL_NOW,                                                                              # Muestra el remitente que se usará.
        API_KEY_EXISTS                                                                               # Indica si hay API key (True/False).
    )                                                                                                # Cierra el log previo.

    if DRY_RUN_NOW:                                                                                  # Si la simulación está activa...
        logger.info(f"[DRY_RUN] (HTML) Simular envío a {to_email} | Asunto: {subject}")              # Loguea la simulación.
        return True                                                                                  # Y considera la operación un éxito.

    if not FROM_EMAIL_NOW or not API_KEY_EXISTS:                                                     # Si falta remitente o API key en modo real...
        logger.error("Config de mailer incompleta (HTML): FROM_EMAIL o SENDGRID_API_KEY ausentes.")  # Log de error de configuración.
        send_alert_webhook("🚨 Mailer HTML config", "Falta FROM_EMAIL o SENDGRID_API_KEY (modo real).")  # Alerta por webhook.
        return False                                                                                 # No se puede enviar.

    message = Mail(                                                                                  # Construye el objeto Mail de SendGrid.
        from_email=From(FROM_EMAIL_NOW, EMAIL_SENDER_NAME),                                          # Remitente con nombre legible.
        to_emails=to_email,                                                                          # Destinatario del correo.
        subject=subject,                                                                             # Asunto del correo.
        plain_text_content=(text_fallback or "This email is best viewed in an HTML-compatible client."),  # Fallback de texto plano.
        html_content=html_body                                                                       # Cuerpo del correo en formato HTML.
    )                                                                                                # Fin de la construcción del mensaje.

    try:                                                                                             # Intenta el envío real a través de la red.
        sg = SendGridAPIClient(API_KEY_NOW)                                                          # Inicializa el cliente de SendGrid con la API Key.
        response = sg.send(message)                                                                  # Ejecuta el envío y captura la respuesta.

        # ✅ Log con ID de seguimiento para trazabilidad en SendGrid.
        logger.info(                                                                                 # Log informativo post-envío.
            "SendGrid response: {} | X-Message-Id: {}",                                              # Muestra el código de estado y el ID único.
            response.status_code,                                                                    # 202 si SendGrid aceptó el mensaje.
            response.headers.get("X-Message-Id")                                                     # ID que puedes buscar en la "Email Activity" de SendGrid.
        )                                                                                            # Fin del log informativo.

        if 200 <= response.status_code < 300:                                                        # Si el código de estado está en el rango de éxito (2xx)...
            return True                                                                              # La operación fue exitosa.
        else:                                                                                        # Si SendGrid devolvió un error...
            logger.error(                                                                            # Registra un error detallado para diagnóstico.
                "SendGrid error -> status={} | body={}",                                             # Mensaje con status y cuerpo del error.
                response.status_code,                                                                # Código HTTP devuelto por SendGrid (ej. 401, 403).
                getattr(response, "body", None)                                                      # Cuerpo de la respuesta (contiene el motivo del error).
            )                                                                                        # Fin del log de error.
            send_alert_webhook("🚨 Mailer HTML error", f"No se pudo enviar a {to_email}. Código: {response.status_code}.") # Envía alerta.
            return False                                                                             # La operación falló.

    except Exception as e:                                                                           # Captura cualquier otra excepción (ej. de red).
        logger.exception(f"Excepción enviando HTML a {to_email}: {e}")                               # Loguea la excepción completa con stack trace.
        send_alert_webhook("🚨 Mailer HTML exception", f"Excepción enviando a {to_email}. Error: {e}") # Envía alerta.
        return False                                                                                 # La operación falló.

def send_email(to_email: str, subject: str, body: str) -> bool:                                      # Firma de envío texto plano.
    """Envía correo de texto plano por SendGrid; respeta DRY_RUN y emite alertas ante fallos."""     # Docstring.

    DRY_RUN_NOW = os.getenv("DRY_RUN", "1") == "1"                                                   # Lee DRY_RUN en tiempo de ejecución (consistente con HTML).
    FROM_EMAIL_NOW = os.getenv("EMAIL_FROM", "")                                                     # Lee remitente en tiempo de ejecución (evita staleness).
    API_KEY_NOW = os.getenv("SENDGRID_API_KEY", "")                                                  # Lee la API key en tiempo de ejecución.
    API_KEY_EXISTS = bool(API_KEY_NOW)                                                               # Evalúa presencia de API key (bool).

    if DRY_RUN_NOW:                                                                                  # Si está en modo simulación...
        logger.info(f"[DRY_RUN] Simular envío a {to_email} | Asunto: {subject}\n{body}")             # Log de simulación con cuerpo.
        return True                                                                                  # Considera éxito.

    if not FROM_EMAIL_NOW or not API_KEY_EXISTS:                                                     # Si falta remitente o API key en modo real...
        logger.error("Config de mailer incompleta (TXT): FROM_EMAIL o SENDGRID_API_KEY ausentes.")   # Log de error de configuración.
        send_alert_webhook("🚨 Mailer TXT config", "Falta FROM_EMAIL o SENDGRID_API_KEY (modo real).")# Alerta por webhook.
        return False                                                                                 # No puede enviar.

    message = Mail(                                                                                  # Construye objeto Mail.
        from_email=From(FROM_EMAIL_NOW, EMAIL_SENDER_NAME),                                          # Remitente con nombre.
        to_emails=to_email,                                                                          # Destinatario.
        subject=subject,                                                                             # Asunto.
        plain_text_content=body,                                                                     # Cuerpo texto.
    )                                                                                                # Fin construcción.

    try:                                                                                             # Intenta envío real.
        sg = SendGridAPIClient(API_KEY_NOW)                                                          # Cliente SendGrid con API key en runtime.
        response = sg.send(message)                                                                  # Envía y captura respuesta.

        logger.info(                                                                                 # Log estandarizado (paridad con HTML).
            "SendGrid response: {} | X-Message-Id: {}",                                              # Código + ID para trazar en Activity.
            response.status_code,                                                                    # Status HTTP (202 esperado).
            response.headers.get("X-Message-Id")                                                     # ID único del mensaje.
        )                                                                                            # Cierre del log.

        if 200 <= response.status_code < 300:                                                        # Rango 2xx indica éxito.
            return True                                                                              # Devuelve True en éxito.
        logger.error(                                                                                # Log detallado si no fue 2xx.
            "Error al enviar a {}. Código: {}. Cuerpo: {}",                                          # Mensaje con cuerpo incluido.
            to_email,                                                                                # Destinatario.
            response.status_code,                                                                    # Código.
            getattr(response, "body", None)                                                          # Cuerpo devuelto por SendGrid.
        )                                                                                            # Cierre del log.
        send_alert_webhook("🚨 Mailer error", f"No se pudo enviar a {to_email}. Código: {response.status_code}. Asunto: {subject}")  # Alerta webhook.
        return False                                                                                 # Indica fallo.

    except Exception as e:                                                                           # Excepción general (red, cliente, etc.).
        logger.error(f"Excepción enviando a {to_email}: {e}")                                        # Log de excepción legible.
        send_alert_webhook("🚨 Mailer exception", f"Excepción enviando a {to_email}. Asunto: {subject}. Error: {e}")                 # Alerta webhook.
        return False                                                                                 # Indica fallo.

# =================================================================================
# 🧩 Helpers de alto nivel (API simple para el resto del backend)                      # Funciones de alto nivel.
# =================================================================================
def send_rsvp_reminder_email(to_email: str, guest_name: str, invited_to_ceremony: bool, language: str | Enum, deadline_dt: datetime) -> bool:  # Firma recordatorio TXT.
    """Envía recordatorio en texto plano (i18n) con fecha límite y CTA opcional."""                   # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")                 # Normaliza entrada Enum/str.
    lang_map = TEMPLATES.get(lang_value) or TEMPLATES.get("en", {})                                   # Obtiene bundle o EN.
    if not lang_map:                                                                                  # Si ni EN existe...
        logger.error("TEMPLATES no contiene definiciones mínimas para 'en'.")                         # Log crítico de config.
        return False                                                                                  # Abortamos.
    safe_lang = lang_value if lang_value in SUPPORTED_LANGS else "en"                                 # Asegura idioma soportado.
    deadline_str = format_deadline(deadline_dt, safe_lang)                                            # Formatea fecha límite.
    cta_line = lang_map.get("cta", "👉 Open: {url}").format(url=RSVP_URL) if RSVP_URL else ""         # CTA si hay RSVP_URL.
    key = "reminder_both" if invited_to_ceremony else "reminder_reception"                            # Selección de plantilla.
    body = lang_map.get(key, "Please confirm your attendance.\n{cta}").format(                        # Rellena plantilla.
        name=guest_name, deadline=deadline_str, cta=cta_line                                          # Variables nombradas.
    )                                                                                                 # Cierre format.
    subject = SUBJECTS["reminder"].get(lang_value, SUBJECTS["reminder"]["en"])                        # Asunto i18n.
    return send_email(to_email=to_email, subject=subject, body=body)                                  # Envío texto plano.

def send_recovery_email(to_email: str, guest_name: str, guest_code: str, language: str | Enum) -> bool:  # Firma recuperación TXT.
    """Envía correo de recuperación de código de invitado en texto plano (i18n)."""                    # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")                  # Normaliza idioma.
    lang_map = TEMPLATES.get(lang_value) or TEMPLATES.get("en", {})                                    # Obtiene bundle o EN.
    if not lang_map:                                                                                   # Validación mínima.
        logger.error("TEMPLATES no contiene definiciones mínimas para 'en'.")                          # Log crítico.
        return False                                                                                   # Abortamos.
    cta_line = lang_map.get("cta", "👉 Open: {url}").format(url=RSVP_URL) if RSVP_URL else ""          # CTA opcional.
    body = lang_map.get("recovery", "Your guest code is: {guest_code}\n{cta}").format(                 # Rellena plantilla.
        name=guest_name, guest_code=guest_code, cta=cta_line                                           # Variables.
    )                                                                                                  # Cierre format.
    subject = SUBJECTS["recovery"].get(lang_value, SUBJECTS["recovery"]["en"])                         # Asunto i18n.
    return send_email(to_email=to_email, subject=subject, body=body)                                   # Envío texto plano.

def send_magic_link_email(to_email: str, language: str | Enum, magic_url: str) -> bool:                # Firma Magic Link HTML.
    """Envía el correo de Magic Link usando la plantilla HTML (i18n) con logs y fallback i18n."""      # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")                  # Normaliza idioma.
    lang_code = lang_value if lang_value in SUPPORTED_LANGS else "en"                                  # Asegura idioma compatible.
    logger.info(f"Preparando envío de Magic Link -> to={to_email} lang={lang_code}")                   # Log útil de idioma final.
    html = _build_email_html(lang_code, magic_url)                                                     # Construye HTML con CTA.
    subject = SUBJECTS["magic_link"].get(lang_code, SUBJECTS["magic_link"]["en"])                      # Asunto i18n.
    text_fallbacks = {                                                                                 # Fallback de texto por idioma.
        "es": f"Abre este enlace para confirmar tu asistencia: {magic_url}",                           # ES.
        "ro": f"Deschide acest link pentru a-ți confirma prezența: {magic_url}",                       # RO.
        "en": f"Open this link to confirm your attendance: {magic_url}",                               # EN.
    }                                                                                                  # Fin mapa de fallbacks.
    text_fallback = text_fallbacks.get(lang_code, text_fallbacks["en"])                                # Selecciona fallback final.
    return send_email_html(                                                                            # Envía HTML con fallback.
        to_email=to_email,
        subject=subject,
        html_body=html,
        text_fallback=text_fallback
    )                                                                                                  # Fin de llamada.

def send_guest_code_email(to_email: str, guest_name: str, guest_code: str, language: str | Enum) -> bool:  # Define la función pública para enviar el correo con código de invitado.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")                      # Normaliza el idioma por si viene como Enum o string.
    lang_code = lang_value if lang_value in SUPPORTED_LANGS else "en"                                      # Asegura que el idioma esté soportado; usa 'en' por defecto.
    logger.info(f"Preparando envío de Guest Code -> to={to_email} lang={lang_code}")                        # Log informativo para trazabilidad de idioma/destinatario.

    # --- Asuntos por idioma (simples y claros) ---
    subject_map = {                                                                                        # Mapa de asuntos por idioma.
        "es": "Tu código de invitación • Boda Daniela & Cristian",                                        # Asunto en español.
        "en": "Your invitation code • Daniela & Cristian Wedding",                                        # Asunto en inglés.
        "ro": "Codul tău de invitație • Nunta Daniela & Cristian",                                        # Asunto en rumano.
    }                                                                                                      # Cierre del mapa de asuntos.
    subject = subject_map.get(lang_code, subject_map["en"])                                                # Selecciona el asunto final con fallback a inglés.

    # --- Cuerpo HTML mínimo (no usa plantilla global para que sea auto-contenido y seguro) ---
    #     Si quieres, más adelante podemos migrarlo a tu plantilla 'wedding_email_template.html' con i18n JSON.
    greet = "Hola" if lang_code == "es" else ("Bună" if lang_code == "ro" else "Hi")                      # Calcula el saludo según idioma.
    instr = (                                                                                              # Calcula la instrucción de uso según idioma.
        "Usa este código en la página de Iniciar sesión."
        if lang_code == "es" else
        ("Folosește acest cod pe pagina de autentificare." if lang_code == "ro" else "Use this code on the login page.")
    )                                                                                                      # Cierre de la instrucción.
    btn_label = "Iniciar sesión" if lang_code == "es" else ("Conectare" if lang_code == "ro" else "Log in")# Etiqueta del botón i18n.

    # --- Construye el botón opcional al Login si PUBLIC_LOGIN_URL está configurada ---
    cta_html = ""                                                                                          # Inicializa el bloque CTA vacío.
    if PUBLIC_LOGIN_URL:                                                                                   # Si hay URL pública de Login en .env...
        cta_html = (                                                                                        # Construye un botón accesible y sobrio.
            "<p style='margin-top:16px;'>"
            f"<a href='{PUBLIC_LOGIN_URL}' "                                                                # Inserta la URL de Login del entorno.
            "style='display:inline-block;padding:10px 16px;border-radius:8px;"
            "background:#6D28D9;color:#fff;text-decoration:none;font-weight:600;'"
            f">{btn_label}</a></p>"                                                                         # Inserta la etiqueta del botón según idioma.
        )                                                                                                   # Cierre del bloque CTA.

    # --- HTML final del correo (simple y consistente) ---
    html_body = (                                                                                           # Abre el ensamblado del HTML del correo.
        "<div style='font-family:Inter,Arial,sans-serif;line-height:1.6'>"                                  # Contenedor con tipografía legible.
        f"<h2>{subject}</h2>"                                                                               # Inserta el título usando el asunto.
        f"<p>{greet} {guest_name},</p>"                                                                     # Saludo personalizado con nombre.
        f"<p>{'Tu código de invitación es' if lang_code=='es' else ('Codul tău de invitație este' if lang_code=='ro' else 'Your invitation code is')}: "
        f"<strong style='font-size:18px;letter-spacing:1px'>{guest_code}</strong></p>"                      # Código en negrita con tracking amplio.
        f"<p>{instr}</p>"                                                                                   # Instrucción de uso del código.
        f"{cta_html}"                                                                                       # Inyecta el CTA solo si hay URL pública.
        "</div>"                                                                                            # Cierra el contenedor HTML.
    )                                                                                                       # Cierra el ensamblado HTML.

    # --- Fallback de texto plano (para clientes que no renderizan HTML) ---
    text_fallback = (                                                                                       # Construye texto alternativo legible.
        f"Hola {guest_name},\n\nTu código de invitación es: {guest_code}\n\n{instr}"                        # Versión ES.
        if lang_code == "es" else                                                                           # Condición para español.
        (f"Bună {guest_name},\n\nCodul tău de invitație este: {guest_code}\n\n{instr}")                     # Versión RO.
        if lang_code == "ro" else                                                                           # Condición para rumano.
        (f"Hi {guest_name},\n\nYour invitation code is: {guest_code}\n\n{instr}")                           # Versión EN.
    )                                                                                                       # Cierre del fallback.

    # --- Envío usando tu helper central con SendGrid (respeta DRY_RUN y logs) ---
    return send_email_html(                                                                                 # Llama al helper de envío HTML.
        to_email=to_email,                                                                                  # Pasa el destinatario.
        subject=subject,                                                                                    # Pasa el asunto ya i18n.
        html_body=html_body,                                                                                # Pasa el HTML ensamblado.
        text_fallback=text_fallback                                                                         # Pasa el texto alternativo.
    )                                                                                                       # Retorna True/False según resultado.

def send_confirmation_email(to_email: str, language: str | Enum, summary: dict) -> bool:                 # Define la función de confirmación de RSVP.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")                    # Normaliza idioma (Enum o string).
    lang_code = lang_value if lang_value in SUPPORTED_LANGS else "en"                                    # Garantiza idioma soportado.

    # --- Asunto por idioma ---
    subject_map = {                                                                                      # Mapa de asuntos i18n.
        "es": "✅ Confirmación recibida • Boda Daniela & Cristian",                                      # Español.
        "en": "✅ RSVP received • Daniela & Cristian Wedding",                                           # Inglés.
        "ro": "✅ Confirmare înregistrată • Nunta Daniela & Cristian",                                   # Rumano.
    }                                                                                                     # Cierre mapa asuntos.
    subject = subject_map.get(lang_code, subject_map["en"])                                               # Selección con fallback.

    # --- Extrae campos esperados del resumen (defensivo) ---
    guest_name = summary.get("guest_name", "")                                                            # Nombre del titular (siempre que esté).
    invite_scope = summary.get("invite_scope", "reception-only")                                          # Alcance de invitación.
    attending = summary.get("attending", None)                                                            # Asistencia confirmada (True/False/None).
    companions = summary.get("companions", [])                                                            # Lista de acompañantes (si aplica).
    allergies = summary.get("allergies", "")                                                              # Alergias declaradas (si aplica).
    notes = summary.get("notes", "")                                                                      # Notas del invitado (opcional).

    # --- Pequeños diccionarios i18n para el cuerpo ---
    scope_value = {                                                                                       # Traducción del alcance de invitación.
        "ceremony+reception": {"es":"Ceremonia + Recepción","en":"Ceremony + Reception","ro":"Ceremonie + Recepție"},
        "reception-only": {"es":"Solo Recepción","en":"Reception only","ro":"Doar Recepție"},
    }                                                                                                     # Cierre mapa de alcance.
    att_map = {                                                                                           # Traducción de asistencia.
        True:  {"es":"Asistencia: Sí","en":"Attending: Yes","ro":"Participare: Da"},
        False: {"es":"Asistencia: No","en":"Attending: No","ro":"Participare: Nu"},
        None:  {"es":"Asistencia: —","en":"Attending: —","ro":"Participare: —"},
    }                                                                                                     # Cierre mapa de asistencia.

    # --- Construcción del HTML del resumen (compacto y claro) ---
    greet = "Hola" if lang_code == "es" else ("Bună" if lang_code == "ro" else "Hi")                     # Saludo por idioma.
    html_parts = []                                                                                       # Inicializa lista de líneas HTML.
    html_parts.append("<div style='font-family:Inter,Arial,sans-serif;line-height:1.6'>")                 # Contenedor principal.
    html_parts.append(f"<h2>{subject}</h2>")                                                               # Título con asunto.
    html_parts.append(f"<p>{greet} {guest_name},</p>")                                                     # Saludo con nombre.
    html_parts.append(                                                                                    # Línea de invitación.
        f"<p>{ {'es':'Invitación: ', 'en':'Invitation: ', 'ro':'Invitație: '}.get(lang_code,'Invitation: ') }"
        f"{scope_value.get(invite_scope, scope_value['reception-only']).get(lang_code)}</p>"
    )                                                                                                      # Cierre de línea de invitación.
    html_parts.append(f"<p>{att_map.get(attending, att_map[None]).get(lang_code)}</p>")                   # Línea de asistencia.

    if companions:                                                                                        # Si hay acompañantes...
        html_parts.append("<h3>👥 Acompañantes</h3>")                                                      # Título de sección.
        html_parts.append("<ul>")                                                                          # Lista HTML.
        for c in companions:                                                                              # Itera cada acompañante.
            label = c.get("label","")                                                                     # Toma etiqueta (adulto/niño).
            name = c.get("name","")                                                                       # Toma nombre.
            allergens = c.get("allergens","")                                                              # Toma alérgenos.
            html_parts.append(                                                                            # Agrega ítem de lista.
                f"<li><strong>{name}</strong> — {label} — "
                f"{('Alergias:' if lang_code=='es' else ('Alergii:' if lang_code=='ro' else 'Allergies:'))} "
                f"{allergens or '—'}</li>"
            )                                                                                              # Cierre ítem.
        html_parts.append("</ul>")                                                                         # Cierra lista.

    if allergies:                                                                                         # Si el titular declaró alergias...
        html_parts.append(                                                                                # Agrega línea de alergias.
            f"<p>{('Alergias' if lang_code=='es' else ('Alergii' if lang_code=='ro' else 'Allergies'))}: {allergies}</p>"
        )                                                                                                  # Cierre de línea.

    if notes:                                                                                             # Si hay notas...
        html_parts.append(                                                                                # Agrega línea de notas.
            f"<p>{('Notas' if lang_code=='es' else ('Note' if lang_code=='ro' else 'Notes'))}: {notes}</p>"
        )                                                                                                  # Cierre de línea.

    html_parts.append("</div>")                                                                           # Cierra contenedor HTML.
    html_body = "".join(html_parts)                                                                       # Une el HTML final.

    text_fallback = f"{subject}\n\n{guest_name}\n"                                                         # Construye fallback de texto mínimo.
    return send_email_html(                                                                               # Usa tu helper de envío HTML+texto.
        to_email=to_email,                                                                                # Destinatario del correo.
        subject=subject,                                                                                  # Asunto i18n.
        html_body=html_body,                                                                              # Cuerpo HTML.
        text_fallback=text_fallback                                                                       # Texto alternativo.
    )                                                                                                     # Devuelve True/False.
    

def send_rsvp_reminder_email_html(to_email: str, guest_name: str, invited_to_ceremony: bool, language: str | Enum, deadline_dt: datetime) -> bool:  # Firma recordatorio HTML.
    """(Opcional) Envía un recordatorio usando la plantilla HTML (i18n)."""                            # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")                  # Normaliza idioma.
    lang_code = lang_value if lang_value in SUPPORTED_LANGS else "en"                                  # Asegura idioma soportado.
    cta_url = RSVP_URL or "#"                                                                          # Usa RSVP_URL o '#'.
    html = _build_email_html(lang_code, cta_url)                                                       # Construye HTML base.
    deadline_str = format_deadline(deadline_dt, lang_code)                                             # Formatea fecha límite.
    html = html.replace("</p>", f"<br/><strong>{deadline_str}</strong></p>", 1)                        # Inserta deadline visible (primera ocurrencia de </p>).
    subject = SUBJECTS["reminder"].get(lang_code, SUBJECTS["reminder"]["en"])                          # Asunto i18n.
    return send_email_html(to_email=to_email, subject=subject, html_body=html)                         # Envío HTML.

# =================================================================================
# 🔁 Compatibilidad retro: alias con firma antigua                                     # Mantiene routers viejos funcionando.
# =================================================================================
def send_magic_link(email: str, url: str, lang: str = "en") -> bool:                                   # Wrapper retrocompatible.
    """Wrapper retrocompatible: firma antigua → nueva función HTML."""                                  # Docstring.
    return send_magic_link_email(to_email=email, language=lang, magic_url=url)                          # Redirige al helper moderno.
