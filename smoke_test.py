# smoke_test.py  # Script de verificación rápida (smoke test) end-to-end del backend.

import os                               # Para leer variables de entorno (URL, claves, rutas).
import json                             # Por si queremos imprimir/depurar JSON.
import time                             # Para timestamps únicos y pequeñas esperas.
import sqlite3                          # Para leer el magic token desde SQLite en DRY_RUN=1.
from typing import Optional, Dict, Any, List  # Tipado opcional para claridad.
import requests                         # Cliente HTTP para llamar a la API.

# -------------------------------
# ⚙️ Configuración (por entorno)
# -------------------------------
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")  # URL base del backend (sin barra final).
ADMIN_API_KEY = os.getenv("SMOKE_ADMIN_KEY", os.getenv("ADMIN_API_KEY", "supersecreto123"))  # Clave admin.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wedding.db")  # URL de SQLite (como en tu .env).
DB_PATH = os.getenv(                                                 # Resuelve la ruta física de la base.
    "SMOKE_DB_PATH",                                                # Permite override directo con SMOKE_DB_PATH.
    DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "") # Quita prefijos sqlite://*/.
) or "wedding.db"                                                   # Fallback simple si quedara vacío.
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"                          # Si True, backend no envía correos reales.

# -------------------------------
# 📦 Datos de prueba dinámicos
# -------------------------------
NOW = int(time.time())                                             # Timestamp entero para unicidad.
TEST_GUEST_CODE = f"SMK-{NOW}"                                     # guest_code único para identificar el registro.
TEST_GUEST_EMAIL = f"smoke.{NOW}@example.com"                      # Email único por corrida.
TEST_GUEST_PHONE = f"+999{NOW}"                                    # Teléfono único por corrida.
TEST_MAGIC_EMAIL = os.getenv("SMOKE_MAGIC_EMAIL", TEST_GUEST_EMAIL) # Dónde “llegaría” el magic link en producción.
LANG_DEFAULT = "en"                                                # Idioma por defecto.

# Posibles rutas de magic-login (por si tu router cambia el path).
MAGIC_LOGIN_ENDPOINTS = ["/api/magic-login", "/api/login/magic", "/api/magic_login"]  # Variantes aceptadas.

# Cabeceras estándar.
JSON_HEADERS = {"Content-Type": "application/json"}                # Indicamos JSON.
ADMIN_HEADER_CANDIDATES = [
    {"X-Admin-Api-Key": ADMIN_API_KEY, **JSON_HEADERS},
    {"x-admin-api-key": ADMIN_API_KEY, **JSON_HEADERS},
    {"x-admin-key": ADMIN_API_KEY, **JSON_HEADERS},
]

# Token de sesión (se setea tras login).
SESSION_TOKEN: Optional[str] = None                                # Empezamos sin token.

# -------------------------------
# 🧰 Utilidades de apoyo
# -------------------------------
def get(url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:  # Define wrapper GET.
    return requests.get(url, headers=headers or {}, timeout=10)                    # Hace GET con timeout.

def post(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> requests.Response:  # Wrapper POST.
    return requests.post(url, headers=headers or JSON_HEADERS, json=payload, timeout=15)                      # POST con timeout.

def try_keys(data: Dict[str, Any], candidates: List[str]) -> Optional[Any]:  # Busca una clave válida en orden.
    for k in candidates:                                                     # Itera claves candidatas.
        if k in data:                                                        # Si existe la clave…
            return data[k]                                                   # Devuelve el valor.
    return None                                                              # Si no, devuelve None.

def db_has_column(db_path: str, table: str, column: str) -> bool:           # Verifica existencia de columna.
    try:
        conn = sqlite3.connect(db_path)                                      # Abre conexión SQLite.
        cur = conn.cursor()                                                  # Crea cursor.
        cur.execute(f"PRAGMA table_info({table});")                          # Pide info de columnas.
        cols = [row[1] for row in cur.fetchall()]                            # Extrae nombres.
        conn.close()                                                         # Cierra conexión.
        return column in cols                                                # Retorna True/False.
    except Exception:
        return False                                                         # Si falla, asume que no existe.

def pretty(ok: bool) -> str:                                                 # Imprime icono ✅/❌.
    return "✅" if ok else "❌"

# -------------------------------
# 1) Health check (espera 200 o 404)
# -------------------------------
def test_health_check() -> bool:
    candidates = ["/api/health", "/api/ping", "/health", "/ping"]
    for path in candidates:
        try:
            r = get(f"{BASE_URL}{path}")
            if r.status_code == 200:
                return True
        except Exception:
            pass
    # Fallback 404 en ruta inexistente para detectar “servidor vivo”
    try:
        r = get(f"{BASE_URL}/__this_route_should_not_exist__")
        return r.status_code == 404
    except Exception:
        return False

# -------------------------------
# 2) Import admin (crear invitado)
# -------------------------------
def test_admin_import() -> bool:                                             # Crea un invitado de prueba.
    guest_payload = {                                                        # Datos del invitado (ajustados a tu schema).
        "guest_code": TEST_GUEST_CODE,                                       # Código conocido para login clásico.
        "full_name": "Smoke Test Guest",                                     # Nombre visible.
        "email": TEST_GUEST_EMAIL,                                           # Email único.
        "phone": TEST_GUEST_PHONE,                                           # Teléfono único.
        "phone_last4": TEST_GUEST_PHONE[-4:],                                # Últimos 4 del teléfono.
        "language": LANG_DEFAULT,                                            # Idioma (Enum).
        "max_accomp": 1,                                                     # Cupo total de acompañantes (int).
        "invite_type": "full"                                                # Enum válido: "full" o "ceremony".
    }
    # Aceptamos envolturas distintas; tu router usa "items".
    bodies = [{"items": [guest_payload]}, {"rows": [guest_payload]}, {"guests": [guest_payload]}]  # Variantes.
    last = None                                                              # Guarda el último error/respuesta.
    for body in bodies:                                                      # Intenta cada variante.
        for admin_headers in ADMIN_HEADER_CANDIDATES:
            r = post(f"{BASE_URL}/api/admin/import-guests", body, headers=admin_headers)
            if r.status_code // 100 != 2:
                last = f"HTTP {r.status_code}: {r.text}"
                continue
            try:
                j = r.json()                                                 # Parsea JSON.
            except Exception:
                return False                                                 # Sin JSON → falla.
            created = try_keys(j, ["created", "to_create", "inserted"]) or 0     # Detecta contador de creación.
            updated = try_keys(j, ["updated", "to_update"]) or 0                 # Detecta contador de actualización.
            skipped = try_keys(j, ["skipped", "omitted"]) or 0                   # Detecta invitados ya existentes.
            ok = try_keys(j, ["ok", "success"])                                  # Algunas APIs devuelven ok/success.
            if ok is True or (created + updated + skipped) >= 1:                 # Condición de éxito flexible.
                time.sleep(0.3)                                                  # Pequeña espera para asegurar commit.
                return True                                                      # Éxito.
            last = f"Unexpected JSON: {j}"                                       # Guarda detalle si no encaja.
    print(f"   • Import failed: {last}")                                     # Loguea el último error.
    return False                                                             # Falla si ninguna variante pasó.

# -------------------------------
# 3) Login clásico
# -------------------------------
def test_classic_login() -> bool:                                            # Prueba /api/login (guest_code + email).
    global SESSION_TOKEN                                                     # Vamos a setear el token global.
    payload = {"guest_code": TEST_GUEST_CODE, "email": TEST_GUEST_EMAIL, "phone": TEST_GUEST_PHONE}  # Soporta email o phone.
    try:
        r = post(f"{BASE_URL}/api/login", payload, headers=JSON_HEADERS)     # Llama a /api/login.
        r.raise_for_status()                                                 # Lanza si no es 2xx.
        j = r.json()                                                         # Parsea JSON.
        token = try_keys(j, ["access_token", "token"])                       # Busca campo de token.
        if not token:                                                        # Si no hay token…
            print(f"   • Login response without token: {j}")                 # Log informativo.
            return False                                                     # Falla.
        SESSION_TOKEN = token                                                # Guarda el token para siguientes pasos.
        return True                                                          # Éxito.
    except Exception as e:                                                   # Manejo de error.
        print(f"   • Classic login failed: {e}")                             # Log del error.
        return False                                                         # Falla.

# -------------------------------
# 4) Flujo Magic Link
# -------------------------------
def test_magic_link_flow() -> bool:                                          # Define la función para probar el flujo de Magic Link (debe devolver True/False).
    if os.getenv("SEND_ACCESS_MODE", "code").strip().lower() != "magic":     # Lee SEND_ACCESS_MODE y comprueba si NO es 'magic'.
        print("   • SEND_ACCESS_MODE != 'magic'; omito flujo de magic link.")# Informa que se omite el flujo (no es fallo, solo omitido).
        return False                                                         # Devuelve False para marcar que no se ejecutó el flujo (seguirá con login clásico).

    global SESSION_TOKEN                                                     # Indica que modificaremos la variable global SESSION_TOKEN (para siguientes peticiones autenticadas).

    print(f"   • MagicLink | BASE_URL={BASE_URL} | DB_PATH={DB_PATH}")       # Traza: muestra URL base y ruta de BD para depuración.
    print(f"   • MagicLink | EMAIL={TEST_MAGIC_EMAIL} | PHONE_LAST4={TEST_GUEST_PHONE[-4:]}")  # Traza: muestra email/últimos 4 del teléfono.

    req = {                                                                  # Construye el cuerpo para solicitar el enlace mágico.
        "full_name": "Smoke Test Guest",                                     # Debe coincidir con el import previo (para match).
        "phone_last4": TEST_GUEST_PHONE[-4:],                                # Últimos 4 dígitos del teléfono importado.
        "email": TEST_MAGIC_EMAIL,                                           # Email destino del enlace (en producción llegaría por correo).
        "consent": True,                                                     # Consentimiento (si aplica en tu API).
        "preferred_language": LANG_DEFAULT                                   # Idioma preferido para el correo.
    }
    print("   • MagicLink | POST /api/request-access …")                     # Traza: indica que hará la petición de solicitud de acceso.
    r = post(f"{BASE_URL}/api/request-access", req, headers=JSON_HEADERS)    # Realiza el POST a /api/request-access con JSON.
    print(f"     → HTTP {r.status_code}")                                    # Traza: imprime el código de respuesta HTTP.
    if r.status_code // 100 != 2:                                            # Comprueba que sea 2xx (éxito).
        print(f"     → Body: {r.text[:200]}")                                # Traza: muestra parte del body para diagnóstico.
        print("   • MagicLink | request-access FAILED")                      # Traza: marca fallo en la solicitud.
        return False                                                         # Devuelve False (no se pudo solicitar el enlace).

    if not os.path.exists(DB_PATH):                                          # Verifica existencia de la BD local (DRY_RUN=1).
        print("   • MagicLink | DB not found; cannot auto-fetch magic token.")# Traza: no puede leer el token si no hay BD local.
        return False                                                         # Devuelve False (flujo no completado).

    print("   • MagicLink | Detectando columna del token en 'guests' …")     # Traza: indica que detectará la columna del token.
    token_col = next(                                                        # Detecta el nombre real de la columna del token.
        (c for c in ["magic_link_token", "magic_token", "magic_jwt"]         # Lista candidatos de nombre de columna.
         if db_has_column(DB_PATH, "guests", c)),                            # Comprueba cada candidato en la tabla guests.
        None                                                                 # Si no encuentra, devuelve None.
    )
    print(f"     → token_col={token_col}")                                   # Traza: imprime la columna detectada (o None).
    if not token_col:                                                        # Si no hay columna válida…
        print("   • MagicLink | No magic token column in DB; skipping.")     # Traza: informa que no se puede continuar.
        return False                                                         # Devuelve False (flujo no ejecutable).

    print("   • MagicLink | Leyendo token desde SQLite con reintentos …")    # Traza: indica que leerá el token con reintentos.
    magic_token = None                                                       # Inicializa contenedor para el token leído.
    for attempt in range(1, 6):                                              # Hará 5 intentos (1..5).
        time.sleep(0.5)                                                      # Espera 0.5s entre intentos (dar tiempo a persistencia).
        try:                                                                 # Manejo de errores de acceso a la BD.
            conn = sqlite3.connect(DB_PATH)                                  # Abre conexión SQLite a la BD.
            cur = conn.cursor()                                              # Crea cursor para ejecutar consulta.
            cur.execute(                                                     # Ejecuta SELECT para recuperar el token por email.
                f"SELECT {token_col} FROM guests WHERE email = ?;",          # Usa la columna detectada dinámicamente.
                (TEST_MAGIC_EMAIL,)                                          # Filtra por el email del invitado de prueba.
            )
            row = cur.fetchone()                                             # Obtiene una fila (si existe).
            conn.close()                                                     # Cierra conexión con la BD.
            has_value = bool(row and row[0])                                 # Evalúa si hay valor de token.
            print(f"     → intento {attempt}/5 | found={has_value}")         # Traza: informa si se encontró token en este intento.
            if has_value:                                                    # Si encontró token…
                magic_token = row[0]                                         # Guarda el token encontrado.
                break                                                        # Sale del bucle de reintentos.
        except Exception as e:                                               # Captura excepciones de SQLite.
            print(f"     → intento {attempt}/5 | DB error: {e}")             # Traza: imprime el error y continúa intentando.
    if not magic_token:                                                      # Tras los intentos, si no hay token…
        print("   • MagicLink | Token not found after retries.")             # Traza: informa que no se obtuvo token.
        return False                                                         # Devuelve False (flujo incompleto).

    # >>> SUB: S04 Redeem & reuse (Magic Link)                                # Marcador para identificar este sub-bloque.
    print(f"   • MagicLink | Intentando canjear token en endpoints: {MAGIC_LOGIN_ENDPOINTS}")  # Traza: lista endpoints candidatos.
    for ep in MAGIC_LOGIN_ENDPOINTS:                                         # Itera cada endpoint posible para canjear el magic link.
        candidate_payloads = [                                               # Define payloads alternativos porque varía por backend.
            {"token": magic_token},                                          # Variante 1: campo 'token'.
            {"magic_token": magic_token},                                    # Variante 2: campo 'magic_token'.
            {"token": magic_token, "email": TEST_MAGIC_EMAIL},               # Variante 3: 'token' + 'email'.
            {"magic_token": magic_token, "email": TEST_MAGIC_EMAIL},         # Variante 4: 'magic_token' + 'email'.
        ]
        for payload in candidate_payloads:                                   # Itera cada payload candidato.
            print(f"     → POST {ep} with keys={list(payload.keys())} …")    # Traza: muestra claves enviadas en el body.
            r2 = post(f"{BASE_URL}{ep}", payload, headers=JSON_HEADERS)      # Envía POST de canje al endpoint actual.
            print(f"       → HTTP {r2.status_code}")                         # Traza: código HTTP de respuesta.
            if r2.status_code // 100 != 2:                                   # Si NO es 2xx…
                continue                                                     # Prueba siguiente payload o endpoint.
            try:
                j = r2.json()                                                # Intenta parsear respuesta JSON.
            except Exception:                                                # Si no es JSON…
                print("       → Respuesta no-JSON; pruebo siguiente payload/endpoint")  # Traza: lo indica y sigue.
                continue                                                     # Continúa con siguiente payload/endpoint.
            token = try_keys(j, ["access_token", "token"])                   # Busca access token en la respuesta.
            print(f"       → access_token_present={bool(token)}")            # Traza: indica si encontró access token.
            if token:                                                        # Si hay token…
                SESSION_TOKEN = token                                        # Guarda token de sesión para siguientes llamadas.
                r3 = post(f"{BASE_URL}{ep}", payload, headers=JSON_HEADERS)  # Intenta reusar el mismo magic token (debe fallar).
                print(f"     → Reuse HTTP {r3.status_code} (esperado 401)")  # Traza: muestra status del reuso esperado.
                if r3.status_code != 401:                                    # Comprueba que el reuso sea rechazado.
                    print(f"     → WARNING: reuse debería ser 401 y fue {r3.status_code}")  # Advierte si no es 401.
                return True                                                  # Éxito total del flujo Magic Link.
    print("   • MagicLink | Ningún endpoint/payload de canje funcionó.")     # Traza: no funcionó ningún endpoint/payload.
    return False                                                             # Devuelve False: no se logró canjear el token.
    # <<< SUB: S04 Redeem & reuse (Magic Link)                                # Fin del sub-bloque.

# -------------------------------
# 5) Endpoints autenticados
# -------------------------------
def test_authenticated_endpoints() -> bool:                                   # /api/guest/me y /rsvp.
    if not SESSION_TOKEN:                                                     # Sin token → no seguimos.
        print("   • Missing session token.")                                  # Informa.
        return False                                                          # Falla.
    auth = {**JSON_HEADERS, "Authorization": f"Bearer {SESSION_TOKEN}"}       # Header Bearer.
    # Perfil
    r = get(f"{BASE_URL}/api/guest/me", headers=auth)                         # GET /me.
    if r.status_code != 200:                                                  # Debe ser 200.
        print(f"   • GET /me failed: {r.status_code} {r.text}")               # Log del fallo.
        return False                                                          # Falla.
    # RSVP (mínimo)
    payloads = [
        # Variante mínima absoluta (si tu API la acepta)
        {"attending": True},

        # Variante “v7.2” con notas (queremos validar que se persiste y no ejecuta HTML)
        {
            "attending": True,
            "companions": [],  # Sin acompañantes; si tu API pide int, ver siguiente variante
            "notes": "Notas de prueba E2E (smoke).",
            "allergies": "Ninguna"
        },

        # Variante alternativa si el esquema espera entero en companions
        {
            "attending": True,
            "companions": 0,
            "notes": "Notas de prueba E2E (smoke).",
            "allergies": "Ninguna"
        },
    ]
    # Intentar en los endpoints típicos (primero /me/rsvp; fallback /api/rsvp si existe)
    rsvp_endpoints = ["/api/guest/me/rsvp", "/api/rsvp"]
    for p in payloads:
        for ep in rsvp_endpoints:
            r2 = post(f"{BASE_URL}{ep}", p, headers=auth)
            if r2.status_code // 100 == 2:
                # (Opcional) Validación rápida del echo-back si tu endpoint devuelve el RSVP guardado.
                try:
                    saved = r2.json()
                    if "notes" in p:
                        assert (
                            ("notes" in saved) or
                            ("data" in saved and "notes" in saved.get("data", {}))
                        ), "RSVP no devolvió 'notes'."
                except Exception:
                    pass
                return True  # ÉXITO: alguna variante fue aceptada
    print("   • RSVP failed with all payload variants.")                       # Si ninguno pasó → informa.
    return False                                                               # Falla.

# -------------------------------
# 🏁 Orquestación
# -------------------------------
def run() -> int:                                                              # Función principal.
    print("=== Smoke Test for RSVP API ===")                                   # Cabecera.
    print(f"BASE_URL = {BASE_URL}")                                            # Muestra URL base.
    print(f"DB_PATH  = {DB_PATH}")                                             # Muestra ruta DB.
    print(f"DRY_RUN  = {DRY_RUN}")                                             # Muestra DRY_RUN.

    ok1 = test_health_check();   print(f"[1/5] Health: {pretty(ok1)}")         # Test 1.
    if not ok1: return 1                                                       # Si falla → sal.

    ok2 = test_admin_import();  print(f"[2/5] Admin import: {pretty(ok2)}")    # Test 2.
    if not ok2: return 1                                                       # Si falla → sal.

    ok3 = test_classic_login(); print(f"[3/5] Classic login: {pretty(ok3)}")   # Test 3.

    ok4 = False                                                                # Inicializa flag magic.
    if not ok3:                                                                # Si falló login clásico…
        ok4 = test_magic_link_flow(); print(f"[4/5] Magic link: {pretty(ok4)}")# Intenta magic.
        if not ok4: return 1                                                   # Si también falla → sal.

    ok5 = test_authenticated_endpoints(); print(f"[5/5] Auth endpoints: {pretty(ok5)}")  # Test 5.
    if not ok5: return 1                                                       # Si falla → sal.

    print("🎉 Smoke test PASSED – backend core flows look healthy.")           # Mensaje final OK.
    return 0                                                                   # Retorno 0 (éxito).

if __name__ == "__main__":                                                     # Punto de entrada.
    raise SystemExit(run())                                                    # Ejecuta y devuelve exit code.