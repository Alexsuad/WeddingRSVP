# pages/01_Recuperar_Codigo.py                                                             # Ruta de la página en Streamlit

# =======================================================================================
# 🔁 Recuperar código de invitado — UI limpia, centrada y consistente (ES/EN/RO)
# ---------------------------------------------------------------------------------------
# - Título centrado (h3) para igualar jerarquía con el resto.
# - Un (1) único CTA: "Solicitar recuperación".
# - Link inferior "Volver al inicio" (sin botón extra de RSVP).
# - Menú lateral coherente (Inicio / Solicitar Acceso / Iniciar sesión), ocultando "Recuperar".
# - Sin dependencias de utils/nav.py (usamos utils/ui.py).
# =======================================================================================

import os                                              # Accede a variables de entorno
import requests                                        # Realiza la llamada POST a la API
import streamlit as st                                 # UI de Streamlit
from utils.lang_selector import render_lang_selector   # Selector de idioma (ES/EN/RO)
from utils.translations import t                       # Función de traducción i18n
from utils.ui import apply_global_styles, render_side_nav  # Estilos globales + menú lateral

# ---------------------------------------------
# 1) Configuración de página (PRIMERO SIEMPRE)
# ---------------------------------------------
st.set_page_config(                                   # Define metadatos de la página
    page_title="Recuperar código",                    # Título de la pestaña del navegador
    page_icon="🔁",                                   # Icono de la pestaña
    layout="centered",                                # Layout centrado
    initial_sidebar_state="collapsed",                # Colapsa sidebar nativa
)

# ---------------------------------------------
# 2) Estilos globales compartidos (UI base)
# ---------------------------------------------
apply_global_styles()                                 # Inyecta tipografías, fondo y limpieza del <form>

# ---------------------------------------------
# 3) Constantes / Endpoints
# ---------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")  # Base de la API (env o local)
RECOVER_ENDPOINT = f"{API_BASE_URL.rstrip('/')}/api/recover-code"  # Endpoint de recuperación

# ---------------------------------------------
# 4) Idioma y menú lateral coherente
# ---------------------------------------------
lang = render_lang_selector()                         # Dibuja selector de idioma y retorna el idioma activo
render_side_nav(                                      # Dibuja el menú flotante coherente
    t,                                                # Función de traducción
    lang,                                             # Idioma activo
    position="left",                                  # Menú a la IZQUIERDA para coherencia con tus capturas
    side_offset_px=300,                                # Separación del borde para que no quede "pegado"
    hide=["recover"],                                 # Oculta "Recuperar Código" (estamos en esta página)
    show_emojis=True                                  # Muestra emojis en los botones del menú
)

# ---------------------------------------------
# 5) Cabecera centrada (título + subtítulo)
# ---------------------------------------------
st.markdown(                                          # Título h3 centrado con Playfair (coherente al resto)
    f"""
    <div style="text-align:center; margin-top: 16px; margin-bottom: 8px;">
      <h3 style="font-family:'Playfair Display',serif; font-weight:700; margin:0;">
        {t("recover.title", lang)}
      </h3>
    </div>
    """,
    unsafe_allow_html=True,                           # Permitimos HTML para estilizar
)
st.write(t("recover.subtitle", lang))                 # Subtítulo explicativo corto
st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)  # Pequeño respiro vertical

# ---------------------------------------------
# 6) Formulario (1 solo CTA)
# ---------------------------------------------
with st.form("recover_form"):                         # Abre el <form> controlado por Streamlit
    # Placeholders localizados (solo aquí para UX; si prefieres, los llevamos a translations)
    email_ph = "tu-correo@ejemplo.com" if lang == "es" else ("name@example.com" if lang == "en" else "email@exemplu.com")  # Placeholder por idioma
    phone_ph = "+34 600 123 123" if lang == "es" else ("+44 7700 900123" if lang == "en" else "+40 712 345 678")           # Placeholder por idioma

    email = st.text_input(                            # Campo de email opcional
        t("recover.email", lang),                     # Etiqueta traducida
        value="",                                     # Valor por defecto vacío
        placeholder=email_ph,                         # Placeholder localizado
    )
    phone = st.text_input(                            # Campo de teléfono opcional
        t("recover.phone", lang),                     # Etiqueta traducida
        value="",                                     # Valor por defecto vacío
        placeholder=phone_ph,                         # Placeholder localizado
    )

    submit = st.form_submit_button(                   # ÚNICO CTA del formulario
        t("recover.submit", lang),                    # Texto del botón traducido
        type="primary",                               # Botón primario (negro por estilos globales)
        use_container_width=True,                     # Ocupa el ancho del contenedor
    )

# ---------------------------------------------
# 7) Lógica del envío (sin botón cancelar)
# ---------------------------------------------
if submit:                                            # Solo actúa si el usuario pulsó "Solicitar recuperación"
    email_norm = (email or "").strip().lower()        # Normaliza email
    phone_norm = (phone or "").strip()                # Normaliza teléfono (de momento solo recortamos)

    if not email_norm and not phone_norm:             # Si no envía nada, advertimos
        st.warning(t("recover.invalid", lang))        # Mensaje de validación
    else:
        payload = {"email": email_norm or None, "phone": phone_norm or None}  # Cuerpo de la petición
        with st.spinner("…"):                         # Muestra spinner breve durante la llamada
            try:
                resp = requests.post(RECOVER_ENDPOINT, json=payload, timeout=10)  # Llama a la API
                if resp.status_code == 200:           # Éxito
                    st.success(t("recover.success", lang))  # Mensaje positivo
                elif resp.status_code == 429:         # Rate limit
                    retry_after = resp.headers.get("Retry-After", None)          # Lee cabecera Retry-After
                    human_retry = (f"{retry_after} s" if (retry_after and str(retry_after).isdigit())
                                    else {"es": "unos segundos", "en": "a few seconds", "ro": "câteva secunde"}.get(lang, "a few seconds"))  # Texto amable
                    st.warning(t("recover.rate_limited", lang).format(retry=human_retry))  # Mensaje con tiempo
                elif resp.status_code == 400:         # Petición inválida
                    st.error(t("recover.invalid", lang))                              # Error de validación
                else:                                 # Cualquier otro caso
                    st.error(t("recover.generic", lang))                              # Error genérico
            except requests.RequestException as e:    # Errores de red/timeout/etc.
                st.error(t("recover.network", lang).format(err=e))                   # Mensaje de red

# ---------------------------------------------
# 8) Enlace inferior: Volver al inicio (solo 1)
# ---------------------------------------------
st.markdown(                                          # Pintamos un enlace ligero, centrado
    f"""
    <div style="text-align:center; margin-top: 12px;">
      <a href="/Login" target="_self" style="color: var(--muted); text-decoration:none; font-weight:500;">
        ⬅️ {t("recover.back", lang)}
      </a>
    </div>
    """,
    unsafe_allow_html=True,                           # Permitimos HTML
)
