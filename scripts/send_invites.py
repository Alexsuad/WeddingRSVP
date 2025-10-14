# scripts/send_invites.py
# =================================================================================
# ✉️ Envío inicial de invitaciones (MVP)
# - Selecciona invitados con email y sin 'last_reminder_at' para no duplicar envíos.
# - Construye asunto/cuerpo por idioma (ES/RO/EN) usando EVENT_DATE_HUMAN y RSVP_URL.
# - Respeta DRY_RUN=1 del .env para probar sin enviar.
# =================================================================================

import os                                   # Acceso a variables de entorno (.env).
from datetime import datetime               # Sello de fecha/hora para marcar envíos.
from zoneinfo import ZoneInfo               # Zona horaria coherente con el evento.
from dotenv import load_dotenv              # Carga .env en desarrollo.
from loguru import logger                   # Logs bonitos para consola/archivo.

from app.db import SessionLocal             # Sesión SQLAlchemy de tu app.
from app.models import Guest                # Modelo ORM de invitados.
from app.mailer import send_email           # Envío real por SendGrid.

# --- Configuración de entorno ---
load_dotenv()                               # Carga variables desde .env si existe.
EVENT_TZ = ZoneInfo(os.getenv("EVENT_TIMEZONE", "Europe/Bucharest"))  # Zona horaria del evento.
RSVP_URL = os.getenv("RSVP_URL", "").strip()                           # URL pública del formulario.
EVENT_DATE_HUMAN = os.getenv("EVENT_DATE_HUMAN", "20 Mayo 2026")       # Fecha legible del evento.
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"                              # Si "1", no envía (solo loguea).

# --- Plantillas simples de invitación (por idioma) ---
SUBJECTS = {                         # Asuntos por idioma.
    "es": "¡Estás invitado! Confirma tu asistencia",
    "ro": "Ești invitat! Confirmă prezența",
    "en": "You’re invited! Please RSVP",
}
BODIES = {                           # Cuerpos por idioma (texto plano).
    "es": lambda name, code: (
        f"Hola {name},\n\n"
        f"¡Nos encantaría contar contigo el {EVENT_DATE_HUMAN}! 🎉\n"
        f"Por favor confirma tu asistencia en {RSVP_URL}.\n\n"
        f"Tu código de invitación es: {code}\n\n"
        f"Un abrazo,\nJenny & Cristian"
    ),
    "ro": lambda name, code: (
        f"Bună {name},\n\n"
        f"Ne-ar plăcea să fii alături de noi pe {EVENT_DATE_HUMAN}! 🎉\n"
        f"Te rugăm să îți confirmi prezența pe {RSVP_URL}.\n\n"
        f"Codul tău de invitație este: {code}\n\n"
        f"Cu drag,\nJenny & Cristian"
    ),
    "en": lambda name, code: (
        f"Hi {name},\n\n"
        f"We’d love to have you with us on {EVENT_DATE_HUMAN}! 🎉\n"
        f"Please RSVP at {RSVP_URL}.\n\n"
        f"Your invitation code is: {code}\n\n"
        f"With love,\nJenny & Cristian"
    ),
}

def main() -> None:
    """Recorre invitados con email y sin last_reminder_at; envía invitación o hace DRY RUN."""
    logger.info("Iniciando envío inicial de invitaciones…")                      # Log de inicio.
    db = SessionLocal()                                                          # Abre sesión DB.
    now = datetime.now(tz=EVENT_TZ)                                              # Fecha/hora actual evento.

    try:
        # Selecciona candidatos: tienen email y nunca se les envió nada (usamos last_reminder_at como marcador MVP).
        guests = (                                                               # Ejecuta consulta.
            db.query(Guest)                                                      # Tabla guests.
            .filter(Guest.email.isnot(None))                                     # Deben tener email.
            .filter(Guest.email != "")                                           # Email no vacío.
            .filter(Guest.last_reminder_at.is_(None))                            # Aún sin marcar envío previo.
            .all()                                                               # Recupera lista.
        )

        logger.info(f"Invitados a invitar (estimado): {len(guests)}")            # Reporta tamaño.

        sent, skipped, errors = 0, 0, 0                                          # Contadores básicos.
        for g in guests:                                                         # Itera cada invitado.
            lang = (getattr(g, "language", None) or "es").value if hasattr(g, "language") else "es"  # Idioma.
            subject = SUBJECTS.get(lang, SUBJECTS["en"])                         # Asunto según idioma.
            body = BODIES.get(lang, BODIES["en"])(g.full_name, g.guest_code)     # Cuerpo con nombre y código.

            if DRY_RUN:                                                          # Si es modo prueba…
                logger.info(f"[DRY_RUN] → {g.email} | {subject}")                # …solo loguea destinatario/asunto.
                skipped += 1                                                    # Suma a omitidos (prueba).
                continue                                                         # Pasa al siguiente.

            ok = send_email(to_email=g.email, subject=subject, body=body)        # Envía email real con SendGrid.
            if ok:                                                               # Si fue exitoso…
                g.last_reminder_at = now                                         # Marca fecha (MVP: usamos este campo).
                db.add(g)                                                        # Asegura en sesión.
                sent += 1                                                        # Incrementa enviados.
            else:                                                                # Si falló envío…
                errors += 1                                                      # Incrementa errores.
                logger.error(f"Fallo al enviar a {g.email}")                     # Log de error.

        db.commit()                                                              # Confirma cambios (marcas de envío).
        logger.info(f"Fin. Enviados={sent}, Simulados/omitidos={skipped}, Errores={errors}")  # Resumen final.

    finally:
        db.close()                                                               # Cierra sesión siempre.

if __name__ == "__main__":                                                       # Punto de entrada CLI.
    main()                                                                       # Ejecuta proceso principal.

