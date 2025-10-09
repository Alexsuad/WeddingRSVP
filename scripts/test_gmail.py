# scripts/test_gmail.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Añade la raíz del proyecto al path para poder importar 'app'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Carga las variables de entorno desde el archivo .env
load_dotenv()
print("✅ Archivo .env cargado.")

# Ahora importa el mailer de tu aplicación
from app import mailer
from loguru import logger

# --- DATOS DE PRUEBA ---
# Usamos tu propio correo como destinatario de la prueba.
TEST_TO_EMAIL = "nalexsua75@gmail.com"
TEST_GUEST_NAME = "Alex (Prueba Local)"
TEST_GUEST_CODE = "TEST-1234"
TEST_LANG = "es"

logger.info(f"Intentando enviar correo de prueba a: {TEST_TO_EMAIL}")
logger.info(f"Usando el proveedor: {os.getenv('EMAIL_PROVIDER')}")
logger.info(f"Usando el usuario: {os.getenv('EMAIL_USER')}")
logger.info(f"DRY_RUN está en: {os.getenv('DRY_RUN')}")

try:
    # Llama a la misma función que usa tu API para enviar el código
    success = mailer.send_guest_code_email(
        to_email=TEST_TO_EMAIL,
        guest_name=TEST_GUEST_NAME,
        guest_code=TEST_GUEST_CODE,
        language=TEST_LANG,
    )

    if success:
        logger.success("✅ Correo enviado con éxito (según el mailer). Revisa tu bandeja de entrada.")
    else:
        logger.error("❌ El mailer devolvió 'False'. Hubo un error durante el envío. Revisa los logs anteriores.")

except Exception as e:
    logger.exception("💥 Ocurrió una excepción inesperada durante el envío del correo.")
    print("\n--- POSIBLES CAUSAS ---")
    print("1. ¿La contraseña en EMAIL_PASS es una 'Contraseña de Aplicación' de 16 dígitos de Google?")
    print("2. ¿La Autenticación en Dos Pasos (2FA) está activada en esa cuenta de Google?")
    print("3. ¿Hay algún firewall (Windows, antivirus) bloqueando la conexión al puerto 587?")
    print("4. ¿Has recibido un email de 'Alerta de seguridad' de Google en tu cuenta indicando un intento de inicio de sesión bloqueado?")