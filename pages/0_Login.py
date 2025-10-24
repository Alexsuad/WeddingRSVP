# pages/0_Login.py

# =================================================================================
# 💍 Página de Login (Rediseño Visual)
# =================================================================================

# --- Importaciones (sin cambios) ---
import os
import re
import requests
import streamlit as st
from dotenv import load_dotenv
from utils.lang_selector import render_lang_selector
from utils.translations import t
from utils.ui import (
    apply_global_styles,
    render_side_nav,
)  # Importa estilos globales y la botonera lateral (solo UI)


# --- Utilidades de limpieza UI (sin cambios, respetando la lógica existente) ---
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
st.set_page_config(  # Configura parámetros de la página de Streamlit
    page_title="Iniciar Sesión • Boda D&C",  # Título de la pestaña del navegador
    page_icon="💍",  # Icono de la pestaña
    layout="centered",  # Layout centrado (contenido en el centro)
    initial_sidebar_state="collapsed",  # Sidebar nativa colapsada (además la ocultamos por CSS)
)  # Cierra la configuración

load_dotenv()  # Carga variables de entorno del archivo .env
apply_global_styles()  # ← Aplica estilos globales (fondo, tipografías, oculta sidebar, etc.)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
RECOVERY_URL = os.getenv("RECOVERY_URL", "")

# --- UI Global: Menú y Selector de Idioma ---
lang = (
    render_lang_selector()
)  # Renderiza el selector de idioma y devuelve el idioma activo (es/en/ro)
render_side_nav(t, lang, hide=["login"])  # Usa los defaults de ui.py


# --- Parche UI (sin cambios) ---
_inject_ghost_killer_css()
# _remove_ghost_input_js()
# _debug_outline_boxes(enabled=True)

# --- Redirección si ya hay sesión activa ---
if st.session_state.get("token"):
    st.switch_page("pages/1_Formulario_RSVP.py")

# --- ESTILOS MEJORADOS Y UNIFICADOS ---
st.markdown(
    """
    <style>
        /* 1) Fuentes (debe ir FUERA de :root) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:wght@600;700&display=swap'); /* Carga tipografías */

        /* 2) Tokens (un SOLO :root) */
        :root{ /* Variables globales */
            --bg:#FFFFFF; /* Fondo base */
            --text:#111111; /* Texto principal */
            --muted:#666666; /* Texto secundario */
            --primary:#0F0F0F; /* Negro de marca */
            --shadow:0 10px 35px rgba(0,0,0,.08); /* Sombra suave */
            --radius:12px; /* Radio estándar */
            --primary-color:#0F0F0F; /* Primario usado por Streamlit (forzamos negro) */
        } /* fin :root */

        /* 3) Fondo suave + sin header/sidebar */
        .stApp{ /* Contenedor principal */
            background-image:
            linear-gradient(rgba(255,255,255,.9), rgba(255,255,255,.9)), /* Velo blanco 0.9 */
            url('https://images.unsplash.com/photo-1515934751635-c81c6bc9a2d8?auto=format&fit=crop&q=80&w=2070'); /* Imagen anillos */
            background-size:cover; /* Cubre viewport */
            background-position:center center; /* Centra imagen */
        }
        [data-testid="stHeader"]{ display:none; } /* Oculta header nativo */
        [data-testid="stSidebar"]{ display:none !important; } /* Oculta sidebar */
        [data-testid="stSidebarCollapsedControl"]{ display:none !important; } /* Oculta control «» */
        [data-testid="stAppViewContainer"] > .main{ margin-left:0 !important; } /* Quita margen de sidebar */
        .main .block-container{ padding-left:0 !important; } /* Quita sangría residual */

        /* 4) Tipografía, hero y card (idénticos a la base) */
        html, body, [class*="block-container"]{ font-family:'Inter',sans-serif; } /* Texto Inter */
        h1,h2,h3{ font-family:'Playfair Display',serif !important; font-weight:700; color:var(--text); } /* Títulos Playfair */
        .hero{ text-align:center; padding:2rem 0 4rem 0; } /* Ritmo vertical */
        .hero h1{ margin:0 0 10px 0; font-size:2.8rem; } /* Tamaño H1 */
        .hero p{ margin:0; color:var(--muted); font-size:1.1rem; } /* Subtítulo */
        .card{ background:var(--bg); border-radius:var(--radius); box-shadow:var(--shadow); padding:2.5rem; max-width:500px; margin:-50px auto 0; } /* Tarjeta */

        /* 5) Anti “caja fantasma” del form (encapsulado por id #login) */
        #login form{ background:transparent !important; border:none !important; box-shadow:none !important; padding:0 !important; } /* Form transparente */
        #login form > div{ background:transparent !important; border:none !important; box-shadow:none !important; padding:0 !important; } /* Wrapper transparente */
        #login div[data-testid="stFormSubmitButton"]{ background:transparent !important; border:none !important; box-shadow:none !important; } /* Contenedor submit transparente */

        /* 6) Botones de idioma (outline blanco + hover gris) */
        .stButton > button:not([kind="primary"]){ background:#FFF !important; color:#111 !important; border:1px solid #E5E5E5 !important; border-radius:8px !important; font-weight:600 !important; transition:all .2s ease !important; } /* Outline */
        .stButton > button:not([kind="primary"]):hover{ background:#F5F5F5 !important; } /* Hover gris */

        /* 7) Botón primario “Acceder” en NEGRO — cubrimos 3 variantes de Streamlit */
        #login [data-testid="stFormSubmitButton"] > button{ background:var(--primary-color) !important; color:#FFF !important; border:none !important; border-radius:10px !important; width:100% !important; padding:10px 16px !important; box-shadow:0 1px 2px rgba(0,0,0,.06) !important; transition:transform .02s ease, opacity .2s ease !important; } /* Variante wrapper */
        #login .stButton > button[kind="primary"]{ background:var(--primary-color) !important; color:#FFF !important; border:none !important; border-radius:10px !important; } /* Variante con atributo kind */
        #login button[data-testid="baseButton-primary"]{ background:var(--primary-color) !important; color:#FFF !important; border:none !important; border-radius:10px !important; } /* Variante por data-testid nueva */
        /* Hover grisado para todas las variantes */
        #login [data-testid="stFormSubmitButton"] > button:hover,
        #login .stButton > button[kind="primary"]:hover,
        #login button[data-testid="baseButton-primary"]:hover{ filter:brightness(.9) !important; } /* Hover */

        /* 8) Enlace inferior (igual a la base) */
        .login-link{ text-align:center; margin-top:1.5rem; padding-top:1.5rem; border-top:1px solid #EEE; } /* Contenedor link */
        .login-link a{ color:var(--muted); text-decoration:none; font-size:1rem; font-weight:500; transition:color .2s; } /* Link */
        .login-link a:hover{ color:var(--primary); text-decoration:underline; } /* Hover link */
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
        elif resp.status_code == 429:
            return None, t("login.errors_rate_limit", lang)
        return None, f"{server_err} (HTTP {resp.status_code})"
    except requests.exceptions.RequestException:
        return None, server_err


# --- Interfaz de Usuario (Hero + Tarjeta de Login) ---
st.markdown(
    f"""
    <div class="hero">
      <h1>Jenny &amp; Cristian</h1>
      <p>{t("login.intro", lang)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div id="login">', unsafe_allow_html=True
)  # Abre un contenedor con id="login" para aislar estilos del formulario.

with st.form("login_form"):  # Abre el formulario (lógica intacta).
    guest_code = st.text_input(
        t("login.code", lang), key="guest_code_input"
    )  # Campo código (sin cambios de lógica).
    contact = st.text_input(
        t("login.contact", lang), key="contact_input"
    )  # Campo contacto (sin cambios de lógica).
    st.markdown(
        '<div style="height: 1rem;"></div>', unsafe_allow_html=True
    )  # Espaciador visual (igual que antes).
    login_btn = st.form_submit_button(
        t("login.submit", lang),  # Botón de enviar (tipo primario).
        use_container_width=True,
        type="primary",
    )  # Ancho completo y primario.

st.markdown(
    "</div>", unsafe_allow_html=True
)  # Cierra el contenedor #login para poder “encapsular” el CSS.

# --- Lógica de Acciones ---
if login_btn:
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

# --- Acceso a recuperación de código (con nuevo estilo) ---
st.markdown(
    f"""
    <div class="login-link">
        <a href="/Recuperar_Codigo" target="_self">
            <span>🔑</span>&nbsp;
            {t("login.forgot", lang)}
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
