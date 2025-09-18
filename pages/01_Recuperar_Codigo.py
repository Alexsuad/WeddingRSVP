# pages/01_Recuperar_Codigo.py  # Ruta y nombre del archivo (página interna de recuperación).

# =====================================================================================  # Separador visual.
# 🔁 Recuperar código de invitado — Multilenguaje (ES/EN/RO)                              # Título descriptivo.
# -------------------------------------------------------------------------------------  # Separador.
# UI que permite solicitar recuperación del código de invitado contra /api/recover-code  # Descripción general.
# usando i18n con utils/lang_selector.py (selector de idioma) y utils/translations.py    # Utilidades i18n del proyecto.
# (t()). Incluye fallbacks locales si faltan claves recover.* en el archivo de           # Seguridad ante claves faltantes.
# traducciones, para evitar mostrar las claves crudas en pantalla.                       # UX robusta.
# =====================================================================================  # Cierre de cabecera.

import os                                        # Importa os para leer variables de entorno (.env).
from pathlib import Path                         # Importa Path para comprobar/inyectar CSS de tokens.
import requests                                  # Importa requests para realizar el POST al backend.
import streamlit as st                           # Importa Streamlit para construir la UI.
from utils.lang_selector import render_lang_selector  # Importa el selector de idioma (con banderas).
from utils.translations import t                 # Importa la función central de traducciones (i18n).
from utils.nav import hide_native_sidebar_nav, render_nav  # Importa helpers para el menú lateral.

# -------------------------------------------------------------------------------------  # Fallbacks locales por idioma si faltan claves recover.* en translations.py.
LOCAL_STRINGS = {                                 # Diccionario de textos por idioma para cubrir claves ausentes.
    "es": {                                       # Bloque de textos en español.
        "title": "Recuperar tu código",           # Título de la página.
        "subtitle": "Ingresa tu email o teléfono usado en la invitación. Si estás en la lista, te enviaremos un mensaje.",  # Subtítulo explicativo.
        "email": "Email (opcional)",              # Etiqueta del input de email.
        "phone": "Teléfono (opcional)",           # Etiqueta del input de teléfono.
        "submit": "Solicitar recuperación",       # Texto del botón de envío.
        "success": "Si tu contacto está en la lista de invitados, recibirás un mensaje en breve.",  # Mensaje neutro de éxito (200).
        "rate_limited": "Has realizado demasiados intentos. Inténtalo nuevamente en ~{retry}.",     # Mensaje para 429 con Retry-After.
        "invalid": "Solicitud inválida. Verifica los datos ingresados e inténtalo de nuevo.",       # Mensaje para 400.
        "generic": "No pudimos procesar la solicitud en este momento. Inténtalo más tarde.",        # Mensaje para otros códigos de error.
        "network": "No hay conexión con el servidor. Detalle: {err}",                               # Mensaje para errores de red.
        "back": "⬅️ Volver al inicio",             # Texto del botón para volver a Login.
        "go_rsvp": "Ir al formulario RSVP",       # Texto del botón para ir al formulario público.
    },
    "en": {                                       # Bloque de textos en inglés.
        "title": "Recover your code",             # Título de la página.
        "subtitle": "Enter the email or phone used in your invitation. If you are on the list, we will send you a message.",  # Subtítulo.
        "email": "Email (optional)",              # Etiqueta email.
        "phone": "Phone (optional)",              # Etiqueta phone.
        "submit": "Request recovery",             # Texto del botón enviar.
        "success": "If your contact is on our guest list, you will receive a message shortly.",      # Mensaje neutro 200.
        "rate_limited": "Too many attempts. Try again in ~{retry}.",                                 # Mensaje 429.
        "invalid": "Invalid request. Please check the data and try again.",                          # Mensaje 400.
        "generic": "We could not process your request right now. Please try again later.",           # Mensaje otros errores.
        "network": "Cannot reach the server. Details: {err}",                                        # Mensaje error de red.
        "back": "⬅️ Back to home",               # Botón volver.
        "go_rsvp": "Go to RSVP form",            # Botón a formulario público.
    },
    "ro": {                                       # Bloque de textos en rumano.
        "title": "Recuperează-ți codul",          # Título de la página.
        "subtitle": "Introdu emailul sau telefonul folosit în invitație. Dacă ești în listă, vei primi un mesaj.",  # Subtítulo.
        "email": "Email (opțional)",              # Etiqueta email.
        "phone": "Telefon (opțional)",            # Etiqueta telefon.
        "submit": "Solicită recuperarea",         # Botón enviar.
        "success": "Dacă datele tale se află în lista de invitați, vei primi în curând un mesaj.",   # Mensaje 200.
        "rate_limited": "Prea multe încercări. Încearcă din nou peste ~{retry}.",                    # Mensaje 429.
        "invalid": "Cerere invalidă. Verifică datele și încearcă din nou.",                          # Mensaje 400.
        "generic": "Nu am putut procesa cererea acum. Încearcă mai târziu.",                         # Mensaje otros.
        "network": "Nu se poate contacta serverul. Detalii: {err}",                                  # Error de rețea.
        "back": "⬅️ Înapoi la început",         # Botón volver.
        "go_rsvp": "Mergi la formularul RSVP",  # Botón a formular public.
    },
}

def tr(key: str, lang_code: str) -> str:         # Define helper que intenta usar t('recover.*') y cae a fallback local.
    full_key = f"recover.{key}"                   # Construye la clave completa bajo el namespace recover.*.
    try:                                          # Intenta resolver la traducción con la utilidad global t().
        value = t(full_key, lang_code)            # Llama a t(); si la clave existe, devuelve el string traducido.
        if value and value != full_key:           # Si vino algo distinto a la clave literal…
            return value                          # …usa ese valor (traducción oficial).
    except Exception:                              # Si t() lanzara alguna excepción (improbable)…
        pass                                       # …ignoramos y usamos fallback local.
    return LOCAL_STRINGS.get(lang_code, LOCAL_STRINGS["en"]).get(key, full_key)  # Devuelve fallback o la clave si no hubiese.

# -------------------------------------------------------------------------------------  # Configuración de página y entorno.
st.set_page_config(                              # Configura metadatos de la página de Streamlit.
    page_title="Recuperar código",               # Título de pestaña del navegador (estático para no depender de t() aquí).
    page_icon="🔁",                              # Icono de la pestaña.
    layout="centered",                           # Layout centrado para foco en el formulario.
)                                                # Cierra configuración de página.

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")            # Lee la base URL de la API (fallback local).
RECOVER_ENDPOINT = f"{API_BASE_URL.rstrip('/')}/api/recover-code"            # Construye URL absoluta al endpoint.
RSVP_URL = os.getenv("RSVP_URL", "").strip()                                  # Lee URL pública del formulario RSVP (si existe).

# -------------------------------------------------------------------------------------  # Menú lateral e idioma (como en el login).
hide_native_sidebar_nav()                        # Oculta el navegador multipage nativo para mantener UX propia.
lang = render_lang_selector()                    # Dibuja el selector de idioma y obtiene el código (es/en/ro).
render_nav({                                     # Renderiza el menú lateral propio con etiquetas traducidas globales.
    "pages/0_Login.py": t("nav.login", lang),           # Entrada de Login (traducción existente en translations.py).
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),  # Entrada de Formulario (traducción existente).
    "pages/2_Confirmado.py": t("nav.confirmed", lang),  # Entrada de Confirmado (traducción existente).
})                                               # Cierra render_nav.

# -------------------------------------------------------------------------------------  # Inyección opcional de tokens CSS para look&feel coherente.
tokens_path = Path("tokens.css")                 # Ruta esperada para el archivo de tokens de estilo.
if tokens_path.exists():                         # Comprueba que el archivo exista antes de leerlo.
    st.markdown(                                 # Inyecta su contenido como <style> en la página.
        f"<style>{tokens_path.read_text(encoding='utf-8')}</style>",  # Embebe los estilos del proyecto.
        unsafe_allow_html=True,                  # Permite HTML para que el CSS funcione.
    )                                            # Cierra el bloque de inyección CSS.

# -------------------------------------------------------------------------------------  # Encabezado i18n de la página.
st.title(f"🔁 {tr('title', lang)}")              # Muestra el título traducido con un emoji.
st.write(tr("subtitle", lang))                   # Muestra el subtítulo traducido (instrucciones).

# -------------------------------------------------------------------------------------  # Formulario de solicitud (email o teléfono).
with st.form("recover_form"):                    # Crea un formulario para inputs y submit atómico.
    email = st.text_input(                       # Crea campo de entrada para email.
        tr("email", lang),                       # Etiqueta traducida (con fallback).
        value="",                                # Valor inicial vacío.
        placeholder="tu-correo@ejemplo.com" if lang == "es" else ("email@example.com" if lang == "en" else "email@exemplu.com"),  # Placeholder por idioma.
    )                                            # Fin input email.

    phone = st.text_input(                       # Crea campo de entrada para teléfono.
        tr("phone", lang),                       # Etiqueta traducida (con fallback).
        value="",                                # Valor inicial vacío.
        placeholder="+34 600 123 123" if lang == "es" else ("+44 7700 900123" if lang == "en" else "+40 712 345 678"),  # Placeholder por idioma.
    )                                            # Fin input teléfono.

    submit = st.form_submit_button(              # Crea el botón de envío del formulario.
        tr("submit", lang),                      # Texto del botón traducido (con fallback).
        type="primary",                          # Estilo de botón primario.
        use_container_width=True,                # Usa todo el ancho del contenedor.
    )                                            # Cierra definición del botón.

# -------------------------------------------------------------------------------------  # Lógica de envío al backend con manejo de estados.
if submit:                                       # Si el usuario pulsó el botón de enviar…
    email_norm = email.strip().lower()           # Normaliza el email (quita espacios y pasa a minúsculas).
    phone_norm = phone.strip()                   # Normaliza teléfono (quita espacios extremos).

    if not email_norm and not phone_norm:        # Valida que se haya ingresado al menos un dato de contacto…
        st.warning(tr("invalid", lang))          # Muestra mensaje traducido de solicitud inválida.
    else:                                        # Si la validación mínima es correcta…
        payload = {                              # Construye el payload JSON para el POST.
            "email": email_norm or None,         # Incluye email si no está vacío; si está vacío, manda None.
            "phone": phone_norm or None,         # Incluye phone si no está vacío; si está vacío, manda None.
        }                                        # Cierra el diccionario payload.

        with st.spinner("…"):                    # Muestra spinner mientras se realiza la llamada (neutral en todos los idiomas).
            try:                                 # Protege la llamada HTTP con try/except.
                resp = requests.post(            # Realiza la solicitud POST al backend.
                    RECOVER_ENDPOINT,            # URL del endpoint /api/recover-code.
                    json=payload,                # Envía el cuerpo como JSON.
                    timeout=10,                  # Define un timeout prudente (10s).
                )                                # Cierra la llamada a requests.post.

                if resp.status_code == 200:      # Si el backend responde 200 OK…
                    st.success(tr("success", lang))  # Muestra mensaje de éxito neutro (no revela existencia).
                elif resp.status_code == 429:    # Si responde 429 (rate limit)…
                    retry_after = resp.headers.get("Retry-After", None)  # Lee cabecera Retry-After si existe.
                    human_retry = (              # Calcula un string amigable para el tiempo de espera.
                        f"{retry_after} s" if (retry_after and retry_after.isdigit()) else
                        {"es": "unos segundos", "en": "a few seconds", "ro": "câteva secunde"}.get(lang, "a few seconds")  # Fallback por idioma.
                    )                            # Cierra cálculo de human_retry.
                    st.warning(tr("rate_limited", lang).format(retry=human_retry))  # Muestra aviso traducido con tiempo estimado.
                elif resp.status_code == 400:    # Si responde 400 (payload inválido)…
                    st.error(tr("invalid", lang))  # Muestra mensaje de error traducido.
                else:                            # Para cualquier otro código inesperado…
                    st.error(tr("generic", lang))  # Muestra error genérico traducido.
            except requests.RequestException as e:  # Si ocurrió un error de red/timeout…
                st.error(tr("network", lang).format(err=e))  # Muestra mensaje traducido con detalle de error.

# -------------------------------------------------------------------------------------  # Acciones auxiliares (volver / ir al formulario público).
st.divider()                                     # Inserta un separador visual entre secciones inferiores.
col1, col2 = st.columns(2)                       # Crea dos columnas para ubicar acciones paralelas.

with col1:                                       # Columna izquierda (volver al login).
    try:                                         # Intenta usar navegación programática de Streamlit.
        st.button(                               # Crea un botón que navega al login.
            tr("back", lang),                    # Texto traducido del botón (volver).
            on_click=lambda: st.switch_page("pages/0_Login.py"),  # Acción: cambiar de página a Login.
            use_container_width=True,            # Ocupa todo el ancho de la columna.
        )                                        # Cierra el botón.
    except Exception:                              # Si switch_page no está disponible en la versión actual…
        st.write("↩️")                            # Muestra un fallback mínimo (icono).
        st.write(t("nav.login", lang))           # Muestra el texto "Login" del menú (como pista).

with col2:                                       # Columna derecha (ir al formulario público).
    if RSVP_URL:                                 # Si existe URL pública del formulario RSVP…
        st.link_button(                          # Crea un botón-enlace externo.
            tr("go_rsvp", lang),                 # Texto traducido del botón (ir al formulario).
            RSVP_URL,                            # URL de destino (externo).
            use_container_width=True,            # Ocupa todo el ancho de la columna.
        )                                        # Cierra el botón-enlace.
    else:                                        # Si no hay URL pública configurada…
        st.write(" ")                            # Deja espacio en blanco para mantener simetría visual.
