# app/utils/alerts.py                                                                 # Ruta del archivo (nuevo).

# ==================================================================================== # Separador visual.
# 📣 Utilidad de alertas por correo (admin)                                            # Título descriptivo.
# ------------------------------------------------------------------------------------ # Descripción.
# - Envía un email de alerta al administrador usando el mailer del proyecto.          # Función.
# - Si no hay ADMIN_ALERT_EMAIL definido, sólo registra un warning (no rompe).        # Comportamiento seguro.
# ==================================================================================== # Cierre encabezado.

import os                                                                              # Importa os para leer variables de entorno.
from loguru import logger                                                              # Logger para trazas.
from app import mailer                                                                 # Reutiliza tu mailer central (send_email).

# Lee el correo del admin desde entorno (opcional).                                    # Comentario: variable de entorno.
ADMIN_ALERT_EMAIL = os.getenv("ADMIN_ALERT_EMAIL")                                     # Puede ser None si no está definido.

def alert_admin(subject: str, body: str) -> bool:                                      # Define la función pública de alerta.
    """
    Envía un correo de alerta al admin.                                                # Docstring: propósito.
    Devuelve True si se envió, False en caso contrario.                                # Docstring: retorno.
    """                                                                                # Fin docstring.
    if not ADMIN_ALERT_EMAIL:                                                          # Si no hay destinatario configurado...
        logger.warning("ADMIN_ALERT_EMAIL no configurado; se omite envío de alerta.")  # ...avisa en logs y no rompe.
        return False                                                                   # Devuelve False (no enviado).

    try:                                                                               # Intenta enviar el correo.
        ok = mailer.send_email(ADMIN_ALERT_EMAIL, subject, body)                       # Usa send_email(to, subject, body).
        if ok:                                                                         # Si el envío fue exitoso...
            logger.info(f"Alerta enviada a admin <{ADMIN_ALERT_EMAIL}>")               # ...lo registra como info.
        else:                                                                          # Si send_email devolvió False...
            logger.error(f"Fallo enviando alerta a <{ADMIN_ALERT_EMAIL}>")            # ...registra error.
        return ok                                                                      # Devuelve el resultado.
    except Exception as e:                                                             # Si ocurre una excepción inesperada...
        logger.exception(f"Excepción enviando alerta admin: {e}")                      # ...registra stacktrace.
        return False                                                                    # Devuelve False.
