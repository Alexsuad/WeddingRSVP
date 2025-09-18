# sendgrid_test.py  # Script aislado para probar envío de correo real con SendGrid.

import os  # Importa 'os' para leer variables de entorno.
from sendgrid import SendGridAPIClient  # Cliente oficial de SendGrid para enviar correos.
from sendgrid.helpers.mail import Mail, From  # Clases helper para construir el email.
try:
    from dotenv import load_dotenv  # Intenta importar python-dotenv para cargar .env.
    load_dotenv()  # Carga variables desde .env si existe (no falla si no está).
except Exception:
    pass  # Si no existe python-dotenv, seguimos; asumimos que el entorno ya tiene las vars.

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")  # Lee la API key de SendGrid desde el entorno.
FROM_EMAIL = os.getenv("EMAIL_FROM", "")  # Lee el remitente configurado (debe estar verificado en SendGrid).
TO_EMAIL = os.getenv("TEST_TO_EMAIL", "nalexsua75@gmail.com")  # Destinatario de prueba (puedes cambiarlo con TEST_TO_EMAIL).

# Validaciones básicas para evitar ejecuciones vacías.
if not SENDGRID_API_KEY:  # Comprueba que exista la API key.
    raise RuntimeError("Falta SENDGRID_API_KEY en el entorno (.env). Renuévala y colócala correctamente.")  # Falla si no está.
if not FROM_EMAIL:  # Comprueba que exista el remitente.
    raise RuntimeError("Falta EMAIL_FROM en el entorno (.env). Usa un remitente VERIFICADO en SendGrid.")  # Falla si no está.

# Construye el mensaje con subject, texto y HTML.
message = Mail(  # Crea el objeto Mail para enviar por SendGrid.
    from_email=From(FROM_EMAIL, "Daniela & Cristian"),  # Remitente con nombre “humano”.
    to_emails=TO_EMAIL,  # Destinatario de prueba.
    subject="Prueba aislada SendGrid (SDK) ✅",  # Asunto del correo.
    plain_text_content="Hola! Esta es una prueba aislada del backend RSVP usando el SDK de SendGrid.",  # Cuerpo en texto plano.
    html_content="<strong>Hola!</strong> Esta es una <em>prueba aislada</em> del backend RSVP usando el SDK de SendGrid.",  # Cuerpo en HTML.
)

try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)  # Instancia el cliente con la API key.
    resp = sg.send(message)  # Envía el mensaje al endpoint /v3/mail/send.
    # A partir de aquí, imprimimos todo para diagnóstico claro:
    print("=== RESULTADO SENDGRID (SDK) ===")  # Encabezado visual.
    print("Status Code:", resp.status_code)  # Muestra el código HTTP (202 esperado en éxito).
    print("Headers:", dict(resp.headers))  # Muestra headers devueltos por SendGrid (útil para trazas).
    try:
        # Algunos envíos no devuelven body; si lo hay, lo mostramos.
        print("Body:", resp.body.decode() if hasattr(resp.body, "decode") else resp.body)  # Imprime el cuerpo si existe.
    except Exception:
        print("Body: <no body>")  # Si no se puede decodificar, lo indicamos.
except Exception as e:
    # Capturamos y mostramos cualquier excepción (autenticación, remitente inválido, etc.).
    print("💥 EXCEPCIÓN EN ENVÍO (SDK):", repr(e))  # Imprime la excepción completa para depurar.
