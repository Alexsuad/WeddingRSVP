# pages/2_Confirmado.py
# Versión Corregida y Limpiada

import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Importa todas las utilidades necesarias al principio
from utils.lang_selector import render_lang_selector
from utils.translations import t, normalize_lang
from utils.nav import hide_native_sidebar_nav, render_nav

# ======================================================================
# DEFINICIÓN DE FUNCIONES (al principio del archivo)
# ======================================================================

def fetch_latest_rsvp(api_url: str, auth_headers: dict, current_lang: str):
    """Obtiene el último estado de RSVP del invitado autenticado."""
    try:
        resp = requests.get(f"{api_url}/api/guest/me", headers=auth_headers, timeout=12)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.session_state.pop("token", None)
            # Usa 'current_lang' que le pasamos como argumento
            st.warning(t("form.session_expired", current_lang))
            st.switch_page("pages/0_Login.py")
        else:
            st.error(t("ok.load_error", current_lang))
    except requests.exceptions.RequestException:
        st.error(t("ok.load_error", current_lang))
    return None

def best_effort_resend_confirmation(api_url: str, auth_headers: dict, endpoint: str, summary: dict | None):
    """Intenta disparar el reenvío del correo de confirmación."""
    if not endpoint:
        return False
    try:
        resp = requests.post(
            f"{api_url}{endpoint}",
            headers=auth_headers,
            json=(summary or {}),
            timeout=10,
        )
        return resp.status_code in (200, 202, 204)
    except requests.exceptions.RequestException:
        return False

# ======================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ======================================================================

st.set_page_config(
    page_title="Confirmación RSVP • Boda D&C",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Carga de variables de entorno
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
RESEND_ENDPOINT = os.getenv("RESEND_CONFIRM_ENDPOINT", "/api/guest/me/resend-confirmation")

# Guard de sesión: si no hay token, no continuamos.
if not st.session_state.get("token"):
    st.switch_page("pages/0_Login.py")

# ======================================================================
# LÓGICA PRINCIPAL (Carga de datos -> Resolución de idioma -> Render)
# ======================================================================

# 1. Define las cabeceras de autenticación una sola vez
headers = {"Authorization": f"Bearer {st.session_state.get('token')}"}

# 2. Resuelve el idioma inicial (antes de llamar a la API)
#    Esto nos da un idioma para los mensajes de error si la API falla
initial_lang = normalize_lang(st.session_state.get("lang", "en"))

# 3. Carga los datos del invitado
rsvp_data = st.session_state.get("last_rsvp")
if not rsvp_data:
    rsvp_data = fetch_latest_rsvp(API_BASE_URL, headers, initial_lang)
    if not rsvp_data:
        st.stop() # Si no se pueden cargar los datos, detiene la ejecución

# 4. Resuelve el idioma final con los datos del invitado
guest_lang = rsvp_data.get("language")
final_lang = normalize_lang(guest_lang or initial_lang or "en")
st.session_state["lang"] = final_lang

# 5. Renderiza la UI con el idioma final
hide_native_sidebar_nav()
render_lang_selector() # Permite al usuario cambiar el idioma si lo desea
render_nav({
    "pages/0_Login.py": t("nav.login", final_lang),
    "pages/1_Formulario_RSVP.py": t("nav.form", final_lang),
    "pages/2_Confirmado.py": t("nav.confirmed", final_lang),
})

# ======================================================================
# RENDERIZADO DEL CONTENIDO DE LA PÁGINA
# ======================================================================

st.markdown(
    """
    <style>
      .confirm-card { background: #FFF; border: 1px solid #EAEAEA; border-radius: 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,.06); padding: 28px; max-width: 720px; margin: 0 auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="confirm-card">', unsafe_allow_html=True)

# Usa 'final_lang' para todas las traducciones
st.title("🎉 " + t("ok.title", final_lang))

# ... (El resto del código de renderizado, usando 'final_lang' en lugar de 'lang')
# ... (He copiado el resto de tu código aquí abajo para que sea completo)

# Alcance de invitación / pista de horarios
invited_to_ceremony: bool = bool(rsvp_data.get("invited_to_ceremony"))
ceremony_time: str = st.secrets.get("CEREMONY_TIME", "15:00")
reception_time: str = st.secrets.get("RECEPTION_TIME", "17:00")

panel_title: str = t("invite.panel_title", final_lang)
scope_text_key: str = "invite.scope.full" if invited_to_ceremony else "invite.scope.reception"
scope_text: str = t(scope_text_key, final_lang)
times_hint: str = t("invite.times.hint", final_lang).format(
    ceremony_time=ceremony_time, reception_time=reception_time
)

panel_renderer = st.success if (rsvp_data.get("attending") or rsvp_data.get("confirmed")) else st.info
panel_renderer(f"### {panel_title}\n\n{scope_text}\n\n_{times_hint}_")

# Mensajes y Resumen
if rsvp_data.get("attending") or rsvp_data.get("confirmed"):
    st.success(t("ok.msg_yes", final_lang))
    st.markdown("**" + t("ok.summary", final_lang) + "**")

    companions = rsvp_data.get("companions", [])
    num_adults = rsvp_data.get("num_adults", 1)
    num_children = rsvp_data.get("num_children", 0)

    st.write(f"**{t('ok.main_guest', final_lang)}:** {rsvp_data.get('full_name', 'N/A')}")
    st.write(f"**{t('ok.adults_children', final_lang)}:** {num_adults} / {num_children}")

    if rsvp_data.get("allergies"):
        st.write(f"**{t('ok.allergies', final_lang)}:** {rsvp_data['allergies']}")

    if companions:
        st.markdown("**" + t("ok.companions", final_lang) + "**")
        for c in companions:
            name = c.get("name", "—")
            child_icon = "👶" if c.get("is_child") else "👤"
            allergies = f"({t('ok.alrg_item', final_lang)}: {c.get('allergies')})" if c.get('allergies') else ""
            st.markdown(f"- {child_icon} {name} {allergies}")
else:
    st.info(t("ok.msg_no", final_lang))

st.markdown("---")

# Acciones
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button(t("ok.btn_edit", final_lang), use_container_width=True):
        st.switch_page("pages/1_Formulario_RSVP.py")

with col2:
    if st.button(t("ok.btn_resend_email", final_lang), use_container_width=True):
        with st.spinner(t("ok.sending", final_lang)):
            ok = best_effort_resend_confirmation(API_BASE_URL, headers, RESEND_ENDPOINT, rsvp_data)
        if ok:
            st.success(t("ok.resent_ok", final_lang))
        else:
            st.warning(t("ok.resent_fail", final_lang))

with col3:
    if st.button(t("ok.btn_logout", final_lang), use_container_width=True):
        st.session_state.pop("token", None)
        st.session_state.pop("last_rsvp", None)
        st.switch_page("pages/0_Login.py")

st.markdown("</div>", unsafe_allow_html=True)