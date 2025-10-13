# ─────────────────────────────────────────────────────────
# TEST LOCAL · Mailer directo (usa tu .env)
# ─────────────────────────────────────────────────────────
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── BLOQUE 1 · Importación proyecto y .env ───────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
load_dotenv()  # Carga variables del .env (EMAIL_*, DRY_RUN, PUBLIC_LOGIN_URL, etc.)

# ── BLOQUE 2 · Importar mailer y logger ──────────────────────────────────────
from app import mailer
from loguru import logger

# ── BLOQUE 3 · Datos de prueba (personalizables por .env) ────────────────────
TO_EMAIL = os.getenv("TEST_TO", os.getenv("EMAIL_USER"))      # Si no se define TEST_TO, usa tu remitente.
GUEST_NAME = "Invitat Test"
GUEST_CODE = "ABC-123"
MAGIC_URL = os.getenv("PUBLIC_LOGIN_URL", "https://rsvp.local/login")

# ── BLOQUE 4 · Info de contexto (útil en consola) ────────────────────────────
logger.info(f"→ Destinatario: {TO_EMAIL}")
logger.info(f"→ Provider: {os.getenv('EMAIL_PROVIDER')}")
logger.info(f"→ DRY_RUN: {os.getenv('DRY_RUN')} (1=simula, 0=envío real)")

def main():
    # ── Caso 1: guest_code en RO con variante regional ───────────────────────
    logger.info("Caso 1 · guest_code con language='ro-RO' (debe normalizar a 'ro').")
    ok1 = mailer.send_guest_code_email(
        to_email=TO_EMAIL,
        guest_name=GUEST_NAME,
        guest_code=GUEST_CODE,
        language="ro-RO",  # Variante regional; tu mailer la normaliza a 'ro'
    )
    logger.info(f"guest_code enviado: {ok1}")

    # ── Caso 2: magic_link en RO en mayúsculas ───────────────────────────────
    logger.info("Caso 2 · magic_link con language='RO' (debe normalizar a 'ro').")
    ok2 = mailer.send_magic_link_email(
        to_email=TO_EMAIL,
        language="RO",     # Mayúsculas; tu mailer la normaliza a 'ro'
        magic_url=MAGIC_URL,
    )
    logger.info(f"magic_link enviado: {ok2}")

    # ── Caso 3: fallback EN (sin language) ───────────────────────────────────
    logger.info("Caso 3 · guest_code sin language (debe caer a EN por defecto).")
    ok3 = mailer.send_guest_code_email(
        to_email=TO_EMAIL,
        guest_name=GUEST_NAME,
        guest_code=GUEST_CODE,
        language=None,     # Forzamos vacío → debe caer a EN (tu preferencia)
    )
    logger.info(f"guest_code (fallback EN) enviado: {ok3}")

if __name__ == "__main__":
    try:
        main()
        logger.success("✅ Pruebas terminadas. Revisa consola (DRY_RUN=1) o tu bandeja (DRY_RUN=0).")
    except Exception:
        logger.exception("💥 Excepción durante la prueba local.")
