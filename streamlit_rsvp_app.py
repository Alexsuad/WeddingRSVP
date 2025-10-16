# streamlit_rsvp_app.py                                                      # Nombre del archivo principal de Streamlit (entrypoint de la app RSVP).
# =================================================================================
# 🚀 Punto de Entrada — App de Invitados (Streamlit Multipage)               # Descripción breve del rol del archivo.
# Rol: decidir destino según JWT en sesión y redirigir (Login ↔ Formulario). # Explica que decide a qué página navegar según haya token o no.
# Extras opcionales: botones de rescate si falla la navegación y logout por query. # Menciona utilidades adicionales disponibles.
# =================================================================================

# ================================================================
# 🌙 MAINTENANCE MODE (Controlado por variables) + THEME_MODE
# ================================================================
import os                                                                    # Importa 'os' para leer variables de entorno (MAINTENANCE_MODE, THEME_MODE, etc.).
import streamlit as st                                                       # Importa Streamlit para construir la interfaz de usuario.

MAINTENANCE = os.getenv("MAINTENANCE_MODE", "0")                             # Lee si el modo mantenimiento está activo: "1"=sí, "0"=no (por defecto).
THEME_MODE  = os.getenv("THEME_MODE", "light").lower()                       # Lee el tema visual: "light" (por defecto) o "dark".
BG_URL      = os.getenv(                                                     # URL opcional de la imagen de fondo durante el mantenimiento.
    "MAINTENANCE_BG_URL",
    "https://rsvp.suarezsiicawedding.com/assets/fondo_mantenimiento.jpg"     # Puedes cambiarla por tu ruta real en el dominio.
)                                                                            # Fin de lectura de variables.

if MAINTENANCE == "1":                                                       # Si el modo mantenimiento está activado…
    st.set_page_config(                                                      # Configura metadatos de la página (solo para el modo mantenimiento).
        page_title="💍 Jenny & Cristian — Maintenance",                    # Título de la pestaña del navegador.
        page_icon="💍",                                                      # Ícono de la pestaña (anillo de boda).
        layout="centered"                                                    # Centra el contenido en pantalla.
    )                                                                        # Fin de set_page_config.

    # ----- Paletas y filtros según THEME_MODE -----
    if THEME_MODE == "dark":                                                 # Si el tema indicado es oscuro…
        bg_color   = "#1a1410"                                               # Color base del fondo (oscuro cálido).
        card_bg    = "#1f1a17ee"                                             # Fondo de la tarjeta (oscuro con transparencia).
        card_bd    = "#3a2f29"                                               # Borde sutil de la tarjeta en modo oscuro.
        text_main  = "#f3e9df"                                               # Color de texto principal (marfil claro).
        accent     = "#d4a373"                                               # Acento dorado suave.
        blur_css   = "blur(10px) brightness(0.7) sepia(0.1)"                 # Difuminado + oscurecer + tono cálido.
    else:                                                                    # En cualquier otro caso (tema claro)…
        bg_color   = "#fffaf7"                                               # Color base del fondo (marfil claro).
        card_bg    = "#ffffffee"                                             # Fondo de la tarjeta (blanco con transparencia).
        card_bd    = "#e9e1d8"                                               # Borde sutil claro.
        text_main  = "#3e3e3e"                                               # Color de texto principal (gris cálido).
        accent     = "#d4a373"                                               # Acento dorado suave.
        blur_css   = "blur(8px) brightness(1.05)"                            # Difuminado + leve realce de luz.

    # ----- Estilos + tarjeta elegante con fondo difuminado -----
    st.markdown(                                                             # Inyecta HTML/CSS del modo mantenimiento.
        f"""
        <style>
          /* Fondo base según tema */
          body {{
            background-color: {bg_color};                                    /* Color de fondo base (claro u oscuro). */
          }}

          /* Capa de imagen difuminada de pantalla completa */
          body::before {{
            content: "";
            position: fixed;
            inset: 0;                                                        /* Ataja top/right/bottom/left en una sola propiedad. */
            background-image: url('{BG_URL}');                               /* Imagen de fondo configurable por variable. */
            background-size: cover;                                          /* Escala para cubrir toda la pantalla. */
            background-position: center;                                     /* Centra la imagen. */
            filter: {blur_css};                                              /* Aplica blur y ajuste de brillo/tono según tema. */
            z-index: -1;                                                     /* Envía la imagen detrás del contenido. */
          }}

          /* Tarjeta central elegante */
          .card {{
            background: {card_bg};                                           /* Fondo de la tarjeta con transparencia. */
            border: 1px solid {card_bd};                                     /* Borde sutil coherente con el tema. */
            border-radius: 20px;                                             /* Esquinas redondeadas. */
            padding: 32px 26px;                                              /* Espaciado interno cómodo. */
            max-width: 720px;                                                /* Ancho máximo para buena lectura. */
            margin: 12vh auto;                                               /* Centra vertical y horizontalmente con respiro. */
            text-align: center;                                              /* Alinea el texto al centro. */
            box-shadow: 0 10px 30px rgba(0,0,0,.18);                         /* Sombra suave (flotado). */
          }}

          /* Tipografía y colores */
          h1 {{
            font-family: serif;                                              /* Tipografía clásica que combina con bodas. */
            color: {text_main};                                              /* Color del título según tema. */
            margin: .2em 0;                                                  /* Espaciado vertical del título. */
          }}
          p {{ color: {text_main}; }}                                        /* Color de párrafos según tema. */
          .heart {{ font-size: 28px; color: {accent}; }}                     /* Ícono/acento dorado. */
        </style>

        <!-- Contenido de la tarjeta -->
        <div class="card">
          <div class="heart">💍</div>
          <h1>Jenny & Cristian</h1>
          <p>We are preparing a special experience for you.</p>
          <p><em>Please come back soon to confirm your attendance.</em></p>
        </div>
        """,                                                                 # Fin del bloque HTML/CSS.
        unsafe_allow_html=True                                               # Permite renderizar HTML personalizado.
    )                                                                        # Fin de st.markdown.

    st.stop()                                                                # Detiene el resto de la app mientras haya mantenimiento.
# ================================================================
# End of maintenance mode
# ================================================================

st.set_page_config(                                                          # Configura metadatos de la app cuando NO hay mantenimiento.
    page_title="RSVP • Jenny & Cristian",                                  # Título consistente para el sistema RSVP.
    layout="centered",                                                       # Layout centrado para foco en formularios.
    initial_sidebar_state="collapsed",                                       # Sidebar colapsado para una UI limpia.
)                                                                            # Fin de configuración de página.

# --- Multipage routes (mantén estos nombres/ubicación en /pages) -------------
LOGIN_PAGE = "pages/0_Login.py"                                              # Ruta a la pantalla de Login (usa API y token).
FORM_PAGE  = "pages/1_Formulario_RSVP.py"                                    # Ruta al formulario protegido (requiere token válido).
REQUEST_ACCESS_PAGE = "pages/00_Solicitar_Acceso.py"                         # Ruta a la página "Solicitar Acceso" (flujo inicial).

# ==============================================================================
# ✅ Lógica de inicialización del idioma por defecto
# ------------------------------------------------------------------------------
# Se ejecuta UNA VEZ al inicio de la sesión del usuario.                      # Controla el idioma por URL o por defecto.
# 1) Lee el idioma desde ?lang=...                                            # Prioriza el idioma indicado en la URL.
# 2) Si no existe, usa el guardado en sesión.                                 # Reutiliza el idioma previo de la sesión.
# 3) Si no hay ninguno, usa 'en' (Inglés).                                    # Fija un idioma por defecto coherente con tu sitio.
# ------------------------------------------------------------------------------
try:
    query_lang = st.query_params.get("lang")                                 # Obtiene el valor de ?lang= si está disponible.
except Exception:
    query_lang = None                                                        # Si hay error, asume que no hay idioma en la URL.

if "lang" not in st.session_state:                                           # Solo inicializa si aún no hay idioma en la sesión.
    if query_lang in ["en", "es", "ro"]:                                     # Valida los idiomas permitidos.
        st.session_state["lang"] = query_lang                                # Usa el idioma de la URL si es válido.
    else:
        st.session_state["lang"] = "en"                                      # Por defecto, inglés.
# ==============================================================================

# --- (Opcional) Logout por query param ----------------------------------------
try:
    if st.query_params.get("logout") in ("1", "true", "True"):               # Si la URL trae ?logout=1/true, interpretarlo como logout.
        st.session_state.pop("token", None)                                  # Elimina el JWT de la sesión (cierra sesión).
        st.session_state.pop("last_rsvp", None)                              # Limpia el último resultado de confirmación almacenado.
        st.query_params.clear()                                              # Limpia los parámetros de la URL para evitar bucles.
except Exception:
    pass                                                                     # Si la versión de Streamlit no soporta query_params, no falla.

goto_page = ""
try:
    # Intenta leer el parámetro 'goto' usando la API moderna de Streamlit.
    query_params = st.query_params
    goto_raw = query_params.get("goto")
    # Normaliza el valor: lo convierte en string, quita espacios y lo pasa a minúsculas.
    goto_page = (goto_raw[0] if isinstance(goto_raw, list) else goto_raw or "").strip().lower()
except Exception:
    # Si la API moderna falla (por una versión antigua de Streamlit), usa la experimental como fallback.
    try:
        query_params = st.experimental_get_query_params()
        goto_page = (query_params.get("goto", [""])[0]).strip().lower()
    except Exception:
        # Si todo falla, la variable se queda vacía y el bloque no hará nada.
        goto_page = ""

# Si el parámetro 'goto' tiene el valor 'login'...
if goto_page == "login":
    # ...navega inmediatamente a la página de Login y detiene la ejecución de este script.
    st.switch_page("pages/0_Login.py")

# --- Decisión de destino ------------------------------------------------------
target_page = FORM_PAGE if st.session_state.get("token") else REQUEST_ACCESS_PAGE  # Con token → Formulario; sin token → Solicitar Acceso.

# --- Navegación con manejo de errores ----------------------------------------
try:
    st.switch_page(target_page)                                              # Intenta redirigir a la página objetivo.
except Exception:
    st.error(f"Unable to redirect to '{target_page}'.")                      # Muestra error claro si no se puede redirigir.
    st.info("Make sure the file exists in the `pages/` folder with that name.")   # Pista para corregir rutas/archivos.
    st.link_button("Go to Access Page", REQUEST_ACCESS_PAGE)                 # Botón de rescate hacia Solicitar Acceso.
    st.link_button("Go to RSVP Form", FORM_PAGE)                             # Botón de rescate hacia el Formulario.
