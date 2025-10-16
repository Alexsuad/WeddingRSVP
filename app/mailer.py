# app/mailer.py  # Ruta y nombre del archivo.                                               # Indica el nombre del módulo y su ubicación.

# =================================================================================
# 📧 MÓDULO DE ENVÍO DE CORREOS (con soporte HTML)                                   # Describe propósito del módulo.
# (Patch: Brevo por defecto, sin fallback SendGrid en HTML, replyTo en Brevo API)
# ---------------------------------------------------------------------------------
# Centraliza envío por Brevo, Gmail o SendGrid, plantillas (texto y HTML),           # Explica funciones principales.
# i18n y helpers de alto nivel. Mantiene compatibilidad retro y DRY_RUN.             # Indica funcionalidades cubiertas.
# =================================================================================

# 🐍 Importaciones
import os                                                                              # Acceso a variables de entorno (.env).
from enum import Enum                                                                  # Soporte para tipos Enum (idioma/segmento).
from datetime import datetime                                                          # Tipo de fecha para formateo de deadline.
import json                                                                            # Serialización JSON para payloads/leer plantillas.
import requests                                                                        # HTTP simple para webhook opcional.
from functools import lru_cache                                                        # Cache de lectura i18n para evitar I/O repetido.
from loguru import logger                                                              # Logger estructurado para trazas legibles.
# (SendGrid: import perezoso más abajo para no romper si no está instalado)           # Evitamos ImportError en entornos sin SendGrid.
from pathlib import Path                                                               # Manejo de rutas de archivos de forma robusta.
import html                                                                            # Escape seguro para valores libres en HTML.
import smtplib                                                                         # Envío SMTP (Gmail).
from email.mime.text import MIMEText                                                   # Construcción de cuerpo de texto/HTML.
from email.mime.multipart import MIMEMultipart                                         # Contenedor de mensaje (headers + partes).


import socket                                      # importa socket para resolver DNS y controlar familia IPv4
from ssl import create_default_context             # importa helper para crear un contexto TLS seguro

def _smtp_connect_ipv4(host: str, port: int, timeout: float) -> smtplib.SMTP:
    """
    Crea una conexión SMTP forzando IPv4 y soporta 587 (STARTTLS) y 465 (SMTPS).
    Conecta explícitamente a la IP v4 resuelta para evitar IPv6.
    """
    # Resuelve SOLO IPv4
    addrinfo = socket.getaddrinfo(
        host,
        port,
        socket.AF_INET,          # fuerza familia IPv4
        socket.SOCK_STREAM
    )
    ipv4_ip = addrinfo[0][4][0]  # toma la IP v4 literal (p.ej. '74.125.206.108')

    if port == 465:
        # TLS directo
        context = create_default_context()
        # Conecta ya a la IP v4 (no al hostname)
        server = smtplib.SMTP_SSL(
            host=ipv4_ip,
            port=port,
            timeout=timeout,
            context=context
        )
        return server

    # STARTTLS (587)
    server = smtplib.SMTP(timeout=timeout)
    # Forzamos conexión a la IP v4 (evita una nueva resolución que podría ir a IPv6)
    server.connect(ipv4_ip, port)
    return server

# =================================================================================
# ✅ Configuración unificada al inicio del archivo.
# ---------------------------------------------------------------------------------
# Se centraliza la lectura de variables de entorno y se valida credenciales
# solo si DRY_RUN=0 (evita fallos en dev/CI).
# =================================================================================
SUPPORTED_LANGS = ("en", "es", "ro")
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("EMAIL_FROM", "")
RSVP_URL = os.getenv("RSVP_URL", "")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Jenny & Cristian")
TEMPLATES_DIR = (Path(__file__).parent / "templates" / "emails").resolve()
PUBLIC_LOGIN_URL = os.getenv("PUBLIC_LOGIN_URL", "").strip()

# Valida configuración crítica solo si NO estamos en modo simulación.
if not DRY_RUN:                                                                       # Si se quiere envío real...
    provider_now = os.getenv("EMAIL_PROVIDER", "brevo").lower()                       # Lee proveedor activo, Brevo por defecto.

    if provider_now == "sendgrid":                                                    # Reglas para SendGrid.
        if not SENDGRID_API_KEY:
            raise RuntimeError("Falta SENDGRID_API_KEY para envíos reales con SendGrid.")
        if not FROM_EMAIL:
            raise RuntimeError("Falta EMAIL_FROM para envíos reales con SendGrid.")

    elif provider_now == "gmail":                                                     # Reglas para Gmail (SMTP).
        if not os.getenv("EMAIL_USER", "") or not os.getenv("EMAIL_PASS", ""):
            raise RuntimeError("Faltan EMAIL_USER o EMAIL_PASS para envíos reales con Gmail/SMTP.")
        if not FROM_EMAIL:
            FROM_EMAIL = os.getenv("EMAIL_USER", "")

    elif provider_now == "brevo":                                                     # Reglas para Brevo (API HTTPS).
        if not os.getenv("BREVO_API_KEY", ""):
            raise RuntimeError("Falta BREVO_API_KEY para envíos reales con Brevo API.")
        if not FROM_EMAIL:
            raise RuntimeError("Falta EMAIL_FROM para envíos reales con Brevo API.")

    else:
        raise RuntimeError(f"EMAIL_PROVIDER desconocido: {provider_now}")

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

SUBJECTS.setdefault("confirmation", {                                                 # Asegura clave para confirmación de RSVP.
    "es": "✅ Confirmación recibida • Boda Jenny & Cristian",                       # Español.
    "ro": "✅ Confirmare înregistrată • Nunta Jenny & Cristian",                    # Rumano.
    "en": "✅ RSVP received • Jenny & Cristian Wedding",                            # Inglés.
})                                                                                    # Cierre setdefault para confirmación.

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
            "Un abrazo,\nJenny & Cristian"
        ),
        "reminder_reception": (                                                       # Recordatorio solo recepción.
            "Hola {name},\n\n"
            "Este es un amable recordatorio para que confirmes tu asistencia a nuestra recepción.\n"
            "La fecha límite para confirmar es el {deadline}.\n\n"
            "{cta}\n\n"
            "¡Nos encantaría celebrar contigo!\n\n"
            "Un abrazo,\nJenny & Cristian"
        ),
        "recovery": (                                                                 # Recuperación de código.
            "Hola {name},\n\n"
            "Has solicitado recuperar tu código de invitado.\n"
            "Tu código es: {guest_code}\n\n"
            "Puedes usarlo junto con tu email o teléfono para iniciar sesión en el formulario.\n"
            "{cta}\n\n"
            "Si no solicitaste este mensaje, puedes ignorarlo.\n\n"
            "Un abrazo,\nJenny & Cristian"
        ),
        "cta": "👉 Confirma aquí: {url}",                                             # CTA de texto con URL.
        "confirmation": (                                                             # Confirmación de RSVP.
            "Hola {name},\n\n"
            "¡Gracias por confirmar tu asistencia!\n"
            "Invitación: {invite_scope}\n"
            "Asistencia: {attending}\n"
            "{companions}\n"
            "{allergies}\n"
            "{notes}\n\n"
            "Te iremos informando con más detalles conforme se acerque la fecha.\n\n"
            "Un abrazo,\nJenny & Cristian"
        ),
    },
    "ro": {                                                                           # Rumano (completo).
        "reminder_both": (
            "Bună {name},\n\n"
            "Acesta este un memento prietenos pentru a confirma participarea la ceremonia și recepție.\n"
            "Data limită pentru confirmare este {deadline}.\n\n"
            "{cta}\n\n"
            "Sperăm să te vedem acolo!\n\n"
            "Cu drag,\nJenny & Cristian"
        ),
        "reminder_reception": (
            "Bună {name},\n\n"
            "Acesta este un memento prietenos pentru a confirma participarea la recepția noastră.\n"
            "Data limită pentru confirmare este {deadline}.\n\n"
            "{cta}\n\n"
            "Ne-ar plăcea să sărbătorim cu tine!\n\n"
            "Cu drag,\nJenny & Cristian"
        ),
        "recovery": (
            "Bună {name},\n\n"
            "Ai solicitat recuperarea codului tău de invitat.\n"
            "Codul tău este: {guest_code}\n\n"
            "Îl poți folosi împreună cu emailul sau telefonul pentru autentificare în formular.\n"
            "{cta}\n\n"
            "Dacă nu ai solicitat acest mesaj, îl poți ignora.\n\n"
            "Cu drag,\nJenny & Cristian"
        ),
        "cta": "👉 Confirmă aici: {url}",                                             # CTA de texto con URL.
        "confirmation": (
            "Bună {name},\n\n"
            "Îți mulțumim că ai confirmat prezența!\n"
            "Invitație: {invite_scope}\n"
            "Participare: {attending}\n"
            "{companions}\n"
            "{allergies}\n"
            "{notes}\n\n"
            "Te vom ține la curent cu mai multe detalii pe măsură ce se apropie data.\n\n"
            "Cu drag,\nJenny & Cristian"
        ),
    },
    "en": {                                                                           # Inglés (completo).
        "reminder_both": (
            "Hi {name},\n\n"
            "This is a friendly reminder to confirm your attendance for our ceremony and reception.\n"
            "The deadline to RSVP is {deadline}.\n\n"
            "{cta}\n\n"
            "We hope to see you there!\n\n"
            "Best,\nJenny & Cristian"
        ),
        "reminder_reception": (
            "Hi {name},\n\n"
            "This is a friendly reminder to confirm your attendance for our reception.\n"
            "The deadline to RSVP is {deadline}.\n\n"
            "{cta}\n\n"
            "We would love to celebrate with you!\n\n"
            "Best,\nJenny & Cristian"
        ),
        "recovery": (
            "Hi {name},\n\n"
            "You requested to recover your guest code.\n"
            "Your code is: {guest_code}\n\n"
            "Use it along with your email or phone to log in to the form.\n"
            "{cta}\n\n"
            "If you did not request this, you can ignore this message.\n\n"
            "Best,\nJenny & Cristian"
        ),
        "cta": "👉 Confirm here: {url}",                                              # CTA de texto con URL.
        "confirmation": (
            "Hi {name},\n\n"
            "Thank you for confirming your attendance!\n"
            "Invitation: {invite_scope}\n"
            "Attending: {attending}\n"
            "{companions}\n"
            "{allergies}\n"
            "{notes}\n\n"
            "We’ll keep you updated with more details as the date approaches.\n\n"
            "Best,\nJenny & Cristian"
        ),
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
    Carga el JSON (title, message, cta_label, footer_text) según idioma,              # Docstring de función.
    probando múltiples nombres; si ninguno existe/parsea, retorna fallback seguro.    # Explica fallback.
    """
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
    html_out = template_html.replace("{{html_lang}}", lang_code)                      # Inserta atributo lang.
    html_out = html_out.replace("{{title}}", content.get("title", ""))                # Inserta título.
    html_out = html_out.replace("{{message}}", content.get("message", ""))            # Inserta cuerpo del mensaje.
    html_out = html_out.replace("{{cta_label}}", content.get("cta_label", "Open"))    # Inserta etiqueta del botón.
    html_out = html_out.replace("{{cta_url}}", cta_url or "#")                        # Inserta URL del botón (fallback '#').
    html_out = html_out.replace("{{footer_text}}", content.get("footer_text", ""))    # Inserta texto del pie.
    return html_out                                                                   # Devuelve HTML final.

# =================================================================================
# ✉️ Motores de envío internos
# =================================================================================
def _send_plain_via_gmail(to_email: str, subject: str, body: str) -> bool:            # Define función interna para Gmail texto.
    """Envía un correo de texto plano usando un servidor SMTP (pensado para Gmail)."""
    host = os.getenv("EMAIL_HOST", "smtp.gmail.com")                                  # Host SMTP de Gmail por defecto.
    port = int(os.getenv("EMAIL_PORT", "587"))                                        # Puerto TLS estándar.
    user = os.getenv("EMAIL_USER", "")                                                # Usuario/correo remitente (Gmail).
    pwd  = os.getenv("EMAIL_PASS", "")                                                # Contraseña de aplicación de 16 dígitos.
    sender_name = os.getenv("EMAIL_SENDER_NAME", "RSVP")                              # Nombre amigable del remitente.
    from_addr = os.getenv("EMAIL_FROM", user)                                         # Dirección From (por defecto el user de Gmail).

    if not (user and pwd and from_addr):                                              # Valida credenciales mínimas requeridas.
        logger.error("Gmail SMTP no está configurado correctamente (EMAIL_USER/EMAIL_PASS/EMAIL_FROM).")  # Error de config.
        return False                                                                  # Indica fallo sin intentar enviar.

    try:                                                                              # Bloque de envío real.
        msg = MIMEMultipart()                                                         # Crea el contenedor del mensaje.
        msg["From"] = f"{sender_name} <{from_addr}>"                                  # Setea el remitente con nombre.
        msg["To"] = (to_email or "").strip()                                          # Limpia destinatario de espacios.
        if os.getenv("EMAIL_REPLY_TO"):                                               # Si se definió Reply-To...
            msg["Reply-To"] = os.getenv("EMAIL_REPLY_TO")                             # Añade cabecera Reply-To.
        msg["Subject"] = subject                                                      # Setea el asunto.
        msg.attach(MIMEText(body, "plain", "utf-8"))                                  # Adjunta cuerpo de texto UTF-8.
        timeout = float(os.getenv("SMTP_TIMEOUT", "30"))   # timeout configurable (30s por defecto)
        server = _smtp_connect_ipv4(host, port, timeout)   # crea conexión SMTP forzando IPv4 (evita IPv6)
        if port == 587:                                    # si estamos en STARTTLS (puerto 587)
            server.ehlo()                                  # saludo EHLO inicial
            server.starttls(context=create_default_context())  # eleva a TLS con contexto seguro
            server.ehlo()                                  # EHLO posterior según buenas prácticas
        server.login(user, pwd)                                                       # Autentica con usuario/contraseña de aplicación.
        server.sendmail(from_addr, [msg["To"]], msg.as_string())                      # Envía el mensaje crudo.
        server.quit()                                                                 # Cierra la conexión SMTP.
        logger.info(f"Gmail SMTP → enviado a {msg['To']}")                            # Loguea éxito del envío.
        return True                                                                   # Devuelve True como éxito.
    except Exception as e:                                                            # Captura cualquier excepción.
        logger.exception(f"Gmail SMTP → excepción enviando a {to_email}: {e}")        # Traza de error detallada.
        return False                                                                  # Devuelve False como fallo.

def _send_html_via_gmail(to_email: str, subject: str, html_body: str, text_fallback: str = "") -> bool:
    """Envía HTML usando Gmail SMTP, incluyendo parte de texto plano como multipart/alternative."""
    host = os.getenv("EMAIL_HOST", "smtp.gmail.com")                                  # Host SMTP Gmail.
    port = int(os.getenv("EMAIL_PORT", "587"))                                        # Puerto TLS.
    user = os.getenv("EMAIL_USER", "")                                                # Usuario Gmail.
    pwd  = os.getenv("EMAIL_PASS", "")                                                # Contraseña de aplicación.
    sender_name = os.getenv("EMAIL_SENDER_NAME", "RSVP")                              # Nombre remitente visible.
    from_addr = os.getenv("EMAIL_FROM", user)                                         # Dirección From.

    if not (user and pwd and from_addr):                                              # Verifica configuración mínima.
        logger.error("Gmail SMTP no está configurado (EMAIL_USER/EMAIL_PASS/EMAIL_FROM).")  # Error de configuración.
        return False                                                                  # Retorna fallo.

    try:                                                                              # Bloque de envío real.
        msg = MIMEMultipart("alternative")                                            # Contenedor multiparte (texto + HTML).
        msg["From"] = f"{sender_name} <{from_addr}>"                                  # Remitente con nombre.
        msg["To"] = (to_email or "").strip()                                          # Limpia destinatario.
        if os.getenv("EMAIL_REPLY_TO"):                                               # Si hay Reply-To configurado...
            msg["Reply-To"] = os.getenv("EMAIL_REPLY_TO")                             # Añade cabecera Reply-To.
        msg["Subject"] = subject                                                      # Asunto del mensaje.

        if text_fallback:                                                             # Si tenemos fallback de texto...
            msg.attach(MIMEText(text_fallback, "plain", "utf-8"))                     # Adjunta parte de texto plano primero (mejor deliverability).
        msg.attach(MIMEText(html_body, "html", "utf-8"))                              # Adjunta el cuerpo HTML como segunda parte.

        timeout = float(os.getenv("SMTP_TIMEOUT", "30"))                                # fija un timeout razonable (30s)
        server = _smtp_connect_ipv4(host, port, timeout)                                # abre conexión forzando IPv4
        if port == 587:                                                                    # si usamos STARTTLS (587)
            server.ehlo()                                                               # EHLO inicial
            server.starttls(context=create_default_context())                           # activa TLS con contexto seguro
            server.ehlo()                                                               # EHLO posterior
        server.login(user, pwd)                                                       # Inicia sesión.
        server.sendmail(from_addr, [msg["To"]], msg.as_string())                      # Envía el correo.
        server.quit()                                                                 # Cierra conexión.
        logger.info(f"Gmail SMTP (HTML) → enviado a {msg['To']}")                     # Log de éxito.
        return True                                                                   # Éxito.
    except Exception as e:                                                            # Si algo falla...
        logger.exception(f"Gmail SMTP (HTML) → excepción enviando a {to_email}: {e}") # Traza de error.
        return False                                                                  # Fallo.

def _send_html_via_brevo_api(to_email: str, subject: str, html_body: str, text_fallback: str, to_name: str = "") -> bool:
    """Envía un correo usando la API HTTPS de Brevo, incluyendo nombre de destinatario y Reply-To opcional."""
    # Lee la configuración necesaria de las variables de entorno.
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("EMAIL_FROM")
    sender_name = os.getenv("EMAIL_SENDER_NAME")

    # Construye el cuerpo (payload) de la petición a la API de Brevo.
    payload = {
        "sender": {"email": from_email, "name": sender_name},
        "to": [{"email": (to_email or '').strip(), "name": (to_name or '').strip()}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_fallback or "Open with an HTML-capable client."
    }
    
    # Añade la cabecera 'Reply-To' si está definida en el entorno, para que las respuestas vayan a otro correo.
    reply_to = os.getenv("EMAIL_REPLY_TO", "").strip()
    if reply_to:
        payload["replyTo"] = {"email": reply_to, "name": sender_name}

    # Define las cabeceras HTTP requeridas para la autenticación y el formato de datos.
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Realiza la petición POST a la API de Brevo para enviar el correo.
    try:
        resp = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=15)
        
        # Verifica si la respuesta de la API fue exitosa (código 2xx).
        if 200 <= resp.status_code < 300:
            logger.info(f"Brevo API → enviado correctamente a {to_name} <{to_email}>")
            return True
        
        # Si hubo un error, lo registra con detalles para facilitar la depuración.
        logger.error(f"Brevo API error -> status={resp.status_code} body={resp.text}")
        return False
    except Exception as e:
        # Captura cualquier excepción (ej. timeout, error de red) y la registra.
        logger.exception(f"Brevo API → excepción enviando a {to_email}: {e}")
        return False

# =================================================================================
# ✉️ ROUTER: envío HTML (Brevo via API / Gmail SMTP)
# =================================================================================
def send_email_html(to_email: str, subject: str, html_body: str, text_fallback: str = "", to_name: str = "") -> bool:
    """Router principal para enviar correos HTML, priorizando Brevo."""
    # Si el modo DRY_RUN está activo, solo se simula el envío y se registra en logs.
    if DRY_RUN:
        logger.info(f"[DRY_RUN] (HTML) Simular envío a {to_name} <{to_email}> | Asunto: {subject}")
        return True

    # Se establece 'brevo' como el proveedor por defecto si no se especifica otro.
    provider = os.getenv("EMAIL_PROVIDER", "brevo").lower()

    # Enruta al motor de envío correspondiente según el proveedor configurado.
    if provider == "brevo":
        return _send_html_via_brevo_api(to_email, subject, html_body, text_fallback, to_name)

    if provider == "gmail":
        return _send_html_via_gmail(to_email, subject, html_body, text_fallback)

    # Si el proveedor no es 'brevo' ni 'gmail', se registra un error explícito. No hay fallback.
    logger.error(f"EMAIL_PROVIDER inválido o no soportado: {provider}")
    return False

# =================================================================================
# ✉️ ROUTER: envío TEXTO (Brevo via API / Gmail SMTP / SendGrid legacy)
# =================================================================================
def send_email(to_email: str, subject: str, body: str, to_name: str = "") -> bool:
    """Router principal para enviar correos de texto plano."""
    # Simula el envío si DRY_RUN está activado.
    if DRY_RUN:
        logger.info(f"[DRY_RUN] (TXT) Simular envío a {to_name} <{to_email}> | Asunto: {subject}\n{body}")
        return True
    
    # Usa 'brevo' como proveedor por defecto para correos de texto también.
    provider = os.getenv("EMAIL_PROVIDER", "brevo").lower()

    if provider == "brevo":
        # Convierte el texto plano a un HTML simple para enviarlo vía la API de Brevo.
        html_body = f"<pre style='font-family:monospace; white-space:pre-wrap;'>{html.escape(body)}</pre>"
        return _send_html_via_brevo_api(to_email, subject, html_body, text_fallback=body, to_name=to_name)

    if provider == "gmail":
        return _send_plain_via_gmail(to_email, subject, body)

    # Mantiene SendGrid como fallback solo para el envío de texto plano por compatibilidad.
    if provider == "sendgrid":
        api_key = os.getenv("SENDGRID_API_KEY", "")
        from_email = os.getenv("EMAIL_FROM", "")
        if not api_key or not from_email:
            logger.error("SendGrid (TXT): falta SENDGRID_API_KEY o EMAIL_FROM.")
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, From
        except ImportError:
            logger.error("SendGrid no instalado. Usa EMAIL_PROVIDER=brevo o gmail.")
            return False

        message = Mail(
            from_email=From(from_email, os.getenv("EMAIL_SENDER_NAME", "RSVP")),
            to_emails=to_email,
            subject=subject,
            plain_text_content=body,
        )
        try:
            sg = SendGridAPIClient(api_key)
            resp = sg.send(message)
            if 200 <= resp.status_code < 300:
                logger.info(f"SendGrid TXT → enviado a {to_email}")
                return True
            logger.error(f"SendGrid TXT error -> status={resp.status_code} body={getattr(resp, 'body', None)}")
            return False
        except Exception as e:
            logger.exception(f"SendGrid TXT → excepción enviando a {to_email}: {e}")
            return False
    
    logger.error(f"EMAIL_PROVIDER inválido o no soportado para texto: {provider}")
    return False

# =================================================================================
# 🧩 Helpers de alto nivel (API simple para el resto del backend)                      # Funciones de alto nivel.
# =================================================================================
def send_rsvp_reminder_email(to_email: str, guest_name: str, invited_to_ceremony: bool, language: str | Enum, deadline_dt: datetime) -> bool:
    """Envía recordatorio en texto plano (i18n) con fecha límite y CTA opcional."""   # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en") # Normaliza entrada Enum/str.
    lang_map = TEMPLATES.get(lang_value) or TEMPLATES.get("en", {})                   # Obtiene bundle o EN.
    if not lang_map:                                                                  # Si ni EN existe…
        logger.error("TEMPLATES no contiene definiciones mínimas para 'en'.")         # Log crítico de config.
        return False                                                                  # Abortamos.
    safe_lang = lang_value if lang_value in SUPPORTED_LANGS else "en"                 # Asegura idioma soportado.
    deadline_str = format_deadline(deadline_dt, safe_lang)                            # Formatea fecha límite.
    cta_line = lang_map.get("cta", "👉 Open: {url}").format(url=RSVP_URL) if RSVP_URL else ""  # CTA si hay RSVP_URL.
    key = "reminder_both" if invited_to_ceremony else "reminder_reception"            # Selección de plantilla.
    body = lang_map.get(key, "Please confirm your attendance.\n{cta}").format(        # Rellena plantilla.
        name=guest_name, deadline=deadline_str, cta=cta_line                          # Variables nombradas.
    )                                                                                 # Cierre format.
    subject = SUBJECTS["reminder"].get(lang_value, SUBJECTS["reminder"]["en"])        # Asunto i18n.
    return send_email(to_email=to_email, subject=subject, body=body, to_name=guest_name) # Envío texto plano, pasando el nombre.

def send_recovery_email(to_email: str, guest_name: str, guest_code: str, language: str | Enum) -> bool:
    """Envía correo de recuperación de código de invitado en texto plano (i18n)."""   # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en") # Normaliza idioma.
    lang_map = TEMPLATES.get(lang_value) or TEMPLATES.get("en", {})                   # Obtiene bundle o EN.
    if not lang_map:                                                                  # Validación mínima.
        logger.error("TEMPLATES no contiene definiciones mínimas para 'en'.")         # Log crítico.
        return False                                                                  # Abortamos.
    cta_line = lang_map.get("cta", "👉 Open: {url}").format(url=RSVP_URL) if RSVP_URL else ""  # CTA opcional.
    body = lang_map.get("recovery", "Your guest code is: {guest_code}\n{cta}").format( # Rellena plantilla.
        name=guest_name, guest_code=guest_code, cta=cta_line                          # Variables.
    )                                                                                 # Cierre format.
    subject = SUBJECTS["recovery"].get(lang_value, SUBJECTS["recovery"]["en"])        # Asunto i18n.
    return send_email(to_email=to_email, subject=subject, body=body, to_name=guest_name) # Envío texto plano, pasando el nombre.

def send_magic_link_email(to_email: str, language: str | Enum, magic_url: str) -> bool:
    """Envía el correo de Magic Link usando plantilla HTML (i18n) con logs y fallback i18n.
    - language puede venir como Enum, str, vacío o con variante regional (ro-RO, en-US, es-419).
    - Objetivo: conservar RO/ES/EN cuando corresponde y caer a EN solo si todo falla.
    """

    # ─────────────────────────────────────────────────────────────────────────────
    # BLOQUE 1 · Normalización defensiva de idioma (manteniendo EN como fallback)
    # ─────────────────────────────────────────────────────────────────────────────
    _raw_lang = getattr(language, "value", language)          # Acepta Enum(.value) o str/None.
    _lang = (_raw_lang or "").strip().lower()                 # Minúsculas y trimming; None → "".

    if not _lang:                                             # Si viene vacío, usa fallback inmediato…
        _lang = "en"                                          # …EN (idioma por defecto del sistema).

    if "-" in _lang:                                          # Si viene con región (ro-RO, en-US, es-419)…
        _lang = _lang.split("-")[0]                           # …quédate con el código base: ro/en/es.

    if _lang not in SUPPORTED_LANGS:                          # Si aún no coincide exactamente…
        if _lang.startswith("ro"):                            # Variantes de rumano → ro
            _lang = "ro"
        elif _lang.startswith("es"):                          # Variantes de español → es
            _lang = "es"
        elif _lang.startswith("en"):                          # Variantes de inglés → en
            _lang = "en"
        else:                                                 # Cualquier otro valor raro → fallback final
            _lang = "en"

    lang_code = _lang                                         # "es" | "en" | "ro" (o "en" por fallback final)
    logger.info(f"[MAILER] Preparando envío de Magic Link → to={to_email} lang={lang_code}")

    # ─────────────────────────────────────────────────────────────────────────────
    # BLOQUE 2 · Asunto i18n
    # ─────────────────────────────────────────────────────────────────────────────
    # Usa tu mapa global SUBJECTS["magic_link"] y cae a EN si faltara la clave.
    subject = SUBJECTS["magic_link"].get(lang_code, SUBJECTS["magic_link"]["en"])

    # ─────────────────────────────────────────────────────────────────────────────
    # BLOQUE 3 · Cuerpo HTML (helper existente)
    # ─────────────────────────────────────────────────────────────────────────────
    # Mantiene tu helper actual para construir el HTML con CTA.
    html_out = _build_email_html(lang_code, magic_url)

    # ─────────────────────────────────────────────────────────────────────────────
    # BLOQUE 4 · Fallback de texto plano por idioma (clientes sin HTML)
    # ─────────────────────────────────────────────────────────────────────────────
    text_fallbacks = {
        "es": f"Abre este enlace para confirmar tu asistencia: {magic_url}",
        "ro": f"Deschide acest link pentru a-ți confirma prezența: {magic_url}",
        "en": f"Open this link to confirm your attendance: {magic_url}",
    }
    text_fallback = text_fallbacks.get(lang_code, text_fallbacks["en"])

    # ─────────────────────────────────────────────────────────────────────────────
    # BLOQUE 5 · Envío (helper HTML+texto)
    # ─────────────────────────────────────────────────────────────────────────────
    return send_email_html(
        to_email=to_email,
        subject=subject,
        html_body=html_out,
        text_fallback=text_fallback,
        to_name=""  # En esta función no pasamos nombre del invitado.
    )


def send_guest_code_email(to_email: str, guest_name: str, guest_code: str, language: str | Enum) -> bool:
    """Envía un correo HTML minimalista con el código de invitación (i18n + CTA opcional a Login)."""  # Docstring.

    # ─────────────────────────────────────────────────────────────────────────────
    # Normalización defensiva del idioma (manteniendo EN como fallback por defecto)
    # ─────────────────────────────────────────────────────────────────────────────
    _raw_lang = getattr(language, "value", language)          # Si 'language' es Enum, usa .value; si es str/None, úsalo tal cual.
    _lang = (_raw_lang or "").strip().lower()                 # Convierte a minúsculas, quita espacios; si venía None, queda "".

    if not _lang:                                             # Si llega vacío (None o ""), decide idioma de reserva…
        _lang = "en"                                          # …EN como fallback porque es tu idioma por defecto.

    if "-" in _lang:                                          # Si llega con región (ej. "ro-RO", "en-US", "es-419")…
        _lang = _lang.split("-")[0]                           # …quédate solo con el código base ("ro", "en", "es").

    if _lang not in SUPPORTED_LANGS:                          # Si aún no coincide con los soportados exactos…
        if _lang.startswith("ro"):                            # …cubre variantes de rumano ("ro-ro", "ro_md", etc.)…
            _lang = "ro"                                      # …normaliza a "ro".
        elif _lang.startswith("es"):                          # …cubre variantes de español ("es-419", etc.)…
            _lang = "es"                                      # …normaliza a "es".
        elif _lang.startswith("en"):                          # …cubre variantes de inglés ("en-gb", "en-us")…
            _lang = "en"                                      # …normaliza a "en".
        else:                                                 # …si no es reconocible…
            _lang = "en"                                      # …aplica fallback final EN.

    lang_code = _lang                                         # Idioma final ya normalizado: "es" | "en" | "ro" (o "en" por fallback).
    # ─────────────────────────────────────────────────────────────────────────────

    logger.info(f"[MAILER] Preparando envío de Guest Code → to={to_email} lang={lang_code}")  # Log informativo.

    # -----------------------------
    # Asuntos por idioma (mapa i18n)
    # -----------------------------
    subject_map = {                                           # Diccionario local con asunto por idioma.
        "es": "Tu código de invitación • Boda Jenny & Cristian",   # ES.
        "en": "Your invitation code • Jenny & Cristian Wedding",   # EN.
        "ro": "Codul tău de invitație • Nunta Jenny & Cristian",   # RO.
    }

    subject = subject_map.get(lang_code, subject_map["en"])   # Usa el asunto del idioma; si faltara, cae a EN.

    # ----------------------------------
    # Textos cortos por idioma (saludo + instrucción + etiqueta de botón)
    # ----------------------------------
    greet = "Hola" if lang_code == "es" else ("Bună" if lang_code == "ro" else "Hi")   # Saludo i18n.
    instr = (                                                                           # Instrucción i18n (frase bajo el código).
        "Usa este código en la página de Iniciar sesión." if lang_code == "es"
        else ("Folosește acest cod pe pagina de autentificare." if lang_code == "ro"
              else "Use this code on the login page.")
    )
    btn_label = (                                                                       # Etiqueta del botón (CTA) i18n.
        "Iniciar sesión" if lang_code == "es" else ("Conectare" if lang_code == "ro" else "Log in")
    )

    # ----------------------------------
    # CTA opcional (enlace a login público si está configurado)
    # ----------------------------------
    cta_html = ""                                                                       # Inicializa CTA vacío por defecto.
    if PUBLIC_LOGIN_URL:                                                                 # Si hay URL pública definida…
        from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl              # Importa helpers para manipular querystring.
        parts = list(urlparse(PUBLIC_LOGIN_URL))                                         # Descompone la URL base en partes (scheme, netloc, path, query, etc.).
        q = dict(parse_qsl(parts[4]))                                                    # Convierte la query actual (si existe) en dict.

        q["goto"] = "login"                                                              # Fuerza el deep-link hacia la página de Login en Streamlit.
        q["lang"] = lang_code                                                            # Propaga el idioma del invitado (es/en/ro) para mantener coherencia visual.

        parts[4] = urlencode(q)                                                          # Re-ensambla la query con los nuevos parámetros.
        cta_url = urlunparse(parts)                                                      # Reconstruye la URL final con ?goto=login&lang=xx.

        cta_html = (                                                                     # Construye el HTML del botón accesible (inline CSS).
            f'<p style="margin-top:16px;">'                                              # Margen superior para respirar.
            f'  <a href="{cta_url}" '                                                    # Usa la URL final con los parámetros de deep-link.
            f'     style="display:inline-block;padding:10px 16px;border-radius:8px;'     # Botón con padding y bordes redondeados.
            f'            background:#6D28D9;color:#fff;text-decoration:none;font-weight:600;">'  # Color, contraste y peso de fuente.
            f'    {btn_label}'                                                           # Etiqueta i18n del botón (ES/EN/RO).
            f'  </a>'                                                                    # Cierre del enlace.
            f'</p>'                                                                      # Cierre del contenedor <p>.
        )


    # ----------------------------------
    # Cuerpo HTML del email (simple, seguro y responsive básico)
    # ----------------------------------
    html_body = (                                                                         # Plantilla HTML mínima.
        f'<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'            line-height:1.6;color:#0F172A;font-size:16px;">'
        f'  <p>{greet} {html.escape(guest_name)}</p>'                                     # Saludo + nombre (escapado por seguridad XSS).
        f'  <p style="margin:0 0 8px 0;">{instr}</p>'                                     # Instrucción corta.
        f'  <p style="font-size:24px;letter-spacing:1px;word-break:break-all;'
        f'            background:#F1F5F9;border:1px solid #E2E8F0;border-radius:8px;'
        f'            padding:12px 16px;display:inline-block;">'
        f'    <strong>{html.escape(guest_code)}</strong>'                                 # Código destacado y escapado.
        f'  </p>'
        f'  {cta_html}'                                                                   # Inserta CTA si existe.
        f'  <p style="margin-top:20px;color:#475569;font-size:14px;">'
        f'    Jenny & Cristian'
        f'  </p>'
        f'</div>'
    )

    # ----------------------------------
    # Versión de texto plano (fallback para clientes sin HTML)
    # ----------------------------------
    if lang_code == "es":                                                                 # Texto plano ES.
        text_fallback = (
            f"Hola {guest_name}\n\n"
            f"Tu código de invitación es: {guest_code}\n\n"
            f"{instr}\n"
            f"{('Login: ' + cta_url) if PUBLIC_LOGIN_URL else ''}\n"
        )
    elif lang_code == "ro":                                                               # Texto plano RO.
        text_fallback = (
            f"Bună {guest_name}\n\n"
            f"Codul tău de invitație este: {guest_code}\n\n"
            f"{instr}\n"
            f"{('Autentificare: ' + cta_url) if PUBLIC_LOGIN_URL else ''}\n"
        )
    else:                                                                                 # Texto plano EN (fallback por defecto).
        text_fallback = (
            f"Hi {guest_name}\n\n"
            f"Your invitation code is: {guest_code}\n\n"
            f"{instr}\n"
            f"{('Login: ' + cta_url) if PUBLIC_LOGIN_URL else ''}\n"
        )

    # ----------------------------------
    # Envío (helper HTML + texto)
    # ----------------------------------
    return send_email_html(                                                               # Llama al helper central de envío.
        to_email=to_email,                                                                # Correo de destino.
        subject=subject,                                                                  # Asunto i18n.
        html_body=html_body,                                                              # Cuerpo HTML.
        text_fallback=text_fallback,                                                      # Alternativa en texto plano.
        to_name=guest_name                                                                # Nombre del invitado para personalizar encabezados.
    )                                                                                     # Devuelve True/False según resultado.


def send_confirmation_email(to_email: str, language: str | Enum, summary: dict) -> bool:
    """Envía correo de confirmación de RSVP en HTML con resumen (i18n, seguro contra XSS)."""  # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en") # Normaliza idioma (Enum o str).
    lang_code = lang_value if lang_value in SUPPORTED_LANGS else "en"                  # Garantiza idioma.

    subject = SUBJECTS["confirmation"].get(lang_code, SUBJECTS["confirmation"]["en"])  # Asunto i18n.

    guest_name = html.escape(summary.get("guest_name", ""))                            # Escapa nombre (XSS-safe).
    invite_scope = summary.get("invite_scope", "reception-only")                       # Alcance de invitación.
    attending = summary.get("attending", None)                                         # Asistencia (True/False/None).
    companions = summary.get("companions", [])                                         # Lista de acompañantes.
    allergies = html.escape(summary.get("allergies", "")) if summary.get("allergies") else ""  # Alergias.
    notes = html.escape(summary.get("notes", "")) if summary.get("notes") else ""      # Notas.
    event_date = html.escape(str(summary.get("event_date", "")))                       # Fecha evento (string).
    headcount = html.escape(str(summary.get("headcount", "")))                         # Número asistentes (string).
    menu_choice = html.escape(str(summary.get("menu_choice", "")))                     # Menú (string).

    scope_value = {                                                                    # Traducciones del alcance.
        "ceremony+reception": {"es":"Ceremonia + Recepción","en":"Ceremony + Reception","ro":"Ceremonie + Recepție"},
        "reception-only": {"es":"Solo Recepción","en":"Reception only","ro":"Doar Recepție"},
    }                                                                                  # Fin mapa.
    att_map = {                                                                        # Traducciones de asistencia.
        True:  {"es":"Asistencia: Sí","en":"Attending: Yes","ro":"Participare: Da"},
        False: {"es":"Asistencia: No","en":"Attending: No","ro":"Participare: Nu"},
        None:  {"es":"Asistencia: —","en":"Attending: —","ro":"Participare: —"},
    }                                                                                  # Fin mapa.

    greet = "Hola" if lang_code == "es" else ("Bună" if lang_code == "ro" else "Hi")  # Saludo por idioma.
    html_parts = []                                                                     # Acumula líneas HTML.
    html_parts.append("<div style='font-family:Inter,Arial,sans-serif;line-height:1.6'>")  # Contenedor principal.
    html_parts.append(f"<h2>{subject}</h2>")                                            # Título con asunto.
    html_parts.append(f"<p>{greet} {guest_name},</p>")                                  # Saludo.
    html_parts.append(                                                                  # Línea de invitación.
        f"<p>{ {'es':'Invitación: ', 'en':'Invitation: ', 'ro':'Invitație: '}.get(lang_code,'Invitation: ') }"
        f"{scope_value.get(invite_scope, scope_value['reception-only']).get(lang_code)}</p>"
    )                                                                                   # Cierre línea.
    html_parts.append(f"<p>{att_map.get(attending, att_map[None]).get(lang_code)}</p>") # Asistencia.
    html_parts.append(f"<p><strong>{'Fecha del evento' if lang_code=='es' else ('Data evenimentului' if lang_code=='ro' else 'Event date')}:</strong> {event_date}</p>" if event_date else "")  # Fecha.
    html_parts.append(f"<p><strong>{'Invitados' if lang_code=='es' else ('Invitați' if lang_code=='ro' else 'Guests')}:</strong> {headcount}</p>" if headcount else "")  # Headcount.
    html_parts.append(f"<p><strong>{'Menú' if lang_code=='es' else ('Meniu' if lang_code=='ro' else 'Menu')}:</strong> {menu_choice}</p>" if menu_choice else "")  # Menú.

    if companions:                                                                      # Si hay acompañantes…
        html_parts.append(
            f"<h3>👥 { 'Acompañantes' if lang_code=='es' else ('Însoțitori' if lang_code=='ro' else 'Companions') }</h3>"
        )                                                                                # Título de sección.
        html_parts.append("<ul>")                                                        # Lista HTML.
        for c in companions:                                                             # Itera acompañantes.
            label = html.escape(c.get("label",""))                                       # Escapa etiqueta.
            name = html.escape(c.get("name",""))                                         # Escapa nombre.
            allergens = html.escape(c.get("allergens","")) if c.get("allergens") else "" # Escapa alérgenos.
            html_parts.append(                                                           # Ítem de lista.
                f"<li><strong>{name}</strong> — {label} — "
                f"{('Alergias:' if lang_code=='es' else ('Alergii:' if lang_code=='ro' else 'Allergies:'))} "
                f"{allergens or '—'}</li>"
            )                                                                            # Cierre ítem.
        html_parts.append("</ul>")                                                       # Cierra lista.

    if allergies:                                                                        # Si hay alergias…
        html_parts.append(                                                               # Línea de alergias.
            f"<p>{('Alergias' if lang_code=='es' else ('Alergii' if lang_code=='ro' else 'Allergies'))}: {allergies}</p>"
        )                                                                                # Cierre línea.

    if notes:                                                                            # Si hay notas…
        html_parts.append(                                                               # Línea de notas.
            f"<p>{('Notas' if lang_code=='es' else ('Note' if lang_code=='ro' else 'Notes'))}: {notes}</p>"
        )                                                                                # Cierre línea.

    html_parts.append("</div>")                                                          # Cierra contenedor HTML.
    html_body = "".join(html_parts)                                                      # Une HTML final.

    companions_text = ""                                                                 # Texto de acompañantes (fallback).
    if companions:                                                                       # Si hay lista…
        companions_text = "\n".join(                                                     # Construye items en texto plano.
            f"- {html.escape(c.get('name',''))} ({html.escape(c.get('label',''))}) — "
            f"{('Alergias: ' if lang_code=='es' else ('Alergii: ' if lang_code=='ro' else 'Allergies: '))}"
            f"{html.escape(c.get('allergens','')) or '—'}"
            for c in companions
        )                                                                                # Cierre join.

    tf = []                                                                              # Partes de texto plano.
    tf.append(f"{greet} {guest_name},")                                                 # Saludo.
    tf.append(
        "¡Gracias por confirmar tu asistencia!" if lang_code=="es"
        else ("Îți mulțumim că ai confirmat prezența!" if lang_code=="ro" else "Thank you for confirming your attendance!")
    )                                                                                    # Mensaje de agradecimiento.
    tf.append(
        f"{'Invitación' if lang_code=='es' else ('Invitație' if lang_code=='ro' else 'Invitation')}: "
        f"{scope_value.get(invite_scope, scope_value['reception-only']).get(lang_code)}"
    )                                                                                    # Línea de invitación.
    tf.append(att_map.get(attending, att_map[None]).get(lang_code))                      # Línea de asistencia.
    if event_date:                                                                       # Fecha si existe…
        tf.append(
            f"{'Fecha del evento: ' if lang_code=='es' else ('Data evenimentului: ' if lang_code=='ro' else 'Event date: ')}{event_date}"
        )                                                                                # Fecha.
    if headcount:                                                                        # Headcount si existe…
        tf.append(
            f"{'Invitados: ' if lang_code=='es' else ('Invitați' if lang_code=='ro' else 'Guests: ')}{headcount}"
        )                                                                                # Headcount.
    if menu_choice:                                                                      # Menú si existe…
        tf.append(
            f"{'Menú: ' if lang_code=='es' else ('Meniu: ' if lang_code=='ro' else 'Menu: ')}{menu_choice}"
        )                                                                                # Menú.
    if companions_text:                                                                  # Lista de acompañantes si existe…
        tf.append(
            ('Acompañantes:\n' if lang_code=='es' else ('Însoțitori:\n' if lang_code=='ro' else 'Companions:\n')) + companions_text
        )                                                                                # Agrega la lista.
    if allergies:                                                                        # Alergias si existe…
        tf.append(
            f"{'Alergias: ' if lang_code=='es' else ('Alergii: ' if lang_code=='ro' else 'Allergies: ')}{allergies}"
        )                                                                                # Alergias.
    if notes:                                                                            # Notas si existe…
        tf.append(
            f"{'Notas: ' if lang_code=='es' else ('Note: ' if lang_code=='ro' else 'Notes: ')}{notes}"
        )                                                                                # Notas.
    tf.append(
        "Te iremos informando con más detalles conforme se acerque la fecha." if lang_code=='es'
        else ("Te vom ține la curent cu mai multe detalii pe măsură ce se apropie data." if lang_code=='ro'
              else "We’ll keep you updated with more details as the date approaches.")
    )                                                                                    # Mensaje final.
    text_fallback = "\n".join(tf)                                                        # Une el texto plano final.

    return send_email_html(                                                              # Envío HTML + fallback.
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_fallback=text_fallback,
        to_name=guest_name # Pasa el nombre del invitado para personalizar el envío.
    )                                                                                    # Retorna True/False.

def send_rsvp_reminder_email_html(to_email: str, guest_name: str, invited_to_ceremony: bool, language: str | Enum, deadline_dt: datetime) -> bool:
    """(Opcional) Envía un recordatorio usando la plantilla HTML (i18n)."""            # Docstring.
    lang_value = language.value if isinstance(language, Enum) else (language or "en")  # Normaliza idioma.
    lang_code = lang_value if lang_value in SUPPORTED_LANGS else "en"                  # Asegura idioma soportado.
    cta_url = RSVP_URL or "#"                                                          # Usa RSVP_URL o '#'.
    html_out = _build_email_html(lang_code, cta_url)                                   # Construye HTML base.
    deadline_str = format_deadline(deadline_dt, lang_code)                             # Formatea fecha límite.
    html_out = html_out.replace("</p>", f"<br/><strong>{deadline_str}</strong></p>", 1) # Inserta deadline visible.
    subject = SUBJECTS["reminder"].get(lang_code, SUBJECTS["reminder"]["en"])          # Asunto i18n.
    return send_email_html(to_email=to_email, subject=subject, html_body=html_out, to_name=guest_name) # Envío HTML, pasando el nombre.

# =================================================================================
# 🔁 Compatibilidad retro: alias con firma antigua                                     # Mantiene routers viejos funcionando.
# =================================================================================
def send_magic_link(email: str, url: str, lang: str = "en") -> bool:                   # Wrapper retrocompatible.
    """Wrapper retrocompatible: firma antigua → nueva función HTML."""                 # Docstring.
    return send_magic_link_email(to_email=email, language=lang, magic_url=url)         # Redirige al helper moderno.