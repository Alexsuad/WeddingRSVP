# pages/1_Formulario_RSVP.py  # Ruta del archivo dentro del proyecto.                                              # Comentario: indica ubicación.

# =================================================================================                                                                       # Separador visual.
# 📝 Página de Formulario RSVP (Invitados)                                                                                                                # Título descriptivo.
# ---------------------------------------------------------------------------------                                                                        # Separador.
# - Requiere token de sesión válido.                                                                                                                       # Requisito de auth.
# - Carga datos del invitado y metadatos desde el backend.                                                                                                 # Carga inicial.
# - Permite confirmar/rechazar, registrar acompañantes y confirmar datos de contacto.                                                                      # Funcionalidad.
# - Añade un campo de notas opcional y lo envía al backend (notes).                                                                                        # Novedad 7.2.
# - Envía la respuesta al backend y redirige a la página de confirmación.                                                                                  # Flujo final.
# =================================================================================                                                                       # Fin encabezado.

# --- Bootstrap imports path (para que 'utils' funcione en Streamlit) ----------------------------------------------                                      # Comentario sección.
import os                                                                                                           # Importa os para rutas/env.
import sys                                                                                                          # Importa sys para manipular sys.path.
ROOT = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))                                              # Calcula la ruta raíz del app Streamlit.
if ROOT not in sys.path:                                                                                            # Si la ruta no está en sys.path...
    sys.path.insert(0, ROOT)                                                                                        # ...la inserta para poder importar utils/*.
# ------------------------------------------------------------------------------------------------------------------                                      # Fin sección.

# --- Importaciones estándar/terceros -------------------------------------------------------------------------------                                     # Comentario sección.
import re                                                                                                           # Expresiones regulares para validaciones.
import requests                                                                                                     # HTTP cliente para consumir la API.
import streamlit as st                                                                                              # Framework de UI Streamlit.
from dotenv import load_dotenv                                                                                      # Carga de variables de entorno para front.
# ------------------------------------------------------------------------------------------------------------------                                      # Fin sección.

# --- Cargar .env temprano -------------------------------------------------------------------------------------------                                     # Comentario sección.
load_dotenv()                                                                                                       # Carga variables desde .env en tiempo de ejecución.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")                                                  # Lee base URL de API con fallback local.
# ------------------------------------------------------------------------------------------------------------------                                      # Fin sección.

# --- Importaciones del proyecto ------------------------------------------------------------------------------------                                     # Comentario sección.
from utils.lang_selector import render_lang_selector                                                                # Selector de idioma para la UI.
from utils.invite import normalize_invite_type                                                                       # Helper de normalización (no crítico, pero útil).
from utils.translations import t                                                                                    # Función de traducción i18n.
from utils.nav import hide_native_sidebar_nav, render_nav                                                           # Helpers de navegación/estilo.
# ------------------------------------------------------------------------------------------------------------------                                      # Fin sección.

# --- Configuración de página ---------------------------------------------------------------------------------------                                     # Comentario sección.
st.set_page_config(                                                                                                 # Configura metadatos de la página.
    page_title="Formulario RSVP • Boda D&C",                                                                        # Título de pestaña del navegador.
    page_icon="📝",                                                                                                  # Ícono de pestaña.
    layout="centered",                                                                                               # Layout centrado para mejor lectura.
    initial_sidebar_state="collapsed",                                                                               # Sidebar colapsada por defecto.
)                                                                                                                    # Fin set_page_config.

# --- UI Global y Guardia de Autenticación --------------------------------------------------------------------------                                     # Comentario sección.
hide_native_sidebar_nav()                                                                                           # Oculta navegación nativa de Streamlit.
lang = render_lang_selector()                                                                                       # Renderiza selector de idioma y obtiene el idioma actual.
render_nav({                                                                                                        # Dibuja navegación principal (breadcrumb simple).
    "pages/0_Login.py": t("nav.login", lang),                                                                       # Enlace a Login.
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),                                                              # Enlace a Formulario.
    "pages/2_Confirmado.py": t("nav.confirmed", lang),                                                              # Enlace a Confirmación.
})                                                                                                                  # Fin render_nav.

if not st.session_state.get("token"):                                                                               # Si no hay token en sesión...
    st.switch_page("pages/0_Login.py")                                                                              # ...redirige a Login inmediatamente.

headers = {"Authorization": f"Bearer {st.session_state['token']}"}                                                 # Prepara encabezado Authorization Bearer para la API.

# --- Estilos -------------------------------------------------------------------------------------------------------                                     # Comentario sección.
st.markdown("""                                                                                                     # Inyecta CSS mínimo para tarjetas.
    <style>
      :root{ --bg:#FFFFFF; --text:#111; --border:#EAEAEA; --card:#F7F7F7; --shadow:0 4px 18px rgba(0,0,0,.06); --radius:16px; }
      .form-card{ background:var(--bg); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); padding:28px; max-width:720px; margin:0 auto; }
    </style>
""", unsafe_allow_html=True)                                                                                        # Permite HTML en el markdown para aplicar estilos.

# --- Helpers de validación -----------------------------------------------------------------------------------------                                     # Comentario sección.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")                                                                # Regex simple para validar email básico.
PHONE_RE = re.compile(r"^\+\d{8,15}$")                                                                              # Regex para teléfono en formato +######## (8–15 dígitos).

def _is_valid_email(v: str) -> bool:                                                                                # Define helper de validación de email.
    return bool(v and EMAIL_RE.match(v.strip()))                                                                     # Devuelve True si cumple el patrón.

def _is_valid_phone(v: str) -> bool:                                                                                # Define helper de validación de teléfono.
    if not v: return False                                                                                           # Si está vacío, inválido.
    raw = v.strip().replace(" ", "").replace("-", "")                                                                # Limpia espacios y guiones.
    return bool(PHONE_RE.match(raw))                                                                                 # Valida contra el patrón +########.

# --- Carga de datos (invitado + meta) ------------------------------------------------------------------------------                                     # Comentario sección.
@st.cache_data(show_spinner=False)                                                                                   # Cachea la función para evitar llamadas repetidas.
def fetch_initial_data(token):                                                                                       # Define función para traer datos iniciales.
    guest_data, meta_options = {}, {}                                                                                # Inicializa contenedores de respuesta.
    auth_headers = {"Authorization": f"Bearer {token}"}                                                              # Prepara headers con el token recibido.
    try:                                                                                                             # Intenta llamar endpoints del backend.
        r_guest = requests.get(f"{API_BASE_URL}/api/guest/me", headers=auth_headers, timeout=12)                    # Pide perfil del invitado autenticado.
        r_guest.raise_for_status()                                                                                   # Lanza error si el status no es 2xx.
        guest_data = r_guest.json()                                                                                  # Decodifica JSON del perfil.

        r_meta = requests.get(f"{API_BASE_URL}/api/meta/options", headers=auth_headers, timeout=8)                  # Pide metadatos (sugerencias alergias, etc.).
        if r_meta.status_code == 200:                                                                                # Si respondió OK...
            meta_options = r_meta.json()                                                                             # ...lee JSON de opciones meta.
    except requests.exceptions.RequestException as e:                                                                 # Si hubo excepción de requests...
        status_code = e.response.status_code if getattr(e, "response", None) is not None else 503                    # Obtiene código si existe, si no 503.
        return {"error": str(e), "status_code": status_code}                                                          # Devuelve error para manejo en UI.
    return {"guest": guest_data, "meta": meta_options}                                                                # Devuelve datos agregados.

initial_data = fetch_initial_data(st.session_state.get("token"))                                                     # Ejecuta la carga con el token de sesión.

if "error" in initial_data:                                                                                          # Si la carga falló...
    if initial_data.get("status_code") == 401:                                                                       # ...y fue 401 (token inválido/expirado)...
        st.session_state.pop("token", None)                                                                          # ...borra el token de la sesión.
        st.warning(t("form.session_expired", lang))                                                                   # Muestra aviso de sesión expirada.
        st.switch_page("pages/0_Login.py")                                                                            # Redirige a Login.
        st.stop()                                                                                                     # Detiene la ejecución de la página.
    else:                                                                                                             # En otros errores...
        st.error(t("form.load_error", lang))                                                                          # ...muestra error genérico de carga.
        st.stop()                                                                                                     # Detiene ejecución.

guest = initial_data.get("guest", {})                                                                                # Extrae datos del invitado del resultado.
meta = initial_data.get("meta", {})                                                                                  # Extrae metadatos del resultado.
allergy_suggestions = (                                                                                              # Calcula lista de sugerencias de alergias.
    meta.get("allergy_suggestions")                                                                                  # Intenta con clave 1.
    or meta.get("allergens")                                                                                          # Fallback a clave 2.
    or meta.get("suggestions")                                                                                        # Fallback a clave 3.
    or []                                                                                                             # Fallback final: lista vacía.
)                                                                                                                     # Fin cálculo.

# --- Panel informativo de alcance de invitación --------------------------------------------------------------------                                     # Comentario sección.
invite_scope: str = (guest.get("invite_scope") or "reception-only").strip()                                          # Lee alcance de invitación (normalizado).
invited_to_ceremony: bool = bool(guest.get("invited_to_ceremony"))                                                   # Booleano: si está invitado a ceremonia.
ceremony_time: str = st.secrets.get("CEREMONY_TIME", "15:00")                                                        # Hora tentativa de ceremonia (secrets).
reception_time: str = st.secrets.get("RECEPTION_TIME", "17:00")                                                      # Hora tentativa de recepción (secrets).

panel_title: str = t("invite.panel_title", lang)                                                                     # Título del panel (i18n).
scope_text_key: str = "invite.scope.full" if invited_to_ceremony else "invite.scope.reception"                       # Clave i18n según alcance.
scope_text: str = t(scope_text_key, lang)                                                                            # Texto del alcance (i18n).
times_hint: str = t("invite.times.hint", lang).format(                                                               # Texto de pista con horarios.
    ceremony_time=ceremony_time, reception_time=reception_time                                                       # Inserta horas formateadas.
)                                                                                                                     # Fin format.

st.info(f"### {panel_title}\n\n{scope_text}\n\n_{times_hint}_")                                                      # Muestra panel informativo.

# --- Variables para UI -------------------------------------------------------------------------------------------------                               # Comentario sección.
full_name = guest.get("full_name", "")                                                                              # Nombre del invitado para saludo.
max_accomp = int(guest.get("max_accomp", 0))                                                                        # Máximo de acompañantes permitido.

# --- Interfaz ---------------------------------------------------------------------------------------------------------                               # Comentario sección.
st.markdown('<div class="form-card">', unsafe_allow_html=True)                                                      # Abre tarjeta visual contenedora.
st.title(f"👋 {t('form.hi', lang)} {full_name}")                                                                    # Título con saludo e i18n.
st.caption(t("form.subtitle", lang))                                                                                # Subtítulo descriptivo (i18n).

attending = st.radio(                                                                                               # Control de radio Sí/No asistencia.
    t("form.attending", lang),                                                                                      # Etiqueta i18n de la pregunta.
    [t("form.yes", lang), t("form.no", lang)],                                                                      # Opciones i18n.
    horizontal=True,                                                                                                # Disposición horizontal.
    index=0 if guest.get("confirmed", True) else 1                                                                  # Índice por defecto según estado previo.
)                                                                                                                   # Fin radio.

def send_rsvp_to_api(payload):                                                                                      # Define helper para POST al backend.
    try:                                                                                                            # Intenta enviar la petición.
        resp = requests.post(f"{API_BASE_URL}/api/guest/me/rsvp", headers=headers, json=payload, timeout=20)       # Envía POST con JSON y timeout.
        if resp.status_code == 200:                                                                                 # Si fue exitoso...
            st.session_state["last_rsvp"] = resp.json()                                                             # ...guarda respuesta en sesión.
            st.switch_page("pages/2_Confirmado.py")                                                                 # ...navega a página de confirmación.
        elif resp.status_code == 401:                                                                               # Si 401 (token inválido/expirado)...
            st.session_state.pop("token", None)                                                                     # ...borra token.
            st.warning(t("form.session_expired", lang))                                                             # ...avisa en UI.
            st.switch_page("pages/0_Login.py")                                                                       # ...redirige a Login.
            st.stop()                                                                                               # ...detiene ejecución.
        else:                                                                                                       # Otros códigos (4xx/5xx)...
            st.error(resp.json().get("detail", "Ocurrió un error al guardar tu respuesta."))                        # ...muestra error del backend o genérico.
    except requests.exceptions.RequestException:                                                                     # En excepción de red/timeout...
        st.error(t("form.net_err", lang))                                                                           # ...muestra error de red i18n.

# --- Rama: NO asiste ---------------------------------------------------------------------------------------------------                           # Comentario sección.
if attending == t("form.no", lang):                                                                                 # Si seleccionó que NO asiste...
    st.subheader(t("form.contact_title", lang))                                                                     # Subtítulo de contacto.
    st.caption(t("form.contact_note", lang))                                                                        # Nota aclaratoria de contacto.
    email_input_no = st.text_input(t("form.contact_email", lang), value=(guest.get("email") or ""), key="contact_email_no")  # Input email por si quiere actualizar.
    phone_input_no = st.text_input(t("form.contact_phone", lang), value=(guest.get("phone") or ""), key="contact_phone_no")  # Input teléfono por si quiere actualizar.

    # --- NUEVO: Área de notas opcional (no asiste) ------------------------------------------------------------------                            # Comentario novedad.
    notes_no = st.text_area(                                                                                        # Renderiza campo de notas (textarea).
        label=t("form.notes.label", lang),                                                                          # Etiqueta i18n (ej. "¿Quieres dejarnos un mensaje?").
        value="",                                                                                                   # Valor inicial vacío.
        placeholder=t("form.notes.placeholder", lang),                                                              # Placeholder i18n (ej. "Escribe aquí tus comentarios...").
        help=t("form.notes.help", lang),                                                                            # Texto de ayuda i18n (ej. "Opcional. Máx. 500 caracteres.").
        max_chars=500,                                                                                               # Limita a 500 caracteres.
        height=120,                                                                                                  # Altura cómoda de escritura.
        key="notes_no"                                                                                               # Clave única de estado para Streamlit.
    )                                                                                                                # Fin text_area.

    if st.button(t("form.submit", lang)):                                                                           # Botón de envío para caso 'no asiste'.
        email_clean_no = email_input_no.strip()                                                                      # Normaliza email (trim).
        phone_clean_no = phone_input_no.strip().replace(" ", "").replace("-", "")                                   # Normaliza teléfono (quita espacios/guiones).
        if not email_clean_no and not phone_clean_no:                                                                # Exige al menos un medio de contacto.
            st.error(t("form.contact_required_one", lang)); st.stop()                                               # Muestra error i18n y detiene.
        if email_clean_no and not _is_valid_email(email_clean_no):                                                  # Valida email si viene.
            st.error(t("form.contact_invalid_email", lang)); st.stop()                                              # Error de email inválido.
        if phone_clean_no and not _is_valid_phone(phone_clean_no):                                                  # Valida teléfono si viene.
            st.error(t("form.contact_invalid_phone", lang)); st.stop()                                              # Error de teléfono inválido.

        payload = {                                                                                                  # Construye payload JSON para backend.
            "attending": False,                                                                                      # Marca que NO asiste.
            "companions": [],                                                                                        # Sin acompañantes.
            "allergies": None,                                                                                       # Sin alergias cuando no asiste.
            "notes": (notes_no.strip() or None),                                                                     # NUEVO: envía notas (None si vacío).
            "email": email_clean_no or None,                                                                         # Incluye email si lo proporcionó (si backend lo ignora, no rompe).
            "phone": phone_clean_no or None,                                                                         # Incluye teléfono si lo proporcionó (ídem comentario).
        }                                                                                                            # Fin payload.
        with st.spinner(t("form.sending", lang)):                                                                    # Spinner mientras envía.
            send_rsvp_to_api(payload)                                                                                # Llama helper de envío.

# --- Rama: SÍ asiste ---------------------------------------------------------------------------------------------------                           # Comentario sección.
else:                                                                                                               # Si seleccionó que SÍ asiste...
    with st.form("rsvp_form"):                                                                                      # Usa un formulario para agrupar inputs y enviar juntos.
        st.subheader(t('form.titular_allergies', lang))                                                             # Subtítulo para alergias del titular.
        default_allergies = guest.get("allergies", "").split(", ") if guest.get("allergies") else []                # Calcula selección inicial de alergias (si existían).
        titular_allergies_selected = st.multiselect(t("form.allergy_suggestions", lang), options=allergy_suggestions, default=default_allergies)  # Selector múltiple con sugerencias.
        titular_allergies_other = st.text_input(t('form.other_allergy', lang))                                      # Campo para otras alergias (texto libre).

        st.subheader(t("form.contact_title", lang))                                                                 # Subtítulo de contacto.
        st.caption(t("form.contact_note", lang))                                                                    # Nota de contacto.
        default_email = (guest.get("email") or "").strip()                                                          # Email por defecto del invitado.
        default_phone = (guest.get("phone") or "").strip()                                                          # Teléfono por defecto del invitado.
        email_input = st.text_input(t("form.contact_email", lang), value=default_email, key="contact_email")        # Input de email.
        phone_input = st.text_input(t("form.contact_phone", lang), value=default_phone, key="contact_phone")        # Input de teléfono.

        st.subheader(t("form.companions_title", lang))                                                              # Subtítulo de acompañantes.
        existing_companions = guest.get("companions", []) or []                                                     # Carga acompañantes guardados (si los hay).
        default_comp = min(len(existing_companions), max(0, max_accomp))                                            # Sugiere cantidad inicial sin pasar el máximo.
        comp_count = st.slider(t("form.companions_count", lang), 0, max_accomp, default_comp)                       # Slider para cantidad de acompañantes.

        companions_data = []                                                                                        # Inicializa lista de acompañantes que se enviará.
        for i in range(comp_count):                                                                                 # Itera por el número de acompañantes indicados.
            st.markdown(f"**Acompañante #{i+1}**")                                                                  # Título del bloque de cada acompañante.
            comp_defaults = guest.get("companions", [])                                                             # Lee defaults de acompañantes previos.
            default_name = comp_defaults[i]["name"] if i < len(comp_defaults) else ""                               # Nombre por defecto si existía.
            default_is_child = comp_defaults[i]["is_child"] if i < len(comp_defaults) else False                    # Flag niño por defecto si existía.
            default_c_allergies = comp_defaults[i]["allergies"].split(", ") if i < len(comp_defaults) and comp_defaults[i].get("allergies") else []  # Alergias por defecto si existían.
            c_name = st.text_input(t("form.companion_name", lang), value=default_name, key=f"c_name_{i}")           # Input nombre acompañante.
            c_is_child = st.checkbox(t("form.companion_is_child", lang), value=default_is_child, key=f"c_is_child_{i}")  # Checkbox niño/adulto.
            c_allergies_selected = st.multiselect(t("form.allergy_suggestions", lang), options=allergy_suggestions, default=default_c_allergies, key=f"c_allergies_{i}")  # Multi-select alergias.
            c_allergies_other = st.text_input(f"{t('form.other_allergy', lang)} #{i+1}", key=f"c_allergies_other_{i}")  # Campo de otras alergias (texto libre).
            companions_data.append({                                                                                 # Agrega el acompañante armado a la lista.
                "name": c_name,                                                                                      # Nombre del acompañante.
                "is_child": c_is_child,                                                                              # Flag niño/adulto.
                "allergies": ", ".join([*c_allergies_selected, c_allergies_other.strip()] if c_allergies_other.strip() else c_allergies_selected) or None  # Alergias combinadas o None.
            })                                                                                                       # Fin append.

        # --- NUEVO: Área de notas opcional (sí asiste) -------------------------------------------------------------                            # Comentario novedad.
        notes_yes = st.text_area(                                                                                     # Renderiza campo de notas en el formulario.
            label=t("form.notes.label", lang),                                                                         # Etiqueta i18n.
            value="",                                                                                                  # Valor inicial vacío.
            placeholder=t("form.notes.placeholder", lang),                                                             # Placeholder i18n.
            help=t("form.notes.help", lang),                                                                           # Texto de ayuda i18n.
            max_chars=500,                                                                                             # Límite de 500 caracteres.
            height=120,                                                                                                # Altura del textarea.
            key="notes_yes"                                                                                            # Clave única de estado.
        )                                                                                                              # Fin text_area.
        st.caption(f"{len(notes_yes)}/500")                                                                            # Muestra contador simple de caracteres usados.

        submitted = st.form_submit_button(t("form.submit", lang))                                                      # Botón de envío del formulario.
        if submitted:                                                                                                   # Si el usuario presionó enviar...
            email_clean = email_input.strip()                                                                           # Normaliza email titular.
            phone_clean = phone_input.strip().replace(" ", "").replace("-", "")                                        # Normaliza teléfono titular.
            if not email_clean and not phone_clean:                                                                     # Exige al menos un medio de contacto.
                st.error(t("form.contact_required_one", lang)); st.stop()                                              # Error y detención.
            if email_clean and not _is_valid_email(email_clean):                                                       # Valida email si existe.
                st.error(t("form.contact_invalid_email", lang)); st.stop()                                             # Error de email inválido.
            if phone_clean and not _is_valid_phone(phone_clean):                                                       # Valida teléfono si existe.
                st.error(t("form.contact_invalid_phone", lang)); st.stop()                                             # Error de teléfono inválido.

            final_allergies = ", ".join([*titular_allergies_selected, titular_allergies_other.strip()] if titular_allergies_other.strip() else titular_allergies_selected) or None  # Une alergias seleccionadas y libres.
            payload = {                                                                                                # Construye payload JSON para backend.
                "attending": True,                                                                                     # Marca que SÍ asiste.
                "allergies": final_allergies,                                                                          # Alergias del titular (o None).
                "notes": (notes_yes.strip() or None),                                                                  # NUEVO: envía notas (None si vacío).
                "companions": companions_data,                                                                          # Lista de acompañantes armada.
                "email": email_clean or None,                                                                          # Incluye email si lo proporcionó (si backend lo ignora, no rompe).
                "phone": phone_clean or None,                                                                          # Incluye teléfono si lo proporcionó (ídem comentario).
            }                                                                                                          # Fin payload.
            with st.spinner(t("form.sending", lang)):                                                                  # Muestra spinner de envío.
                send_rsvp_to_api(payload)                                                                              # Llama helper de envío.

st.markdown("</div>", unsafe_allow_html=True)                                                                          # Cierra el contenedor visual de la tarjeta.
