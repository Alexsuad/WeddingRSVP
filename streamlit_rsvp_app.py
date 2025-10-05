# streamlit_rsvp_app.py                                                      # Nombre del archivo principal de Streamlit (entrypoint de la app RSVP).
# =================================================================================
# 🚀 Punto de Entrada — App de Invitados (Streamlit Multipage)               # Descripción breve del rol del archivo.
# Rol: decidir destino según JWT en sesión y redirigir (Login ↔ Formulario). # Explica que decide a qué página navegar según haya token o no.
# Extras opcionales: botones de rescate si falla la navegación y logout por query. # Menciona utilidades adicionales disponibles.
# =================================================================================

# ================================================================
# 🌙 MODO MANTENIMIENTO (Controlado por variable de entorno)
# ================================================================
import os                                                                    # Importa 'os' para leer variables de entorno como MAINTENANCE_MODE.
import streamlit as st                                                       # Importa Streamlit para construir la interfaz de usuario.

# Si la variable MAINTENANCE_MODE está activa, mostramos aviso elegante y detenemos la app.
if os.getenv("MAINTENANCE_MODE") == "1":                                     # Comprueba si MAINTENANCE_MODE="1" para activar el modo mantenimiento.
    st.set_page_config(                                                      # Configura metadatos de la página mientras estamos en mantenimiento.
        page_title="💍 Daniela & Cristian — Mantenimiento",                  # Título de la pestaña del navegador, acorde al estilo de la boda.
        page_icon="💍",                                                      # Icono de la pestaña (emoji anillo).
        layout="centered"                                                    # Centra el contenido (mejor presentación del aviso).
    )                                                                        # Fin de configuración de página en modo mantenimiento.

    st.markdown(                                                             # Inyecta HTML/CSS personalizado para mostrar una tarjeta elegante.
        """
        <style>
          body { background:#fffaf7; }                                       /* Fondo marfil suave, coherente con la web principal. */
          .card{
            background:#ffffffee; border:1px solid #e9e1d8; border-radius:20px;
            padding:32px 26px; max-width:720px; margin:12vh auto; text-align:center;
            box-shadow:0 10px 30px rgba(0,0,0,.08);
          }
          h1{ font-family:serif; color:#5a4632; margin:.2em 0; }             /* Tipografía tipo serif y color cálido. */
          p{ color:#3e3e3e; }                                                /* Texto gris suave para buena legibilidad. */
          .heart{ font-size:28px; color:#d4a373; }                           /* Detalle dorado en el ícono para reforzar estética. */
        </style>
        <div class="card">                                                   <!-- Contenedor de la tarjeta central. -->
          <div class="heart">💍</div>                                        <!-- Ícono principal. -->
          <h1>Daniela & Cristian</h1>                                        <!-- Encabezado con los nombres. -->
          <p>Estamos preparando una experiencia especial para ti.</p>        <!-- Mensaje principal para invitados. -->
          <p><em>Vuelve pronto para confirmar tu asistencia.</em></p>        <!-- Mensaje secundario en cursiva. -->
        </div>
        """,                                                                 # Cierra el bloque HTML/CSS.
        unsafe_allow_html=True                                               # Permite renderizar HTML dentro de Streamlit.
    )                                                                        # Fin de inyección de HTML/CSS.

    st.stop()                                                                # Detiene la ejecución del resto de la app mientras haya mantenimiento.
# ================================================================
# Fin del modo mantenimiento
# ================================================================

st.set_page_config(                                                          # Configura metadatos básicos de la app cuando NO hay mantenimiento.
    page_title="RSVP • Daniela & Cristian",                                  # Título consistente del sistema RSVP.
    layout="centered",                                                       # Layout centrado: mejor foco en formularios.
    initial_sidebar_state="collapsed",                                       # Oculta la barra lateral por defecto para una UI limpia.
)                                                                            # Fin de configuración de página.

# --- Rutas multipage (mantén estos nombres/ubicación en /pages) ---------------
LOGIN_PAGE = "pages/0_Login.py"                                              # Ruta hacia la pantalla de Login (requiere API y token).
FORM_PAGE  = "pages/1_Formulario_RSVP.py"                                    # Ruta hacia el Formulario protegido (requiere token válido).
REQUEST_ACCESS_PAGE = "pages/00_Solicitar_Acceso.py"                         # Ruta a la página para solicitar acceso (flujo inicial).

# ==============================================================================
# ✅ Lógica de inicialización del idioma por defecto
# ------------------------------------------------------------------------------
# Esta lógica se ejecuta UNA VEZ al inicio de la sesión del usuario.           # Explica que se guarda en session_state.
# 1) Lee el idioma desde la URL (?lang=...).                                   # Prioriza el parámetro de la URL.
# 2) Si no existe, usa el ya guardado en sesión si lo hubiera.                 # Reutiliza el idioma previo de la sesión.
# 3) Si no existe ninguno, establece 'en' (Inglés) como idioma por defecto.    # Fija un idioma por defecto.
# ------------------------------------------------------------------------------
try:                                                                          # Intenta acceder a los parámetros de la URL de forma segura.
    query_lang = st.query_params.get("lang")                                  # Obtiene el valor de ?lang= si está disponible.
except Exception:                                                             # Captura posibles incompatibilidades de versión.
    query_lang = None                                                         # Si hay error, no hay idioma en la URL.

if "lang" not in st.session_state:                                            # Solo inicializa el idioma si no está aún en la sesión.
    if query_lang in ["en", "es", "ro"]:                                      # Valida que el idioma sea uno de los permitidos.
        st.session_state["lang"] = query_lang                                 # Guarda el idioma proveniente de la URL en la sesión.
    else:                                                                     # Si no vino un idioma válido por URL…
        st.session_state["lang"] = "en"                                       # …usa 'en' como idioma por defecto.
# ==============================================================================

# --- (Opcional) Logout por query param ----------------------------------------
try:                                                                          # Maneja compatibilidad de versiones de Streamlit.
    if st.query_params.get("logout") in ("1", "true", "True"):                # Si la URL trae ?logout=1/true, se interpreta como cierre de sesión.
        st.session_state.pop("token", None)                                   # Elimina el JWT de la sesión (desautentica).
        st.session_state.pop("last_rsvp", None)                               # Limpia el último resultado de confirmación almacenado.
        st.query_params.clear()                                               # Limpia todos los parámetros de la URL para evitar bucles.
except Exception:                                                             # Si la API de query_params no existe en la versión actual…
    pass                                                                       # No se considera crítico: simplemente no se hace nada.

# --- Decisión de destino ------------------------------------------------------
target_page = FORM_PAGE if st.session_state.get("token") else REQUEST_ACCESS_PAGE  # Si hay token → Formulario; si no → Solicitar Acceso.

# --- Navegación con manejo de errores ----------------------------------------
try:                                                                          # Intenta usar la navegación multipágina nativa de Streamlit.
    st.switch_page(target_page)                                               # Cambia a la página objetivo según la lógica anterior.
except Exception:                                                             # Si falla (archivo movido/renombrado/problema de sintaxis)…
    st.error(f"No se pudo redirigir a '{target_page}'.")                      # Muestra un error claro al usuario.
    st.info("Verifica que el archivo exista en la carpeta `pages/` con ese nombre.")  # Pista para corregir la ruta.
    st.link_button("Ir a la página de acceso", REQUEST_ACCESS_PAGE)           # Botón de rescate hacia la página de Solicitar Acceso.
    st.link_button("Ir al Formulario", FORM_PAGE)                             # Botón de rescate hacia el Formulario (si existe).
