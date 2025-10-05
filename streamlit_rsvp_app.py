# streamlit_rsvp_app.py
# =================================================================================
# 🚀 Punto de Entrada — App de Invitados (Streamlit Multipage)
# Rol: decidir destino según JWT en sesión y redirigir (Login ↔ Formulario).
# Extras opcionales: botones de rescate si falla la navegación y logout por query.
# =================================================================================

# ================================================================
# 🌙 MODO MANTENIMIENTO (Controlado por variable de entorno)
# ================================================================
import os
import streamlit as st

# Si MAINTENANCE_MODE está activo, mostrar aviso y detener la app
if os.getenv("MAINTENANCE_MODE") == "1":
    st.set_page_config(page_title="Mantenimiento", page_icon="🌙")
    st.warning("🌙 El sistema está en mantenimiento.\n\nVuelve más tarde, por favor.")
    st.stop()

# ================================================================
# Fin del modo mantenimiento
# ================================================================



st.set_page_config(                              # Configura metadatos básicos de la app.
    page_title="RSVP • Daniela & Cristian",     # Título consistente en todo el proyecto.
    layout="centered",                           # Layout centrado para enfoque en formularios.
    initial_sidebar_state="collapsed",           # Sidebar colapsado para una UI limpia.
)                                                # Fin de configuración de página.

# --- Rutas multipage (mantén estos nombres/ubicación en /pages) ---------------
LOGIN_PAGE = "pages/0_Login.py"                  # Ruta hacia la pantalla de Login.
FORM_PAGE  = "pages/1_Formulario_RSVP.py"        # Ruta hacia el Formulario protegido.
# ✅ AJUSTE: Añadimos la ruta a la nueva página de Solicitud de Acceso (Magic Link)
REQUEST_ACCESS_PAGE = "pages/00_Solicitar_Acceso.py" 

# ==============================================================================
# ✅ AJUSTE: Lógica de inicialización del idioma por defecto
# ------------------------------------------------------------------------------
# Esta lógica se ejecuta UNA VEZ al inicio de la sesión del usuario.
# 1. Intenta leer el idioma desde la URL (?lang=...).
# 2. Si no existe, comprueba si ya hay un idioma en la sesión.
# 3. Si tampoco existe, establece el idioma por defecto a 'en' (Inglés).
# ------------------------------------------------------------------------------
try:
    query_lang = st.query_params.get("lang")
except Exception:
    query_lang = None

if "lang" not in st.session_state:
    # Si viene un idioma válido en la URL, lo usamos. Si no, usamos 'en' por defecto.
    if query_lang in ["en", "es", "ro"]: # Aseguramos que sea uno de los idiomas válidos
        st.session_state["lang"] = query_lang
    else:
        st.session_state["lang"] = "en"  # <-- IDIOMA POR DEFECTO ESTABLECIDO AQUÍ
# ==============================================================================

# --- (Opcional) Logout por query param ----------------------------------------
try:                                             # Envuelto en try por compatibilidad de versiones.
    if st.query_params.get("logout") in ("1", "true", "True"):  # Si la URL trae ?logout=1/true...
        st.session_state.pop("token", None)      # Elimina el JWT de la sesión (cierra sesión).
        st.session_state.pop("last_rsvp", None)  # Limpia últimos datos de confirmación.
        # ✅ AJUSTE: Limpiamos todos los query params para evitar bucles o estados no deseados.
        st.query_params.clear() 
except Exception:                                 # Si la API de query_params no existe…
    pass                                         # Ignora silenciosamente; no es crítico.

# --- Decisión de destino ------------------------------------------------------
# ✅ AJUSTE: Si hay token, va al Formulario. Si no hay token, va a la nueva página de Solicitud de Acceso.
target_page = FORM_PAGE if st.session_state.get("token") else REQUEST_ACCESS_PAGE

# --- Navegación con manejo de errores ----------------------------------------
try:
    st.switch_page(target_page)                  # Intenta redirigir usando multipage nativo.
except Exception:                                 # Si falla (ruta movida/renombrada/sintaxis rota)…
    st.error(f"No se pudo redirigir a '{target_page}'.")  # Mensaje claro de fallo de navegación.
    st.info("Verifica que el archivo exista en la carpeta `pages/` con ese nombre.")  # Pista de corrección.
    # Botones de rescate (opcionales) para no dejar al usuario bloqueado:
    # ✅ AJUSTE: Cambiamos el botón de "Ir al Login" por "Ir a la página de acceso"
    st.link_button("Ir a la página de acceso", REQUEST_ACCESS_PAGE) 
    st.link_button("Ir al Formulario", FORM_PAGE) # Enlace directo al Formulario (si existe).