# ─────────────────────────────────────────────────────────
# TEST OFFLINE · Simulación de envíos con logs (sin SMTP)
# ─────────────────────────────────────────────────────────
"""
Propósito
- Probar el mailer en local SIN internet (DRY_RUN=1) y ver logs del idioma final.
- Casos: RO con formatos distintos (ro / RO / ro-RO) y fallback EN (language vacío).

Cómo usar
- Asegúrate de tener DRY_RUN=1 en tu .env.
- Ejecuta:  python scripts/test_mail_offline.py
- Observa la consola: debe mostrar lang=ro en los casos 1 y 2, y lang=en en el caso 3.
"""

# ── BLOQUE 1 · Carga de entorno y proyecto ───────────────────────────────────
import os, sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
load_dotenv()

# ── BLOQUE 2 · Importar mailer y logger ──────────────────────────────────────
from loguru import logger
from app import mailer

# ── BLOQUE 3 · Parámetros de prueba ──────────────────────────────────────────
TO_EMAIL    = os.getenv("TEST_TO", os.getenv("EMAIL_USER"))
GUEST_NAME  = "Invitat Test"
GUEST_CODE  = "ABC-123"
MAGIC_URL   = os.getenv("PUBLIC_LOGIN_URL", "https://rsvp.local/login")

def main():
    logger.info(f"→ DRY_RUN={os.getenv('DRY_RUN')} (1=simula, 0=envío real)")
    logger.info(f"→ Provider declarado: {os.getenv('EMAIL_PROVIDER')}  (no se usará con DRY_RUN=1)")
    logger.info(f"→ Destinatario: {TO_EMAIL}")

    # Caso 1: guest_code con 'ro-RO' → debe normalizar a 'ro'
    logger.info("Caso 1 · guest_code con language='ro-RO' (esperado lang=ro)")
    ok1 = mailer.send_guest_code_email(
        to_email=TO_EMAIL,
        guest_name=GUEST_NAME,
        guest_code=GUEST_CODE,
        language="ro-RO"
    )
    logger.info(f"guest_code (ro-RO) → enviado={ok1}")

    # Caso 2: magic_link con 'RO' mayúsculas → debe normalizar a 'ro'
    logger.info("Caso 2 · magic_link con language='RO' (esperado lang=ro)")
    ok2 = mailer.send_magic_link_email(
        to_email=TO_EMAIL,
        language="RO",
        magic_url=MAGIC_URL
    )
    logger.info(f"magic_link (RO) → enviado={ok2}")

    # Caso 3: guest_code sin language → debe caer a fallback EN
    logger.info("Caso 3 · guest_code sin language (esperado lang=en por fallback)")
    ok3 = mailer.send_guest_code_email(
        to_email=TO_EMAIL,
        guest_name=GUEST_NAME,
        guest_code=GUEST_CODE,
        language=None
    )
    logger.info(f"guest_code (fallback EN) → enviado={ok3}")

if __name__ == "__main__":
    try:
        main()
        logger.success("✅ Prueba OFFLINE completada. Revisa que los logs muestren lang=ro / lang=en según el caso.")
    except Exception:
        logger.exception("💥 Error durante la prueba OFFLINE.")
