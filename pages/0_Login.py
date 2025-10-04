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
import os
import re
import requests
import streamlit as st
from dotenv import load_dotenv
from utils.lang_selector import render_lang_selector
from utils.translations import t
from utils.nav import hide_native_sidebar_nav, render_nav

# --- Utilidades de limpieza UI (caja fantasma) ---
def _inject_ghost_killer_css() -> None:
    st.markdown(
        """
        <style>
          /* CSS suave: no ocultamos nada por defecto */
        </style>
        """,
        unsafe_allow_html=True,
    )

def _remove_ghost_input_js() -> None:
    st.markdown(
        """
        <script>
        (function () {
          try {
            const root = document.querySelector('main');
            if (!root) return;
            const WHITELIST = new Set([
              "Código de invitación","Email o teléfono de contacto",
              "Invitation code","Email or phone",
              "Cod invitație","Email sau telefon"
            ]);
            const isRealFormInput = (el) => {
              const inForm = !!el.closest('[data-testid="stForm"]');
              const label = el.querySelector('label');
              const labelText = (label && label.textContent || "").trim();
              return inForm && WHITELIST.has(labelText);
            };
            const hideGhosts = () => {
              const nodes = root.querySelectorAll('div[data-testid="stTextInputRoot"]');
              nodes.forEach(el => {
                if (isRealFormInput(el)) { el.style.display = ""; return; }
                const label = el.querySelector('label');
                const labelText = (label && label.textContent || "").trim();
                const looksGhost = !labelText || !el.closest('[data-testid="stForm"]');
                if (looksGhost) el.style.display = "none";
              });
            };
            hideGhosts();
            const obs = new MutationObserver(() => {
              clearTimeout(window.__ghost_killer_timer);
              window.__ghost_killer_timer = setTimeout(hideGhosts, 30);
            });
            obs.observe(root, { childList: true, subtree: true });
          } catch (e) {}
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

def _debug_outline_boxes(enabled: bool = False) -> None:
    if not enabled:
        return
    st.markdown(
        """
        <style>
          main div { outline: 1px dashed rgba(200,0,0,.15); }
        </style>
        """,
        unsafe_allow_html=True,
    )

# --- Configuración de Página y Entorno ---
st.set_page_config(
    page_title="Confirmar Asistencia • Boda D&C",
    page_icon="💍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
RECOVERY_URL = os.getenv("RECOVERY_URL", "")

# --- UI Global: Menú y Selector de Idioma ---
hide_native_sidebar_nav()
lang = render_lang_selector()
render_nav({
    "pages/0_Login.py": t("nav.login", lang),
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),
    "pages/2_Confirmado.py": t("nav.confirmed", lang),
})

# --- Parche UI: intenta ocultar/eliminar la caja fantasma SI aparece ---
_inject_ghost_killer_css()
# _remove_ghost_input_js()
# _debug_outline_boxes(enabled=True)

# --- Redirección si ya hay sesión activa ---
if st.session_state.get("token"):
    st.switch_page("pages/1_Formulario_RSVP.py")

# --- Estilos (estética general) ---
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:wght@600;700&display=swap');
      :root{
        --bg:#FFFFFF; --text:#111111; --muted:#666666; --border:#EAEAEA; --card:#FFFFFF;
        --shadow:0 10px 30px rgba(0,0,0,.08); --radius:18px; --radius-sm:14px;
      }
      html, body, [class*="block-container"]{
        background:var(--bg); color:var(--text); font-family:'Inter', sans-serif;
      }
      h1, h2, h3{ font-family:'Playfair Display', serif !important; font-weight:700; }
      .hero{ text-align:center; margin-bottom:20px; }
      .hero h1{ font-size:clamp(34px, 5vw, 52px); margin:0 0 6px 0; }
      .hero p{ margin:0; color:var(--muted); font-size:clamp(14px, 2vw, 18px); }
      .login-card{ background:var(--card); border:1px solid var(--border); border-radius:var(--radius);
                   box-shadow:var(--shadow); padding:28px 26px; max-width:720px; margin:0 auto; }
      .muted{ color:var(--muted); font-size:14px; }
      .center{ text-align:center; }
      div[data-testid="stImage"]{ display:flex; justify-content:center; margin-top:6px; }
      div[data-testid="stImage"] > img{ height:24px !important; width:auto !important; }
      .stButton > button{ margin-bottom:6px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Funciones Helper (autenticación) ---
def sanitize_contact(value: str) -> tuple[str | None, str | None]:
    v = (value or "").strip()
    if "@" in v:
        return v.lower(), None
    phone = re.sub(r"[^\d+]", "", v)
    return None, (phone or None)

def api_login(guest_code: str, contact: str) -> tuple[str | None, str | None]:
    email, phone = sanitize_contact(contact)
    payload = {"guest_code": (guest_code or "").strip(), "email": email, "phone": phone}
    server_err = t("login.server_err", lang)
    if server_err == "login.server_err":
        server_err = t("form.server_err", lang)
    try:
        resp = requests.post(f"{API_BASE_URL}/api/login", json=payload, timeout=12)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                return None, server_err
            token = (data or {}).get("access_token")
            return (token, None) if token else (None, server_err)
        elif resp.status_code == 401:
            return None, t("login.errors_auth", lang)
        return None, f"{server_err} (HTTP {resp.status_code})"
    except requests.exceptions.RequestException:
        return None, server_err

# --- Interfaz de Usuario (Hero + Tarjeta de Login) ---
st.markdown(
    f"""
    <div class="hero">
      <h1>Daniela &amp; Cristian</h1>
      <p>{t("login.intro", lang)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="login-card">', unsafe_allow_html=True)

with st.form("login_form"):
    guest_code = st.text_input(t("login.code", lang), key="guest_code_input")
    contact = st.text_input(t("login.contact", lang), key="contact_input")
    # Botones lado a lado: Acceder / Cancelar
    col_ok, col_cancel = st.columns(2)
    login_btn = col_ok.form_submit_button(t("login.submit", lang), type="primary", use_container_width=True)
    cancel_btn = col_cancel.form_submit_button(t("form.cancel", lang), use_container_width=True)

# --- Acciones de los botones ---
if cancel_btn:
    # Navega a "Solicitar Acceso" (pantalla previa), sin validar.
    st.switch_page("pages/00_Solicitar_Acceso.py")

elif login_btn:
    if not guest_code.strip() or not contact.strip():
        st.error(t("login.errors_empty", lang))
    else:
        with st.spinner(t("login.validating", lang)):
            token, error = api_login(guest_code, contact)
        if token:
            st.session_state["token"] = token
            st.success(t("login.success", lang))
            st.rerun()
        else:
            st.error(error)

# --- Acceso a recuperación de código (robusto) ---
with st.container():
    st.markdown('<div class="center muted">', unsafe_allow_html=True)
    try:
        if RECOVERY_URL.strip():
            st.markdown(
                f'<a href="{RECOVERY_URL}" target="_blank">{t("login.forgot", lang)}</a>',
                unsafe_allow_html=True,
            )
        else:
            # OJO: si tu archivo es "01_Recuperar_Codigo.py", ajusta la ruta aquí.
            st.page_link("pages/01_Recuperar_Codigo.py", label=t("login.forgot", lang), icon="🔑")
    except Exception:
        if not RECOVERY_URL.strip():
            st.write(f"🔑 {t('login.forgot', lang)}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
