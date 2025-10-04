# pages/00_Solicitar_Acceso.py
# =========================================================================================
# 🔑 Solicitar Acceso (Magic Link) — Mockup UX Multilenguaje
# =========================================================================================

import os
import re
import streamlit as st
from dotenv import load_dotenv
from utils.translations import t
from utils.lang_selector import render_lang_selector
from utils.nav import hide_native_sidebar_nav, render_nav

# --- Configuración básica de la página ---
st.set_page_config(
    page_title="Solicitar Acceso • Boda D&C",
    page_icon="🔑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Entorno y constantes ---
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

# --- Menú / Idioma ---
hide_native_sidebar_nav()
lang = render_lang_selector()
render_nav({
    "pages/00_Solicitar_Acceso.py": t("request.title", lang),
    "pages/0_Login.py": t("nav.login", lang),
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),
    "pages/2_Confirmado.py": t("nav.confirmed", lang),
})

# --- Estilos ---
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:wght@600;700&display=swap');
      :root{
        --bg:#FFFFFF; --text:#111111; --muted:#666666; --border:#EAEAEA; --card:#FFFFFF;
        --shadow:0 10px 30px rgba(0,0,0,.08); --radius:18px;
      }
      html, body, [class*="block-container"]{
        background:var(--bg); color:var(--text); font-family:'Inter', sans-serif;
      }
      h1, h2, h3{ font-family:'Playfair Display', serif !important; font-weight:700; }
      .card{ background:var(--card); border:1px solid var(--border); border-radius:var(--radius);
             box-shadow:var(--shadow); padding:28px 26px; max-width:720px; margin:0 auto; }
      .muted{ color:var(--muted); font-size:14px; }
      .center{ text-align:center; }
      .spacer{ height:8px; }
      .hero{ text-align:center; margin-bottom:16px; }
      .hero h1{ margin:0 0 6px 0; font-size:clamp(28px, 4vw, 40px); }
      .hero p{ margin:0; color:var(--muted); font-size:clamp(13px, 2vw, 16px); }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Cabecera/hero ---
st.markdown(
    f"""
    <div class="hero">
      <h1>{t("request.title", lang)}</h1>
      <p>{t("request.intro", lang)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Tarjeta contenedora ---
st.markdown('<div class="card">', unsafe_allow_html=True)

# --- Formulario ---
with st.form("request_access_form"):
    full_name = st.text_input(t("request.full_name", lang), key="full_name_input", help=t("request.full_name", lang))
    phone_last4 = st.text_input(
        t("request.phone_last4", lang),
        key="last4_input",
        placeholder=t("request.phone_last4_placeholder", lang),
        max_chars=4,
    )
    email = st.text_input(t("request.email", lang), key="email_input")
    consent = st.checkbox(t("request.consent", lang), key="req_consent", value=True)

    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

    # Botones lado a lado: Solicitar acceso / Cancelar
    col_ok, col_cancel = st.columns(2)
    submit = col_ok.form_submit_button(t("request.submit", lang), use_container_width=True, type="primary")
    cancel = col_cancel.form_submit_button(t("form.cancel", lang), use_container_width=True)

# --- Acciones de botones ---
if cancel:
    # Volver al Login sin validar ni enviar
    st.switch_page("pages/0_Login.py")

elif submit:
    # Validaciones
    name_ok = len((full_name or "").strip()) >= 3
    phone_ok = bool(re.fullmatch(r"\d{4}", (phone_last4 or "").strip()))
    email_ok = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", (email or "").strip()))
    consent_ok = bool(consent)

    def _msg_neutro() -> str:
        txt = t("request.success_message_neutral", lang)
        return txt if isinstance(txt, str) and txt.strip() else (
            "Si los datos coinciden con tu invitación, recibirás un enlace en tu correo. "
            "Revisa tu bandeja de entrada y también Spam/Promociones."
        )

    has_errors = False
    try:
        if not name_ok:   st.error(t("request.invalid_name", lang));  has_errors = True
        if not phone_ok:  st.error(t("request.invalid_phone4", lang)); has_errors = True
        if not email_ok:  st.error(t("request.invalid_email", lang));  has_errors = True
        if not consent_ok: st.error(t("request.consent_required", lang)); has_errors = True
    except Exception:
        if not name_ok:   st.error("⚠️ Nombre inválido"); has_errors = True
        if not phone_ok:  st.error("⚠️ Los últimos 4 dígitos deben ser numéricos (0000–9999)."); has_errors = True
        if not email_ok:  st.error("⚠️ Ingresa un correo válido (ej. nombre@dominio.com)."); has_errors = True
        if not consent_ok: st.error("⚠️ Debes aceptar el consentimiento para continuar."); has_errors = True

    if not has_errors:
        if DEMO_MODE:
            st.info(_msg_neutro())
        else:
            payload = {
                "full_name": (full_name or "").strip(),
                "phone_last4": (phone_last4 or "").strip(),
                "email": (email or "").strip().lower(),
                "preferred_language": lang,
                "consent": consent_ok,
            }
            APP_DEBUG = os.getenv("APP_DEBUG", "0") == "1"
            try:
                import requests
                r = requests.post(f"{API_BASE_URL}/api/request-access", json=payload, timeout=12)
                st.info(_msg_neutro())
                if r.status_code != 200 and APP_DEBUG:
                    st.warning(f"DEBUG • API {r.status_code}: {r.text[:300]}", icon="🔧")
            except Exception as e:
                st.info(_msg_neutro())
                if APP_DEBUG:
                    st.warning(f"DEBUG • Excepción al llamar API: {e}", icon="🔧")

# --- Enlace de ayuda para volver a Login (se mantiene) ---
st.markdown(
    f"""
    <div class="center muted">
      <p>•</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.page_link("pages/0_Login.py", label=t("nav.login", lang), icon="↩️")

st.markdown('</div>', unsafe_allow_html=True)
