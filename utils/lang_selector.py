# utils/lang_selector.py
# =================================================================================
# 🌍 Selector de idioma con banderas. (Versión Final con render HTML)
# ---------------------------------------------------------------------------------
# - Renderiza las banderas como HTML (`<img>`) para un control total del estilo.
# - Soluciona el problema de alineación y el botón "fullscreen".
# - Mantiene toda la lógica de sesión y caché de la versión anterior.
# =================================================================================

import streamlit as st
from pathlib import Path
from typing import Dict, List, Optional
import base64
import io

# --- Configuración (sin cambios) ---
LANGS: List[str] = ["es", "en", "ro"]
NAMES: Dict[str, str] = {"es": "Español", "en": "English", "ro": "Română"}
EMOJI: Dict[str, str] = {"es": "🇨🇴", "en": "🇬🇧", "ro": "🇷🇴"}
FLAG_FILES: Dict[str, str] = {"es": "es.png", "en": "en.png", "ro": "ro.png"}

try:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    FLAGS_DIR = PROJECT_ROOT / "assets" / "flags"
except Exception:
    FLAGS_DIR = Path("assets") / "flags"

# --- Funciones Helper (adaptadas para Base64) ---

def image_to_base64(path: Path) -> str | None:
    """Convierte un archivo de imagen a una cadena de texto base64."""
    if not path.exists():
        return None
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def _load_flags_as_base64() -> Dict[str, Optional[str]]:
    """Carga las banderas como cadenas base64 y las cachea."""
    b64_images: Dict[str, Optional[str]] = {}
    for code in LANGS:
        b64_images[code] = image_to_base64(FLAGS_DIR / FLAG_FILES[code])
    return b64_images

def _normalize_lang(code: Optional[str], default: str = "es") -> str:
    """Normaliza un código a uno soportado; si no, devuelve default."""
    c = (code or "").strip().lower()
    return c if c in LANGS else default

def _read_query_lang() -> Optional[str]:
    """Lee ?lang=... desde la URL de forma segura."""
    try:
        return st.query_params.get("lang")
    except Exception:
        return None

# --- Render Principal (con st.markdown para las banderas) ---
def render_lang_selector(session_key: str = "lang") -> str:
    """Dibuja un selector de idioma visual y devuelve el código del idioma activo."""
    # 1) Lógica de determinación de idioma (IDÉNTICA A LA VERSIÓN ANTERIOR)
    query_lang = _read_query_lang()
    current = _normalize_lang(st.session_state.get(session_key) or query_lang or "es")
    st.session_state[session_key] = current
    
    # 2) Carga de imágenes (ahora como texto Base64)
    flags_b64 = _load_flags_as_base64()

    # 3) UI en columnas (IDÉNTICA A LA VERSIÓN ANTERIOR)
    cols = st.columns(len(LANGS))
    selected = None

    for idx, code in enumerate(LANGS):
        with cols[idx]:
            if st.button(NAMES[code], key=f"btn_{code}", use_container_width=True):
                selected = code
            
            # [CAMBIO] Se renderiza la bandera usando st.markdown en lugar de st.image
            flag_html = ""
            if flags_b64.get(code):
                # Si tenemos la imagen, la incrustamos como base64 en una etiqueta <img>
                flag_html = f'<img src="data:image/png;base64,{flags_b64[code]}" style="height: 24px; width: auto; border-radius: 4px;">'
            else:
                # El fallback a emoji se mantiene igual
                flag_html = f'<div style="font-size:24px;">{EMOJI[code]}</div>'
            
            # Se inyecta el HTML centrado
            st.markdown(f'<div style="display: flex; justify-content: center; margin-top: 6px;">{flag_html}</div>', unsafe_allow_html=True)

    # 4) Lógica de actualización de estado (IDÉNTICA A LA VERSIÓN ANTERIOR)
    if selected and selected != current:
        st.session_state[session_key] = selected
        try:
            st.query_params["lang"] = selected
        except Exception:
            pass
        st.rerun()

    # 5) Retorno del idioma activo (IDÉNTICO A LA VERSIÓN ANTERIOR)
    return st.session_state[session_key]