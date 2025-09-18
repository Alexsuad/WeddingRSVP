# pages/00_Solicitar_Acceso.py
# =========================================================================================
# 🔑 Solicitar Acceso (Magic Link) — Mockup UX Multilenguaje
# -----------------------------------------------------------------------------------------
# Objetivo:
# - Pantalla previa para capturar: Nombre completo + últimos 4 del teléfono + email + consentimiento.
# - Multilenguaje con tus utilidades (utils/lang_selector.py y utils/translations.py).
# - Modo DEMO (no llama a backend): simula "éxito" para validar el flujo antes de implementar API.
# - Diseño alineado con el look & feel existente (tipografías, tarjeta centrada, botones).
# =========================================================================================

# --- Importaciones estándar y utilidades del proyecto ---
import os                                  # Para leer variables de entorno (.env) si hace falta.
import re                                  # Para validaciones simples (últimos 4, email básico).
import streamlit as st                     # Librería Streamlit para UI.
from dotenv import load_dotenv             # Cargar variables de entorno locales en desarrollo.
from utils.translations import t           # Función de traducción i18n centralizada.
from utils.lang_selector import render_lang_selector  # Selector de idioma (banderitas).
from utils.nav import hide_native_sidebar_nav, render_nav  # Navegación personalizada.

# --- Configuración básica de la página ---
st.set_page_config(                        # Debe ser la primera llamada: configura la pestaña.
    page_title="Solicitar Acceso • Boda D&C",  # Título de la pestaña del navegador.
    page_icon="🔑",                        # Icono de la pestaña.
    layout="centered",                     # Centra el contenido.
    initial_sidebar_state="collapsed",     # Sidebar colapsado por defecto.
)

# --- Entorno y constantes ---
load_dotenv()                              # Carga .env en entorno local (no hace nada en prod si no existe).
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")  # URL base de la API (para futuro).
DEMO_MODE = True                           # ⚠️ True = NO llama a la API; simula éxito UX. Cambiar a False cuando conectes backend.

# --- Oculta navegación nativa y pinta la tuya con i18n ---
hide_native_sidebar_nav()                  # Oculta el multipage nativo de Streamlit.
lang = render_lang_selector()              # Muestra selector de idioma (banderitas) y devuelve el idioma activo.
render_nav({                               # Dibuja menú lateral consistente con el resto de páginas.
    "pages/00_Solicitar_Acceso.py": t("request.title", lang),     # Esta página (título i18n).
    "pages/0_Login.py": t("nav.login", lang),                     # Acceso tradicional (por si lo quieren usar).
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),            # Formulario RSVP (protegido).
    "pages/2_Confirmado.py": t("nav.confirmed", lang),            # Resumen/confirmado.
})

# --- Estilos suaves para tarjeta y tipografías (alineado con tu look & feel) ---
st.markdown(                               # Inyecta CSS para tarjeta y fuentes.
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
      .card{
        background:var(--card); border:1px solid var(--border); border-radius:var(--radius);
        box-shadow:var(--shadow); padding:28px 26px; max-width:720px; margin:0 auto;
      }
      .muted{ color:var(--muted); font-size:14px; }
      .center{ text-align:center; }
      .spacer{ height:8px; }
      .hero{ text-align:center; margin-bottom:16px; }
      .hero h1{ margin:0 0 6px 0; font-size:clamp(28px, 4vw, 40px); }
      .hero p{ margin:0; color:var(--muted); font-size:clamp(13px, 2vw, 16px); }
    </style>
    """,
    unsafe_allow_html=True,                # Permite HTML para estilos embebidos.
)

# --- Cabecera/hero ---
st.markdown(                               # Renderiza encabezado cálido y breve.
    f"""
    <div class="hero">
      <h1>{t("request.title", lang)}</h1>                         <!-- Título i18n -->
      <p>{t("request.intro", lang)}</p>                           <!-- Intro i18n (con segundo factor) -->
    </div>
    """,
    unsafe_allow_html=True,               # Permite HTML en el bloque.
)

# --- Tarjeta contenedora del formulario ---
st.markdown('<div class="card">', unsafe_allow_html=True)  # Abre contenedor estilizado.

# --- Formulario de solicitud (Magic Link / Captura de correo) ---
with st.form("request_access_form"):       # Crea un formulario con estado atómico (envío único).
    full_name = st.text_input(             # Campo: nombre completo como aparece en la invitación.
        t("request.full_name", lang),      # Etiqueta i18n con aclaración.
        key="req_full_name",               # Clave de estado.
        help=t("request.full_name", lang), # Repite la aclaración como ayuda (opcional).
    )
    phone_last4 = st.text_input(           # Campo: últimos 4 del teléfono.
        t("request.phone_last4", lang),    # Etiqueta i18n.
        key="req_phone_last4",             # Clave de estado.
        placeholder=t("request.phone_last4_placeholder", lang),  # Placeholder i18n.
        max_chars=4,                       # Limita a 4 caracteres.
    )
    email = st.text_input(                 # Campo: email donde recibirá el enlace.
        t("request.email", lang),          # Etiqueta i18n.
        key="req_email",                   # Clave de estado.
    )
    consent = st.checkbox(                 # Casilla: consentimiento de comunicaciones.
        t("request.consent", lang),        # Texto i18n.
        key="req_consent",                 # Clave de estado.
        value=True,                        # Por defecto marcado (puedes poner False si prefieres).
    )
    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)  # Espaciador visual pequeño.
    submit = st.form_submit_button(        # Botón de envío del formulario.
        t("request.submit", lang),         # Etiqueta i18n (enviar enlace de acceso).
        use_container_width=True,          # Botón ancho completo.
    )

# --- Validación ligera en el cliente (antes de conectar al backend) ---
if submit:                                 # Si el usuario pulsó "Enviar enlace de acceso"…
    # 1) Validar nombre (mínimo 3 caracteres útiles).
    name_ok = len((full_name or "").strip()) >= 3                      # Comprueba longitud mínima del nombre.
    # 2) Validar últimos 4 (exactamente 4 dígitos 0-9).
    phone_ok = bool(re.fullmatch(r"\d{4}", (phone_last4 or "").strip()))  # Regex: cuatro dígitos exactos.
    # 3) Validar email (chequeo rápido: contiene "@" y algo después).
    email_ok = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", (email or "").strip()))  # Regex simple de email.
    # 4) Consentimiento debe estar marcado.
    consent_ok = bool(consent)                                           # Debe ser True.

    # --- Mostrar errores específicos si aplican ---
    if not name_ok:                                                      # Si el nombre no pasa validación…
        st.error(t("request.full_name", lang))                           # Muestra la etiqueta como recordatorio (puedes crear request.invalid_name si quieres).
    if not phone_ok:                                                     # Si los últimos 4 no son válidos…
        st.error(t("request.invalid_phone4", lang))                      # Mensaje i18n específico.
    if not email_ok:                                                     # Si el email no parece válido…
        st.error(t("request.invalid_email", lang))                       # Mensaje i18n específico.
    if not consent_ok:                                                   # Si no aceptó consentimiento…
        st.error(t("form.contact_required_one", lang))                   # Reutiliza un texto existente o crea uno específico (p.ej., request.consent_required).

    # --- Si todo es válido, simular o llamar a backend ---
    if name_ok and phone_ok and email_ok and consent_ok:                 # Solo si todas las validaciones pasan…
        if DEMO_MODE:                                                    # Si estamos en modo DEMO (mock UX)…
            st.success(t("request.success", lang))                       # Muestra mensaje de éxito i18n (revisa tu correo).
            # Aquí podrías simular además un "reenviar" con un botón secundario si quieres validar UX.
        else:                                                            # Si conectas a backend real…
            # Ejemplo de payload esperado por POST /api/request-access (a implementar en tu API).
            payload = {
                "full_name": (full_name or "").strip(),                 # Nombre limpio.
                "phone_last4": (phone_last4 or "").strip(),             # Últimos 4.
                "email": (email or "").strip().lower(),                 # Email normalizado.
                "lang": lang,                                           # Idioma seleccionado (para registro preferencia).
            }
            # Aquí harías la llamada real:
            # import requests
            # try:
            #     r = requests.post(f"{API_BASE_URL}/api/request-access", json=payload, timeout=12)
            #     if r.status_code == 200:
            #         st.success(t("request.success", lang))
            #     else:
            #         st.error(t("request.error", lang) + f" (HTTP {r.status_code})")
            # except requests.exceptions.RequestException:
            #     st.error(t("request.error", lang))
            st.info("🔧 Modo DEMO desactivado pendiente de backend. Aquí se llamaría a POST /api/request-access.")  # Mensaje informativo.

# --- Enlace útil para volver al Login tradicional (opcional) ---
st.markdown(                             # Muestra un enlace centrado para navegar a Login.
    f"""
    <div class="center muted">
      <p>•</p>
    </div>
    """,
    unsafe_allow_html=True,              # HTML permitido.
)
st.page_link(                            # Enlace nativo de Streamlit para cambiar de página.
    "pages/0_Login.py",                  # Ruta a la página de Login.
    label=t("nav.login", lang),          # Etiqueta i18n.
    icon="↩️",                           # Icono de retorno.
)

# --- Cierre del contenedor de la tarjeta ---
st.markdown('</div>', unsafe_allow_html=True)  # Cierra el div .card.
