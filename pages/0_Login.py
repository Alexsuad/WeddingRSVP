# pages/0_Login.py                                                        # Nombre del archivo y ruta dentro de /pages.            # Ruta/rol del archivo.

# =================================================================================                                            # Separador visual.
# 💍 Página de Aterrizaje y Login (Invitados)                                                                                  # Título descriptivo.
# ---------------------------------------------------------------------------------                                            # Separador.
# - ÚNICA página pública del flujo RSVP.                                                                                       # Alcance.
# - Valida al invitado con guest_code + (email o teléfono).                                                                     # Función principal.
# - Si el login es correcto, guarda el JWT y redirige al formulario.                                                           # Flujo exitoso.
# - Implementa un menú de navegación lateral traducible y selector de idioma.                                                  # UX i18n.
# - Incluye un fix no invasivo para ocultar la “caja fantasma” (input huérfano).                                               # Limpieza UI.
# =================================================================================                                            # Fin encabezado.

# --- Importaciones ---
import os                                   # Módulo estándar para leer variables de entorno.                                   # Import OS.
import re                                   # Módulo estándar para expresiones regulares (sanear teléfono).                     # Import RE.
import requests                             # Librería HTTP para consumir la API de FastAPI.                                    # Import requests.
import streamlit as st                      # Librería principal de UI para construir la app.                                   # Import Streamlit.
from dotenv import load_dotenv              # Carga variables desde un archivo .env local.                                      # Import dotenv.
from utils.lang_selector import render_lang_selector  # Componente para seleccionar idioma (con banderas).                     # Import selector idioma.
from utils.translations import t                        # Función centralizada de traducciones (i18n).                         # Import i18n t().
from utils.nav import hide_native_sidebar_nav, render_nav  # Oculta nav nativo y dibuja nav propio traducible.                 # Import helpers nav.

# --- Utilidades de limpieza UI (caja fantasma) ---
def _inject_ghost_killer_css() -> None:     # Define función para inyectar CSS suave contra inputs “fantasma”.                  # Función CSS.
    """
    Inyecta CSS mínimo (no agresivo) por si el selector moderno :has() está disponible.                                         # Docstring.
    No oculta inputs legítimos del formulario; el filtrado fuerte lo hace el JS de abajo.                                      # Aclaración.
    """                                                                                                                         # Fin docstring.
    st.markdown(  # Inyecta un pequeño bloque <style> en el documento.                                                          # Markdown CSS.
        """
        <style>
          /* Este CSS es deliberadamente suave; dejamos el trabajo fino al JS. */
          /* Aquí NO ocultamos nada por defecto para no romper los inputs reales. */
        </style>
        """,
        unsafe_allow_html=True,            # Permitimos HTML en el markdown (para <style>).                                     # Permite HTML.
    )                                      # Fin inyección CSS.                                                                  # Fin función.

def _remove_ghost_input_js() -> None:      # Define función que pincha JS para ocultar inputs huérfanos.                        # Función JS.
    """
    Observa el DOM de Streamlit y oculta cualquier stTextInput 'huérfano' (sin etiqueta
    o fuera de un formulario válido) sin tocar los campos reales de login.
    Usa una lista blanca de etiquetas por idioma y exige pertenecer a un st.form.
    """                                                                                                                         # Fin docstring.
    st.markdown(  # Inyecta un bloque <script> para ejecutar JS en el navegador.                                               # Markdown JS.
        """
        <script>
        (function () {
          try {
            const root = document.querySelector('main');                         // Localiza el nodo raíz principal del contenido.
            if (!root) return;                                                   // Si no existe, aborta silenciosamente.

            // Lista blanca de labels válidos para inputs del formulario de login (ES/EN/RO).
            const WHITELIST = new Set([
              "Código de Invitación", "Email o Teléfono de contacto",            // Español (ES)
              "Invitation Code", "Email or Phone",                               // Inglés (EN)
              "Cod invitație", "Email sau Telefon de contact"                    // Rumano (RO)
            ]);

            // Función auxiliar: ¿el input pertenece a un formulario real y tiene una etiqueta de la lista blanca?
            const isRealFormInput = (el) => {
              const inForm = !!el.closest('[data-testid="stForm"]');            // Comprueba si está dentro de un st.form (estructura de Streamlit).
              const label = el.querySelector('label');                           // Busca la etiqueta (label) asociada al input.
              const labelText = (label && label.textContent || "").trim();       // Extrae texto plano y limpia espacios.
              return inForm && WHITELIST.has(labelText);                         // Es válido solo si está en form y su label está en la whitelist.
            };

            // Función principal: oculta inputs "fantasma" y deja visibles los legítimos del formulario.
            const hideGhosts = () => {
              const nodes = root.querySelectorAll('div[data-testid="stTextInputRoot"]');  // Obtiene todos los nodos tipo text input de Streamlit.
              nodes.forEach(el => {                                              // Itera por cada input detectado.
                if (isRealFormInput(el)) {                                       // Si es un campo real del formulario...
                  el.style.display = "";                                         // ...asegura que esté visible.
                  return;                                                        // ...y pasa al siguiente.
                }
                const label = el.querySelector('label');                         // Toma la etiqueta si existe.
                const labelText = (label && label.textContent || "").trim();     // Extrae el texto de la etiqueta.
                const looksGhost = !labelText || !el.closest('[data-testid="stForm"]');  // Fantasma si no hay label o está fuera de un st.form.
                if (looksGhost) {                                                // Si parece fantasma...
                  el.style.display = "none";                                     // ...lo ocultamos visualmente.
                }
              });
            };

            hideGhosts();                                                         // Ejecuta una primera limpieza al montar la página.

            // Observa cambios en el DOM (Streamlit re-renderiza con frecuencia) para mantener la limpieza.
            const obs = new MutationObserver(() => {                              // Crea un observador de mutaciones.
              clearTimeout(window.__ghost_killer_timer);                          // Debounce: cancela temporizador previo si lo hay.
              window.__ghost_killer_timer = setTimeout(hideGhosts, 30);           // Reaplica la limpieza con un pequeño retardo.
            });
            obs.observe(root, { childList: true, subtree: true });                // Observa cambios en todo el subárbol del main.
          } catch (e) {                                                           // Manejo silencioso de cualquier excepción JS.
            /* no-op */                                                           // No hacemos nada: evitamos romper la página.
          }
        })();
        </script>
        """,
        unsafe_allow_html=True,               # Permitimos HTML para insertar <script>.                                  # Permite HTML.
    )                                         # Fin inyección JS.                                                        # Fin función.

def _debug_outline_boxes(enabled: bool = False) -> None:  # Dibuja bordes de depuración si se activa.                  # Función debug.
    """
    (Opcional) Dibuja bordes de depuración alrededor de todos los contenedores del main
    para localizar visualmente de dónde proviene la "caja fantasma".
    """                                                                                                                 # Fin docstring.
    if not enabled:                           # Si no está activado el modo depuración...                               # Condición.
        return                                # ...salimos sin inyectar nada.                                           # Early return.
    st.markdown(                              # Inyecta estilos de depuración.                                          # Markdown CSS.
        """
        <style>
          main div { outline: 1px dashed rgba(200,0,0,.15); }    /* Bordes suaves para inspección visual */
        </style>
        """,
        unsafe_allow_html=True,               # Permitimos HTML (para <style>).                                         # Permite HTML.
    )                                         # Fin estilos debug.                                                       # Fin función.

# --- Configuración de Página y Entorno ---
st.set_page_config(                           # Debe ser la primera llamada de Streamlit en el script.                 # Config página.
    page_title="Confirmar Asistencia • Boda D&C",  # Título de la pestaña del navegador.                               # Título pestaña.
    page_icon="💍",                           # Emoji usado como icono de la pestaña.                                   # Icono.
    layout="centered",                        # Distribución centrada para estética y legibilidad.                      # Layout.
    initial_sidebar_state="collapsed",        # Sidebar colapsado por defecto para evitar distracciones.               # Sidebar.
)                                             # Fin set_page_config.                                                    # Fin bloque.

load_dotenv()                                 # Carga variables definidas en el archivo .env.                           # Carga .env.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")  # URL base del backend (por defecto local).        # Base API.
RECOVERY_URL = os.getenv("RECOVERY_URL", "")  # URL opcional para recuperar el código de invitación (externo).         # URL externa.

# --- UI Global: Menú y Selector de Idioma ---
hide_native_sidebar_nav()                     # Oculta el navegador multipage nativo (no traducible).                  # Oculta nav nativo.
lang = render_lang_selector()                 # Dibuja el selector de idioma y devuelve el idioma activo.              # Selector idioma.
render_nav({                                  # Dibuja nuestro menú lateral propio con etiquetas traducidas.           # Render nav propio.
    "pages/0_Login.py": t("nav.login", lang),       # Entrada de menú: Login (traducida).                              # Nav login.
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),  # Entrada de menú: Formulario (traducida).                     # Nav form.
    "pages/2_Confirmado.py": t("nav.confirmed", lang),  # Entrada de menú: Confirmado (traducida).                     # Nav ok.
})                                            # Fin render_nav.                                                        # Fin bloque nav.

# --- Parche UI: intenta ocultar/eliminar la caja fantasma SI aparece ---
_inject_ghost_killer_css()                    # Inyecta CSS mínimo (no agresivo) para entorno moderno.                 # CSS suave.
# _remove_ghost_input_js()                    # (Opcional) JS con MutationObserver para inputs huérfanos (desactivado).# JS opcional.
_debug_outline_boxes(enabled=True)            # (Opcional) Activa bordes de debug temporalmente para ubicar problemas. # Debug ON.

# --- Redirección si ya hay sesión activa ---
if st.session_state.get("token"):             # Si ya existe un JWT guardado en la sesión...                           # Chequea sesión.
    st.switch_page("pages/1_Formulario_RSVP.py")  # ...redirige al formulario protegido directamente.                 # Redirección.

# --- Inyección de Estilos (estética general, sin ocultar inputs) ---
st.markdown(                                  # Inyecta CSS para tipografías y estilos del hero y la tarjeta.          # Markdown CSS.
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:wght@600;700&display=swap');

      :root{
        --bg:#FFFFFF;              /* Color de fondo base */
        --text:#111111;            /* Color de texto principal */
        --muted:#666666;           /* Color de texto secundario */
        --border:#EAEAEA;          /* Color de borde sutil */
        --card:#FFFFFF;            /* Fondo de tarjetas */
        --shadow:0 10px 30px rgba(0,0,0,.08);  /* Sombra suave para tarjetas */
        --radius:18px;             /* Radio general de bordes redondeados */
        --radius-sm:14px;          /* Radio de bordes redondeados menor */
      }

      html, body, [class*="block-container"]{
        background:var(--bg);      /* Aplica fondo claro al contenedor principal */
        color:var(--text);         /* Establece el color de texto base */
        font-family:'Inter', sans-serif;  /* Tipografía base */
      }

      h1, h2, h3{
        font-family:'Playfair Display', serif !important; /* Titulares con serif elegante */
        font-weight:700;            /* Peso fuerte para títulos */
      }

      .hero{                        /* Encabezado superior tipo “hero” */
        text-align:center;          /* Centra el contenido horizontalmente */
        margin-bottom:20px;         /* Espacio inferior para separarlo de la tarjeta */
      }
      .hero h1{
        font-size:clamp(34px, 5vw, 52px); /* Tamaño fluido del título (responsive) */
        margin:0 0 6px 0;                 /* Margen inferior sutil bajo el título */
      }
      .hero p{
        margin:0;                          /* Sin margen extra */
        color:var(--muted);                /* Texto en color secundario */
        font-size:clamp(14px, 2vw, 18px);  /* Tamaño fluido para la línea descriptiva */
      }

      .login-card{                  /* Tarjeta que contiene el formulario de login */
        background:var(--card);     /* Fondo blanco */
        border:1px solid var(--border);  /* Borde fino gris claro */
        border-radius:var(--radius);     /* Bordes redondeados */
        box-shadow:var(--shadow);   /* Sombra suave para dar profundidad */
        padding:28px 26px;          /* Relleno interno generoso */
        max-width:720px;            /* Ancho máximo de la tarjeta */
        margin:0 auto;              /* Centra la tarjeta horizontalmente */
      }

      .muted{                       /* Estilo para textos secundarios (p.ej. enlaces) */
        color:var(--muted);         /* Color gris medio */
        font-size:14px;             /* Tamaño de fuente pequeño */
      }

      .center{                      /* Utilidad para centrar texto */
        text-align:center;          /* Centra el contenido en el eje horizontal */
      }

      /* Banderas: pequeñas y centradas bajo los botones del selector de idioma */
      div[data-testid="stImage"]{
        display:flex;               /* Convierte el contenedor en flexbox */
        justify-content:center;     /* Centra horizontalmente la imagen */
        margin-top:6px;             /* Separa un poco la bandera del botón superior */
      }
      div[data-testid="stImage"] > img{
        height:24px !important;     /* Fija una altura pequeña a la bandera */
        width:auto !important;      /* Mantiene la proporción original */
      }

      .stButton > button{
        margin-bottom:6px !important;  /* Añade aire debajo de los botones de idioma */
      }
    </style>
    """,
    unsafe_allow_html=True,                 # Permitimos HTML (para el bloque <style>).                               # Permite HTML.
)                                           # Fin estilos globales.                                                   # Fin bloque.

# --- Funciones Helper (autenticación) ---
def sanitize_contact(value: str) -> tuple[str | None, str | None]:  # Normaliza contacto a (email, phone).           # Helper limpieza.
    """Normaliza el contacto: si parece email, retorna (email, None); si no, limpia teléfono y retorna (None, phone)."""  # Docstring.
    v = (value or "").strip()              # Limpia espacios al inicio y al final.                                     # Limpia input.
    if "@" in v:                           # Si contiene '@', lo interpretamos como email.                              # Heurística email.
        return v.lower(), None             # Devuelve el email en minúsculas, y None para phone.                        # Retorno email.
    phone = re.sub(r"[^\d+]", "", v)       # Quita todo lo que no sea dígitos o '+' del teléfono.                      # Limpia teléfono.
    return None, (phone or None)           # Devuelve teléfono limpio (o None si quedó vacío) y None para email.        # Retorno phone.

def api_login(guest_code: str, contact: str) -> tuple[str | None, str | None]:  # Llama a /api/login; retorna (token, error).  # Helper login.
    """Llama a POST /api/login y retorna (token, error), donde solo uno de los dos viene definido."""  # Docstring.    # Docstring.
    email, phone = sanitize_contact(contact)               # Convierte el contacto en email o phone según corresponda.  # Normaliza contacto.
    payload = {"guest_code": (guest_code or "").strip(),  # Construye el cuerpo JSON con guest_code sin espacios...    # guest_code limpio.
               "email": email,                            # ...email (o None)...                                     # Campo email.
               "phone": phone}                            # ...y phone (o None).                                      # Campo phone.
    # Prepara un mensaje genérico de servidor con fallback: si no existe login.server_err, usamos form.server_err.     # Nota fallback.
    server_err = t("login.server_err", lang)              # Intenta cargar la clave específica de login.               # i18n intento.
    if server_err == "login.server_err":                  # Si la clave no existe (t devuelve la clave cruda)...       # Chequeo.
        server_err = t("form.server_err", lang)           # ...usa el mensaje genérico ya existente en el bundle.      # Fallback i18n.
    try:                                                  # Intenta realizar la llamada a la API.                      # Try request.
        resp = requests.post(f"{API_BASE_URL}/api/login", # Hace la petición POST al endpoint de login.                # POST login.
                             json=payload,                # Envía el payload como JSON.                                # JSON body.
                             timeout=12)                  # Define un timeout razonable de red.                        # Timeout.
        if resp.status_code == 200:                       # Si la respuesta es 200 OK...                               # Caso 200.
            try:
                data = resp.json()                        # Intenta decodificar el cuerpo como JSON.                   # JSON parse.
            except ValueError:                            # Si el JSON es inválido...                                  # Excepción JSON.
                return None, server_err                   # ...devuelve error genérico de servidor.                    # Error parse.
            token = (data or {}).get("access_token")      # Extrae el access_token del JSON (si existe).              # Extrae token.
            return (token, None) if token else (None, server_err)  # Devuelve token si hay; si no, error genérico.     # Retorno.
        elif resp.status_code == 401:                     # Si la API devuelve 401 (no autorizado)...                   # Caso 401.
            return None, t("login.errors_auth", lang)     # ...retorna error claro de credenciales.                    # Error auth.
        return None, f"{server_err} (HTTP {resp.status_code})"  # Otros códigos → mensaje genérico con código.         # Otros códigos.
    except requests.exceptions.RequestException:          # Captura errores de conexión, DNS o timeout.                # Excepción red.
        return None, server_err                           # Devuelve error genérico traducido.                         # Error red.

# --- Interfaz de Usuario (Hero + Tarjeta de Login) ---
st.markdown(                                            # Renderiza el encabezado principal tipo “hero”.               # Markdown hero.
    f"""
    <div class="hero">
      <h1>Daniela &amp; Cristian</h1>                   <!-- Título principal estático (marca del evento) -->
      <p>{t("login.intro", lang)}</p>                   <!-- Línea descriptiva traducida (intro del login) -->
    </div>
    """,
    unsafe_allow_html=True,                             # Permitimos HTML para usar <div>, <h1>, <p>.                  # Permite HTML.
)                                                       # Fin hero.                                                    # Fin bloque.

st.markdown('<div class="login-card">', unsafe_allow_html=True)  # Abre el contenedor estilizado de la tarjeta de login. # Abre tarjeta.

with st.form("login_form"):                             # Crea un formulario con estado (envío atómico de campos).      # Form login.
    guest_code = st.text_input(t("login.code", lang),   # Campo de texto para el “Código de Invitación”.               # Input code.
                               key="login_code")        # Clave de estado para el campo.                                # Key code.
    contact_info = st.text_input(t("login.contact", lang),  # Campo de texto para “Email o Teléfono de contacto”.      # Input contact.
                                 key="login_contact")       # Clave de estado para este campo.                           # Key contact.
    submitted = st.form_submit_button(t("login.submit", lang))  # Botón de envío del formulario (traducido).           # Submit.

if submitted:                                           # Si el usuario pulsó el botón de envío...                      # Check submit.
    if not guest_code.strip() or not contact_info.strip():     # ...y si alguno de los campos está vacío...             # Validación vacíos.
        st.error(t("login.errors_empty", lang))         # ...muestra un error traducido de campos vacíos.              # Error UI.
    else:                                               # Si ambos campos están completos...                            # Rama válida.
        with st.spinner(t("login.validating", lang)):   # ...muestra un spinner con “Validando...” traducido.          # Spinner.
            token, error = api_login(guest_code, contact_info)  # Llama a la API de login con los datos ingresados.    # Llama API.
        if token:                                       # Si obtuvimos un token válido...                               # Token OK.
            st.session_state["token"] = token           # ...guarda el JWT en la sesión para futuras llamadas.         # Guarda token.
            st.success(t("login.success", lang))        # ...muestra un mensaje de éxito traducido.                    # Éxito UI.
            st.rerun()                                  # ...recarga el script para que la guardia redirija.           # Rerun.
        else:                                           # Si hubo un error en el login...                               # Sin token.
            st.error(error)                             # ...muestra el mensaje de error correspondiente.              # Error UI.

# --- Acceso a recuperación de código (robusto) ---
with st.container():                                                     # Crea un contenedor para centrar el enlace/botón.        # Contenedor link.
    st.markdown('<div class="center muted">', unsafe_allow_html=True)    # Abre un div centrado con estilo atenuado.               # Div estilizado.
    try:                                                                 # Intenta usar navegación moderna.                         # Try page_link.
        if RECOVERY_URL.strip():                                         # Si hay URL externa (p.ej., WordPress)...                 # Caso externo.
            st.markdown(                                                 # Renderiza un enlace <a> clásico (se mantiene tu UX).     # Anchor externo.
                f'<a href="{RECOVERY_URL}" target="_blank">{t("login.forgot", lang)}</a>',  # Etiqueta traducida.                # HTML <a>.
                unsafe_allow_html=True,                                  # Permite HTML para respetar el <a>.                      # Permite HTML.
            )                                                            # Fin anchor externo.                                      # Fin.
        else:                                                            # Si NO hay URL externa configurada...                     # Caso interno.
            st.page_link(                                                # Usa page_link para navegación multipage robusta.         # page_link.
                "pages/00_Recuperar_Codigo.py",                          # Ruta de la página interna de recuperación.               # Ruta interna.
                label=t("login.forgot", lang),                           # Etiqueta traducida.                                      # Label.
                icon="🔑",                                               # Icono para claridad.                                     # Icono.
            )                                                            # Fin page_link.                                           # Fin.
    except Exception:                                                    # Si tu versión de Streamlit no soporta page_link...       # Except.
        if not RECOVERY_URL.strip():                                     # Solo si NO hay URL externa (ya cubrimos el externo)      # Sin externo.
            st.write(f"🔑 {t('login.forgot', lang)}")                    # Muestra un texto como último recurso (sin navegación).   # Fallback texto.
    st.markdown('</div>', unsafe_allow_html=True)                        # Cierra el div centrado.                                  # Cierre div.
# --- Fin bloque de recuperación ---                                    # Fin bloque.

st.markdown("</div>", unsafe_allow_html=True)           # Cierra el contenedor de la tarjeta de login (único cierre).  # Cierra tarjeta.
