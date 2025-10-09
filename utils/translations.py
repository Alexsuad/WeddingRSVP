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
    # ==================================================
    # Español — tono cálido y cercano (alineado con WP)
    # ==================================================
    "es": {
        # --- Menú ---
        "nav.login": "Iniciar sesión",
        "nav.form": "Formulario RSVP",
        "nav.confirmed": "Confirmado",
        "nav.request": "Solicitar Acceso",
        "nav.recover": "Recuperar Código",

        # --- Login ---
        "login.title": "💍 Confirmar asistencia",
        "login.intro": "¡Qué alegría tenerte aquí! Ingresa los datos de tu invitación para continuar.",
        "login.code": "Código de invitación",
        "login.contact": "Email o teléfono de contacto",
        "login.submit": "Acceder",
        "login.errors_empty": "Por favor, completa ambos campos.",
        "login.errors_auth": "Código, email o teléfono no coinciden.",
        "login.validating": "Validando…",
        "login.success": "¡Listo! Te llevamos al formulario…",
        "login.forgot": "¿Olvidaste tu código? Haz clic aquí",
        "login.server_err": "No pudimos validar en este momento. Inténtalo de nuevo en unos segundos.",

        # --- Solicitar Acceso ---
        "request.title": "🔑 Solicita tu acceso",
        "request.intro": "Para identificarte, indícanos tu nombre completo, los últimos 4 dígitos de tu teléfono y el email donde quieres recibir tu enlace.",
        "request.full_name": "Tu nombre completo",
        "request.phone_last4": "Últimos 4 dígitos de tu teléfono",
        "request.phone_last4_placeholder": "Ej.: 5678",
        "request.email": "Correo electrónico",
        "request.submit": "Solicitar acceso",
        "request.consent": "Acepto recibir comunicaciones de la boda por correo electrónico.",
        "request.success": "¡Listo! Te enviamos un enlace a tu correo. Revisa tu bandeja (y Spam/Promociones).",
        "request.error": "No pudimos procesar tu solicitud. Verifica los datos e inténtalo de nuevo.",
        "request.resend": "¿No te llegó el correo? Haz clic aquí para reenviar.",
        "request.invalid_email": "El email no parece válido.",
        "request.invalid_phone4": "Debes ingresar exactamente 4 dígitos.",
        "request.success_message_neutral": "Si los datos coinciden con tu invitación, recibirás un enlace en tu correo. Revisa tu bandeja de entrada y también Spam/Promociones.",
        "request.invalid_name": "El nombre debe tener al menos 3 caracteres.",
        "request.consent_required": "Debes aceptar el consentimiento para continuar.",

        # --- Formulario RSVP ---
        "form.hi": "Hola",
        "form.subtitle": "Confirma tu asistencia y cuéntanos algunos detalles ✨",
        "form.attending": "¿Asistirás?",
        "form.yes": "Sí",
        "form.no": "No",
        "form.select_option": "Elige una opción para continuar.",
        "form.no_attend_short": "Gracias por avisarnos. ¡Te echaremos de menos! 😔",
        "form.generic_error": "Ocurrió un error al guardar tu respuesta. Inténtalo más tarde.",
        "form.sending": "Enviando…",
        "form.submit": "Enviar respuesta",
        "form.cancel": "Cancelar",
        "form.net_err": "No pudimos contactar el servidor. Inténtalo de nuevo.",
        "form.session_expired": "Tu sesión ha expirado. Por favor, inicia sesión otra vez.",
        "form.load_error": "No pudimos cargar tus datos en este momento.",

        # --- Invitación / horarios ---
        "form.invite_title": "Tu invitación",
        "form.invite_full_access": "Estás invitada/o a la **Ceremonia** y a la **Recepción**. ¡Nos hace muy felices compartir este día contigo! 🕊️",
        "form.invite_reception_only": "Estás invitada/o a la **Recepción**. ¡Será un gusto celebrar juntos! 🎉",
        "form.time_ceremony": "Ceremonia",
        "form.time_reception": "Recepción",
        "form.accomp_note": "Puedes traer **hasta {max_accomp} acompañante{plural}**.",

        # --- Contacto ---
        "form.contact_title": "Datos de contacto",
        "form.contact_caption": "Usaremos estos datos para enviarte la confirmación y recordatorios. 💌",
        "form.field_email": "Email",
        "form.field_phone": "Teléfono (Ej: +573101234567)",
        "form.contact_required_one": "Por favor, proporciona al menos un email o un teléfono.",
        "form.contact_invalid_email": "El formato del email no es válido.",
        "form.contact_invalid_phone": "El teléfono debe incluir el código de país. Ej.: +573101234567",

        # --- Alergias (titular) ---
        "form.titular_allergies": "Alergias o restricciones (titular)",
        "form.allergies_caption": "Cuéntanos si hay algo que debamos tener en cuenta para cuidar de ti. 💙",
        "form.allergies_or_restrictions": "Alergias o restricciones",

        # --- Acompañantes ---
        "form.companions_title": "Acompañantes",
        "form.companions_db_note": "La cantidad de acompañantes permitidos depende de tu invitación.",
        "form.no_companions_info": "Tu invitación no incluye acompañantes.",
        "form.bring_companions": "¿Vienes acompañada/o?",
        "form.companions_count": "¿Cuántas personas te acompañarán?",
        "form.companion_label": "Acompañante",
        "form.field_name": "Nombre",
        "form.placeholder_fullname": "Nombre y apellido",
        "form.field_name_caption": "Nombre completo del acompañante.",
        "form.child_or_adult": "Tipo",
        "form.child_or_adult_caption": "Indica si es adulto o niño.",
        "form.adult": "Adulto",
        "form.child": "Niño",
        "form.companion_name_required": "Por favor, indica el nombre de cada acompañante seleccionado.",

        # --- Mensaje opcional ---
        "form.notes.expander_label": "📝 ¿Quieres dejarnos un mensaje opcional?",
        "form.notes.placeholder": "Ej.: Llegaremos un poco tarde, preferimos una mesa tranquila…",
        
        # --- Página de Confirmado ---
        "ok.title": "¡Confirmación recibida!",
        "ok.msg_yes": "¡Gracias por confirmar! Tu respuesta ha sido guardada.",
        "ok.msg_no": "Hemos registrado que no podrás asistir. ¡Te echaremos de menos!",
        "ok.summary": "Este es un resumen de tu confirmación:",
        "ok.main_guest": "Invitado principal",
        "ok.adults_children": "Adultos / Niños",
        "ok.allergies": "Alergias (titular)",
        "ok.companions": "Acompañantes",
        "ok.alrg_item": "Alergias",
        "ok.btn_edit": "✏️ Editar respuesta",
        "ok.btn_resend_email": "Reenviar email",
        "ok.btn_logout": "Cerrar sesión",
        "ok.load_error": "No pudimos cargar el resumen de tu confirmación.",
        "ok.sending": "Enviando...",
        "ok.resent_ok": "¡Correo de confirmación reenviado!",
        "ok.resent_fail": "No se pudo reenviar el correo.",

        # --- Panel de Invitación (usado en Formulario y Confirmado) ---
        "invite.panel_title": "Tu invitación",
        "invite.scope.full": "Estás invitado/a a la **Ceremonia** y a la **Recepción**.",
        "invite.scope.reception": "Estás invitado/a a la **Recepción**.",
        "invite.times.hint": "Ceremonia {ceremony_time} · Recepție {reception_time}",
    },

    # ==================================================
    # Română — ton cald, clar, cu notă festivă
    # ==================================================
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
        "login.errors_auth": "Cod, email sau telefon nu corespund.",
        "login.validating": "Se verifică…",
        "login.success": "Acces permis! Te ducem la formular…",
        "login.forgot": "Ți-ai uitat codul? Apasă aici",
        "login.server_err": "Nu am putut valida acum. Te rugăm să încerci din nou în scurt timp.",

        # --- Cere Accesul ---
        "request.title": "🔑 Cere accesul",
        "request.intro": "Pentru identificare, te rugăm să ne spui numele complet, ultimele 4 cifre ale telefonului și emailul unde vrei să primești linkul.",
        "request.full_name": "Numele tău complet",
        "request.phone_last4": "Ultimele 4 cifre ale telefonului",
        "request.phone_last4_placeholder": "Ex.: 5678",
        "request.email": "Adresă de email",
        "request.submit": "Trimite linkul de acces",
        "request.consent": "Sunt de acord să primesc comunicări legate de nuntă prin email.",
        "request.success": "Gata! Ți-am trimis un link pe email. Verifică Inbox și Spam/Promotions.",
        "request.error": "Nu am putut procesa cererea. Verifică datele și încearcă din nou.",
        "request.resend": "Nu ai primit emailul? Click aici pentru retrimitere.",
        "request.invalid_email": "Emailul nu pare valid.",
        "request.invalid_phone4": "Introdu exact 4 cifre.",
        "request.success_message_neutral": "Dacă datele se potrivesc invitației, vei primi un link pe email. Verifică Inbox și Spam/Promotions.",
        "request.invalid_name": "Numele trebuie să aibă cel puțin 3 caractere.",
        "request.consent_required": "Trebuie să accepți consimțământul pentru a continua.",

        # --- Formular RSVP ---
        "form.hi": "Salut",
        "form.subtitle": "Confirmă prezența și spune-ne câteva detalii ✨",
        "form.attending": "Vei participa?",
        "form.yes": "Da",
        "form.no": "Nu",
        "form.select_option": "Alege o opțiune pentru a continua.",
        "form.no_attend_short": "Îți mulțumim că ne-ai anunțat. Ne va fi dor de tine. 😔",
        "form.generic_error": "A apărut o eroare la salvarea răspunsului. Te rugăm să încerci mai târziu.",
        "form.sending": "Se trimite…",
        "form.submit": "Trimite răspunsul",
        "form.cancel": "Anulează",
        "form.net_err": "Nu se poate contacta serverul. Încearcă din nou.",
        "form.session_expired": "Sesiunea a expirat. Te rugăm să te autentifici din nou.",
        "form.load_error": "A apărut o eroare la încărcarea datelor tale.",

        # --- Invitație / program ---
        "form.invite_title": "Invitația ta",
        "form.invite_full_access": "Ești invitat(ă) la **Ceremonie** și la **Recepție**. Ne bucurăm să împărtășim această zi cu tine! 🕊️",
        "form.invite_reception_only": "Ești invitat(ă) la **Recepție**. Abia așteptăm să sărbătorim împreună! 🎉",
        "form.time_ceremony": "Ceremonie",
        "form.time_reception": "Recepție",
        "form.accomp_note": "Poți veni cu **până la {max_accomp} însoțitor(i)**.",

        # --- Contact ---
        "form.contact_title": "Date de contact",
        "form.contact_caption": "Vom folosi aceste date pentru confirmare și remindere. 💌",
        "form.field_email": "Email",
        "form.field_phone": "Telefon (Ex: +40722123456)",
        "form.contact_required_one": "Te rugăm să oferi cel puțin un email sau un telefon.",
        "form.contact_invalid_email": "Adresa de email nu pare validă.",
        "form.contact_invalid_phone": "Telefonul trebuie să includă prefixul internațional. Ex.: +40722123456",

        # --- Alergii (titular) ---
        "form.titular_allergies": "Alergii sau restricții (titular)",
        "form.allergies_caption": "Spune-ne dacă există ceva important pentru a avea grijă de tine. 💙",
        "form.allergies_or_restrictions": "Alergii sau restricții",

        # --- Însoțitori ---
        "form.companions_title": "Însoțitori",
        "form.companions_db_note": "Numărul de însoțitori permiși depinde de invitația ta.",
        "form.no_companions_info": "Invitația ta nu include însoțitori.",
        "form.bring_companions": "Vii însoțit(ă)?",
        "form.companions_count": "Câți oameni te vor însoți?",
        "form.companion_label": "Însoțitor",
        "form.field_name": "Nume",
        "form.placeholder_fullname": "Nume și prenume",
        "form.field_name_caption": "Numele complet al însoțitorului.",
        "form.child_or_adult": "Tip",
        "form.child_or_adult_caption": "Indică dacă este adult sau copil.",
        "form.adult": "Adult",
        "form.child": "Copil",
        "form.companion_name_required": "Te rugăm să completezi numele fiecărui însoțitor selectat.",

        # --- Mesaj opțional ---
        "form.notes.expander_label": "📝 Vrei să ne lași un mesaj opțional?",
        "form.notes.placeholder": "Ex.: Venim mai târziu, preferăm o masă liniștită…",
    
    # --- Pagina de Confirmare ---
        "ok.title": "Confirmare primită!",
        "ok.msg_yes": "Îți mulțumim pentru confirmare! Răspunsul tău a fost salvat.",
        "ok.msg_no": "Am înregistrat că nu vei putea participa. Ne va fi dor de tine!",
        "ok.summary": "Iată un sumar al confirmării tale:",
        "ok.main_guest": "Invitat principal",
        "ok.adults_children": "Adulți / Copii",
        "ok.allergies": "Alergii (titular)",
        "ok.companions": "Însoțitori",
        "ok.alrg_item": "Alergii",
        "ok.btn_edit": "✏️ Editează răspunsul",
        "ok.btn_resend_email": "Retrimite email",
        "ok.btn_logout": "Deconectare",
        "ok.load_error": "Nu am putut încărca sumarul confirmării.",
        "ok.sending": "Se trimite...",
        "ok.resent_ok": "Emailul de confirmare a fost retrimis!",
        "ok.resent_fail": "Emailul nu a putut fi retrimis.",

        # --- Panou Invitație (folosit în Formular și Confirmare) ---
        "invite.panel_title": "Invitația ta",
        "invite.scope.full": "Ești invitat(ă) la **Ceremonie** și la **Recepție**.",
        "invite.scope.reception": "Ești invitat(ă) la **Recepție**.",
        "invite.times.hint": "Ceremonie {ceremony_time} · Recepție {reception_time}",
        
    },

    # ==================================================
    # English — warm, clear, a touch celebratory
    # ==================================================
    "en": {
        # --- Menu ---
        "nav.login": "Login",
        "nav.form": "RSVP Form",
        "nav.confirmed": "Confirmed",
        "nav.request": "Request Access",
        "nav.recover": "Recover Code",

        # --- Login ---
        "login.title": "💍 Confirm attendance",
        "login.intro": "We’re so happy you’re here! Enter your invitation details to continue.",
        "login.code": "Invitation code",
        "login.contact": "Email or phone",
        "login.submit": "Continue",
        "login.errors_empty": "Please complete both fields.",
        "login.errors_auth": "Code, email or phone don’t match.",
        "login.validating": "Validating…",
        "login.success": "All set! Taking you to the form…",
        "login.forgot": "Forgot your code? Click here",
        "login.server_err": "We couldn’t validate right now. Please try again in a moment.",

        # --- Request Access ---
        "request.title": "🔑 Request access",
        "request.intro": "To identify you, please share your full name, the last 4 digits of your phone, and the email where you’d like to receive your access link.",
        "request.full_name": "Yourull name",
        "request.phone_last4": "Last 4 digits of your phone",
        "request.phone_last4_placeholder": "E.g., 5678",
        "request.email": "Email address",
        "request.submit": "Send access link",
        "request.consent": "I agree to receive wedding communications by email.",
        "request.success": "Done! We’ve sent a link to your email. Check Inbox and Spam/Promotions.",
        "request.error": "We couldn’t process your request. Please verify your details and try again.",
        "request.resend": "Didn’t get the email? Click here to resend.",
        "request.invalid_email": "The email doesn’t look valid.",
        "request.invalid_phone4": "Enter exactly 4 digits.",
        "request.success_message_neutral": "If your details match an invitation, you'll receive a link by email. Check Inbox and Spam/Promotions.",
        "request.invalid_name": "The name must have at least 3 characters.",
        "request.consent_required": "You must accept the consent to continue.",

        # --- RSVP Form ---
        "form.hi": "Hi",
        "form.subtitle": "Confirm your attendance and share a few details ✨",
        "form.attending": "Will you attend?",
        "form.yes": "Yes",
        "form.no": "No",
        "form.select_option": "Choose an option to continue.",
        "form.no_attend_short": "Thank you for letting us know. We’ll miss you! 😔",
        "form.generic_error": "Something went wrong while saving your response. Please try again later.",
        "form.sending": "Sending…",
        "form.submit": "Send response",
        "form.cancel": "Cancel",
        "form.net_err": "We couldn’t reach the server. Please try again.",
        "form.session_expired": "Your session has expired. Please log in again.",
        "form.load_error": "We couldn’t load your data at this time.",

        # --- Invitation / times ---
        "form.invite_title": "Your invitation",
        "form.invite_full_access": "You’re invited to the **Ceremony** and the **Reception**. We’re thrilled to share this day with you! 🕊️",
        "form.invite_reception_only": "You’re invited to the **Reception**. We can’t wait to celebrate together! 🎉",
        "form.time_ceremony": "Ceremony",
        "form.time_reception": "Reception",
        "form.accomp_note": "You can bring **up to {max_accomp} companion{plural}**.",

        # --- Contact ---
        "form.contact_title": "Contact details",
        "form.contact_caption": "We’ll use this information to send your confirmation and reminders. 💌",
        "form.field_email": "Email",
        "form.field_phone": "Phone (E.g. +447911123456)",
        "form.contact_required_one": "Please provide at least an email or a phone number.",
        "form.contact_invalid_email": "The email doesn’t look valid.",
        "form.contact_invalid_phone": "Phone must include the country code. E.g., +447911123456",

        # --- Allergies (main guest) ---
        "form.titular_allergies": "Allergies or restrictions (main guest)",
        "form.allergies_caption": "Let us know anything we should consider to take good care of you. 💙",
        "form.allergies_or_restrictions": "Allergies or restrictions",

        # --- Companions ---
        "form.companions_title": "Companions",
        "form.companions_db_note": "The number of companions allowed depends on your invitation.",
        "form.no_companions_info": "Your invitation does not include companions.",
        "form.bring_companions": "Will you bring companions?",
        "form.companions_count": "How many people will join you?",
        "form.companion_label": "Companion",
        "form.field_name": "Name",
        "form.placeholder_fullname": "First and last name",
        "form.field_name_caption": "Companion’s full name.",
        "form.child_or_adult": "Type",
        "form.child_or_adult_caption": "Indicate if they are an adult or a child.",
        "form.adult": "Adult",
        "form.child": "Child",
        "form.companion_name_required": "Please provide the name for each selected companion.",

        # --- Optional note ---
        "form.notes.expander_label": "📝 Would you like to leave an optional message?",
        "form.notes.placeholder": "E.g., We might arrive a bit late, we’d love a quiet table…",
        
        # --- Confirmation Page ---
        "ok.title": "Confirmation Received!",
        "ok.msg_yes": "Thank you for confirming! Your response has been saved.",
        "ok.msg_no": "We've noted that you won't be able to attend. We'll miss you!",
        "ok.summary": "Here is a summary of your confirmation:",
        "ok.main_guest": "Main Guest",
        "ok.adults_children": "Adults / Children",
        "ok.allergies": "Allergies (main guest)",
        "ok.companions": "Companions",
        "ok.alrg_item": "Allergies",
        "ok.btn_edit": "✏️ Edit response",
        "ok.btn_resend_email": "Resend email",
        "ok.btn_logout": "Log out",
        "ok.load_error": "We couldn't load your confirmation summary.",
        "ok.sending": "Sending...",
        "ok.resent_ok": "Confirmation email resent!",
        "ok.resent_fail": "Could not resend the email.",

        # --- Invitation Panel (used in Form & Confirmed) ---
        "invite.panel_title": "Your Invitation",
        "invite.scope.full": "You are invited to the **Ceremony** and the **Reception**.",
        "invite.scope.reception": "You are invited to the **Reception**.",
        "invite.times.hint": "Ceremony {ceremony_time} · Reception {reception_time}",
    },
}

def normalize_lang(lang: str | None) -> str:
    code = (lang or "").lower().strip()
    return code if code in VALID_LANGS else DEFAULT_LANG

def t(key: str, lang: str | None = None) -> str:
    code = normalize_lang(lang or DEFAULT_LANG)
    bundle = TRANSLATIONS.get(code, TRANSLATIONS[DEFAULT_LANG])
    return bundle.get(key, key)
