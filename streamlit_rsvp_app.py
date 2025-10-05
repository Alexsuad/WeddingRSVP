# streamlit_rsvp_app.py                                                      # Nombre del archivo principal de Streamlit (entrypoint de la app RSVP).
# =================================================================================
# 🚀 Punto de Entrada — App de Invitados (Streamlit Multipage)               # Descripción breve del rol del archivo.
# Rol: decidir destino según JWT en sesión y redirigir (Login ↔ Formulario). # Explica que decide a qué página navegar según haya token o no.
# Extras opcionales: botones de rescate si falla la navegación y logout por query. # Menciona utilidades adicionales disponibles.
# =================================================================================

# ================================================================
# 🌙 MAINTENANCE MODE (Controlled by environment variable)
# ================================================================
import os                                                                    # Reads environment variables like MAINTENANCE_MODE.
import streamlit as st                                                       # Used to build the user interface.

# If MAINTENANCE_MODE=1, show elegant maintenance notice and stop the app.
if os.getenv("MAINTENANCE_MODE") == "1":                                     # Checks if MAINTENANCE_MODE="1" to activate maintenance mode.
    st.set_page_config(                                                      # Configures metadata for maintenance mode.
        page_title="💍 Daniela & Cristian — Maintenance",                    # Browser tab title.
        page_icon="💍",                                                      # Tab icon (ring emoji).
        layout="centered"                                                    # Centers content for better presentation.
    )                                                                        # End of page configuration.

    st.markdown(                                                             # Injects HTML/CSS to display an elegant maintenance card.
        """
        <style>
          body { background:#fffaf7; }                                       /* Soft ivory background, coherent with main website. */
          .card{
            background:#ffffffee; border:1px solid #e9e1d8; border-radius:20px;
            padding:32px 26px; max-width:720px; margin:12vh auto; text-align:center;
            box-shadow:0 10px 30px rgba(0,0,0,.08);
          }
          h1{ font-family:serif; color:#5a4632; margin:.2em 0; }             /* Serif font and warm color tone. */
          p{ color:#3e3e3e; }                                                /* Soft gray text for readability. */
          .heart{ font-size:28px; color:#d4a373; }                           /* Golden accent for wedding theme. */
        </style>
        <div class="card">                                                   <!-- Central content card -->
          <div class="heart">💍</div>                                        <!-- Icon -->
          <h1>Daniela & Cristian</h1>                                        <!-- Couple's names -->
          <p>We are preparing a special experience for you.</p>              <!-- Main message -->
          <p><em>Please come back soon to confirm your attendance.</em></p>  <!-- Secondary message -->
        </div>
        """,                                                                 # Closes HTML/CSS block.
        unsafe_allow_html=True                                               # Allows HTML rendering in Streamlit.
    )                                                                        # End of markdown injection.

    st.stop()                                                                # Stops execution of the rest of the app while in maintenance.
# ================================================================
# End of maintenance mode
# ================================================================

st.set_page_config(                                                          # Configures metadata for the app when NOT in maintenance.
    page_title="RSVP • Daniela & Cristian",                                  # Consistent title for RSVP system.
    layout="centered",                                                       # Centered layout for better focus on forms.
    initial_sidebar_state="collapsed",                                       # Hides sidebar by default for clean UI.
)                                                                            # End of page configuration.

# --- Multipage routes (keep these names/locations in /pages) -----------------
LOGIN_PAGE = "pages/0_Login.py"                                              # Route to Login screen (requires API and token).
FORM_PAGE  = "pages/1_Formulario_RSVP.py"                                    # Route to protected RSVP form (requires valid token).
REQUEST_ACCESS_PAGE = "pages/00_Solicitar_Acceso.py"                         # Route to the "Request Access" page (entry flow).

# ==============================================================================
# ✅ Default language initialization logic
# ------------------------------------------------------------------------------
# Runs ONCE at session start:
# 1) Reads language from URL (?lang=...).
# 2) If absent, checks session state.
# 3) Defaults to 'en' (English) if not found.
# ------------------------------------------------------------------------------
try:
    query_lang = st.query_params.get("lang")                                 # Reads ?lang= from URL if available.
except Exception:
    query_lang = None                                                        # If error, no language in URL.

if "lang" not in st.session_state:                                           # Initializes only once per session.
    if query_lang in ["en", "es", "ro"]:                                     # Validates allowed languages.
        st.session_state["lang"] = query_lang                                # Uses the one from URL.
    else:
        st.session_state["lang"] = "en"                                      # Defaults to English.
# ==============================================================================

# --- (Optional) Logout by query param -----------------------------------------
try:
    if st.query_params.get("logout") in ("1", "true", "True"):               # If URL has ?logout=1/true → logs out.
        st.session_state.pop("token", None)                                  # Removes JWT (logs out user).
        st.session_state.pop("last_rsvp", None)                              # Clears last RSVP result.
        st.query_params.clear()                                              # Clears query params to avoid loops.
except Exception:
    pass                                                                     # Safe fail: do nothing if unsupported version.

# --- Destination decision -----------------------------------------------------
target_page = FORM_PAGE if st.session_state.get("token") else REQUEST_ACCESS_PAGE  # If token → Form; else → Request Access.

# --- Navigation with error handling -------------------------------------------
try:
    st.switch_page(target_page)                                              # Redirects to appropriate page.
except Exception:
    st.error(f"Unable to redirect to '{target_page}'.")                      # Clear error message if redirection fails.
    st.info("Make sure the file exists in the `pages/` folder with that name.")   # Helpful tip for developers.
    st.link_button("Go to Access Page", REQUEST_ACCESS_PAGE)                 # Rescue button for users.
    st.link_button("Go to RSVP Form", FORM_PAGE)                             # Another rescue option.
