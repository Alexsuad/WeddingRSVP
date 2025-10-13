# pages/00_Solicitar_Acceso.py                                                               # Ruta y nombre del archivo de la página.
# =========================================================================================   # Separador visual superior.
# 🔑 Solicitar Acceso (Magic Link) — Mockup UX Multilenguaje                                  # Título descriptivo de la página.
# =========================================================================================   # Separador visual superior.

import os                                                                                    # Importa os para leer variables de entorno.
import re                                                                                    # Importa re para validaciones con expresiones regulares.
import streamlit as st                                                                       # Importa Streamlit para construir la UI.
from dotenv import load_dotenv                                                               # Importa load_dotenv para cargar .env en local.
from utils.translations import t                                                             # Importa la función de traducción t().
from utils.lang_selector import render_lang_selector                                         # Importa el selector de idioma.
# UI (solo presentación, sin lógica)
from utils.ui import apply_global_styles, render_side_nav                                    # Importa estilos globales y menú lateral.

# -----------------------------------------------------------------------------------------
# ⚙️ Configuración básica de la página
# -----------------------------------------------------------------------------------------
st.set_page_config(                                                                          # Configura parámetros de la página Streamlit.
    page_title="Solicitar Acceso • Boda D&C",                                                # Título de la pestaña del navegador.
    page_icon="💌",                                                                          # Icono de la pestaña.
    layout="centered",                                                                       # Layout centrado.
    initial_sidebar_state="collapsed",                                                       # Barra lateral colapsada por defecto.
)                                                                                            # Fin de la configuración de página.

# -----------------------------------------------------------------------------------------
# 🌱 Entorno y estilos globales
# -----------------------------------------------------------------------------------------
load_dotenv()                                                                                # Carga variables de entorno desde .env (entorno local).
# Estilos globales: tipografías, fondo, botones y fix <form>
apply_global_styles()

# -----------------------------------------------------------------------------------------
# 🌱 Entorno y constantes
# -----------------------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")                            # URL base de la API (fallback local).
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"                                               # Modo demo (no llama API real si está activado).
APP_DEBUG = os.getenv("APP_DEBUG", "0") == "1"                                               # Flag de depuración de UI (muestra pistas si está activado).

# -----------------------------------------------------------------------------------------
# 🈶 Selector de idioma y menú lateral
# -----------------------------------------------------------------------------------------
# hide_native_sidebar_nav()                                                                  # (Opcional) Oculta navegación nativa de Streamlit.
lang = render_lang_selector()                                                                # Renderiza el selector de idioma y devuelve el idioma activo.

# Botonera flotante (Home / Solicitar / Login) a la derecha
render_side_nav(                      # Dibuja la botonera lateral en esta página
    t,                                # Función de traducción para textos del menú
    lang,                             # Idioma activo (devuelto por tu selector de idioma)
    position="left",                 # Ubica el menú a la derecha
    side_offset_px=300,                # Acerca el menú al contenido (en vez de 300)
    hide=["request"],                 # Oculta la opción de la página actual ("Solicitar Acceso")
    show_emojis=True                  # Muestra los iconos (si pones False, se ocultan)
)                                     # Fin de la llamada

# -----------------------------------------------------------------------------------------
# 🎨 Estilos (CSS incrustado)
# -----------------------------------------------------------------------------------------
st.markdown(  # Inyecta CSS mínimo para el hero y la tarjeta sin duplicar reglas globales.
    """
    <style>
      .hero{ text-align:center; padding: 2rem 0 4rem 0; }                                /* Caja superior de título */
      .hero h1{ margin:0 0 10px 0; font-size: 2.8rem; }                                   /* Tamaño del título principal */
      .hero p{ margin:0; color: var(--muted); font-size: 1.1rem; }                        /* Subtítulo */
      .hero-icon{ font-size: 3rem; }                                                       /* Emoji grande arriba */

      .card{ background: var(--bg); border-radius: var(--radius);                         /* Caja tarjeta central */
             box-shadow: var(--shadow); padding: 2.5rem; max-width: 500px;                /* Sombra suave, ancho y padding */
             margin: -50px auto 0; }                                                      /* Centrada y ligeramente solapada al hero */

      .login-link{ text-align:center; margin-top:1.5rem; padding-top:1.5rem;              /* Pie con enlace a Login */
                   border-top:1px solid #EEE; }
      .login-link a{ color:var(--muted); text-decoration:none; font-weight:500;           /* Estilo del enlace */
                     transition: color .2s; }
      .login-link a:hover{ color:var(--primary); text-decoration: underline; }            /* Hover del enlace */
    </style>
    """,
    unsafe_allow_html=True,  # Permite CSS inline.
)

st.markdown(                                                                             # Inyecta un bloque de JavaScript
    """
    <script>
        (function () {
        try {
            const root = document.querySelector('#request');                                  // Toma el contenedor del formulario
            if (!root) return;                                                                // Si no existe, termina

            // Lista de etiquetas válidas (ES / EN / RO). Ajusta si cambias los textos
            const WHITELIST = new Set([
            "Tu nombre completo","Últimos 4 dígitos de tu teléfono","Correo electrónico",  // Español
            "Full name","Last 4 digits of your phone","Email",                              // English
            "Numele complet","Ultimele 4 cifre ale telefonului","E-mail","Email"           // Română
            ]);

            // Oculta cualquier stTextInput que no tenga label reconocido
            const hideGhosts = () => {
            const nodes = root.querySelectorAll('div[data-testid="stTextInputRoot"]');     // Todos los inputs de texto dentro del form
            nodes.forEach(el => {
                const label = el.querySelector('label');                                      // Busca etiqueta del input
                const labelText = (label && label.textContent || "").trim();                 // Toma texto de la etiqueta
                if (!WHITELIST.has(labelText)) {                                             // Si no está en la lista blanca…
                el.style.display = "none";                                                 // …lo ocultamos (era el “fantasma”)
                }
            });
            };

            hideGhosts();                                                                     // Ejecuta al cargar
            new MutationObserver(hideGhosts).observe(root, { childList: true, subtree: true }); // Re-ejecuta si Streamlit re-renderiza

        } catch (e) { /* silencioso */ }
        })();
    </script>
    """,                                                                                 # Cierra el string del script
    unsafe_allow_html=True,                                                              # Permite JS embebido
)                                                                                        # Cierra st.markdown del script

# -----------------------------------------------------------------------------------------
# 🖼️ Hero (cabecera visual)
# -----------------------------------------------------------------------------------------
st.markdown(                                                                                 # Dibuja el bloque hero con icono y textos traducidos.
    f"""
    <div class="hero">
      <h1>{t("request.title", lang)}</h1>
      <p>{t("request.intro", lang)}</p>
    </div>
    """,
    unsafe_allow_html=True,                                                                  # Permite HTML para maquetación hero.
)                                                                                            # Fin del hero.

# -----------------------------------------------------------------------------------------
# 🪪 Tarjeta contenedora (apertura)
# -----------------------------------------------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)                                    # Abre el contenedor tipo tarjeta.

# -----------------------------------------------------------------------------------------
# 📝 Formulario de solicitud (encapsulado para eliminar caja fantasma)
# -----------------------------------------------------------------------------------------
st.markdown('<div id="request">', unsafe_allow_html=True)                                   # Abre un contenedor con id para aplicar CSS específico.

with st.form("request_access_form"):                                                        # Abre el formulario como antes.
    full_name = st.text_input(t("request.full_name", lang), key="full_name_input",          # Campo Nombre completo (sin cambios).
                              help=t("request.full_name", lang))
    phone_last4 = st.text_input(
        t("request.phone_last4", lang),
        key="last4_input",
        placeholder=t("request.phone_last4_placeholder", lang),
        max_chars=4,
    )
    email = st.text_input(t("request.email", lang), key="email_input", placeholder="nombre@ejemplo.com")
    consent = st.checkbox(t("request.consent", lang), key="req_consent", value=True)

    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

    submit = st.form_submit_button(
        t("request.submit", lang),
        use_container_width=True,
        type="primary"
    )

st.markdown('</div>', unsafe_allow_html=True)                                               # Cierra el contenedor #request.

# -----------------------------------------------------------------------------------------
# 🚦 Acciones al pulsar Enviar
# -----------------------------------------------------------------------------------------
if submit:                                                                                   # Solo ejecuta validaciones y envío si el usuario pulsó Enviar.
    # -------------------------------------------------------------------------------------
    # ✅ Validaciones locales de campos
    # -------------------------------------------------------------------------------------
    name_ok = len((full_name or "").strip()) >= 3                                           # Valida que el nombre tenga al menos 3 caracteres (tras trim).
    phone_ok = bool(re.fullmatch(r"\d{4}", (phone_last4 or "").strip()))                    # Valida que sean exactamente 4 dígitos.
    email_ok = bool(re.fullmatch(r"[^@\s]+@[^@\s\.]+\.[a-zA-Z]{2,}", (email or "").strip()))# Valida formato simple de email.
    consent_ok = bool(consent)                                                               # Verifica que el consentimiento esté marcado.

    def _msg_neutro() -> str:                                                                # Define un helper para el mensaje neutro (opcional en DEMO).
        txt = t("request.success_message_neutral", lang)                                     # Intenta obtener traducción del mensaje neutro.
        return txt if isinstance(txt, str) and txt.strip() else (                            # Si hay traducción no vacía, úsala; si no, usa fallback.
            "Si los datos coinciden con tu invitación, recibirás un enlace en tu correo. "   # Fallback parte 1.
            "Revisa tu bandeja de entrada y también Spam/Promociones."                      # Fallback parte 2.
        )                                                                                    # Cierra el retorno del mensaje neutro.

    has_errors = False                                                                       # Bandera de errores de validación locales.
    try:                                                                                     # Intenta mostrar errores con traducciones.
        if not name_ok:   st.error(t("request.invalid_name", lang));   has_errors = True    # Error de nombre inválido.
        if not phone_ok:  st.error(t("request.invalid_phone4", lang)); has_errors = True    # Error de dígitos inválidos.
        if not email_ok:  st.error(t("request.invalid_email", lang));  has_errors = True    # Error de email inválido.
        if not consent_ok: st.error(t("request.consent_required", lang)); has_errors = True # Error por no aceptar consentimiento.
    except Exception:                                                                          # Si fallan traducciones, usa fallback en español.
        if not name_ok:   st.error("⚠️ Nombre inválido"); has_errors = True                 # Fallback de nombre inválido.
        if not phone_ok:  st.error("⚠️ Los últimos 4 dígitos deben ser numéricos (0000–9999)."); has_errors = True  # Fallback de teléfono.
        if not email_ok:  st.error("⚠️ Ingresa un correo válido (ej. nombre@dominio.com)."); has_errors = True     # Fallback de email.
        if not consent_ok: st.error("⚠️ Debes aceptar el consentimiento para continuar."); has_errors = True       # Fallback de consentimiento.

    # -------------------------------------------------------------------------------------
    # 🧳 Construcción de payload (solo si no hay errores) + lógica DEMO
    # -------------------------------------------------------------------------------------
    if not has_errors:                                                                       # Si no hubo errores de validación local…
        payload = {                                                                          # Construye el JSON que consumirá la API.
            "full_name": (full_name or "").strip(),                                          # Normaliza nombre.
            "phone_last4": (phone_last4 or "").strip(),                                      # Normaliza últimos 4 dígitos.
            "email": (email or "").strip().lower(),                                          # Normaliza email a minúsculas.
            "preferred_language": lang,                                                      # Incluye idioma preferido.
            "consent": bool(consent),                                                        # Incluye consentimiento.
        }                                                                                    # Cierra el payload.

        if DEMO_MODE:                                                                        # Si está activo el modo demo…
            st.info(_msg_neutro())                                                           # Muestra mensaje neutro (no llama API real).
        else:                                                                                # Si no es demo, llama a la API real…
            # -----------------------------------------------------------------------------------------
            # 🌐 Llamada a API y política de mensajes (1 solo aviso según resultado)
            # -----------------------------------------------------------------------------------------
            try:                                                                             # Intenta realizar la solicitud HTTP a la API.
                import requests                                                              # Importa requests localmente.
                r = requests.post(f"{API_BASE_URL}/api/request-access",                      # Realiza POST a /api/request-access.
                                   json=payload, timeout=12)                                 # Envía payload y aplica timeout razonable.

                # -----------------------------------------------------------------------------------------
                # 🧠 Política de mensajes: mostrar 1 solo aviso según resultado (sin JSON crudo)
                # -----------------------------------------------------------------------------------------
                if r.status_code == 200:                                                     # Si la API valida y procesa correctamente…
                    ok_msg = t("request.success_message_ok", lang) or (                      # Toma mensaje de éxito traducido o fallback.
                        "✅ Datos verificados. Te enviamos un enlace a tu correo. Revisa Bandeja/Spam/Promociones."
                    )                                                                        # Cierra el fallback de éxito.
                    st.success(ok_msg)                                                       # Muestra mensaje de éxito.

                elif r.status_code in (404, 422):                                            # Si los datos no coinciden o hay validación inválida…
                    fail_msg = t("request.not_found_message", lang) or (                     # Mensaje traducido o fallback genérico (sin revelar campo).
                        "❌ No pudimos verificar tus datos con la invitación. Revísalos e inténtalo de nuevo."
                    )                                                                        # Cierra el fallback de error por no coincidencia.
                    st.error(fail_msg)                                                       # Muestra mensaje de error.
                else:                                                                        # Cualquier otro estado (p. ej., 5xx, 401 no esperado)…
                    sys_msg = t("request.system_error_message", lang) or (                   # Mensaje de error del sistema traducido o fallback.
                        "⚠️ Ocurrió un problema al procesar tu solicitud. Inténtalo de nuevo en unos minutos."
                    )                                                                        # Cierra el fallback de error del sistema.
                    st.error(sys_msg)                                                        # Muestra mensaje genérico de sistema.

                # -----------------------------------------------------------------------------------------
                # 🛠️ DEBUG opcional: solo el código HTTP (sin JSON crudo) si APP_DEBUG=1
                # -----------------------------------------------------------------------------------------
                if APP_DEBUG:                                                                # Si activaste APP_DEBUG en el entorno…
                    st.caption(f"DEBUG • API {r.status_code}")                               # Muestra el status code como pista (sin exponer JSON).

            except Exception:                                                                # Cualquier excepción de red/timeout/etc…
                sys_msg = t("request.system_error_message", lang) or (                       # Mensaje de error del sistema traducido o fallback.
                    "⚠️ Ocurrió un problema al procesar tu solicitud. Inténtalo de nuevo en unos minutos."
                )                                                                            # Cierra el fallback de error del sistema.
                st.error(sys_msg)                                                            # Muestra mensaje de error genérico.

# -----------------------------------------------------------------------------------------
# 🔗 Enlace de ayuda para volver a Login
# -----------------------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="login-link">
      <a href="/Login" target="_self">
        <span>↩️</span>&nbsp;
        {t("nav.login_prompt", lang)} 
      </a>
    </div>
    """,
    # Asumiendo que t("nav.login_prompt", lang) devuelve algo como: 
    # "¿Ya tienes un código? Inicia sesión"
    unsafe_allow_html=True,
)                                                                                            # Fin del bloque de enlace.

# -----------------------------------------------------------------------------------------
# 🪪 Tarjeta contenedora (cierre)
# -----------------------------------------------------------------------------------------
st.markdown('</div>', unsafe_allow_html=True)                                               # Cierra el contenedor tipo tarjeta.
