# pages/2_Confirmado.py                                                     # Ruta del archivo dentro de /pages de Streamlit

# =========================
# ✅ Confirmado (UI final)
# =========================

import os                                                                   # Módulo para leer variables de entorno
import requests                                                             # Librería HTTP para hablar con la API
import streamlit as st                                                      # Streamlit para la interfaz
from dotenv import load_dotenv                                              # Carga variables desde .env

# --- Utilidades del proyecto (i18n + UI) ---
from utils.lang_selector import render_lang_selector                        # Selector de idioma (devuelve el idioma activo)
from utils.translations import t, normalize_lang                            # Funciones de traducción y normalización de idioma
from utils.ui import apply_global_styles                                    # Estilos globales (fondo, tipografías, botones, limpia forms)

# ======================================================================
# 🔧 Funciones auxiliares
# ======================================================================

def fetch_latest_rsvp(api_url: str, auth_headers: dict, current_lang: str):
    """Obtiene el estado más reciente del invitado autenticado desde /api/guest/me."""  # Docstring explicativa
    try:                                                                    # Intenta pedir los datos a la API
        resp = requests.get(f"{api_url}/api/guest/me",                      # Construye URL del recurso
                            headers=auth_headers, timeout=12)               # Envía cabeceras con token y timeout
        if resp.status_code == 200:                                         # Si la respuesta es OK
            return resp.json()                                              # Devuelve el JSON con los datos
        elif resp.status_code == 401:                                       # Si el token expiró o no es válido
            st.session_state.pop("token", None)                             # Limpia el token de sesión
            st.warning(t("form.session_expired", current_lang))             # Muestra aviso de sesión expirada
            st.switch_page("pages/0_Login.py")                              # Redirige a Login
        else:                                                               # Para otros códigos HTTP
            st.error(t("ok.load_error", current_lang))                      # Muestra error genérico de carga
    except requests.exceptions.RequestException:                             # Si falla la red/timeout/etc.
        st.error(t("ok.load_error", current_lang))                          # Muestra mismo error genérico
    return None                                                             # Devuelve None si no hubo datos

def best_effort_resend_confirmation(api_url: str, auth_headers: dict, endpoint: str, summary: dict | None):
    """Intenta reenviar el correo de confirmación (retorna True/False)."""  # Docstring breve
    if not endpoint:                                                        # Si no hay endpoint configurado
        return False                                                        # No podemos reenviar
    try:                                                                    # Intenta disparar el POST
        resp = requests.post(f"{api_url}{endpoint}",                        # URL completa del endpoint
                             headers=auth_headers,                          # Cabeceras con token
                             json=(summary or {}),                          # Cuerpo con el resumen (o vacío)
                             timeout=10)                                    # Timeout razonable
        return resp.status_code in (200, 202, 204)                          # Considera éxito 200/202/204
    except requests.exceptions.RequestException:                             # Cualquier error de red
        return False                                                        # Devuelve False en caso de error

def kill_ghost_inputs():                                                    # Pequeño “mata-fantasmas” para inputs huérfanos
    st.markdown(                                                            # Inyecta un poco de JS/CSS seguro
        """
        <script>
        (function () {
          try {
            const root = document.querySelector('main');                   // Obtiene el contenedor principal
            if (!root) return;                                             // Si no existe, sale
            // Oculta cualquier TextInput que NO esté dentro de un <form> de Streamlit
            const hideGhosts = () => {
              root.querySelectorAll('div[data-testid="stTextInputRoot"]').forEach(el => {  // Busca inputs
                const inForm = !!el.closest('[data-testid="stForm"]');    // Verifica si está en un form real
                if (!inForm) el.style.display = "none";                   // Si no, lo oculta (era fantasma)
              });
            };
            hideGhosts();                                                  // Ejecuta al cargar
            new MutationObserver(hideGhosts).observe(                      // Observa cambios del DOM
              root, { childList: true, subtree: true }                    // Reaplica si Streamlit re-renderiza
            );
          } catch (e) {}
        })();
        </script>
        """,
        unsafe_allow_html=True,                                            # Permite insertar el script
    )

# ======================================================================
# ⚙️ Configuración de página y entorno
# ======================================================================

st.set_page_config(                                                         # Metadatos de la página
    page_title="Confirmación RSVP • Boda D&C",                              # Título de la pestaña
    page_icon="✅",                                                         # Icono de la pestaña
    layout="centered",                                                      # Layout centrado
    initial_sidebar_state="collapsed",                                      # Colapsa sidebar nativa
)                                                                           # Fin configuración

load_dotenv()                                                               # Carga variables de entorno
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")           # URL base de la API (fallback localhost)
RESEND_ENDPOINT = os.getenv("RESEND_CONFIRM_ENDPOINT",                      # Endpoint de reenvío desde .env
                            "/api/guest/me/resend-confirmation")            # Valor por defecto
HOME_URL = os.getenv("HOME_URL", "https://suarezsiicawedding.com/")         # URL pública de Home (fallback a tu dominio)

apply_global_styles()                                                       # Inyecta estilos globales (fondo, tipografías, botones, limpia forms)
kill_ghost_inputs()                                                         # Oculta cualquier input “fantasma” fuera de forms

# Guard de sesión: si no hay token, redirige a Login
if not st.session_state.get("token"):                                       # Verifica token en sesión
    st.switch_page("pages/0_Login.py")                                      # Redirige y corta render

# ======================================================================
# 🔄 Carga de datos + idioma
# ======================================================================

headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}      # Cabeceras con token para la API

initial_lang = normalize_lang(st.session_state.get("lang", "en"))           # Idioma inicial para mensajes tempranos

rsvp_data = st.session_state.get("last_rsvp")                               # Intenta usar el resumen guardado en sesión
if not rsvp_data:                                                           # Si no está
    rsvp_data = fetch_latest_rsvp(API_BASE_URL, headers, initial_lang)      # Lo pide a la API
    if not rsvp_data:                                                       # Si no llega nada usable
        st.stop()                                                           # Detiene ejecución segura

guest_lang = rsvp_data.get("language")                                      # Idioma preferido del invitado (si viene)
final_lang = normalize_lang(guest_lang or initial_lang or "en")             # Normaliza idioma final
st.session_state["lang"] = final_lang                                       # Persiste el idioma final en sesión

# ======================================================================
# 🌐 Idioma (arriba) — sin menú lateral en esta página
# ======================================================================

lang = render_lang_selector()                                               # Renderiza el selector de idioma (arriba) y devuelve el activo
# (No dibujamos render_side_nav en Confirmado para mantener foco y limpieza)  # Comentario: menú lateral desactivado aquí

# ======================================================================
# 🎨 Estilos locales de la tarjeta de confirmación
# ======================================================================

st.markdown(                                                                # Inyecta CSS de la tarjeta contenedora
    """
    <style>
      .confirm-card {
        background: #FFFFFF;                   /* Fondo blanco */
        border: 1px solid #EAEAEA;             /* Borde sutil */
        border-radius: 16px;                   /* Esquinas suaves */
        box-shadow: 0 4px 18px rgba(0,0,0,.06);/* Sombra suave */
        padding: 28px;                         /* Relleno interno */
        max-width: 720px;                      /* Ancho legible */
        margin: 0 auto;                        /* Centrada */
      }
    </style>
    """,
    unsafe_allow_html=True,                                                  # Permite CSS crudo
)

st.markdown('<div class="confirm-card">', unsafe_allow_html=True)            # Abre tarjeta principal

# ======================================================================
# 🖼️ Encabezado y panel de invitación
# ======================================================================

st.title("🎉 " + t("ok.title", final_lang))                                  # Título de página traducido

invited_to_ceremony: bool = bool(rsvp_data.get("invited_to_ceremony"))       # Bandera: invitado a ceremonia
ceremony_time: str = (os.getenv("CEREMONY_TIME")                             # Hora de ceremonia (entorno o secreto)
                      or st.secrets.get("CEREMONY_TIME", "15:00"))           # Fallback 15:00
reception_time: str = (os.getenv("RECEPTION_TIME")                           # Hora de recepción (entorno o secreto)
                       or st.secrets.get("RECEPTION_TIME", "17:00"))         # Fallback 17:00

panel_title: str = t("invite.panel_title", final_lang)                       # Título del panel de invitación
scope_text_key: str = ("invite.scope.full" if invited_to_ceremony            # Clave de alcance según invitación
                       else "invite.scope.reception")                         # Alternativa si solo recepción
scope_text: str = t(scope_text_key, final_lang)                              # Texto de alcance traducido
times_hint: str = t("invite.times.hint", final_lang).format(                 # Línea con horas formateadas
    ceremony_time=ceremony_time, reception_time=reception_time               # Inserta horas reales
)

panel_renderer = (st.success if (rsvp_data.get("attending")                  # Elige componente visual: success si asiste
                                 or rsvp_data.get("confirmed"))              # O info si no asiste
                  else st.info)                                              # Info para no asistentes
panel_renderer(f"### {panel_title}\n\n{scope_text}\n\n_{times_hint}_")       # Dibuja el panel con contenido

# ======================================================================
# 📋 Resumen de la confirmación
# ======================================================================

if rsvp_data.get("attending") or rsvp_data.get("confirmed"):                 # Si asiste / confirmado
    st.success(t("ok.msg_yes", final_lang))                                  # Mensaje de éxito
    st.markdown("**" + t("ok.summary", final_lang) + "**")                   # Título del resumen

    companions = rsvp_data.get("companions", [])                             # Lista de acompañantes
    num_adults = rsvp_data.get("num_adults", 1)                              # Número de adultos (fallback 1)
    num_children = rsvp_data.get("num_children", 0)                          # Número de niños (fallback 0)

    st.write(f"**{t('ok.main_guest', final_lang)}:** "                       # Etiqueta “Invitado principal”
             f"{rsvp_data.get('full_name', 'N/A')}")                         # Nombre (o N/A)
    st.write(f"**{t('ok.adults_children', final_lang)}:** "                  # Etiqueta “Adultos/Niños”
             f"{num_adults} / {num_children}")                               # Números correspondientes

    if rsvp_data.get("allergies"):                                           # Si hay alergias del titular
        st.write(f"**{t('ok.allergies', final_lang)}:** "                    # Etiqueta “Alergias (titular)”
                 f"{rsvp_data['allergies']}")                                # Lista/Texto de alergias

    if companions:                                                           # Si existen acompañantes
        st.markdown("**" + t("ok.companions", final_lang) + "**")            # Título “Acompañantes”
        for c in companions:                                                 # Itera acompañantes
            name = c.get("name", "—")                                        # Toma nombre (o guion)
            child_icon = "👶" if c.get("is_child") else "👤"                 # Icono según niño/adulto
            allergies = (f"({t('ok.alrg_item', final_lang)}: "               # Texto “(Alergias: …)”
                         f"{c.get('allergies')})" if c.get('allergies')      # Solo si tiene alergias
                         else "")                                            # Si no, vacío
            st.markdown(f"- {child_icon} {name} {alergies}")                 # Dibuja ítem de lista
else:                                                                        # Si no asiste
    st.info(t("ok.msg_no", final_lang))                                      # Mensaje de no asistencia

st.markdown("---")                                                           # Separador visual

# ======================================================================
# 🔘 Acciones finales (solo dos): Editar respuesta / Home
# ======================================================================

col1, col2 = st.columns([1, 1])                                             # Dos columnas equilibradas

with col1:                                                                  # Columna izquierda
    if st.button(t("ok.btn_edit", final_lang),                               # Botón “Editar respuesta”
                  use_container_width=True):                                 # Ancho completo
        st.switch_page("pages/1_Formulario_RSVP.py")                         # Vuelve al formulario

with col2:                                                                  # Columna derecha
    st.link_button(                                                          # Botón tipo enlace (navega a Home)
        f"🏠 {t('nav.home', final_lang)}",                                    # Texto traducido “Home/Inicio/Acasă”
        HOME_URL,                                                            # URL pública de inicio
        use_container_width=True,                                            # Ocupa todo el ancho
    )                                                                        # Fin botón Home

st.markdown("</div>", unsafe_allow_html=True)                                # Cierra la tarjeta principal
