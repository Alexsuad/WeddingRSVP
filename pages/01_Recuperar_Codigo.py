# pages/01_Recuperar_Codigo.py  # Ruta y nombre del archivo (página interna de recuperación).

# =====================================================================================
# 🔁 Recuperar código de invitado — Multilenguaje (ES/EN/RO)
# -------------------------------------------------------------------------------------
# UI que permite solicitar recuperación del código de invitado contra /api/recover-code
# usando i18n con utils/lang_selector.py (selector de idioma) y utils/translations.py
# (t()). Incluye fallbacks locales si faltan claves recover.* en el archivo de
# traducciones, para evitar mostrar las claves crudas en pantalla.
# ➕ Añadido: botón "Cancelar" dentro del formulario que vuelve al Login, sin romper UX.
# =====================================================================================

import os
from pathlib import Path
import requests
import streamlit as st
from utils.lang_selector import render_lang_selector
from utils.translations import t
from utils.nav import hide_native_sidebar_nav, render_nav

# -------------------------------------------------------------------------------------
# Fallbacks locales por idioma si faltan claves recover.* en translations.py.
LOCAL_STRINGS = {
    "es": {
        "title": "Recuperar tu código",
        "subtitle": "Ingresa tu email o teléfono usado en la invitación. Si estás en la lista, te enviaremos un mensaje.",
        "email": "Email (opcional)",
        "phone": "Teléfono (opcional)",
        "submit": "Solicitar recuperación",
        "success": "Si tu contacto está en la lista de invitados, recibirás un mensaje en breve.",
        "rate_limited": "Has realizado demasiados intentos. Inténtalo nuevamente en ~{retry}.",
        "invalid": "Solicitud inválida. Verifica los datos e inténtalo de nuevo.",
        "generic": "No pudimos procesar la solicitud en este momento. Inténtalo más tarde.",
        "network": "No hay conexión con el servidor. Detalle: {err}",
        "back": "⬅️ Volver al inicio",
        "go_rsvp": "Ir al formulario RSVP",
    },
    "en": {
        "title": "Recover your code",
        "subtitle": "Enter the email or phone used in your invitation. If you are on the list, we will send you a message.",
        "email": "Email (optional)",
        "phone": "Phone (optional)",
        "submit": "Request recovery",
        "success": "If your contact is on our guest list, you will receive a message shortly.",
        "rate_limited": "Too many attempts. Try again in ~{retry}.",
        "invalid": "Invalid request. Please check the data and try again.",
        "generic": "We could not process your request right now. Please try again later.",
        "network": "Cannot reach the server. Details: {err}",
        "back": "⬅️ Back to home",
        "go_rsvp": "Go to RSVP form",
    },
    "ro": {
        "title": "Recuperează-ți codul",
        "subtitle": "Introdu emailul sau telefonul folosit în invitație. Dacă ești în listă, vei primi un mesaj.",
        "email": "Email (opțional)",
        "phone": "Telefon (opțional)",
        "submit": "Solicită recuperarea",
        "success": "Dacă datele tale se află în lista de invitați, vei primi în curând un mesaj.",
        "rate_limited": "Prea multe încercări. Încearcă din nou peste ~{retry}.",
        "invalid": "Cerere invalidă. Verifică datele și încearcă din nou.",
        "generic": "Nu am putut procesa cererea acum. Încearcă mai târziu.",
        "network": "Nu se poate contacta serverul. Detalii: {err}",
        "back": "⬅️ Înapoi la început",
        "go_rsvp": "Mergi la formularul RSVP",
    },
}

def tr(key: str, lang_code: str) -> str:
    full_key = f"recover.{key}"
    try:
        value = t(full_key, lang_code)
        if value and value != full_key:
            return value
    except Exception:
        pass
    return LOCAL_STRINGS.get(lang_code, LOCAL_STRINGS["en"]).get(key, full_key)

# -------------------------------------------------------------------------------------
# Configuración de página y entorno.
st.set_page_config(
    page_title="Recuperar código",
    page_icon="🔁",
    layout="centered",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
RECOVER_ENDPOINT = f"{API_BASE_URL.rstrip('/')}/api/recover-code"
RSVP_URL = os.getenv("RSVP_URL", "").strip()

# -------------------------------------------------------------------------------------
# Menú lateral e idioma.
hide_native_sidebar_nav()
lang = render_lang_selector()
render_nav({
    "pages/0_Login.py": t("nav.login", lang),
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),
    "pages/2_Confirmado.py": t("nav.confirmed", lang),
})

# -------------------------------------------------------------------------------------
# Inyección opcional de tokens CSS para look&feel coherente.
tokens_path = Path("tokens.css")
if tokens_path.exists():
    st.markdown(
        f"<style>{tokens_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------------------------------
# Encabezado i18n.
st.title(f"🔁 {tr('title', lang)}")
st.write(tr("subtitle", lang))

# -------------------------------------------------------------------------------------
# Formulario de solicitud (email o teléfono) con botón Cancelar.
with st.form("recover_form"):
    email = st.text_input(
        tr("email", lang),
        value="",
        placeholder="tu-correo@ejemplo.com" if lang == "es" else ("email@example.com" if lang == "en" else "email@exemplu.com"),
    )
    phone = st.text_input(
        tr("phone", lang),
        value="",
        placeholder="+34 600 123 123" if lang == "es" else ("+44 7700 900123" if lang == "en" else "+40 712 345 678"),
    )

    # Botones lado a lado: Enviar / Cancelar (el Cancelar no dispara validaciones)
    col_ok, col_cancel = st.columns(2)
    submit = col_ok.form_submit_button(tr("submit", lang), type="primary", use_container_width=True)
    cancel = col_cancel.form_submit_button(t("form.cancel", lang), use_container_width=True)

# -------------------------------------------------------------------------------------
# Lógica de botones (prioridad: cancelar -> no ejecutar validaciones).
if cancel:
    # Volver a Login de inmediato, sin tocar backend ni hacer validaciones
    st.switch_page("pages/0_Login.py")

elif submit:
    email_norm = email.strip().lower()
    phone_norm = phone.strip()

    if not email_norm and not phone_norm:
        st.warning(tr("invalid", lang))
    else:
        payload = {"email": email_norm or None, "phone": phone_norm or None}
        with st.spinner("…"):
            try:
                resp = requests.post(RECOVER_ENDPOINT, json=payload, timeout=10)
                if resp.status_code == 200:
                    st.success(tr("success", lang))
                elif resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", None)
                    human_retry = (
                        f"{retry_after} s" if (retry_after and retry_after.isdigit()) else
                        {"es": "unos segundos", "en": "a few seconds", "ro": "câteva secunde"}.get(lang, "a few seconds")
                    )
                    st.warning(tr("rate_limited", lang).format(retry=human_retry))
                elif resp.status_code == 400:
                    st.error(tr("invalid", lang))
                else:
                    st.error(tr("generic", lang))
            except requests.RequestException as e:
                st.error(tr("network", lang).format(err=e))

# -------------------------------------------------------------------------------------
# Acciones auxiliares (se mantienen como estaban).
st.divider()
col1, col2 = st.columns(2)

with col1:
    try:
        st.button(
            tr("back", lang),
            on_click=lambda: st.switch_page("pages/0_Login.py"),
            use_container_width=True,
        )
    except Exception:
        st.write("↩️")
        st.write(t("nav.login", lang))

with col2:
    if RSVP_URL:
        st.link_button(
            tr("go_rsvp", lang),
            RSVP_URL,
            use_container_width=True,
        )
    else:
        st.write(" ")
