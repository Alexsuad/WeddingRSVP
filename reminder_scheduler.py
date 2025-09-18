# reminder_scheduler.py                                                                  # Nombre del archivo.

# ====================================================================================== # Separador visual.
# ⏰ SCHEDULER DE RECORDATORIOS AUTOMÁTICOS                                               # Título descriptivo.
# -------------------------------------------------------------------------------------- # Descripción.
# - Ejecuta diariamente un job que busca invitados sin confirmar y les envía recordatorio. # Función principal.
# - Añade: alertas a admin, reintentos de envío, lock de proceso, y config por .env.     # Mejoras.
# ====================================================================================== # Cierre encabezado.

import os                                                                                # Para leer variables de entorno.
import time                                                                              # Para sleep en reintentos y timestamps.
from datetime import datetime                                                            # Para manejar fechas y horas.
from zoneinfo import ZoneInfo                                                            # Para timezone nativo (PEP 615).
from apscheduler.schedulers.blocking import BlockingScheduler                            # Scheduler en modo blocking.
from dotenv import load_dotenv                                                           # Carga variables desde .env.
from loguru import logger                                                                # Logger principal.

# Carga .env lo antes posible.                                                           # Comentario.
load_dotenv()                                                                            # Ejecuta carga de entorno.

# Importa componentes de la app.                                                         # Comentario.
from app.db import SessionLocal                                                          # Sesión de BD.
from app.models import Guest                                                             # Modelo Guest.
from app.mailer import build_reminder_body, send_email                                   # Funciones de mailer.
from app.utils.alerts import alert_admin                                                 # Nueva utilidad de alertas.

# -------------------------------------------------------------------------------------- # Configuración de logging a archivo.
os.makedirs("logs", exist_ok=True)                                                       # Asegura carpeta de logs.
logger.add("logs/scheduler_{time}.log", rotation="1 week", retention="4 weeks", level="INFO")  # Rotación semanal.

# -------------------------------------------------------------------------------------- # Lectura y validación de configuración crítica.
RSVP_DEADLINE_STR = os.getenv("RSVP_DEADLINE")                                           # Fecha límite en ISO (YYYY-MM-DD o YYYY-MM-DDTHH:MM).
if not RSVP_DEADLINE_STR:                                                                # Si no está definida...
    logger.critical("Falta RSVP_DEADLINE en entorno. El scheduler no se iniciará.")      # Log crítico.
    raise SystemExit(1)                                                                   # Salida segura con código 1.

try:                                                                                     # Intenta parsear la fecha límite.
    DEADLINE_DT = datetime.fromisoformat(RSVP_DEADLINE_STR)                               # Usa fromisoformat (robusto).
except ValueError as e:                                                                   # Si falla el parseo...
    logger.critical(f"RSVP_DEADLINE inválido: {e}. El scheduler no se iniciará.")         # Log crítico.
    raise SystemExit(1)                                                                   # Salida.

# Valida credenciales mínimas de correo (para operar con normalidad).                     # Comentario.
if not os.getenv("SENDGRID_API_KEY") or not os.getenv("EMAIL_FROM"):                      # Si falta config de correo...
    logger.warning("SENDGRID_API_KEY o EMAIL_FROM no configurados: los envíos fallarán.") # Warning (no detiene scheduler).

# -------------------------------------------------------------------------------------- # Zona horaria y timing del job desde .env.
EVENT_TZ_NAME = os.getenv("SCHED_TZ", "Europe/Bucharest")                                 # TZ configurable (por defecto Bucarest).
EVENT_TIMEZONE = ZoneInfo(EVENT_TZ_NAME)                                                  # Objeto timezone.

def _env_int(name: str, default: int) -> int:                                             # Helper para leer enteros de entorno.
    try:                                                                                  # Intenta convertir a int.
        return int(os.getenv(name, str(default)))                                         # Devuelve el entero o default.
    except ValueError:                                                                    # Si no es entero...
        return default                                                                    # Devuelve default.

SCHED_HOUR = _env_int("SCHED_HOUR", 9)                                                    # Hora local (0-23).
SCHED_MINUTE = _env_int("SCHED_MINUTE", 0)                                                # Minuto (0-59).

# -------------------------------------------------------------------------------------- # Lockfile para evitar instancias concurrentes.
LOCKFILE_PATH = "scheduler.lock"                                                          # Ruta del lockfile.

def acquire_lock() -> bool:                                                               # Intenta crear lockfile exclusivo.
    try:                                                                                  # Usamos O_CREAT|O_EXCL para exclusividad.
        fd = os.open(LOCKFILE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)                 # Crea el archivo si no existe.
        os.write(fd, str(os.getpid()).encode("utf-8"))                                    # Escribe el PID dentro.
        os.close(fd)                                                                       # Cierra descriptor.
        logger.info(f"Lock adquirido ({LOCKFILE_PATH}). PID={os.getpid()}")                # Log info.
        return True                                                                        # Éxito.
    except FileExistsError:                                                                # Si el archivo ya existe...
        logger.error(f"Ya hay un scheduler en ejecución (lock: {LOCKFILE_PATH}).")        # Log error.
        return False                                                                       # Falla.

def release_lock() -> None:                                                                # Elimina lockfile si existe.
    try:                                                                                  # Intenta borrar.
        os.remove(LOCKFILE_PATH)                                                           # Borra el archivo.
        logger.info("Lock liberado.")                                                      # Log info.
    except FileNotFoundError:                                                              # Si no existe...
        pass                                                                               # No hace nada.

# -------------------------------------------------------------------------------------- # Lógica de frecuencia de envío.
def should_send_reminder(today: datetime, last_sent_at: datetime | None) -> bool:          # Decide si enviar según ventana dinámica.
    """
    Incrementa frecuencia al acercarse la fecha límite.                                     # Docstring: resumen.
    >60 días: cada 15 días, 31-60: cada 7 días, 0-30: cada 2 días.                          # Regla de negocio.
    """                                                                                     # Fin docstring.
    if last_sent_at is None:                                                                # Si nunca se envió...
        return True                                                                         # ...envía ahora mismo.

    days_left = (DEADLINE_DT.date() - today.date()).days                                    # Días restantes hasta la fecha límite.

    if days_left > 60:                                                                      # Caso >60 días.
        frequency_days = 15                                                                 # Cada 15 días.
    elif 30 < days_left <= 60:                                                              # Caso 31-60 días.
        frequency_days = 7                                                                  # Cada 7 días.
    elif 0 <= days_left <= 30:                                                              # Caso 0-30 días.
        frequency_days = 2                                                                  # Cada 2 días.
    else:                                                                                   # Si ya pasó la fecha...
        return False                                                                        # ...no enviar más.

    days_since_last = (today.date() - last_sent_at.date()).days                             # Días desde el último envío.
    return days_since_last >= frequency_days                                                # Devuelve si toca enviar.

# -------------------------------------------------------------------------------------- # Envío con reintentos y logging uniforme.
def _send_with_retry(to_email: str, subject: str, body: str, attempts: int = 3, delay_s: float = 1.0) -> bool:
    """
    Envía un email con hasta `attempts` intentos, con espera `delay_s` entre intentos.       # Docstring.
    Devuelve True si alguno de los intentos tiene éxito.                                     # Docstring retorno.
    """                                                                                     # Fin docstring.
    for i in range(1, max(1, attempts) + 1):                                                # Bucle de intentos (al menos 1).
        ok = send_email(to_email=to_email, subject=subject, body=body)                      # Llama al mailer.
        if ok:                                                                              # Si se envió...
            if i > 1:                                                                       # Si fue tras reintento...
                logger.info(f"Reintento {i}/{attempts} OK → {to_email}")                    # Log informa reintento exitoso.
            return True                                                                     # Termina con éxito.
        logger.warning(f"Intento {i}/{attempts} fallido al enviar a {to_email}")            # Log intento fallido.
        time.sleep(delay_s)                                                                 # Espera antes del próximo intento.
    return False                                                                            # Si llegó aquí, fallaron todos.

# -------------------------------------------------------------------------------------- # Job principal del scheduler.
def send_pending_reminders_job():                                                           # Define el job.
    """
    Busca invitados pendientes y envía recordatorio si corresponde.                          # Docstring.
    Registra resumen y envía alerta si hubo errores.                                         # Docstring.
    """                                                                                     # Fin docstring.
    now = datetime.now(tz=EVENT_TIMEZONE)                                                   # Hora actual en TZ del evento.
    logger.info("Iniciando job de envío de recordatorios...")                               # Log de inicio.

    sent_count, skipped_count, error_count = 0, 0, 0                                        # Contadores para resumen.
    db = SessionLocal()                                                                     # Abre sesión de BD.
    try:                                                                                    # Try principal del job.
        pending_guests = db.query(Guest).filter(Guest.confirmed.is_(None)).all()            # Obtiene invitados sin confirmar.
        logger.info(f"{len(pending_guests)} invitados pendientes de confirmación.")         # Log tamaño.

        for guest in pending_guests:                                                        # Itera invitados.
            if not guest.email:                                                             # Si no hay email...
                skipped_count += 1                                                          # Cuenta omitido.
                continue                                                                    # Salta al siguiente.

            if should_send_reminder(now, guest.last_reminder_at):                           # Si corresponde enviar hoy...
                lang_value = guest.language.value if guest.language else "en"               # Idioma preferido o 'en'.
                subject = {                                                                 # Asunto por idioma.
                    "es": "Recordatorio: Confirma tu asistencia a nuestra boda",
                    "ro": "Memento: Confirmă-ți prezența la nunta noastră",
                    "en": "Reminder: Please RSVP for our wedding",
                }.get(lang_value, "Reminder: Please RSVP for our wedding")                  # Fallback inglés.

                # Formatea la fecha límite para el cuerpo (estilo simple).
                deadline_formatted = DEADLINE_DT.strftime("%d %B %Y")                       # Ej.: 22 January 2026.

                # Construye cuerpo con tu helper (usa plantillas del mailer).
                body = build_reminder_body(
                    name=guest.full_name,                                                   # Nombre del invitado.
                    language=lang_value,                                                    # Idioma del mensaje.
                    invited_to_ceremony=guest.invited_to_ceremony,                          # Si va a ambos o solo recepción.
                    deadline=deadline_formatted,                                            # Fecha límite legible.
                )

                # Intenta enviar con hasta 3 intentos.
                was_sent = _send_with_retry(to_email=guest.email, subject=subject, body=body, attempts=3, delay_s=1.2)

                if was_sent:                                                                # Si envío OK...
                    guest.last_reminder_at = now                                            # Actualiza timestamp de último recordatorio.
                    sent_count += 1                                                         # Cuenta envío.
                else:                                                                       # Si falló definitivamente...
                    error_count += 1                                                        # Cuenta error.
            else:                                                                           # Si no toca enviar aún...
                skipped_count += 1                                                          # Cuenta omitido.

        db.commit()                                                                         # Persiste cambios (timestamps).
    except Exception as e:                                                                  # Si el job lanza una excepción...
        logger.exception(f"Error catastrófico durante el job: {e}")                        # Log con stacktrace.
        db.rollback()                                                                       # Revierte transacciones pendientes.
        # Alerta inmediata al admin con el stacktrace resumido.
        alert_admin(                                                                        # Llama a la utilidad de alerta.
            subject="⚠️ Scheduler de recordatorios: fallo crítico",                         # Asunto de alerta.
            body=f"Ocurrió una excepción en el job de recordatorios.\n\nDetalle: {e}",     # Cuerpo con detalle.
        )                                                                                   # Fin alerta.
    finally:                                                                                # Siempre...
        db.close()                                                                          # ...cierra la sesión de BD. 

    # Log de resumen del ciclo.
    logger.info(f"Job finalizado. Enviados: {sent_count}, Omitidos: {skipped_count}, Errores: {error_count}")  # Resumen.

    # Si hubo errores de envío, notifica al admin (no es crítico, pero útil).
    if error_count > 0:                                                                     # Si hubo errores...
        alert_admin(                                                                        # Envía alerta resumida.
            subject="⚠️ Scheduler: errores de envío en recordatorios",                      # Asunto.
            body=f"Se registraron {error_count} errores de envío en la última corrida.\n"   # Cuerpo con conteo.
                 f"Enviados: {sent_count} • Omitidos: {skipped_count}.",                    # Más contexto.
        )                                                                                   # Fin alerta.

# -------------------------------------------------------------------------------------- # Punto de entrada.
if __name__ == "__main__":                                                                 # Solo si se ejecuta directamente.
    if not acquire_lock():                                                                 # Intenta adquirir lock de proceso.
        raise SystemExit(1)                                                                # Si no pudo, sale.

    try:                                                                                   # Bloque principal protegido.
        logger.info("Inicializando el scheduler de recordatorios...")                      # Log info.

        # Configura el scheduler con job defaults prudentes.
        scheduler = BlockingScheduler(                                                     # Instancia scheduler blocking.
            timezone=EVENT_TIMEZONE,                                                       # Usa  TZ configurada.
            job_defaults={                                                                 # Defaults por job.
                "coalesce": True,                                                          # Si se acumulan ejecuciones, coalesce.
                "max_instances": 1,                                                        # No correr dos jobs en paralelo.
                "misfire_grace_time": 3600,                                                # 1 hora de gracia si el proceso estuvo dormido.
            },
        )                                                                                  # Fin instanciación.

        # Programa la tarea diaria a la hora/minuto configurados.
        scheduler.add_job(                                                                 # Añade job cron.
            send_pending_reminders_job,                                                    # Función a ejecutar.
            "cron",                                                                        # Trigger tipo cron.
            hour=SCHED_HOUR,                                                               # Hora local.
            minute=SCHED_MINUTE,                                                           # Minuto local.
        )                                                                                  # Fin add_job.

        logger.info(f"Scheduler configurado → {SCHED_HOUR:02d}:{SCHED_MINUTE:02d} {EVENT_TZ_NAME}")  # Log de configuración.
        logger.info("Ejecución inmediata (smoke test)…")                                    # Aviso de prueba inmediata.

        # Ejecuta una corrida inmediata para testear (no esperar al siguiente cron).
        send_pending_reminders_job()                                                       # Llama una vez ahora.

        # Inicia el loop del scheduler (bloquea el hilo).
        scheduler.start()                                                                   # Arranca scheduling.
    except (KeyboardInterrupt, SystemExit):                                                 # Ctrl+C o señales de parada.
        logger.info("Scheduler detenido por el usuario.")                                   # Log ordenado.
    finally:                                                                                # Siempre al salir…
        release_lock()                                                                      # Libera lockfile aunque haya excepciones.
