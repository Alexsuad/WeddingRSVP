# utils/ui.py
# =============================================================================
# Utilidades de UI compartidas (solo presentación visual, sin lógica de negocio)
# - Estilos globales (fondo, tipografías, botones, limpieza del <form>)
# - Menú superior opcional (no usar en este proyecto, queda oculto por CSS)
# - Menú lateral flotante (derecha por defecto) con versión responsive
# - Script anti “inputs fantasma” de Streamlit
# =============================================================================

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# 1) Estilos globales (tema visual + limpieza de formularios)
# ─────────────────────────────────────────────────────────────────────────────
def apply_global_styles() -> None:
    """
    Inyecta CSS global coherente:
    - Fondo con imagen suavizada, tipografías y tokens visuales.
    - Botones primarios y outline unificados.
    - Oculta header/sidebar nativos para un lienzo limpio.
    - Elimina estilos de <form> que generan “cajas fantasma”.
    - Kill-switch para ocultar cualquier menú centrado .top-nav residual.
    """
    st.markdown(
        """
        <style>
          /* ===== Tipografías y tokens ===== */
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:wght@600;700&display=swap');
          :root{
            --bg:#FFFFFF; --text:#111111; --muted:#666666; --primary:#0F0F0F;
            --shadow:0 10px 35px rgba(0,0,0,.08); --radius:12px;
          }

          /* ===== Lienzo base ===== */
          .stApp{
            background-image:
              linear-gradient(rgba(255,255,255,.9), rgba(255,255,255,.9)),
              url('https://images.unsplash.com/photo-1515934751635-c81c6bc9a2d8?auto=format&fit=crop&q=80&w=2070');
            background-size: cover;
            background-position: center center;
          }
          [data-testid="stHeader"]{ display:none; }
          [data-testid="stSidebar"]{ display:none !important; }
          [data-testid="stSidebarCollapsedControl"]{ display:none !important; }
          html, body, [class*="block-container"]{ font-family:'Inter', sans-serif; }
          h1, h2, h3{ font-family:'Playfair Display', serif !important; font-weight:700; }

          /* ===== Botones ===== */
          /* Outline (idiomas, secundarios) */
          .stButton > button:not([kind="primary"]){
            background:#FFFFFF !important; color:#111111 !important;
            border:1px solid #E5E5E5 !important; border-radius:8px !important;
            font-weight:600 !important; transition:all .2s ease !important;
          }
          .stButton > button:not([kind="primary"]):hover{
            background:#F5F5F5 !important;
          }

          /* Primario (acción principal) */
          .stButton > button[kind="primary"],
          button[data-testid="baseButton-primary"]{
            background:#0F0F0F !important; color:#FFFFFF !important; border:none !important;
            border-radius:10px !important; padding:10px 16px !important;
            box-shadow:0 1px 2px rgba(0,0,0,.06) !important;
            transition:transform .02s ease, opacity .2s ease !important;
          }
          .stButton > button[kind="primary"]:hover,
          button[data-testid="baseButton-primary"]:hover{
            filter:brightness(.9) !important;
          }

          /* ===== Limpieza de formularios (evita “caja fantasma”) ===== */
          form[data-testid="stForm"],
          form[data-testid="stForm"] > div{
            background:transparent !important; border:none !important;
            box-shadow:none !important; padding:0 !important;
          }

          /* ===== Kill-switch temporal: oculta cualquier menú centrado residual ===== */
          .top-nav{ display:none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2) Menú superior horizontal (opcional, NO usar aquí)
#    *Se deja por si alguna página futura lo necesitara. Está oculto por CSS.*
# ─────────────────────────────────────────────────────────────────────────────
def render_top_nav(t, lang: str, home_url: str = "https://suarezsiicawedding.com/") -> None:
    """
    Renderiza un menú horizontal simple (Home / Solicitar Acceso / Login).
    Nota: en este proyecto permanece oculto por el kill-switch .top-nav.
    """
    home_label    = (t("nav.home", lang)    if callable(t) else "Home")
    request_label = (t("nav.request", lang) if callable(t) else "Request Access")
    login_label   = (t("nav.login", lang)   if callable(t) else "Login")

    st.markdown(
        """
        <style>
          .top-nav{
            display:flex; justify-content:center; gap:12px; margin:12px 0 0 0;
          }
          .top-nav a{
            background:#FFF; color:#111; text-decoration:none; border:1px solid #E5E5E5;
            border-radius:8px; font-weight:600; padding:.55rem .9rem; transition:all .2s;
          }
          .top-nav a:hover{ background:#F5F5F5; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="top-nav">
          <a href="{home_url}" target="_self">🏠 {home_label}</a>
          <a href="/Solicitar_Acceso" target="_self">🔑 {request_label}</a>
          <a href="/Login" target="_self">🔒 {login_label}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3) Menú lateral flotante (derecha por defecto) + responsive
# ─────────────────────────────────────────────────────────────────────────────
def render_side_nav(  # Define la función para dibujar el menú lateral
    t,  # Función de traducciones (t(key, lang))
    lang: str,  # Idioma activo
    home_url: str = "https://suarezsiicawedding.com/",  # URL del Home
    position: str = "left",  # Posición del menú: 'right' o 'left'
    side_offset_px: int = 300,  # Separación respecto al borde (acercar/alejar del margen)
    hide: list[str] | None = None,  # Ítems a ocultar: "home","request","login","recover"
    show_emojis: bool = True,  # Si False, se ocultan los emojis del menú
) -> None:
    """Menú lateral flotante con Home / Solicitar Acceso / Login / Recuperar Código, responsive y configurable."""  # Docstring descriptivo
    hide = set(hide or [])  # Convierte hide en set para comprobar pertenencia de forma eficiente

    # ---- Etiquetas traducidas con fallback seguro ----
    def _fallback_home(l: str) -> str:  # Función interna que da texto por defecto de Home si faltara traducción
        return {"es": "Inicio", "en": "Home", "ro": "Acasă"}.get(l, "Home")  # Devuelve por idioma o "Home"

    home_label = t("nav.home", lang) if callable(t) else _fallback_home(lang)  # Texto de Home
    request_label = t("nav.request", lang) if callable(t) else "Solicitar acceso"  # Texto de Solicitar Acceso
    login_label = t("nav.login", lang) if callable(t) else "Iniciar sesión"  # Texto de Iniciar sesión
    recover_label = t("nav.recover", lang) if callable(t) else "Recuperar Código"  # Texto de Recuperar Código

    # ---- Cálculo de posición y empuje del contenido en desktop ----
    pos = (position or "right").lower().strip()  # Normaliza el parámetro de posición
    side = "right" if pos == "right" else "left"  # Determina el lado final ('right' o 'left')
    side_rule = f"{side}:{int(side_offset_px)}px;"  # Construye la regla CSS para el offset lateral
    push_rule = (  # Define el padding del contenedor principal para que el menú no tape contenido
        ".main .block-container{ padding-right: 140px !important; }"  # Empuje cuando el menú está a la derecha
        if side == "right"
        else ".main .block-container{ padding-left: 140px !important; }"  # Empuje cuando está a la izquierda
    )

    # ---- CSS extra para ocultar emojis cuando show_emojis=False ----
    extra_css = "" if show_emojis else ".side-nav .menu-emoji{display:none;}"  # Regla que esconde los emojis

    # ---- Construcción de los enlaces (TODOS como f-strings) ----
    links_html = []  # Lista que almacenará cada <a> ya montado

    if "home" not in hide:  # Si no se debe ocultar Home
        links_html.append(  # Añade el enlace de Home
            f'<a class="menu-link" href="{home_url}" target="_self">'  # Abre el <a> hacia Home
            f'<span class="menu-emoji">🏠</span><span>{home_label}</span></a>'  # Contenido con emoji + etiqueta
        )

    if "request" not in hide:  # Si no se debe ocultar Solicitar Acceso
        links_html.append(  # Añade el enlace de Request
            f'<a class="menu-link" href="/Solicitar_Acceso" target="_self">'  # Abre el <a> hacia la página de solicitud
            f'<span class="menu-emoji">🔑</span><span>{request_label}</span></a>'  # Contenido con emoji + etiqueta
        )

    if "login" not in hide:  # Si no se debe ocultar Login
        links_html.append(  # Añade el enlace de Login
            f'<a class="menu-link" href="/Login" target="_self">'  # Abre el <a> hacia Login
            f'<span class="menu-emoji">🔒</span><span>{login_label}</span></a>'  # Contenido con emoji + etiqueta
        )

    if "recover" not in hide:  # Si no se debe ocultar Recuperar Código
        links_html.append(  # Añade el enlace de Recuperar
            f'<a class="menu-link" href="/Recuperar_Codigo" target="_self">'  # Abre el <a> hacia Recuperar Código
            f'<span class="menu-emoji">🧾</span><span>{recover_label}</span></a>'  # Contenido con emoji + etiqueta
        )

    # Une todos los enlaces en un solo string sin introducir literales ni placeholders
    links_block = "".join(links_html)  # Concatena los <a> ya formateados

    # ---- Inyección final de CSS + HTML del menú ----
    st.markdown(  # Inserta CSS y HTML del menú en la página
        f"""
        <style>  /* Bloque de estilos del menú lateral */
          .side-nav {{ position: fixed; top: 200px; {side_rule} z-index: 100; }}  /* Posición fija y offset lateral */
          .side-nav .menu-card {{  /* Tarjeta contenedora de los enlaces */
            background:#FFFFFF; border:1px solid #EEE; border-radius:12px;
            box-shadow: var(--shadow); padding:12px; display:flex;
            flex-direction:column; gap:12px;
          }}
          .side-nav .menu-link {{  /* Estilo de cada enlace del menú */
            display:flex; align-items:center; gap:.5rem;
            background:#FFF; color:#111; text-decoration:none;
            border:1px solid #E5E5E5; border-radius:8px;
            font-weight:600; padding:.55rem .9rem; transition:all .2s;
          }}
          .side-nav .menu-link:hover {{ background:#F5F5F5; }}  /* Hover sutil */
          .side-nav .menu-link:focus {{ outline:2px solid rgba(15,15,15,.35); outline-offset:2px; }}  /* Accesibilidad foco */
          .side-nav .menu-link:active {{ transform:translateY(1px); }}  /* Feedback al click */
          .side-nav .menu-emoji {{ width:1.1rem; text-align:center; }}  /* Caja fija para alinear emojis */
          @media (min-width: 1100px) {{ {push_rule} }}  /* Empuje en escritorio para no tapar contenido */
          @media (max-width: 1099px) {{  /* Comportamiento responsive: barra superior */
            .side-nav {{ position: static; margin: 8px auto 0 auto; }}  /* Quita posición fija en móvil */
            .side-nav .menu-card {{
              flex-direction: row; justify-content: center;
              padding: 8px; gap: 8px; box-shadow: none; border-radius: 10px;
            }}
          }}
          {extra_css}  /* Regla opcional para ocultar emojis */
        </style>

        <nav class="side-nav">  <!-- Contenedor del menú -->
          <div class="menu-card">  <!-- Tarjeta con los botones -->
            {links_block}  <!-- Inserta aquí todos los <a> ya formateados -->
          </div>
        </nav>
        """,  # Cierra el bloque HTML/CSS
        unsafe_allow_html=True,  # Permite renderizar HTML sin escape
    )  # Fin de st.markdown

# ─────────────────────────────────────────────────────────────────────────────
# 4) Script anti “inputs fantasma” (limpieza visual proactiva)
# ─────────────────────────────────────────────────────────────────────────────
def inject_ghost_killer(form_id: str = "request") -> None:
    """
    Oculta cualquier TextInput “fantasma” que Streamlit pueda renderizar antes
    de los campos válidos (según etiquetas esperadas por idioma).
    """
    st.markdown(
        f"""
        <script>
          (function () {{
            try {{
              const root = document.getElementById('{form_id}');
              if (!root) return;

              const WHITELIST = new Set([
                /* Español */ "Tu nombre completo","Últimos 4 dígitos de tu teléfono","Correo electrónico",
                /* English */ "Full name","Last 4 digits of your phone","Email","Email address",
                /* Română  */ "Numele complet","Ultimele 4 cifre ale telefonului","E-mail","Email"
              ]);

              const hideGhosts = () => {{
                const inputs = root.querySelectorAll('div[data-testid="stTextInputRoot"]');
                inputs.forEach(el => {{
                  const label = el.querySelector('label');
                  const txt = (label && label.textContent || "").trim();
                  if (!WHITELIST.has(txt)) el.style.display = "none";
                }});
              }};

              hideGhosts();
              new MutationObserver(hideGhosts).observe(root, {{ childList: true, subtree: true }});
            }} catch (e) {{ /* silencioso */ }}
          }})();
        </script>
        """,
        unsafe_allow_html=True,
    )
