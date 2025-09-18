# utils/nav.py
# =================================================================================
# 🧭 Menú propio traducible para apps multipage en Streamlit.
# - Oculta el sidebar nativo (que no es traducible) con CSS.
# - Dibuja enlaces traducidos con st.page_link() (requiere Streamlit reciente).
# - Si no hay st.page_link, usa botones link como fallback.
# =================================================================================

import streamlit as st
from typing import Dict

def hide_native_sidebar_nav() -> None:
    """
    Oculta la navegación multipage nativa del sidebar, sin asumir estructura
    exacta (distintas versiones de Streamlit cambian data-testid/markup).
    """
    st.markdown(
        """
        <style>
        /* Oculta el bloque de navegación multipage nativo (varias variantes) */
        section[data-testid="stSidebarNav"],
        div[data-testid="stSidebarNav"],
        nav[aria-label="Main menu"],
        nav[aria-label="Sidebar navigation"] {
            display: none !important;
        }

        /* Oculta títulos "residuales" que suele dejar la nav nativa */
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] hr {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_nav(labels: Dict[str, str]) -> None:                                            # Define la función que dibuja el menú lateral.
    """
    Dibuja un pequeño menú propio en el sidebar con labels traducidos.                      # Docstring: explica qué hace la función.
    `labels` debe mapear ruta_de_script → texto, respetando el orden de inserción.         # Aclara el formato esperado del diccionario.
    Ejemplo:
        {
            "pages/00_Solicitar_Acceso.py": "Solicitar Acceso",                             # Primera entrada del menú.
            "pages/01_Recuperar_Codigo.py": "Recuperar Código",                             # Segunda entrada del menú.
            "pages/0_Login.py": "Iniciar Sesión",                                           # Tercera entrada del menú.
            "pages/1_Formulario_RSVP.py": "Formulario RSVP",                                # Cuarta entrada del menú.
            "pages/2_Confirmado.py": "Confirmado",                                          # Quinta entrada del menú.
        }
    """                                                                                     # Fin del docstring.

    if not labels:                                                                          # Verifica si el diccionario está vacío o es None.
        return                                                                              # Si no hay items, no dibuja nada y sale.

    with st.sidebar:                                                                        # Abre el contexto del sidebar para renderizar dentro.
        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)            # Inserta un separador vertical compacto (espaciado).

        has_page_link = hasattr(st, "page_link")                                            # Detecta de forma segura si existe st.page_link (versiones nuevas).
        for path, text in labels.items():                                                   # Itera por las rutas (keys) y etiquetas (values) en orden de inserción.
            if has_page_link:                                                               # Si la API moderna st.page_link está disponible...
                st.page_link(path, label=text)                                              # ...crea un enlace nativo a la página (ruta del script).
            else:                                                                           # Si no está disponible (versiones más antiguas)...
                # Fallback: usa un botón que internamente hace switch_page hacia la ruta.   # Comentario: explica el plan B.
                st.button(                                                                  # Crea un botón clickable en el sidebar.
                    text,                                                                   # Etiqueta del botón con el texto recibido.
                    on_click=lambda p=path: st.switch_page(p),                              # Callback: cambia de página usando la ruta del script.
                    use_container_width=True,                                               # Estira el botón al ancho del contenedor para mejor UX.
                )                                                                           # Cierra el botón.
