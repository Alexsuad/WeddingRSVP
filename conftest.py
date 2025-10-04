# conftest.py
# -------------------------------------------------------------------------------------
# Archivo: conftest.py (raíz del proyecto)
# Propósito: Configurar pytest con un preflight seguro y un cronómetro en vivo.
#            - Verifica que la app UI (Streamlit) esté arriba antes de correr tests.
#            - (Opcional) Verifica API (salud, openapi/docs) con banderas de entorno.
#            - (Opcional) Verifica Playwright/Chromium con banderas de entorno.
#            - Muestra un cronómetro actualizando en la misma línea durante la suite.
# Uso de variables de entorno (todas opcionales, con valores por defecto razonables):
#   ENTRY_URL="http://localhost:8501"               --> URL base de la UI (Streamlit).
#   API_BASE_URL="http://127.0.0.1:8000"            --> URL base de la API (FastAPI).
#   PYTEST_PREFLIGHT_TIMEOUT="120"                  --> Segundos para esperar la UI.
#   PYTEST_PREFLIGHT_POLL="1.0"                     --> Intervalo de reintento (seg).
#   CHECK_API="0|1"                                 --> Habilita comprobación de API.
#   REQUIRE_API="0|1"                               --> Si 1 y API falla, aborta.
#   CHECK_PLAYWRIGHT="0|1"                          --> Habilita check de Playwright.
#   REQUIRE_PLAYWRIGHT="0|1"                        --> Si 1 y falla, aborta.
# Requisitos:
#   - pytest instalado.
#   - requests en entorno de desarrollo (si falta, se muestra mensaje claro).
#   - Para checks de Playwright: `playwright install chromium` (si habilitas check).
# -------------------------------------------------------------------------------------

from __future__ import annotations  # Permite anotaciones de tipos adelantadas en Python 3.8+
import os                           # Para leer variables de entorno y opciones del sistema
import time                         # Para medir tiempos y pausas entre reintentos
import threading                    # Para ejecutar el cronómetro en un hilo separado
from typing import Optional         # Para anotar tipos opcionales (p. ej., Thread | None)
from urllib.parse import urljoin    # Para construir URLs robustas a partir de base + path

import pytest                       # Framework de testing que orquesta los hooks de sesión

try:
    import requests                 # Librería HTTP; la usamos para tocar endpoints de UI/API
except Exception:                   # Si no está disponible requests, no queremos explotar aquí
    requests = None                 # Marcamos como None y más abajo emitimos un mensaje legible

# =========================
# Configuración por defecto
# =========================
ENTRY_URL = os.getenv("ENTRY_URL", "http://localhost:8501")              # URL base de la UI
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")        # URL base de la API
SMOKE_PATHS = ["/", "/Solicitar_Acceso", "/Login"]                       # Rutas mínimas para probar UI
PREFLIGHT_TIMEOUT = int(os.getenv("PYTEST_PREFLIGHT_TIMEOUT", "120"))    # Tiempo máximo esperando UI
PREFLIGHT_POLL = float(os.getenv("PYTEST_PREFLIGHT_POLL", "1.0"))        # Intervalo entre intentos UI

CHECK_API = os.getenv("CHECK_API", "0") == "1"                           # Si True, comprobamos API
REQUIRE_API = os.getenv("REQUIRE_API", "0") == "1"                       # Si True y API falla, abortamos
CHECK_PLAYWRIGHT = os.getenv("CHECK_PLAYWRIGHT", "0") == "1"             # Si True, comprobamos Playwright
REQUIRE_PLAYWRIGHT = os.getenv("REQUIRE_PLAYWRIGHT", "0") == "1"         # Si True y falla, abortamos

# =======================
# Soporte: cronómetro UI
# =======================
_ticker_stop = threading.Event()                 # Evento para detener el hilo del cronómetro
_ticker_thread: Optional[threading.Thread] = None  # Referencia al hilo del cronómetro
_session_start_monotonic: float = 0.0            # Marca de tiempo (monotónica) al iniciar la suite


def _fmt_hhmmss(elapsed: float) -> str:
    """Convierte segundos (float) a cadena HH:MM:SS para mostrar tiempos de forma legible."""
    total = int(elapsed)                         # Redondea hacia abajo a segundos completos
    h = total // 3600                            # Calcula horas enteras
    m = (total % 3600) // 60                     # Calcula minutos restantes
    s = total % 60                               # Calcula segundos restantes
    return f"{h:02d}:{m:02d}:{s:02d}"            # Devuelve el string formateado con ceros a la izquierda


def _ticker(terminalreporter) -> None:
    """Hilo de fondo que imprime un cronómetro en la misma línea mientras corren los tests."""
    while not _ticker_stop.is_set():                                     # Bucle hasta que se pida detener
        elapsed = time.monotonic() - _session_start_monotonic            # Tiempo transcurrido desde inicio
        hhmmss = _fmt_hhmmss(elapsed)                                    # Formatea en HH:MM:SS
        try:
            terminalreporter.write(f"\r⏱  Ejecutando tests… {hhmmss} ", bold=True)  # Intenta escribir en terminal de pytest
        except Exception:
            print(f"\r⏱  Ejecutando tests… {hhmmss} ", end="", flush=True)           # Fallback si no hay terminalreporter
        time.sleep(1)                                                    # Espera 1 segundo antes de actualizar de nuevo
    try:
        terminalreporter.write_line("")                                  # Al terminar, fuerza salto de línea
    except Exception:
        print()                                                          # Fallback: imprime salto de línea


# =====================
# Helpers de preflight
# =====================
def _server_is_up(base_url: str) -> bool:
    """Intenta tocar varias rutas de la UI; devuelve True si alguna responde 'OK-ish' (<500)."""
    if requests is None:                                                 # Si no tenemos requests instalado
        return False                                                     # No podemos verificar, devolvemos False
    for path in SMOKE_PATHS:                                             # Recorremos rutas de smoke
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))      # Construimos la URL completa
        try:
            r = requests.get(url, timeout=2)                             # Intentamos GET rápido (2s)
            if r.status_code < 500:                                      # Si responde 2xx-4xx, consideramos que el servidor está vivo
                return True                                              # Devolvemos True porque algo contestó
        except Exception:
            pass                                                         # Ignoramos errores puntuales y probamos siguiente
    return False                                                         # Si ninguna ruta respondió, decimos que no está arriba


def _wait_for_ui(base_url: str, timeout_s: int, poll_s: float) -> bool:
    """Espera a que la UI responda dentro del timeout, consultando periódicamente."""
    deadline = time.monotonic() + timeout_s                              # Calcula momento límite
    ok = _server_is_up(base_url)                                         # Comprueba estado inicial
    while not ok and time.monotonic() < deadline:                        # Mientras no esté OK y no haya expirado el tiempo
        time.sleep(poll_s)                                               # Espera intervalo de sondeo
        ok = _server_is_up(base_url)                                     # Reintenta ver si ya está arriba
    return ok                                                            # Devuelve True/False según resultado final


def _check_api(base_url: str) -> tuple[bool, str]:
    """Intenta validar la API llamando a /health, /openapi.json o /docs; devuelve (ok, detalle)."""
    if requests is None:                                                 # Sin requests no podemos verificar API
        return False, "Falta 'requests' para verificar API"              # Devolvemos False y detalle explicativo
    candidates = ("/health", "/openapi.json", "/docs")                   # Endpoints típicos de salud/documentación
    last_err = "Sin respuesta válida de la API"                          # Mensaje por defecto si nada responde
    for path in candidates:                                              # Recorre endpoints candidatos
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))      # Construye URL del endpoint
        try:
            r = requests.get(url, timeout=3)                             # Llama con timeout corto
            if r.status_code < 500:                                      # Si responde <500, lo consideramos señal de vida
                return True, f"OK en {path} (HTTP {r.status_code})"      # Devuelve éxito con detalle
            last_err = f"HTTP {r.status_code} en {path}"                 # Actualiza último error si fue 5xx
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"                        # Guarda excepción como detalle
    return False, last_err                                                # Devuelve fallo con el último detalle recogido


def _check_playwright() -> tuple[bool, str]:
    """Intenta lanzar Chromium en headless con Playwright; devuelve (ok, detalle)."""
    try:
        from playwright.sync_api import sync_playwright                  # Import local para no forzar dependencia si no se usa
    except Exception as e:
        return False, f"No se pudo importar Playwright: {e}"            # Falla si el import rompe

    try:
        with sync_playwright() as p:                                     # Abre contexto Playwright
            browser = p.chromium.launch(headless=True)                   # Intenta abrir Chromium en modo headless
            browser.close()                                              # Cierra el navegador si abrió bien
        return True, "Playwright/Chromium operativo"                     # Éxito: Playwright y Chromium están OK
    except Exception as e:
        return False, f"No se pudo lanzar Chromium: {e}"                 # Falla si lanzar Chromium dio error


# ===========================
# Hooks de ciclo de ejecución
# ===========================
def pytest_sessionstart(session):
    """Hook al inicio de la sesión de pytest: cronómetro + preflight de UI (y opcionales)."""
    global _ticker_thread, _session_start_monotonic                      # Declaramos globales que vamos a modificar

    tr = session.config.pluginmanager.get_plugin("terminalreporter")     # Obtenemos el reportero de terminal de pytest

    # Cabecera de arranque para visibilidad del usuario
    if tr:                                                               # Si tenemos terminalreporter
        tr.write_line("🚀 Pytest iniciado (cronómetro en vivo activado)…")  # Mensaje de inicio
    else:
        print("🚀 Pytest iniciado (cronómetro en vivo activado)…")       # Fallback si no hay terminalreporter

    _session_start_monotonic = time.monotonic()                          # Guardamos marca de tiempo de inicio

    # Lanzamos cronómetro en un hilo daemon
    _ticker_stop.clear()                                                 # Aseguramos que el evento de parada esté limpio
    _ticker_thread = threading.Thread(target=_ticker, args=(tr,), daemon=True)  # Creamos hilo con target _ticker
    _ticker_thread.start()                                               # Iniciamos el hilo del cronómetro

    # Validación de dependencia 'requests' si vamos a tocar red
    if requests is None:                                                 # Si no tenemos requests instalado
        msg = ("❌ Falta la dependencia 'requests'. Instálala con 'pip install requests' "
               "para permitir el preflight de UI/API.")                  # Construimos mensaje claro
        if tr:
            tr.write_line(msg, red=True)                                 # Mostramos el mensaje en rojo en la terminal
        raise pytest.UsageError(msg)                                     # Abortamos la sesión con error de uso

    # Preflight UI: esperar a que la app de Streamlit esté arriba
    base_ui = ENTRY_URL                                                  # Leemos URL base definida arriba (o por entorno)
    if tr:
        tr.write_line(f"🔍 Verificando UI en {base_ui}…")                 # Informamos que verificaremos UI

    ui_ok = _wait_for_ui(base_ui, PREFLIGHT_TIMEOUT, PREFLIGHT_POLL)     # Esperamos hasta timeout o éxito
    if not ui_ok:                                                        # Si la UI no respondió a tiempo
        _ticker_stop.set()                                               # Detenemos el cronómetro para que el mensaje sea legible
        if _ticker_thread:
            _ticker_thread.join(timeout=2)                               # Esperamos a que el hilo termine limpio
        msg = (f"❌ No pude contactar la UI en {base_ui} tras {PREFLIGHT_TIMEOUT}s.\n"
               "   Asegúrate de tener Streamlit corriendo (p.ej. `streamlit run Home.py`) "
               "y que la variable ENTRY_URL apunte a la URL correcta.")  # Mensaje de error orientativo
        if tr:
            tr.write_line(msg, red=True)                                 # Pintamos el mensaje en rojo
        raise pytest.UsageError(msg)                                     # Abortamos de forma explícita

    if tr:
        tr.write_line("✅ UI lista, continuando con preflight opcional…") # Confirmamos que la UI está lista

    # (Opcional) Preflight de API si está habilitado
    if CHECK_API:                                                        # Solo si el usuario activó CHECK_API=1
        api_base = API_BASE_URL                                          # Leemos URL base de la API
        if tr:
            tr.write_line(f"🔍 Comprobando API en {api_base}…")          # Informamos comprobación de API
        api_ok, detail = _check_api(api_base)                            # Ejecutamos verificación de API
        if api_ok:                                                       # Si la API respondió correctamente
            if tr:
                tr.write_line(f"   ✅ API OK: {detail}")                  # Informamos detalle positivo
        else:                                                            # Si la API no respondió adecuadamente
            warn = f"   ⚠️  API no verificada: {detail}"                 # Construimos mensaje de advertencia
            if tr:
                tr.write_line(warn, yellow=True)                         # Mostramos en amarillo
            if REQUIRE_API:                                              # Si el entorno exige API operativa
                _ticker_stop.set()                                       # Detenemos cronómetro antes de abortar
                if _ticker_thread:
                    _ticker_thread.join(timeout=2)                       # Sincronizamos la parada del hilo
                msg = ("❌ API requerida pero no disponible. Activa el backend o deshabilita "
                       "REQUIRE_API=1 si no debe ser bloqueante.")       # Mensaje de error claro para el usuario
                if tr:
                    tr.write_line(msg, red=True)                         # Mostramos en rojo
                raise pytest.UsageError(msg)                             # Abortamos si es requisito

    # (Opcional) Preflight de Playwright/Chromium si está habilitado
    if CHECK_PLAYWRIGHT:                                                 # Solo si el usuario activó CHECK_PLAYWRIGHT=1
        if tr:
            tr.write_line("🔍 Comprobando Playwright/Chromium…")         # Informamos inicio de check de Playwright
        pw_ok, pw_detail = _check_playwright()                           # Ejecutamos verificación de Playwright
        if pw_ok:                                                        # Si Playwright/Chromium están OK
            if tr:
                tr.write_line(f"   ✅ {pw_detail}")                       # Informamos detalle positivo
        else:                                                            # Si algo falló en Playwright
            warn = f"   ⚠️  {pw_detail}. Sugerencia: `playwright install chromium`"  # Sugerimos instalación
            if tr:
                tr.write_line(warn, yellow=True)                         # Mostramos en amarillo
            if REQUIRE_PLAYWRIGHT:                                       # Si se exige Playwright operativo
                _ticker_stop.set()                                       # Detenemos cronómetro antes de abortar
                if _ticker_thread:
                    _ticker_thread.join(timeout=2)                       # Sincronizamos parada del hilo
                msg = ("❌ Playwright requerido pero no disponible. Ejecuta "
                       "`playwright install chromium` o desactiva REQUIRE_PLAYWRIGHT=1.")  # Mensaje de error
                if tr:
                    tr.write_line(msg, red=True)                         # Mostramos en rojo
                raise pytest.UsageError(msg)                             # Abortamos si es requisito

    if tr:
        tr.write_line("🟢 Preflight OK. Iniciando suite…")               # Mensaje final de preflight exitoso


def pytest_sessionfinish(session, exitstatus):
    """Hook al finalizar la sesión: detiene cronómetro y muestra tiempo total."""
    _ticker_stop.set()                                                   # Señalamos al hilo que debe terminar
    if _ticker_thread:                                                   # Si el hilo existe
        _ticker_thread.join(timeout=2)                                   # Esperamos breve para terminar limpio

    tr = session.config.pluginmanager.get_plugin("terminalreporter")     # Obtenemos reportero de terminal
    total = _fmt_hhmmss(time.monotonic() - _session_start_monotonic)     # Calculamos tiempo total de la suite
    line = f"🟢 Suite finalizada. Tiempo total: {total}"                  # Construimos mensaje de cierre
    if tr:
        tr.write_line(line)                                              # Mostramos el mensaje de cierre
    else:
        print("\n" + line)                                               # Fallback si no hay reportero


def pytest_collection_finish(session):
    """Hook cuando pytest termina de recolectar tests: muestra cuántos encontró."""
    tr = session.config.pluginmanager.get_plugin("terminalreporter")     # Obtiene reportero de terminal
    count = len(session.items)                                           # Calcula número de tests descubiertos
    msg = f"📋 Descubiertos {count} tests."                               # Mensaje informativo
    if tr:
        tr.write_line(msg)                                               # Escribe el mensaje informativo
    else:
        print(msg)                                                       # Fallback a print


def pytest_runtest_logstart(nodeid, location):
    """Hook por test: indica inicio de cada caso para mejorar trazabilidad en consola."""
    tr = pytest.config.pluginmanager.get_plugin("terminalreporter") if hasattr(pytest, "config") else None  # Compatibilidad
    line = f"▶️  Iniciando test: {nodeid}"                               # Mensaje de inicio
    try:
        tr.write_line(line) if tr else print(line)                       # Muestra el inicio del test
    except Exception:
        print(line)                                                      # Fallback simple


def pytest_runtest_logfinish(nodeid, location):
    """Hook por test: indica fin de cada caso para cerrar el bloque visualmente."""
    tr = pytest.config.pluginmanager.get_plugin("terminalreporter") if hasattr(pytest, "config") else None  # Compatibilidad
    line = f"✔️  Finalizó test: {nodeid}"                                # Mensaje de fin
    try:
        tr.write_line(line) if tr else print(line)                       # Muestra el fin del test
    except Exception:
        print(line)                                                      # Fallback simple


# ===============================
# (Opcional) Fixtures de utilidad
# ===============================
@pytest.fixture(scope="session")
def entry_url() -> str:
    """Expone la URL base de la UI para usar en tests que la necesiten."""
    return ENTRY_URL                                                     # Devuelve la URL leída de entorno o por defecto


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Expone la URL base de la API para tests que interactúen con endpoints."""
    return API_BASE_URL                                                  # Devuelve la URL de API configurada
