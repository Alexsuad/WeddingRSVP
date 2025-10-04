# pages/1_Formulario_RSVP.py
# ===========================================================================================
# 💍 Formulario RSVP — Refactor UX + i18n + estado (revisado)
# ===========================================================================================

import os, sys, re, requests, streamlit as st
from dotenv import load_dotenv
from typing import List

# --- bootstrap imports path (para utils/*) ---
ROOT = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.lang_selector import render_lang_selector
from utils.translations import t
from utils.nav import hide_native_sidebar_nav, render_nav

# --- setup ---
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Formulario RSVP • Boda D&C",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed",
)

hide_native_sidebar_nav()
lang = render_lang_selector()
render_nav({
    "pages/0_Login.py": t("nav.login", lang),
    "pages/1_Formulario_RSVP.py": t("nav.form", lang),
    "pages/2_Confirmado.py": t("nav.confirmed", lang),
})

if not st.session_state.get("token"):
    st.switch_page("pages/0_Login.py")

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

# --- estilos básicos ---
st.markdown(
    """
    <style>
      :root{ --bg:#fff; --text:#111; --muted:#5f6c80; --border:#eaeaea; --card:#f6f9fe;
             --shadow:0 10px 30px rgba(0,0,0,.08); --radius:18px; }
      .main > div { max-width: 980px; margin: 0 auto; }
      .hero-card { background:#edf3ff; border:1px solid #dfe9ff; border-radius:16px; padding:18px 20px; box-shadow:var(--shadow); }
      .section-title { font-size:22px; font-weight:800; margin:28px 0 12px 0; }
      .title-xl { font-size:34px; font-weight:800; margin:14px 0 8px 0; }
      .subtitle { color:var(--muted); margin-bottom: 12px; }
      .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stMultiSelect [data-baseweb="select"] { border-radius:10px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- helpers ---
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+\d{8,15}$")

def _is_valid_email(v: str) -> bool:
    return bool(v and EMAIL_RE.match(v.strip()))

def _is_valid_phone(v: str) -> bool:
    if not v:
        return False
    raw = v.strip().replace(" ", "").replace("-", "")
    return bool(PHONE_RE.match(raw))

@st.cache_data(ttl=300, show_spinner=False)
def fetch_initial_data(token: str) -> dict:
    try:
        h = {"Authorization": f"Bearer {token}"}
        g = requests.get(f"{API_BASE_URL}/api/guest/me", headers=h, timeout=12)
        g.raise_for_status()
        guest = g.json()
        m = requests.get(f"{API_BASE_URL}/api/meta/options", headers=h, timeout=8)
        meta = m.json() if m.status_code == 200 else {}
        return {"guest": guest, "meta": meta}
    except requests.exceptions.RequestException:
        return {"error": t("form.load_error", lang)}

def _post_rsvp(payload: dict) -> None:
    try:
        r = requests.post(f"{API_BASE_URL}/api/guest/me/rsvp", headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            st.session_state["last_rsvp"] = r.json()
            st.switch_page("pages/2_Confirmado.py")
        elif r.status_code == 401:
            st.session_state.pop("token", None)
            st.warning(t("form.session_expired", lang))
            st.switch_page("pages/0_Login.py")
        else:
            # detalla si el backend retorna mensaje
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = None
            st.error(detail or t("form.generic_error", lang))
    except requests.exceptions.RequestException:
        st.error(t("form.net_err", lang))

# --- fetch ---
data = fetch_initial_data(st.session_state["token"])
if "error" in data:
    st.error(data["error"])
    st.stop()

guest = data.get("guest", {}) or {}
meta  = data.get("meta",  {}) or {}

# --- derivados ---
full_name = (guest.get("full_name") or "").strip()
max_accomp = int(guest.get("max_accomp") or 0)
allergy_suggestions: List[str] = meta.get("allergy_suggestions") or meta.get("allergens") or []

# invited_full robusto (maneja strings)
invited_flag_raw = str(guest.get("invited_to_ceremony", False)).strip().lower()
invited_full = invited_flag_raw in ("true", "1", "yes", "y", "si", "sí")

ceremony_time  = st.secrets.get("CEREMONY_TIME", "15:00")
reception_time = st.secrets.get("RECEPTION_TIME", "17:00")

# --- tarjeta invitación ---
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

# --- saludo ---
st.markdown(f'<div class="title-xl">👋 {t("form.hi", lang)}, {full_name}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">{t("form.subtitle", lang)}</div>', unsafe_allow_html=True)

# --- asistencia (radio) ---
att_choice = st.radio(t("form.attending", lang), [t("form.yes", lang), t("form.no", lang)], horizontal=True)
is_attending = (att_choice == t("form.yes", lang))

# --- flujo NO asiste ---
if not is_attending:
    st.warning(t("form.no_attend_short", lang))
    # Pequeño cuadro para dejar nota (opcional) sin complicar el flujo
    msg_no = st.text_area(
        label=t("form.notes.expander_label", lang),
        placeholder=t("form.notes.placeholder", lang),
        max_chars=500,
        height=120,
        label_visibility="collapsed",
        key="notes_no",
    )
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

# --- controles de acompañantes (FUERA del form, con rerun) ---
st.markdown(f'<div class="section-title">{t("form.companions_title", lang)}</div>', unsafe_allow_html=True)
st.caption(t("form.companions_db_note", lang))

if "comp_count" not in st.session_state:
    # sugerimos lo precargado pero acotado por máx
    existing = guest.get("companions") or []
    st.session_state.comp_count = min(len(existing), max_accomp)

if max_accomp <= 0:
    st.info(t("form.no_companions_info", lang))
    st.session_state.comp_count = 0
else:
    bring = st.radio(
        t("form.bring_companions", lang),
        [t("form.yes", lang), t("form.no", lang)],
        index=0 if st.session_state.comp_count > 0 else 1,
        horizontal=True,
        key="bring_companions_radio",
    )
    if bring == t("form.no", lang):
        if st.session_state.comp_count != 0:
            st.session_state.comp_count = 0
            st.rerun()
    else:
        # SI → seleccionar cantidad 1..máx
        options = list(range(1, max_accomp + 1))
        current = st.session_state.comp_count if st.session_state.comp_count > 0 else 1
        try:
            idx = options.index(current)
        except ValueError:
            idx = len(options) - 1
            st.session_state.comp_count = options[idx]
        new_count = st.selectbox(t("form.companions_count", lang), options, index=idx, key="companions_count_select")
        if new_count != st.session_state.comp_count:
            st.session_state.comp_count = new_count
            st.rerun()

st.write("")  # pequeño respiro visual

# --- FORM PRINCIPAL (envío) ---
with st.form("rsvp_form_yes"):
    # Contacto
    st.markdown(f'<div class="section-title">{t("form.contact_title", lang)}</div>', unsafe_allow_html=True)
    st.caption(t("form.contact_caption", lang))
    email_input = st.text_input(t("form.field_email", lang), value=(guest.get("email") or "").strip())
    phone_input = st.text_input(t("form.field_phone", lang), value=(guest.get("phone") or "").strip())

    # Alergias titular
    st.markdown(f'<div class="section-title">{t("form.titular_allergies", lang)}</div>', unsafe_allow_html=True)
    st.caption(t("form.allergies_caption", lang))
    default_allergies = [s.strip() for s in (guest.get("allergies") or "").split(",") if s.strip()]
    titular_allergies = st.multiselect(
        t("form.allergies_or_restrictions", lang),
        options=allergy_suggestions,
        default=default_allergies,
        label_visibility="collapsed",
        key="titular_allergies",
    )

    # Filas de acompañantes (horizontales)
    companions_data: List[dict] = []
    comp_defaults = guest.get("companions", []) or []

    for i in range(st.session_state.comp_count):
        st.markdown(f"**{t('form.companion_label', lang)} {i+1}**")
        def_name = comp_defaults[i]["name"] if i < len(comp_defaults) else ""
        def_is_child = comp_defaults[i]["is_child"] if i < len(comp_defaults) else False
        def_allergies = (comp_defaults[i].get("allergies") or "") if i < len(comp_defaults) else ""
        def_allergies_list = [s.strip() for s in def_allergies.split(",") if s.strip()]

        col_name, col_kind, col_all = st.columns([2.0, 1.0, 2.0])

        with col_name:
            c_name = st.text_input(
                t("form.field_name", lang),
                value=def_name,
                key=f"c_name_{i}",
                placeholder=t("form.placeholder_fullname", lang),
            )

        with col_kind:
            tipo_txt = st.selectbox(
                t("form.child_or_adult", lang),
                [t("form.adult", lang), t("form.child", lang)],
                index=(1 if def_is_child else 0),
                key=f"c_is_child_{i}",
            )
            c_is_child = (tipo_txt == t("form.child", lang))

        with col_all:
            c_allergies_sel = st.multiselect(
                t("form.allergies_or_restrictions", lang),
                options=allergy_suggestions,
                default=def_allergies_list,
                key=f"c_allergies_{i}",
            )

        companions_data.append({
            "name": c_name.strip(),
            "is_child": c_is_child,
            "allergies": (", ".join(c_allergies_sel) or None),
        })

    # Mensaje opcional en expander para no estorbar
    with st.expander(t("form.notes.expander_label", lang)):
        msg_yes = st.text_area(
            label="msg",
            placeholder=t("form.notes.placeholder", lang),
            max_chars=500,
            height=120,
            label_visibility="collapsed",
            key="notes_yes",
        )

    # Botones (en el form solo el de enviar)
    submitted = st.form_submit_button(t("form.submit", lang), type="primary", use_container_width=True)

# Botón Cancelar fuera del form (no envía)
col_cancel = st.columns([1, 1, 1])[1]
with col_cancel:
    if st.button(t("form.cancel", lang), use_container_width=True):
        # “Cancelar” descarta cambios visuales y te deja en el inicio del formulario
        # (no envía nada, no navega a “Confirmado”).
        for k in [k for k in st.session_state.keys() if k.startswith(("c_name_", "c_is_child_", "c_allergies_", "notes_yes"))]:
            st.session_state.pop(k, None)
        st.experimental_set_query_params()  # limpia la URL
        st.toast(t("form.select_option", lang))
        st.rerun()

# Envío (validaciones y POST)
if submitted:
    email_clean = (email_input or "").strip()
    phone_clean = (phone_input or "").strip().replace(" ", "").replace("-", "")

    if not email_clean and not phone_clean:
        st.error(t("form.contact_required_one", lang)); st.stop()
    if email_clean and not _is_valid_email(email_clean):
        st.error(t("form.contact_invalid_email", lang)); st.stop()
    if phone_clean and not _is_valid_phone(phone_clean):
        st.error(t("form.contact_invalid_phone", lang)); st.stop()

    # Si hay acompañantes, todos con nombre
    if st.session_state.comp_count > 0:
        vacios = [i for i, c in enumerate(companions_data, start=1) if not c["name"]]
        if vacios:
            st.error(t("form.companion_name_required", lang)); st.stop()
        companions_final = companions_data
    else:
        companions_final = []

    payload = {
        "attending": True,
        "allergies": (", ".join(titular_allergies) or None),
        "companions": companions_final,
        "notes": (msg_yes.strip() or None) if "msg_yes" in locals() else None,
        "email": email_clean or None,
        "phone": phone_clean or None,
    }

    with st.spinner(t("form.sending", lang)):
        _post_rsvp(payload)
