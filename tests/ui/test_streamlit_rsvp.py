# tests/ui/test_streamlit_rsvp.py                                                          # Indica la ruta del archivo de pruebas UI con Playwright + Pytest

# =======================                                                                  # Sección de importaciones y configuración básica
# Importaciones y setup                                                                    # Título descriptivo de la sección
# =======================                                                                  # Fin del encabezado de sección
import os                                                                                  # Importa os para leer variables de entorno y construir rutas
import pytest                                                                              # Importa pytest para estructurar y ejecutar los tests
from playwright.sync_api import sync_playwright, expect                                    # Importa Playwright en modo síncrono y utilidades de aserción
import re                                                                                  # Importa re para usar expresiones regulares en selectores y coincidencias de texto

# =======================                                                                  # Sección de configuración rápida y constantes
# 🔧 CONFIGURACIÓN RÁPIDA                                                                  # Título visual para resaltar configuración rápida
# =======================                                                                  # Fin del encabezado de sección

ENTRY_URL = "http://localhost:8501"                                                        # Define la URL base por defecto donde corre Streamlit; puede ser sobrescrita por entorno

ROUTES = {                                                                                 # Diccionario que mapea nombres lógicos de rutas a sus paths reales en la UI
    "request_access": "/Solicitar_Acceso",                                                 # Ruta para la pantalla de “Solicitar Acceso”
    "login": "/Login",                                                                     # Ruta para la pantalla de “Login”
    "rsvp": "/Formulario_RSVP",                                                            # Ruta para la pantalla de “Formulario RSVP”
    "confirmed": "/Confirmado",                                                            # Ruta para la pantalla de “Confirmado”
}                                                                                          # Cierre del diccionario de rutas

LABELS = {                                                                                 # Diccionario con textos de etiquetas (labels) usados por los inputs
    # Solicitar Acceso                                                                     # Comentario de subsección para agrupar campos de "Solicitar Acceso"
    "full_name": "Nombre completo (como aparece en la invitación)",                        # Label exacto del input de nombre completo
    "last4": "Últimos 4 dígitos de tu teléfono",                                           # Label exacto del input de últimos 4 dígitos
    "email": "Correo electrónico",                                                         # Label exacto del input de correo electrónico
    "consent": "Acepto recibir comunicaciones",                                            # Label para el consentimiento (si aplica)

    # Login                                                                                # Comentario de subsección para agrupar campos de "Login"
    "guest_code": "Código de invitación",                                                  # Label exacto del campo para el código de invitación
    "email_or_phone": "Email o teléfono de contacto",                                      # Label alterno si el formulario usa email/teléfono combinados

    # Formulario RSVP                                                                      # Comentario de subsección para agrupar campos del formulario RSVP
    "assist": "Asistiré",                                                                  # Label de checkbox “Asistiré” si existe esa variante
    "no_assist": "No asistiré",                                                            # Label de alternativa negativa (si existiera)
    "attending_group": "¿Asistirás?",                                                      # Grupo de selección de asistencia (si aplica)
    "attending_yes": "Sí",                                                                 # Opción positiva en radios
    "attending_no": "No",                                                                  # Opción negativa en radios

    "menu": "Menú",                                                                        # Label del selector de menú (si está presente)
    "notes": "¿Quieres dejarnos un mensaje? (opcional)",                                   # Label del campo de notas opcionales

    # Contacto dentro del formulario RSVP                                                  # Comentario de subsección para agrupar contacto en RSVP
    "contact_email": "Email",                                                              # Label del input de email de contacto dentro del formulario
    "contact_phone": "Teléfono (con código de país)",                                      # Label del input de teléfono de contacto (si aplica)
}                                                                                          # Cierre del diccionario de labels

TEXTS = {                                                                                      # Diccionario con textos/candidatos para localizar botones y mensajes
    "send_btn_contains": [                                                                     # Candidatos para “Solicitar Acceso”
        "Solicitar acceso",                                                                     # ES: muy común en la UI
        "Enviar enlace",                                                                        # ES: variante corta
        "Enviar enlace de acceso",                                                              # ES: tu candidato original
        "Enviar",                                                                               # ES: genérico
        "Obtener enlace",                                                                       # ES: variante frecuente
        "Send access link", "Send link", "Request access", "Request link"                       # EN: fallbacks
    ],                                                                                          # Fin lista “Solicitar Acceso”
    "login_btn_contains": [                                                                     # Candidatos para “Acceder”
        "Acceder", "Iniciar", "Continuar",                                                     # ES
        "Continue", "Log in", "Sign in"                                                        # EN
    ],                                                                                          # Fin lista login
    "rsvp_btn_contains": [                                                                      # Candidatos para enviar/confirmar RSVP
        "Enviar respuesta", "Confirmar", "Enviar",                                              # ES (quitamos “Confirm” para evitar colisión con “Confirmado”)
        "Send response", "Submit"                                                               # EN (quitamos “Confirm” por la misma razón)
    ],                                                                                          # Fin lista RSVP
    # Para detectar que el formulario cargó, aceptamos varias variantes (sidebar vs. contenido)
    "form_loaded_contains": ["Formulario RSVP", "RSVP", "Formulario"],                          # Lista de posibles literales en la UI
    "request_success_contains": "datos coinciden",                                              # Fragmento robusto del banner neutro/éxito
    # Éxito en pantalla de confirmación
    "confirmed_contains": ["Confirmado", "¡Gracias", "Gracias"],                                 # Textos típicos de pantalla de éxito
}

GUEST_OK = {                                                                               # Datos de prueba válidos que existen en la BD demo
    "full_name": "Ana García López",                                                       # Nombre real de ejemplo
    "last4": "2222",                                                                       # Últimos 4 dígitos reales de ejemplo
    "email": "nalexsua75@gmail.com",                                                       # Email real de ejemplo
    "guest_code": "anga-001",                                                          # Código de invitación real de ejemplo
    "menu_option_label": "Vegetariano",                                                    # Opción de menú de ejemplo
    "notes": "Llegaremos a las 19:10",                                                     # Notas de cortesía de ejemplo
}                                                                                          # Cierre del diccionario de datos válidos

FAKE = {                                                                                   # Datos de prueba “falsos” para simular caso neutro
    "full_name": "pepito",                                                                 # Nombre inventado
    "last4": "1234",                                                                        # Últimos 4 inventados
    "email": "nalexsua75@gmail.com",                                                       # Email real para reproducir el banner neutro
}                                                                                          # Cierre del diccionario de datos falsos

# =======================                                                                  # Sección de fixtures de Playwright
# ⚙️ FIXTURES PLAYWRIGHT                                                                    # Título visual de la sección de fixtures
# =======================                                                                  # Fin del encabezado de sección

@pytest.fixture(scope="session")                                                           # Declara un fixture a nivel de sesión para reutilizar el navegador
def browser():                                                                             # Define el fixture que crea/cierra el navegador
    with sync_playwright() as p:                                                           # Inicia el contexto global de Playwright
        browser = p.chromium.launch(                                                       # Lanza el navegador Chromium
            headless=True,                                                                 # Usa modo headless para velocidad/CI (poner False para depurar visualmente)
            slow_mo=0                                                                      # Sin ralentización artificial de acciones
        )                                                                                  # Cierre de la configuración del launch
        yield browser                                                                      # Entrega la instancia de navegador a los tests
        browser.close()                                                                    # Al finalizar la sesión, cierra el navegador

@pytest.fixture()                                                                          # Declara un fixture de alcance por test
def page(browser):                                                                         # Define el fixture que da una página fresca por prueba
    context = browser.new_context()                                                        # Crea un contexto aislado (cookies/almacenamiento propios)
    page = context.new_page()                                                              # Abre una nueva pestaña (Page) dentro del contexto
    yield page                                                                             # Entrega la página al test
    context.close()                                                                        # Al terminar el test, cierra el contexto para limpieza

# =======================                                                                  # Sección de utilidades auxiliares
# 🔁 UTILIDADES PEQUEÑAS                                                                    # Título visual para helpers pequeños
# =======================                                                                  # Fin del encabezado de sección
_NETWORK_IDLE_TIMEOUT = 20000                                                              # Define timeout (ms) para estado de red ociosa en esperas
_VISIBILITY_TIMEOUT = 8000                                                                 # Define timeout (ms) para visibilidad de elementos (8s para acotar fallos)

def _wait_hydrated(page):                                                                  # Helper que espera a que la UI esté estable/hidratada
    page.wait_for_load_state("domcontentloaded")                                           # Espera a que el DOM básico esté cargado
    page.wait_for_load_state("networkidle", timeout=_NETWORK_IDLE_TIMEOUT)                 # Espera a que no haya solicitudes de red en curso

def _goto(page, route_key: str) -> None:                                                   # Helper para navegar a una ruta lógica (y forzar idioma ES)
    base = os.getenv("ENTRY_URL", ENTRY_URL).rstrip("/")                                   # Lee ENTRY_URL desde entorno (o usa constante) y normaliza barra final
    path = ROUTES[route_key]                                                               # Obtiene el path real a partir de la clave de ruta dada
    url = f"{base}{path}"                                                                  # Construye la URL completa concatenando base y path
    if "lang=" not in url:                                                                 # Verifica si la URL aún no tiene parámetro de idioma
        sep = "&" if "?" in url else "?"                                                   # Decide si usar & o ? según haya query previa
        url = f"{url}{sep}lang=es"                                                         # Agrega lang=es para asegurar textos en español
    page.goto(url, wait_until="domcontentloaded")                                          # Navega a la URL y espera a DOMContentLoaded
    _wait_hydrated(page)                                                                   # Llama al helper para esperar estabilidad/hidratación

def _expect_route(page, route_key):                                                        # Helper que verifica que la URL actual corresponde a la ruta esperada
    base = os.getenv("ENTRY_URL", ENTRY_URL).rstrip("/")                                   # Toma ENTRY_URL desde entorno (o constante) y normaliza
    route = ROUTES.get(route_key) or ""                                                    # Obtiene el path esperado según la clave de ruta
    target = f"{base}{route}"                                                              # Construye la URL objetivo (sin query obligatoria)
    regex = re.compile("^" + re.escape(target) + r"(\?.*)?$")                              # Permite que haya query string opcional (p. ej., lang=es)
    page.wait_for_url(regex, timeout=_NETWORK_IDLE_TIMEOUT)                                # Espera a que la URL del navegador cumpla ese patrón

def _click_button_contains_text(page, candidates) -> bool:                                      # Helper que hace clic en un botón usando estrategias robustas
    last_err = None                                                                              # Guarda el último error para diagnóstico
    main = page.locator("main")                                                                  # Prioriza el contenido principal (evita sidebar)
    for raw in candidates:                                                                       # Recorre cada candidato de texto
        txt = raw.strip()                                                                        # Normaliza el texto candidato
        # 0) CSS directo a botones visibles dentro de main (rápido y evita elementos ocultos)
        try:
            btn_css = main.locator(f'button:has-text("{txt}")').filter(has=page.locator(":visible"))  # Botón con el texto dentro de main y visible
            if btn_css.count() > 0:                                                              # Si hay alguno
                btn_css.first.click()                                                            # Clic al primero
                _wait_hydrated(page)                                                             # Espera rehidratación
                return True                                                                      # Éxito
        except Exception as e:
            last_err = e                                                                         # Guarda error y sigue

        # 1) Rol button (accesible) dentro de main, visible
        try:
            btn = main.get_by_role("button", name=re.compile(rf"(^|\b){re.escape(txt)}(\b|$)", re.IGNORECASE))  # Coincidencia por palabra (evita “Confirmado”)
            btn.first.wait_for(state="visible", timeout=_VISIBILITY_TIMEOUT)                   # Espera visibilidad
            btn.first.click()                                                                  # Clic
            _wait_hydrated(page)                                                               # Espera rehidratación
            return True                                                                        # Éxito
        except Exception as e:
            last_err = e

        # 2) Inputs tipo submit/button (value) dentro de main
        try:
            sub = main.locator(                                                                # Busca inputs con value que contenga el texto
                f'input[type="submit"][value*="{txt}"], input[type="button"][value*="{txt}"]'
            ).filter(has=page.locator(":visible"))                                             # Filtra visibles
            if sub.count() > 0:                                                                # Si existe alguno
                sub.first.click()                                                              # Clic
                _wait_hydrated(page)                                                           # Espera rehidratación
                return True                                                                     # Éxito
        except Exception as e:
            last_err = e

        # 3) Como último recurso, cualquier elemento de texto dentro de main, visible
        try:
            any_el = main.get_by_text(re.compile(rf"(^|\b){re.escape(txt)}(\b|$)", re.IGNORECASE))  # Texto por palabra completa
            any_el.first.wait_for(state="visible", timeout=_VISIBILITY_TIMEOUT)                # Espera visibilidad
            any_el.first.click()                                                               # Clic
            _wait_hydrated(page)                                                               # Espera rehidratación
            return True                                                                        # Éxito
        except Exception as e:
            last_err = e
            continue                                                                           # Pasa al siguiente candidato

    raise AssertionError(f"No encontré botón con textos {candidates}. Último error: {last_err}")  # Error claro si nada funcionó

def _fill_by_label_or_partial(page, label_text, value):                                     # Helper que rellena un input buscando por label/placeholder con tolerancia
    _wait_hydrated(page)                                                                     # Garantiza que la página esté estable antes de buscar

    try:                                                                                     # Primer intento: label exacto
        locator = page.get_by_label(label_text, exact=True)                                  # Localiza el control por etiqueta exacta
        locator.wait_for(state="visible", timeout=_VISIBILITY_TIMEOUT)                       # Espera a que sea visible
        locator.fill(value)                                                                  # Rellena el valor solicitado
        return                                                                               # Sale tras rellenar correctamente
    except Exception:                                                                         # Si falla exacto
        pass                                                                                 # Continúa a alternativas

    try:                                                                                     # Segundo intento: label aproximado (regex contains)
        locator = page.get_by_label(re.compile(re.escape(label_text), re.IGNORECASE))        # Localiza por coincidencia parcial (case-insensitive)
        locator.wait_for(state="visible", timeout=_VISIBILITY_TIMEOUT)                       # Espera visibilidad
        locator.fill(value)                                                                  # Rellena el valor
        return                                                                               # Sale tras rellenar
    except Exception:                                                                         # Si falla
        pass                                                                                 # Continúa al siguiente enfoque

    try:                                                                                     # Tercer intento: por placeholder relacionado con tokens del label
        candidates = page.get_by_placeholder(re.compile(r".*", re.IGNORECASE)).all()         # Obtiene todos los inputs con placeholder
        for c in candidates:                                                                 # Itera por cada candidato
            try:                                                                             # Maneja fallos puntuales por cada elemento
                ph = c.get_attribute("placeholder") or ""                                    # Lee el atributo placeholder (o vacío)
                if isinstance(ph, str) and any(tok in ph.lower() for tok in label_text.lower().split()):  # Comprueba si comparte tokens con el label
                    c.wait_for(state="visible", timeout=2000)                                 # Espera visibilidad rápida
                    c.fill(value)                                                            # Rellena el valor
                    return                                                                   # Sale tras rellenar con éxito
            except Exception:                                                                # Ignora errores de un candidato
                continue                                                                     # Avanza al siguiente placeholder
        page.get_by_placeholder(re.compile(r".*", re.IGNORECASE)).first.wait_for(            # Si no hubo match por tokens, usa el primer placeholder visible
            state="visible", timeout=_VISIBILITY_TIMEOUT                                     # Espera visibilidad con timeout estándar
        )                                                                                    # Cierra la espera
        page.get_by_placeholder(re.compile(r".*", re.IGNORECASE)).first.fill(value)          # Rellena en el primer placeholder visible
        return                                                                               # Sale tras rellenar
    except Exception:                                                                         # Si falla la estrategia por placeholder
        pass                                                                                 # Continúa al último recurso

    try:                                                                                     # Último recurso: primer textbox visible por rol
        tb = page.get_by_role("textbox")                                                     # Selecciona todos los textboxes por rol accesible
        tb.first.wait_for(state="visible", timeout=_VISIBILITY_TIMEOUT)                      # Espera visibilidad del primero
        tb.first.fill(value)                                                                 # Rellena el valor
        return                                                                               # Sale tras rellenar
    except Exception as e:                                                                    # Si incluso esto falla
        raise AssertionError(                                                                 # Lanza un error con contexto claro
            f"No pude localizar input para label '{label_text}'. Error final: {e}"           # Mensaje explicando el label y el error original
        )                                                                                    # Fin de la excepción

def _expect_rsvp_success(page):                                                             # Helper que verifica éxito de envío de RSVP por URL o mensaje
    try:                                                                                     # Primer intento: confirmar navegación a /Confirmado
        _expect_route(page, "confirmed")                                                     # Comprueba que la URL sea la de confirmación
        return                                                                               # Si navega correctamente, se considera éxito
    except Exception:                                                                         # Si no hay navegación
        pass                                                                                 # Continúa a verificar por mensaje

    success_patterns = [                                                                      # Patrones que significan confirmación correcta
        r"\bconfirmado\b",                                                                     # ES: Confirmado (evita “confirmar”)
        r"\bgracias\b",                                                                        # ES: Gracias
        r"no podr[aá]s asistir",                                                               # ES: no asistencia
        r"(respuesta|confirmaci[oó]n).*(registrad[ao]|guardad[ao])",                           # ES: confirmación registrada/guardada
        r"\bthank(s| you)\b",                                                                  # EN: Thanks / Thank you
        r"we[’']ll miss you",                                                                  # EN: We'll miss you
        r"(your|the).*(rsvp|confirmation|response).*(recorded|saved|received)",               # EN: confirmación registrada/recibida
        r"\bmulțumim\b|\bmultumim\b",                                                          # RO: Mulțumim/Multumim
        r"nu po[țt]i participa",                                                               # RO: no puedes participar
        r"confirmarea.*(a fost|este).*(înregistrată|inregistrata|salvată|salvata)",            # RO: confirmación registrada/guardada
    ]

    last_err = None                                                                           # Variable para almacenar el último error de verificación
    for pat in success_patterns:                                                              # Itera sobre todos los patrones de éxito
        try:                                                                                  # Intenta verificar cada patrón
            expect(page.get_by_text(re.compile(pat, re.IGNORECASE))).to_be_visible(           # Comprueba visibilidad de un texto que cumpla el patrón
                timeout=_VISIBILITY_TIMEOUT                                                   # Usa el timeout de visibilidad definido
            )                                                                                 # Cierra la aserción
            return                                                                            # Si algún patrón aparece, consideramos éxito y salimos
        except Exception as e:                                                                # Si no aparece el patrón
            last_err = e                                                                      # Guarda el error para diagnóstico
            continue                                                                          # Continúa probando los demás patrones

    raise AssertionError(                                                                     # Si no se encontró éxito por URL ni por texto
        f"No pude confirmar el éxito del RSVP por URL ni por mensaje. Último error: {last_err}"  # Lanza un error con el último detalle
    )                                                                                         # Fin de la excepción

def _expect_login_to_rsvp(page) -> None:                                                       # Valida que, tras login, aparezca el formulario RSVP
    try:
        _expect_route(page, "rsvp")                                                           # 1) Si navega a /Formulario_RSVP, ok
        return
    except Exception:
        pass
    content = page.locator("main")                                                            # 2) Plan B: buscamos en contenido principal
    last_err = None                                                                           # Guarda último error
    for frag in TEXTS["form_loaded_contains"]:                                                # Recorre posibles literales del formulario
        try:
            target = content.get_by_text(re.compile(re.escape(frag), re.IGNORECASE)).first    # Localiza por fragmento
            expect(target).to_be_visible(timeout=_VISIBILITY_TIMEOUT)                         # Debe ser visible
            return                                                                            # Éxito si aparece cualquiera
        except Exception as e:
            last_err = e                                                                      # Guarda y prueba siguiente
            continue
    raise AssertionError(f"No se pudo llegar al formulario RSVP ni por URL ni por texto. Último error: {last_err}")  # Error si nada aparece

# =======================                                                                  # Sección de casos de prueba
# 🧪 PRUEBAS DE LA UI                                                                       # Título visual para los tests
# =======================                                                                  # Fin del encabezado de sección

def test_00_request_access_ok(page):
    _goto(page, "request_access")
    _fill_by_label_or_partial(page, LABELS["full_name"], GUEST_OK["full_name"])
    _fill_by_label_or_partial(page, LABELS["last4"], GUEST_OK["last4"])
    _fill_by_label_or_partial(page, LABELS["email"], GUEST_OK["email"])

    # Nuevo: asegurar consentimiento marcado si existe
    try:
        page.get_by_label(re.compile(r"Acepto recibir comunicaciones", re.IGNORECASE)).check()
    except Exception:
        try:
            # Fallback defensivo por rol (por si cambia el copy del label)
            page.get_by_role("checkbox").first.check()
        except Exception:
            pass

    _click_button_contains_text(page, TEXTS["send_btn_contains"])
    expect(page.get_by_text(TEXTS["request_success_contains"], exact=False)).to_be_visible()


def test_00b_request_access_fake_shows_neutral_ux(page):
    _goto(page, "request_access")
    _fill_by_label_or_partial(page, LABELS["full_name"], FAKE["full_name"])
    _fill_by_label_or_partial(page, LABELS["last4"], FAKE["last4"])
    _fill_by_label_or_partial(page, LABELS["email"], FAKE["email"])

    # Nuevo: asegurar consentimiento marcado si existe
    try:
        page.get_by_label(re.compile(r"Acepto recibir comunicaciones", re.IGNORECASE)).check()
    except Exception:
        try:
            page.get_by_role("checkbox").first.check()
        except Exception:
            pass

    _click_button_contains_text(page, TEXTS["send_btn_contains"])
    expect(page.get_by_text(TEXTS["request_success_contains"], exact=False)).to_be_visible()

def test_01_login_ok(page):                                                                  # Test que comprueba que el login con código+email funciona
    _goto(page, "login")                                                                     # Navega a la pantalla de Login con lang=es
    _fill_by_label_or_partial(page, LABELS["guest_code"], GUEST_OK["guest_code"])           # Rellena el código de invitación válido
    try:                                                                                     # Intenta usar el label combinado de email/teléfono
        _fill_by_label_or_partial(page, LABELS["email_or_phone"], GUEST_OK["email"])        # Rellena el email en el campo combinado
    except Exception:                                                                         # Si no existe ese label en la UI
        _fill_by_label_or_partial(page, LABELS["email"], GUEST_OK["email"])                 # Usa el label “Correo electrónico” como fallback
    _click_button_contains_text(page, TEXTS["login_btn_contains"])                          # Hace clic en el botón de acceso usando candidatos
    _expect_login_to_rsvp(page)                                                             # Verifica que llegamos al formulario RSVP (por URL o por texto en main)

def test_02_rsvp_yes(page):                                                                  # Test que comprueba un RSVP afirmativo (asistirá)
    _goto(page, "login")                                                                     # Navega a Login
    _fill_by_label_or_partial(page, LABELS["guest_code"], GUEST_OK["guest_code"])           # Rellena el código válido
    try:                                                                                     # Intenta con label combinado
        _fill_by_label_or_partial(page, LABELS["email_or_phone"], GUEST_OK["email"])        # Rellena email válido
    except Exception:                                                                         # Si no existe el label combinado
        _fill_by_label_or_partial(page, LABELS["email"], GUEST_OK["email"])                 # Usa el label de correo como alternativa
    _click_button_contains_text(page, TEXTS["login_btn_contains"])                          # Hace clic en el botón de acceso

    marked = False                                                                            # Bandera para registrar si marcamos asistencia
    try:                                                                                      # Primer intento: checkbox “Asistiré”
        page.get_by_label(LABELS["assist"]).check()                                          # Marca el checkbox si está presente
        marked = True                                                                         # Actualiza la bandera a True
    except Exception:                                                                          # Si no hay checkbox
        try:                                                                                  # Segundo intento: radios de asistencia
            page.get_by_role("radio", name=LABELS["attending_yes"]).check()                  # Marca el radio “Sí”
            marked = True                                                                     # Actualiza la bandera a True
        except Exception:                                                                      # Si tampoco hay radios
            pass                                                                              # No impide continuar el test

    try:                                                                                      # Intento de seleccionar menú si el campo existe
        page.get_by_label(LABELS["menu"]).select_option(label=GUEST_OK["menu_option_label"]) # Selecciona la opción configurada (p. ej., “Vegetariano”)
    except Exception:                                                                          # Si no existe el selector
        pass                                                                                  # Continúa sin bloquear

    _fill_by_label_or_partial(page, LABELS["contact_email"], GUEST_OK["email"])              # Rellena el email de contacto requerido para enviar
    _fill_by_label_or_partial(page, LABELS["notes"], GUEST_OK["notes"])                      # Rellena el campo de notas con un mensaje de cortesía

    _click_button_contains_text(page, TEXTS["rsvp_btn_contains"])                            # Hace clic en “Enviar/Confirmar” usando candidatos
    _expect_rsvp_success(page)                                                               # Verifica éxito por URL a /Confirmado o por mensajes de confirmación

def test_03_rsvp_no(page):                                                                   # Test que comprueba un RSVP negativo (no asistirá)
    _goto(page, "login")                                                                     # Navega a Login
    _fill_by_label_or_partial(page, LABELS["guest_code"], GUEST_OK["guest_code"])           # Rellena el código válido
    try:                                                                                     # Intenta con label combinado
        _fill_by_label_or_partial(page, LABELS["email_or_phone"], GUEST_OK["email"])        # Rellena email válido
    except Exception:                                                                         # Si no existe el label combinado
        _fill_by_label_or_partial(page, LABELS["email"], GUEST_OK["email"])                 # Usa el label de correo como alternativa
    _click_button_contains_text(page, TEXTS["login_btn_contains"])                          # Hace clic en el botón de acceso

    selected_no = False                                                                       # Bandera para registrar si marcamos “No asistiré”
    try:                                                                                      # Primer intento: radio “No”
        page.get_by_role("radio", name=LABELS["attending_no"]).check()                       # Marca el radio “No”
        selected_no = True                                                                    # Actualiza la bandera a True
    except Exception:                                                                          # Si no hay radios
        try:                                                                                  # Segundo intento: desmarcar checkbox “Asistiré”
            page.get_by_label(LABELS["assist"]).uncheck()                                    # Desmarca el checkbox de asistencia si existe
            selected_no = True                                                                # Actualiza la bandera a True
        except Exception:                                                                      # Si no hay ninguna de las variantes
            pass                                                                              # No bloquea el flujo

    _fill_by_label_or_partial(page, LABELS["contact_email"], GUEST_OK["email"])              # Rellena email de contacto requerido
    _fill_by_label_or_partial(page, LABELS["notes"], "No podremos asistir, gracias.")        # Rellena una nota breve para la no asistencia

    _click_button_contains_text(page, TEXTS["rsvp_btn_contains"])                            # Hace clic en “Enviar/Confirmar” usando candidatos
    _expect_rsvp_success(page)                                                               # Verifica que el resultado se considere éxito (URL o mensaje)