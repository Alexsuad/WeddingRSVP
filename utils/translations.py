# utils/translations.py

from typing import Dict, List

DEFAULT_LANG: str = "en"
VALID_LANGS: List[str] = ["en", "es", "ro"]

LANG_DISPLAY: Dict[str, str] = {
    "en": "English (EN)",
    "es": "Español (ES)",
    "ro": "Română (RO)",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # --------------------------------------------------
    # Español
    # --------------------------------------------------
    "es": {
        # --- Menú ---
        "nav.login": "Iniciar Sesión",
        "nav.form": "Formulario RSVP",
        "nav.confirmed": "Confirmado",
        "nav.request": "Solicitar Acceso",
        "nav.recover": "Recuperar Código",

        # --- Login ---
        "login.title": "💍 Confirmar asistencia",
        "login.intro": "¡Qué alegría verte por aquí! Ingresa los datos de tu invitación para continuar.",
        "login.code": "Código de invitación",
        "login.contact": "Email o teléfono de contacto",
        "login.submit": "Acceder",
        "login.errors_empty": "Por favor, completa ambos campos.",
        "login.errors_auth": "Código de invitado, email o teléfono incorrectos.",
        "login.validating": "Validando…",
        "login.success": "¡Acceso concedido! Redirigiendo al formulario…",
        "login.forgot": "¿Olvidaste tu código? Haz clic aquí",

        # --- Formulario RSVP ---
        "form.hi": "Hola",
        "form.subtitle": "Confirma tu asistencia y cuéntanos algunos detalles ✨",
        "form.attending": "¿Asistirás?",
        "form.yes": "Sí",
        "form.no": "No",
        "form.titular_allergies": "Alergias o restricciones (titular)",
        "form.allergy_suggestions": "Sugerencias de alergias frecuentes",
        "form.companions_title": "Acompañantes",
        "form.companions_count": "¿Cuántas personas te acompañarán?",
        "form.companion_name": "Nombre del acompañante",
        "form.companion_is_child": "¿Es niño/niña?",
        "form.companion_allergies": "Alergias del acompañante",
        "form.other_allergy": "Otra alergia (opcional)",
        "form.notes_label": "¿Quieres dejarnos un mensaje? (opcional)",
        "form.notes_placeholder": "Ej.: Llegamos tarde, preferimos mesa tranquila, ¡felices por ustedes!…",
        "form.notes_hint": "Este espacio es para cualquier detalle que quieras compartir 😊",
        "form.submit": "Enviar respuesta",
        "form.sending": "Enviando…",
        "form.net_err": "No hay conexión con el servidor. Inténtalo de nuevo.",
        "form.over_quota": "Has superado el máximo de acompañantes permitidos.",
        "form.loading_guest": "Cargando tus datos…",
        "form.loading_meta": "Cargando sugerencias…",
        "form.server_err": "No se pudo enviar tu respuesta. Intenta de nuevo.",
        "form.session_expired": "Tu sesión ha expirado. Por favor, inicia sesión de nuevo.",
        "form.load_error": "Ocurrió un error al cargar tus datos.",
        "form.contact_title": "Datos de contacto",
        "form.contact_email": "Email",
        "form.contact_phone": "Teléfono (con código de país)",
        "form.contact_note": "Usaremos estos datos para enviarte la confirmación y recordatorios.",
        "form.contact_required_one": "Debes proporcionar al menos un email o un teléfono.",
        "form.contact_invalid_email": "El email no tiene un formato válido.",
        "form.contact_invalid_phone": "El teléfono debe incluir el código de país. Ej.: +573101234567",

        # --- Confirmado ---
        "ok.title": "✅ ¡Gracias por tu respuesta!",
        "ok.msg_no": "Sentiremos tu ausencia. Gracias por avisarnos con tiempo 💛",
        "ok.msg_yes": "¡Qué alegría que puedas acompañarnos! Hemos registrado tu confirmación 🎉",
        "ok.summary": "Tu resumen",
        "ok.main_guest": "Invitado principal",
        "ok.adults_children": "Acompañantes (adultos/niños)",
        "ok.allergies": "Alergias",
        "ok.companions": "Acompañantes",
        "ok.child": "Niño/niña",
        "ok.adult": "Adulto",
        "ok.alrg_item": "Alergias",
        "ok.btn_edit": "✏️ Editar mi respuesta",
        "ok.btn_logout": "🚪 Cerrar sesión",
        "ok.load_error": "No se pudo cargar el resumen de tu respuesta.",
        "ok.btn_resend_email": "Reenviar correo de confirmación",
        "ok.sending": "Enviando…",
        "ok.resent_ok": "Listo, revisa tu bandeja.",
        "ok.resent_fail": "No se pudo enviar ahora. Intenta más tarde.",

        # --- Recuperar Código ---
        "recover.title": "Recuperar tu código",
        "recover.subtitle": "Ingresa tu email o teléfono usado en la invitación. Si estás en la lista, te enviaremos un mensaje.",
        "recover.email": "Email (opcional)",
        "recover.phone": "Teléfono (opcional)",
        "recover.submit": "Solicitar recuperación",
        "recover.success": "Si tu contacto está en la lista de invitados, recibirás un mensaje en breve.",
        "recover.rate_limited": "Has realizado demasiados intentos. Inténtalo nuevamente en ~{retry}.",
        "recover.invalid": "Solicitud inválida. Verifica los datos e inténtalo de nuevo.",
        "recover.generic": "No pudimos procesar la solicitud en este momento. Inténtalo más tarde.",
        "recover.network": "No hay conexión con el servidor. Detalle: {err}",
        "recover.back": "⬅️ Volver al inicio",
        "recover.go_rsvp": "Ir al formulario RSVP",

        # --- Solicitar Acceso ---
        "request.title": "🔑 Solicita tu acceso",
        "request.intro": "Para identificarte, cuéntanos tu nombre, los últimos 4 dígitos de tu teléfono y el correo donde quieres recibir tu enlace de acceso.",
        "request.full_name": "Nombre completo (como aparece en la invitación)",
        "request.phone_last4": "Últimos 4 dígitos de tu teléfono",
        "request.phone_last4_placeholder": "Ej.: 5678",
        "request.email": "Correo electrónico",
        "request.submit": "Enviar enlace de acceso",
        "request.consent": "Acepto recibir comunicaciones sobre la boda por correo electrónico.",
        "request.success": "¡Listo! Te enviamos un enlace a tu correo. Revisa tu bandeja (y Spam/Promociones).",
        "request.error": "No pudimos procesar tu solicitud. Verifica tus datos e intenta de nuevo.",
        "request.resend": "¿No recibiste el correo? Haz clic aquí para reenviar.",
        "request.invalid_email": "El correo no parece válido.",
        "request.invalid_phone4": "Debes introducir exactamente 4 números.",

        # --- Invitación (badge) ---
        "invite.panel_title": "Tu invitación",
        "invite.scope.full": "Estás invitado a la Ceremonia y a la Recepción.",
        "invite.scope.reception": "Estás invitado solo a la Recepción.",
        "invite.times.hint": "Horarios: Ceremonia {ceremony_time} · Recepción {reception_time}",
    },

    # --------------------------------------------------
    # Română
    # --------------------------------------------------
    "ro": {
        # --- Meniu ---
        "nav.login": "Autentificare",
        "nav.form": "Formular RSVP",
        "nav.confirmed": "Confirmat",
        "nav.request": "Solicită Acces",
        "nav.recover": "Recuperează Codul",

        # --- Login ---
        "login.title": "💍 Confirmă prezența",
        "login.intro": "Ne bucurăm că ești aici! Introdu datele invitației pentru a continua.",
        "login.code": "Cod invitație",
        "login.contact": "Email sau telefon",
        "login.submit": "Continuă",
        "login.errors_empty": "Te rugăm să completezi ambele câmpuri.",
        "login.errors_auth": "Cod, email sau telefon incorecte.",
        "login.validating": "Se validează…",
        "login.success": "Acces permis! Redirecționare către formular…",
        "login.forgot": "Ți-ai uitat codul? Click aici",

        # --- Formular RSVP ---
        "form.hi": "Salut",
        "form.subtitle": "Confirmă prezența și spune-ne câteva detalii ✨",
        "form.attending": "Vei participa?",
        "form.yes": "Da",
        "form.no": "Nu",
        "form.titular_allergies": "Alergii sau restricții (titular)",
        "form.allergy_suggestions": "Sugestii de alergii frecvente",
        "form.companions_title": "Însoțitori",
        "form.companions_count": "Câți însoțitori te vor însoți?",
        "form.companion_name": "Numele însoțitorului",
        "form.companion_is_child": "Este copil?",
        "form.companion_allergies": "Alergii însoțitor",
        "form.other_allergy": "Altă alergie (opțional)",
        "form.notes_label": "Vrei să ne lași un mesaj? (opțional)",
        "form.notes_placeholder": "Ex.: Venim mai târziu, preferăm o masă liniștită, suntem tare bucuroși pentru voi!…",
        "form.notes_hint": "Spațiu pentru orice detaliu dorești să împărtășești 😊",
        "form.submit": "Trimite răspunsul",
        "form.sending": "Se trimite…",
        "form.net_err": "Nu se poate contacta serverul. Încearcă din nou.",
        "form.over_quota": "Ai depășit numărul maxim de însoțitori.",
        "form.loading_guest": "Se încarcă datele tale…",
        "form.loading_meta": "Se încarcă sugestiile…",
        "form.server_err": "Nu s-a putut trimite răspunsul. Încearcă din nou.",
        "form.session_expired": "Sesiunea ta a expirat. Te rugăm să te autentifici din nou.",
        "form.load_error": "A apărut o eroare la încărcarea datelor.",
        "form.contact_title": "Date de contact",
        "form.contact_email": "Email",
        "form.contact_phone": "Telefon (cu prefix internațional)",
        "form.contact_note": "Vom folosi aceste date pentru confirmare și remindere.",
        "form.contact_required_one": "Te rugăm să oferi cel puțin un email sau un telefon.",
        "form.contact_invalid_email": "Formatul adresei de email nu este valid.",
        "form.contact_invalid_phone": "Telefonul trebuie să includă prefixul internațional. Ex.: +40722123456",

        # --- Confirmat ---
        "ok.title": "✅ Îți mulțumim pentru răspuns!",
        "ok.msg_no": "Ne pare rău că nu poți participa. Mulțumim că ne-ai anunțat din timp 💛",
        "ok.msg_yes": "Ne bucurăm că poți fi alături de noi! Ți-am înregistrat confirmarea 🎉",
        "ok.summary": "Rezumatul tău",
        "ok.main_guest": "Invitat principal",
        "ok.adults_children": "Însoțitori (adulți/copii)",
        "ok.allergies": "Alergii",
        "ok.companions": "Însoțitori",
        "ok.child": "Copil",
        "ok.adult": "Adult",
        "ok.alrg_item": "Alergii",
        "ok.btn_edit": "✏️ Editează răspunsul",
        "ok.btn_logout": "🚪 Deconectare",
        "ok.load_error": "Nu s-a putut încărca rezumatul răspunsului.",
        "ok.btn_resend_email": "Retrimite emailul de confirmare",
        "ok.sending": "Se trimite…",
        "ok.resent_ok": "Gata, verifică-ți inboxul.",
        "ok.resent_fail": "Nu s-a putut trimite acum. Încearcă mai târziu.",

        # --- Recover ---
        "recover.title": "Recuperează-ți codul",
        "recover.subtitle": "Introdu emailul sau telefonul folosit în invitație. Dacă ești în listă, vei primi un mesaj.",
        "recover.email": "Email (opțional)",
        "recover.phone": "Telefon (opțional)",
        "recover.submit": "Solicită recuperarea",
        "recover.success": "Dacă datele tale se află în lista de invitați, vei primi în curând un mesaj.",
        "recover.rate_limited": "Prea multe încercări. Încearcă din nou peste ~{retry}.",
        "recover.invalid": "Cerere invalidă. Verifică datele și încearcă din nou.",
        "recover.generic": "Nu am putut procesa cererea acum. Încearcă mai târziu.",
        "recover.network": "Nu se poate contacta serverul. Detalii: {err}",
        "recover.back": "⬅️ Înapoi la început",
        "recover.go_rsvp": "Mergi la formularul RSVP",

        # --- Request Access ---
        "request.title": "🔑 Solicită accesul",
        "request.intro": "Pentru identificare, te rugăm să indici numele tău, ultimele 4 cifre ale telefonului și adresa de email unde vrei să primești linkul de acces.",
        "request.full_name": "Nume complet (așa cum apare pe invitație)",
        "request.phone_last4": "Ultimele 4 cifre ale telefonului",
        "request.phone_last4_placeholder": "Ex.: 5678",
        "request.email": "Adresă de email",
        "request.submit": "Trimite linkul de acces",
        "request.consent": "Sunt de acord să primesc comunicări despre nuntă prin email.",
        "request.success": "Gata! Ți-am trimis un link pe email. Verifică-ți inboxul (și Spam/Promotions).",
        "request.error": "Nu am putut procesa cererea. Verifică datele și încearcă din nou.",
        "request.resend": "Nu ai primit emailul? Click aici pentru re-trimitere.",
        "request.invalid_email": "Adresa de email nu pare validă.",
        "request.invalid_phone4": "Trebuie să introduci exact 4 cifre.",

        # --- Invitație (badge) ---
        "invite.panel_title": "Invitația ta",
        "invite.scope.full": "Ești invitat la ceremonie și la recepție.",
        "invite.scope.reception": "Ești invitat doar la recepție.",
        "invite.times.hint": "Program: Ceremonie {ceremony_time} · Recepție {reception_time}",
    },

    # --------------------------------------------------
    # English
    # --------------------------------------------------
    "en": {
        # --- Menu ---
        "nav.login": "Login",
        "nav.form": "RSVP Form",
        "nav.confirmed": "Confirmed",
        "nav.request": "Request Access",
        "nav.recover": "Recover Code",

        # --- Login ---
        "login.title": "💍 Confirm attendance",
        "login.intro": "So happy you’re here! Enter your invitation details to continue.",
        "login.code": "Invitation code",
        "login.contact": "Email or phone",
        "login.submit": "Continue",
        "login.errors_empty": "Please complete both fields.",
        "login.errors_auth": "Invalid code, email, or phone.",
        "login.validating": "Validating…",
        "login.success": "Access granted! Redirecting to the form…",
        "login.forgot": "Forgot your code? Click here",

        # --- RSVP Form ---
        "form.hi": "Hi",
        "form.subtitle": "Confirm your attendance and share a few details ✨",
        "form.attending": "Will you attend?",
        "form.yes": "Yes",
        "form.no": "No",
        "form.titular_allergies": "Allergies or restrictions (main guest)",
        "form.allergy_suggestions": "Frequent allergy suggestions",
        "form.companions_title": "Companions",
        "form.companions_count": "How many companions will join you?",
        "form.companion_name": "Companion name",
        "form.companion_is_child": "Is a child?",
        "form.companion_allergies": "Companion allergies",
        "form.other_allergy": "Other allergy (optional)",
        "form.notes_label": "Want to leave us a note? (optional)",
        "form.notes_placeholder": "E.g., We might arrive late, we prefer a quiet table, so happy for you!…",
        "form.notes_hint": "Use this space for anything you’d like to share 😊",
        "form.submit": "Send response",
        "form.sending": "Sending…",
        "form.net_err": "Cannot reach the server. Please try again.",
        "form.over_quota": "You exceeded your companions quota.",
        "form.loading_guest": "Loading your data…",
        "form.loading_meta": "Loading suggestions…",
        "form.server_err": "Could not send your response. Please try again.",
        "form.session_expired": "Your session has expired. Please log in again.",
        "form.load_error": "An error occurred while loading your data.",
        "form.contact_title": "Contact details",
        "form.contact_email": "Email",
        "form.contact_phone": "Phone (with country code)",
        "form.contact_note": "We’ll use these details to send your confirmation and reminders.",
        "form.contact_required_one": "Please provide at least an email or a phone number.",
        "form.contact_invalid_email": "Email format looks invalid.",
        "form.contact_invalid_phone": "Phone must include the country code. E.g., +447911123456",

        # --- Confirmed ---
        "ok.title": "✅ Thanks for your response!",
        "ok.msg_no": "We’ll miss you. Thanks for letting us know 💛",
        "ok.msg_yes": "We’re happy you can join! Your confirmation has been recorded 🎉",
        "ok.summary": "Your summary",
        "ok.main_guest": "Main guest",
        "ok.adults_children": "Companions (adults/children)",
        "ok.allergies": "Allergies",
        "ok.companions": "Companions",
        "ok.child": "Child",
        "ok.adult": "Adult",
        "ok.alrg_item": "Allergies",
        "ok.btn_edit": "✏️ Edit my response",
        "ok.btn_logout": "🚪 Log out",
        "ok.load_error": "Could not load the summary of your response.",
        "ok.btn_resend_email": "Resend confirmation email",
        "ok.sending": "Sending…",
        "ok.resent_ok": "Done, check your inbox.",
        "ok.resent_fail": "Couldn't send right now. Try again later.",

        # --- Recover ---
        "recover.title": "Recover your code",
        "recover.subtitle": "Enter the email or phone used in your invitation. If you’re on the list, we’ll send you a message.",
        "recover.email": "Email (optional)",
        "recover.phone": "Phone (optional)",
        "recover.submit": "Request recovery",
        "recover.success": "If your contact is on our guest list, you’ll receive a message shortly.",
        "recover.rate_limited": "Too many attempts. Try again in ~{retry}.",
        "recover.invalid": "Invalid request. Please check the data and try again.",
        "recover.generic": "We couldn’t process your request right now. Please try again later.",
        "recover.network": "Cannot reach the server. Details: {err}",
        "recover.back": "⬅️ Back to home",
        "recover.go_rsvp": "Go to RSVP form",

        # --- Request Access ---
        "request.title": "🔑 Request your access",
        "request.intro": "To identify you, please share your full name, the last 4 digits of your phone, and the email where you’d like to receive your access link.",
        "request.full_name": "Full name (as on the invitation)",
        "request.phone_last4": "Last 4 digits of your phone",
        "request.phone_last4_placeholder": "E.g., 5678",
        "request.email": "Email address",
        "request.submit": "Send access link",
        "request.consent": "I agree to receive wedding communications by email.",
        "request.success": "Done! We’ve sent a link to your email. Check your inbox (and Spam/Promotions).",
        "request.error": "We couldn’t process your request. Please verify your details and try again.",
        "request.resend": "Didn’t get the email? Click here to resend.",
        "request.invalid_email": "The email doesn’t look valid.",
        "request.invalid_phone4": "You must enter exactly 4 digits.",

        # --- Invitation (badge) ---
        "invite.panel_title": "Your invitation",
        "invite.scope.full": "You’re invited to the Ceremony and the Reception.",
        "invite.scope.reception": "You’re invited to the Reception only.",
        "invite.times.hint": "Times: Ceremony {ceremony_time} · Reception {reception_time}",
    },
}

def normalize_lang(lang: str | None) -> str:
    code = (lang or "").lower().strip()
    return code if code in VALID_LANGS else DEFAULT_LANG

def t(key: str, lang: str | None = None) -> str:
    code = normalize_lang(lang or DEFAULT_LANG)
    bundle = TRANSLATIONS.get(code, TRANSLATIONS[DEFAULT_LANG])
    return bundle.get(key, key)
