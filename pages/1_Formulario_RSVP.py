# pages/1_Formulario_RSVP.py
# =================================================================================
# ⚠️ NOTA DE MODIFICACIÓN
# =================================================================================
# Se ha identificado y corregido un bloque de código mal creado en la sección de
# envío del formulario (`if submitted:`). El código original intentaba convertir
# las alergias de etiquetas a códigos de una manera que resultaba en la pérdida
# de datos de los acompañantes y asignaba incorrectamente las alergias. Este

# bloque ha sido reemplazado por una lógica de conversión robusta y correcta,
# asegurando que los datos se procesen y envíen a la API de forma adecuada.
# =================================================================================


# ===========================================================================================
# 📦 Importaciones y configuración de la página
# ===========================================================================================

import os, sys, re, requests, streamlit as st
from dotenv import load_dotenv
from typing import List
from utils.ui import apply_global_styles, render_side_nav  # Estilos globales + menú lateral (solo UI)


# --- Sub-bloque: Añadir la raíz del proyecto al path para importar utilidades ---
ROOT = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- Sub-bloque: Importación de módulos de utilidad locales ---
from utils.lang_selector import render_lang_selector
from utils.translations import t


# --- Sub-bloque: Configuración inicial de la aplicación ---
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# --- Sub-bloque: Configuración de la página de Streamlit ---
st.set_page_config(
    page_title="Formulario RSVP • Boda D&C",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed",
)

apply_global_styles()  # Oculta header/sidebar nativos y aplica fondo/tipografías/botones

# --- Sub-bloque: Renderizado de componentes de navegación y UI comunes ---
lang = render_lang_selector()  # Muestra el selector y devuelve "es"/"en"/"ro"

# --- Sub-bloque: Verificación de sesión de usuario ---
if not st.session_state.get("token"):
    st.switch_page("pages/0_Login.py")

# Menú lateral (en esta página ocultamos "Login" y "Solicitar Acceso")
render_side_nav(t, lang, hide=["login", "request"])


# --- Sub-bloque: Preparación de cabeceras para la API ---
headers = {"Authorization": f"Bearer {st.session_state['token']}"}

# =================================================================================
# 🎨 Estilos CSS personalizados
# =================================================================================
# Inyecta CSS para unificar la apariencia de los botones y el formulario.
st.markdown(
    """
   <style>
        /* --- BOTONES: restaurar estilo del selector de idioma y mantener el submit en primario --- */
        .stButton > button:not([data-testid="stFormSubmitButton"]) { /* Selecciona cualquier botón que NO sea el submit del form */
            background: #FFFFFF !important;                          /* Fondo blanco para “outline” como en la hoja base */
            color: #111111 !important;                               /* Texto oscuro legible */
            border: 1px solid #E5E5E5 !important;                    /* Borde gris sutil */
            border-radius: 8px !important;                           /* Radio consistente */
            font-weight: 600 !important;                             /* Peso medio para legibilidad */
            transition: all .2s ease !important;                     /* Transición suave al hover */
        }                                                          /* Fin botón secundario */

        .stButton > button:not([data-testid="stFormSubmitButton"]):hover { /* Estado hover del botón de idioma */
            background: #F5F5F5 !important;                          /* Gris muy claro al pasar el cursor */
        }                                                          /* Fin hover */

        /* Botón de envío del formulario (solo este va con primario) */
        form[data-testid="stForm"] [data-testid="stFormSubmitButton"] button { /* Ubica el botón submit dentro del form */
            background: var(--primary) !important;                    /* Usa el color primario definido en tokens */
            color: #FFFFFF !important;                                /* Texto blanco para contraste */
            border: none !important;                                  /* Sin borde para look sólido */
            border-radius: 10px !important;                           /* Redondeo acorde a inputs */
            width: 100% !important;                                   /* Ocupa el ancho del contenedor */
            padding: 10px 16px !important;                            /* Área clicable cómoda */
            box-shadow: 0 1px 2px rgba(0,0,0,.06) !important;         /* Sombra leve para relieve */
            transition: transform .02s ease, opacity .2s ease !important; /* Feedback sutil en interacción */
        }                                                          /* Fin submit */

        form[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover { /* Hover del submit */
            opacity: .95 !important;                                  /* Leve atenuación para indicar interacción */
        }                                                          /* Fin hover submit */

        /* --- FORM WRAPPER: eliminar definitivamente la “caja blanca fantasma” --- */
        form[data-testid="stForm"],                                /* Selecciona el form de Streamlit */
        form[data-testid="stForm"] > div {                         /* Y su contenedor inmediato (varía según versión) */
            background: transparent !important;                      /* Fondo totalmente transparente */
            border: none !important;                                 /* Quita cualquier borde heredado */
            box-shadow: none !important;                             /* Sin sombra (adiós caja flotante) */
            padding: 0 !important;                                   /* Sin padding extra del wrapper */
        }                                                          /* Fin override del wrapper */
    </style>

    """,
    unsafe_allow_html=True,
)

# =================================================================================
# 🛠️ Funciones de ayuda (Helpers)
# =================================================================================

# --- Sub-bloque: Funciones de validación de datos ---
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _is_valid_email(v: str) -> bool:
    # Valida si una cadena de texto tiene formato de email.
    return bool(v and EMAIL_RE.match(v.strip()))

def _is_valid_phone(v: str) -> bool:
    # Valida si un teléfono es aceptable contando solo sus dígitos.
    # Ignora espacios, guiones y el signo '+' inicial.
    if not v:
        return False
    # Quita cualquier carácter que no sea un dígito numérico
    digits_only = re.sub(r'\D', '', v)
    # Comprueba que la cantidad de dígitos sea razonable (ej. entre 8 y 15)
    return 8 <= len(digits_only) <= 15

# --- Sub-bloque: Funciones de interacción con la API ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_initial_data(token: str) -> dict:
    # Obtiene los datos iniciales del invitado y metadatos (como alérgenos) desde la API.
    try:
        # Prepara las cabeceras de autorización
        h = {"Authorization": f"Bearer {token}"}
        # Petición para obtener los datos del invitado
        g = requests.get(f"{API_BASE_URL}/api/guest/me", headers=h, timeout=12)
        g.raise_for_status()
        guest = g.json()
        # Petición para obtener los metadatos de la aplicación
        m = requests.get(f"{API_BASE_URL}/api/meta/options", headers=h, timeout=8)
        meta = m.json() if m.status_code == 200 else {}

        # ─────────────────────────────────────────────────────────
        # BLOQUE · Normalizar meta a CÓDIGOS neutros (no textos ES)
        # ─────────────────────────────────────────────────────────
        # Compatibilidad: si el backend ya devuelve códigos, no hacemos nada.
        # Si devolviera textos en español (backend viejo), mapeamos a códigos.
        SPANISH_TO_CODE = {
            "Gluten": "gluten",
            "Lácteos": "dairy",
            "Frutos secos": "nuts",
            "Mariscos": "seafood",
            "Huevos": "eggs",
            "Soja": "soy",
        }

        # 1) Fuente preferida: "allergens" (nueva). 2) Alias legacy: "allergy_suggestions".
        allergens = meta.get("allergens") or meta.get("allergy_suggestions") or []

        if allergens and isinstance(allergens[0], str):
            # Si detectamos textos ES, convertir a códigos.
            if any(x in SPANISH_TO_CODE for x in allergens):
                allergens = [SPANISH_TO_CODE.get(x, x) for x in allergens]

        # Reescribimos meta con la clave estándar "allergens" a CÓDIGOS.
        meta["allergens"] = allergens

        return {"guest": guest, "meta": meta}
    
    except requests.exceptions.RequestException as e:
            # Devolvemos un diccionario con una clave de error para manejarlo en la UI
            return {"error": f"No se pudieron cargar los datos iniciales. Error: {e}"}
    except Exception as e:
            # Captura otros errores (ej. JSON mal formado)
            return {"error": f"Ocurrió un error inesperado al cargar los datos: {e}"}

# --- INICIO DEL CÓDIGO A REEMPLAZAR ---

def _post_rsvp(payload: dict) -> None:
    """
    Envía la respuesta del formulario (RSVP) a la API y maneja los casos
    de éxito, sesión expirada y conflicto de email/teléfono ya en uso.
    Requiere en el módulo: requests, st, API_BASE_URL, headers, lang, t().
    """
    try:
        r = requests.post(
            f"{API_BASE_URL}/api/guest/me/rsvp",
            headers=headers,
            json=payload,
            timeout=20,
        )

        if r.status_code == 200:
            # ÉXITO → guardamos la respuesta y vamos a la confirmación
            st.session_state["last_rsvp"] = r.json()
            st.switch_page("pages/2_Confirmado.py")

        elif r.status_code == 401:
            # SESIÓN EXPIRADA → limpiamos token y enviamos a Login
            st.session_state.pop("token", None)
            st.warning(t("form.session_expired", lang))
            st.switch_page("pages/0_Login.py")

        elif r.status_code == 409:
            # CONFLICTO (unicidad de email/teléfono)
            # Mostramos mensaje traducido usando message_key si viene;
            # si no, usamos la clave estándar de conflicto.
            try:
                err = r.json() or {}
            except Exception:
                err = {}
            key = err.get("message_key")
            if isinstance(key, str):
                st.error(t(key, lang))
            else:
                st.error(t("form.email_or_phone_conflict", lang))

            # Importante: cortar aquí para evitar reenvíos en bucle
            return

        else:
            # OTROS ERRORES → intentamos mostrar "detail" o un genérico
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = None
            st.error(detail or t("form.generic_error", lang))

    except requests.exceptions.RequestException:
        # ERROR DE RED / TIMEOUT
        st.error(t("form.net_err", lang))


# =================================================================================
# 🔄 Carga y preparación de datos
# =================================================================================
# --- Sub-bloque: Ejecución de la carga de datos ---
data = fetch_initial_data(st.session_state["token"])
if "error" in data:
    st.error(data["error"])
    st.stop()

# --- Sub-bloque: Desempaquetado de datos en variables locales ---
guest = data.get("guest", {}) or {}
meta  = data.get("meta",  {}) or {}

# --- Sub-bloque: Cálculo de variables derivadas y lógicas ---
full_name = (guest.get("full_name") or "").strip()
max_accomp = int(guest.get("max_accomp") or 0)

# ----------------------------------------------------------------------
# Allergen i18n (codes → labels) y mapas bidireccionales
# - Fuente canónica: meta["allergens"] en CÓDIGOS (normalizado en fetch)
# - UI: muestra labels traducidos
# - API: recibe y guarda CÓDIGOS (conversión labels → codes en el submit)
# ----------------------------------------------------------------------
allergen_codes: List[str] = (
    meta.get("allergens") 
    or meta.get("allergy_suggestions") 
    or []
)

# Lista de opciones visibles (labels traducidos) en el idioma activo
allergy_suggestions: List[str] = [
    t(f"options.allergen.{code}", lang) for code in allergen_codes
]

if not allergy_suggestions:
    allergy_suggestions = []  # Asegura lista vacía (nunca None)

# Mapas label ↔ code para convertir UI ⇄ API de forma segura
label_to_code_map = {
    label: code for label, code in zip(allergy_suggestions, allergen_codes)
}
code_to_label_map = {
    code: label for label, code in label_to_code_map.items()
}

# Preselección del titular (si en BD ya hay alergias en CÓDIGOS)
saved_titular_allergies_codes: List[str] = [
    s.strip() for s in (guest.get("allergies") or "").split(",") if s.strip()
]

preselected_labels_titular: List[str] = [
    code_to_label_map.get(code, code) for code in saved_titular_allergies_codes
]
preselected_labels_titular = [lbl for lbl in preselected_labels_titular if lbl in allergy_suggestions]  # Filtra defaults no presentes en options


# invited_full robusto (maneja strings)
invited_flag_raw = str(guest.get("invited_to_ceremony", False)).strip().lower()
invited_full = invited_flag_raw in ("true", "1", "yes", "y", "si", "sí")

# Horarios del evento obtenidos de variables de entorno o secretos
ceremony_time = os.getenv("CEREMONY_TIME") or st.secrets.get("CEREMONY_TIME", "15:00")
reception_time = os.getenv("RECEPTION_TIME") or st.secrets.get("RECEPTION_TIME", "17:00")


# =================================================================================
# 🖼️ Renderizado de la interfaz de usuario (UI)
# =================================================================================
# --- Sub-bloque: Tarjeta de invitación ---
st.markdown('<div class="hero-card">', unsafe_allow_html=True)
st.markdown(f"### {t('form.invite_title', lang)}")
if invited_full:
    st.write(t("form.invite_full_access", lang))
    st.write(f"_{t('form.time_ceremony', lang)} {ceremony_time} · {t('form.time_reception', lang)} {reception_time}_")
else:
    st.write(t("form.invite_reception_only", lang))
    st.write(f"_{t('form.time_reception', lang)}: {reception_time}_")
if max_accomp > 0:
    plural = "" if max_accomp == 1 else "s"
    st.write(t("form.accomp_note", lang).format(max_accomp=max_accomp, plural=plural))
st.markdown("</div>", unsafe_allow_html=True)

# --- Sub-bloque: Saludo personalizado ---
st.markdown(f'<div class="title-xl">👋 {t("form.hi", lang)}, {full_name}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">{t("form.subtitle", lang)}</div>', unsafe_allow_html=True)

# --- Sub-bloque: Selector principal de asistencia ---
att_choice = st.radio(t("form.attending", lang), [t("form.yes", lang), t("form.no", lang)], horizontal=True)
is_attending = (att_choice == t("form.yes", lang))


# --- Sub-bloque: Flujo para invitados que NO asisten ---
if not is_attending:
    st.warning(t("form.no_attend_short", lang))
    # Área de texto para mensaje opcional
    msg_no = st.text_area(
        label=t("form.notes.expander_label", lang),
        placeholder=t("form.notes.placeholder", lang),
        max_chars=500,
        height=120,
        label_visibility="collapsed",
        key="notes_no",
    )
    # Botón de envío para la respuesta de no asistencia
    if st.button(t("form.submit", lang), type="primary"):
        payload = {
            "attending": False,
            "companions": [],
            "allergies": None,
            "notes": (msg_no.strip() or None),
            "email": None,
            "phone": None,
        }
        with st.spinner(t("form.sending", lang)):
            _post_rsvp(payload)
    st.stop()

# --- Sub-bloque: Controles dinámicos para acompañantes (fuera del formulario principal) ---
st.markdown(f'<div class="section-title">{t("form.companions_title", lang)}</div>', unsafe_allow_html=True)
st.caption(t("form.companions_db_note", lang))

# Inicializa el contador de acompañantes en el estado de la sesión si no existe
if "comp_count" not in st.session_state:
    existing = guest.get("companions") or []
    st.session_state.comp_count = min(len(existing), max_accomp)

if max_accomp <= 0:
    # Muestra un mensaje si el invitado no puede llevar acompañantes
    st.info(t("form.no_companions_info", lang))
    st.session_state.comp_count = 0
else:
    # Permite al usuario indicar si llevará acompañantes
    bring = st.radio(
        t("form.bring_companions", lang),
        [t("form.yes", lang), t("form.no", lang)],
        index=0 if st.session_state.comp_count > 0 else 1,
        horizontal=True,
        key="bring_companions_radio",
    )
    if bring == t("form.no", lang):
        # Si el usuario selecciona "No", reinicia el contador y la interfaz
        if st.session_state.comp_count != 0:
            st.session_state.comp_count = 0
            st.rerun()
    else:
        # Si el usuario selecciona "Sí", muestra el selector de cantidad
        options = list(range(1, max_accomp + 1))
        current = st.session_state.comp_count if st.session_state.comp_count > 0 else 1
        try:
            idx = options.index(current)
        except ValueError:
            idx = len(options) - 1
            st.session_state.comp_count = options[idx]
        new_count = st.selectbox(t("form.companions_count", lang), options, index=idx, key="companions_count_select")
        # Si cambia la cantidad, actualiza el estado y la interfaz
        if new_count != st.session_state.comp_count:
            st.session_state.comp_count = new_count
            st.rerun()

st.write("")  # Pequeño espacio visual

# =================================================================================                      # Sección claramente delimitada para el formulario “SÍ asisten”.
# 📝 Formulario principal para invitados que SÍ asisten                                                   # Título de sección.
# =================================================================================
with st.form("rsvp_form_yes"):                                                                            # Abre un formulario con manejo transaccional (solo envía al pulsar submit).
    # --- Sub-bloque: Campos de contacto ---                                                             # Subtítulo de contactos.
    st.markdown(f'<div class="section-title">{t("form.contact_title", lang)}</div>', unsafe_allow_html=True)  # Renderiza título HTML para contactos.
    email_input = st.text_input(                                                                             # Input de email (cadena).
        t("form.field_email", lang),                                                                      # Etiqueta traducida del campo.
        value=(guest.get("email") or "").strip()                                                         # Valor por defecto: email del invitado si existe.
    )
    phone_input = st.text_input(                                                                          # Input de teléfono (cadena).
        t("form.field_phone", lang),                                                                      # Etiqueta traducida del campo.
        value=(guest.get("phone") or "").strip()                                                          # Valor por defecto: teléfono del invitado si existe.
    )
    st.caption(t("form.contact_caption", lang))                                                           # Pie/ayuda para el bloque de contacto (corrige el typo: st.caption).

    # --- Sub-bloque: Selección de alergias para el invitado titular ---                                  # Subtítulo de alergias del titular.
    st.markdown(f'<div class="section-title">{t("form.titular_allergies", lang)}</div>', unsafe_allow_html=True)  # Renderiza sección para el titular.
    st.caption(t("form.allergies_caption", lang))                                                         # Texto auxiliar sobre cómo seleccionar alergias.
    titular_allergies: List[str] = st.multiselect(                                                        # Multiselect para alergias del titular (trabaja en LABELS).
        label=t("form.allergies_or_restrictions", lang),                                                  # Etiqueta/placeholder del multiselect.
        options=allergy_suggestions,                                                                      # Opciones visibles (LABELS traducidos) ya construidas arriba.
        default=preselected_labels_titular,                                                               # Defaults del titular (LABELS) filtrados contra options.
        label_visibility="collapsed",                                                                     # Oculta la etiqueta para un look más limpio.
        key="titular_allergies_multiselect"                                                               # Clave de estado para el widget.
    )

    # --- Sub-bloque: Generación dinámica de campos para acompañantes ---                                 # Sección para acompañantes.
    companions_data: List[dict] = []                                                                      # Lista que recogerá los datos de cada acompañante (para UI y payload).
    comp_defaults = (guest.get("companions") or [])                                                       # Defaults de acompañantes guardados previamente (si existen).

    for i in range(st.session_state.get("comp_count", 0)):                                                # Itera tantos acompañantes como indique el estado.
        st.markdown(f"**{t('form.companion_label', lang)} {i+1}**")                                       # Título por acompañante (p.ej. “Acompañante 1”).
        def_name = comp_defaults[i]["name"] if i < len(comp_defaults) else ""                             # Nombre por defecto del acompañante i (si existe).
        def_is_child = comp_defaults[i]["is_child"] if i < len(comp_defaults) else False                  # Indicador niño/adulto por defecto para i (si existe).
        def_allergies_str = (comp_defaults[i].get("allergies") or "") if i < len(comp_defaults) else ""   # Alergias por defecto (STRING codificada por comas) para i.
        def_codes = [s.strip() for s in def_allergies_str.split(",") if s.strip()]                         # Normaliza STRING → lista de CÓDIGOS (trim de cada item).
        def_labels = [code_to_label_map.get(c, c) for c in def_codes]                                      # Mapea CÓDIGOS → LABELS para mostrarlos en el multiselect.
        def_labels = [lbl for lbl in def_labels if lbl in allergy_suggestions]                             # Filtra LABELS que ya no estén en las opciones visibles.

        col_name, col_kind, col_all = st.columns([2.0, 1.0, 2.0])                                         # Tres columnas: nombre / tipo / alergias.

        with col_name:                                                                                     # Columna del nombre del acompañante.
            c_name = st.text_input(                                                                        # Input de texto para el nombre.
                t("form.field_name", lang),                                                                # Etiqueta traducida del campo.
                value=def_name,                                                                            # Valor por defecto calculado arriba.
                key=f"c_name_{i}",                                                                         # Clave de estado única por acompañante.
                placeholder=t("form.placeholder_fullname", lang),                                          # Placeholder amigable.
            )

        with col_kind:                                                                                     # Columna tipo (adulto/niño).
            tipo_txt = st.selectbox(                                                                       # Select que muestra adulto/niño traducidos.
                t("form.child_or_adult", lang),                                                            # Etiqueta del select.
                [t("form.adult", lang), t("form.child", lang)],                                            # Opciones visibles (labels traducidos).
                index=(1 if def_is_child else 0),                                                          # Índice por defecto según estado.
                key=f"c_is_child_{i}",                                                                     # Clave de estado única.
            )
            c_is_child = (tipo_txt == t("form.child", lang))                                               # Booleano resultante a partir del label seleccionado.

        with col_all:                                                                                      # Columna de alergias del acompañante.
            c_selected_labels = st.multiselect(                                                            # Multiselect para alergias (LABELS) del acompañante i.
                t("form.allergies_or_restrictions", lang),                                                 # Etiqueta/placeholder del multiselect.
                options=allergy_suggestions,                                                               # Opciones visibles (LABELS traducidos).
                default=def_labels,                                                                        # Defaults (LABELS) filtrados previamente.
                key=f"c_allergies_{i}",                                                                    # Clave única por acompañante.
            )

        companions_data.append({                                                                           # Agrega datos del acompañante a la lista (para construir payload).
            "name": (c_name or "").strip(),                                                                # Nombre limpio (o cadena vacía).
            "is_child": bool(c_is_child),                                                                  # Indicador booleano niño/adulto.
            "allergies": (",".join(c_selected_labels) or None),                                           # Alergias en LABELS como STRING (serán mapeadas a CÓDIGOS al enviar).
        })

    # --- Sub-bloque: Campo opcional para notas adicionales ---                                            # Sección de notas opcionales.
    with st.expander(t("form.notes.expander_label", lang)):                                                # Expander para las notas (colapsible).
        msg_yes = st.text_area(                                                                            # Área de texto para detalles adicionales.
            label="msg",                                                                                   # Etiqueta interna (oculta).
            placeholder=t("form.notes.placeholder", lang),                                                 # Placeholder traducido amigable.
            max_chars=500,                                                                                 # Límite de caracteres para el mensaje.
            height=120,                                                                                    # Altura del área de texto.
            label_visibility="collapsed",                                                                  # Oculta la etiqueta del widget.
            key="notes_yes",                                                                               # Clave de estado para la nota.
        )

    # --- Sub-bloque: Botón de envío del formulario ---                                                     # ÚNICO botón submit, dentro del with.
    submitted = st.form_submit_button(                                                                     # Crea el botón que dispara el envío de este form.
        t("form.submit", lang),                                                                            # Texto traducido del botón (p.ej. “Enviar respuesta”).
        type="primary",                                                                                    # Estilo primario (negro en tu tema).
        use_container_width=True                                                                           # Botón ocupa el ancho del contenedor.
    )


# --- Sub-bloque: Botón para cancelar y reiniciar el formulario (fuera del form) ------------------------- # Botón de cancelar independiente.
col_cancel = st.columns([1, 1, 1])[1]                                                                       # Crea tres columnas y toma la central para centrar el botón.
with col_cancel:                                                                                             # Usa la columna central.
    if st.button(t("form.cancel", lang), use_container_width=True):                                         # Botón “Cancelar” de ancho completo.
        for k in [k for k in st.session_state.keys() if k.startswith(("c_name_", "c_is_child_", "c_allergies_", "notes_yes", "titular_allergies_multiselect"))]:   # Itera y borra claves del form.
            st.session_state.pop(k, None)                                                                   # Elimina cada clave del estado de sesión.
        st.query_params.clear()                                                                             # Limpia parámetros de la URL (evita re-ejecuciones).
        st.toast(t("form.select_option", lang))                                                             # Mensaje toast informativo.
        st.rerun()                                                                                          # Re-lanza la app para refrescar.

# =================================================================================
# 📤 Lógica de envío del formulario
# =================================================================================
# Se ejecuta solo si el botón de envío del formulario fue presionado.
if submitted:
    # --- Sub-bloque: Limpieza y validación de datos de contacto ---
    email_clean = (email_input or "").strip()
    phone_clean = (phone_input or "").strip().replace(" ", "").replace("-", "")

    if not email_clean and not phone_clean:
        st.error(t("form.contact_required_one", lang)); st.stop()
    if email_clean and not _is_valid_email(email_clean):
        st.error(t("form.contact_invalid_email", lang)); st.stop()
    if phone_clean and not _is_valid_phone(phone_clean):
        st.error(t("form.contact_invalid_phone", lang)); st.stop()

    # --- Sub-bloque: Validación de datos de acompañantes ---
    if st.session_state.comp_count > 0:
        vacios = [i for i, c in enumerate(companions_data, start=1) if not c["name"]]
        if vacios:
            st.error(t("form.companion_name_required", lang)); st.stop()
        companions_final = companions_data
    else:
        companions_final = []

    # ------------------------------------------------------------
    # Conversión final labels → codes para titular y acompañantes
    # (la API debe recibir SIEMPRE códigos canónicos)
    # ------------------------------------------------------------
    # Convierte las alergias del titular de etiquetas a códigos
    titular_allergies_codes: List[str] = [
        label_to_code_map.get(lbl, lbl) for lbl in (titular_allergies or [])
    ]
    
    # Convierte las alergias de cada acompañante de etiquetas a códigos
    for companion in companions_final:
        if companion.get("allergies"):
            comp_labels = [s.strip() for s in str(companion["allergies"]).split(",") if s.strip()]
            comp_codes = [label_to_code_map.get(lbl, lbl) for lbl in comp_labels]
            companion["allergies"] = ",".join(comp_codes) or None

    # --- Sub-bloque: Construcción del payload final para la API ---
    payload = {
        "attending": True,
        "allergies": (",".join(titular_allergies_codes) or None),
        "companions": companions_final,
        "notes": (msg_yes.strip() or None) if "msg_yes" in locals() else None,
        "email": email_clean.lower() if email_clean else None,
        "phone": phone_clean or None,
    }
    
    # --- Sub-bloque: Llamada a la API para enviar los datos ---
    with st.spinner(t("form.sending", lang)):
        _post_rsvp(payload)