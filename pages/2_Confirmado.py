# pages/2_Confirmado.py

import os
import requests
import streamlit as st
from dotenv import load_dotenv
from utils.lang_selector import render_lang_selector
from utils.translations import t
from utils.nav import hide_native_sidebar_nav, render_nav

st.set_page_config(
    page_title="Confirmación RSVP • Boda D&C",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed",
)

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
CONFIRM_RESEND_ON_LOAD = os.getenv("CONFIRM_RESEND_ON_LOAD", "1") == "1"
RESEND_ENDPOINT = "/api/guest/me/resend-confirmation"  # opcional; si no existe, la llamada se ignora

hide_native_sidebar_nav()
lang = render_lang_selector()
render_nav({
    "pages/0_Login.py": t("nav.login", lang),
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),
    "pages/2_Confirmado.py": t("nav.confirmed", lang),
})

if not st.session_state.get("token"):
    st.switch_page("pages/0_Login.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.markdown("""
    <style>
      .confirm-card { background:#FFF; border:1px solid #EAEAEA; border-radius:16px;
                      box-shadow:0 4px 18px rgba(0,0,0,.06); padding:28px; max-width:720px; margin:0 auto; }
    </style>
""", unsafe_allow_html=True)

def fetch_latest_rsvp():
    try:
        resp = requests.get(f"{API_BASE_URL}/api/guest/me", headers=headers, timeout=12)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.session_state.pop("token", None)
            st.warning(t("form.session_expired", lang))
            st.switch_page("pages/0_Login.py")
        else:
            st.error(t("ok.load_error", lang))
    except requests.exceptions.RequestException:
        st.error(t("ok.load_error", lang))
    return None

def best_effort_resend_confirmation(summary_payload: dict | None):
    """
    Intenta (best-effort) disparar el reenvío del correo de confirmación.
    - Si el endpoint no existe o falla, no rompe la UI.
    - summary_payload es opcional; si tu backend lo requiere, lo enviamos.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}{RESEND_ENDPOINT}",
            headers=headers,
            json=(summary_payload or {}),
            timeout=10
        )
        # Aceptamos 200/204/202 como OK; cualquier otra cosa se ignora silenciosamente
        return resp.status_code in (200, 202, 204)
    except requests.exceptions.RequestException:
        return False

# 1) Prioriza datos de sesión (viniendo de /1_Formulario_RSVP)
rsvp_data = st.session_state.get("last_rsvp")

# 2) Si no hay en sesión, carga del backend y (opcional) dispara reenvío al cargar
if not rsvp_data:
    rsvp_data = fetch_latest_rsvp()
    if not rsvp_data:
        st.stop()
    if CONFIRM_RESEND_ON_LOAD:
        best_effort_resend_confirmation(rsvp_data)

# Render principal
st.markdown('<div class="confirm-card">', unsafe_allow_html=True)
st.title("🎉 " + t("ok.title", lang))

invite_scope: str = (rsvp_data.get("invite_scope") or "reception-only").strip()
invited_to_ceremony: bool = bool(rsvp_data.get("invited_to_ceremony"))
ceremony_time: str = st.secrets.get("CEREMONY_TIME", "15:00")
reception_time: str = st.secrets.get("RECEPTION_TIME", "17:00")

panel_title: str = t("invite.panel_title", lang)
scope_text_key: str = "invite.scope.full" if invited_to_ceremony else "invite.scope.reception"
scope_text: str = t(scope_text_key, lang)
times_hint: str = t("invite.times.hint", lang).format(
    ceremony_time=ceremony_time, reception_time=reception_time
)
panel_renderer = st.success if (rsvp_data.get("attending") or rsvp_data.get("confirmed")) else st.info
panel_renderer(f"### {panel_title}\n\n{scope_text}\n\n_{times_hint}_")

if rsvp_data.get("attending") or rsvp_data.get("confirmed"):
    st.success(t("ok.msg_yes", lang))
    st.markdown("**" + t("ok.summary", lang) + "**")

    companions = rsvp_data.get("companions", [])
    num_adults = rsvp_data.get("num_adults", 1)
    num_children = rsvp_data.get("num_children", 0)

    st.write(f"**{t('ok.main_guest', lang)}:** {rsvp_data.get('full_name', 'N/A')}")
    st.write(f"**{t('ok.adults_children', lang)}:** {num_adults} / {num_children}")

    if rsvp_data.get("allergies"):
        st.write(f"**{t('ok.allergies', lang)}:** {rsvp_data['allergies']}")

    if companions:
        st.markdown("**" + t("ok.companions", lang) + "**")
        for c in companions:
            name = c.get("name", "—")
            child_icon = "👶" if c.get("is_child") else "👤"
            allergies = f"({t('ok.alrg_item', lang)}: {c.get('allergies')})" if c.get('allergies') else ""
            st.markdown(f"- {child_icon} {name} {alergies}")
else:
    st.info(t("ok.msg_no", lang))

st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button(t("ok.btn_edit", lang), use_container_width=True):
        st.switch_page("pages/1_Formulario_RSVP.py")

with col2:
    # Botón para reenviar correo de confirmación a voluntad del invitado
    if st.button(t("ok.btn_resend_email", lang), use_container_width=True):
        with st.spinner(t("ok.sending", lang)):
            ok = best_effort_resend_confirmation(rsvp_data)
        if ok:
            st.success(t("ok.resent_ok", lang))
        else:
            st.warning(t("ok.resent_fail", lang))

with col3:
    if st.button(t("ok.btn_logout", lang), use_container_width=True):
        st.session_state.pop("token", None)
        st.session_state.pop("last_rsvp", None)
        st.switch_page("pages/0_Login.py")

st.markdown("</div>", unsafe_allow_html=True)
