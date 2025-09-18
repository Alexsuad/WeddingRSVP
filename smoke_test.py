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
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")  # URL base del backend (puede sobreescribirse).
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
ADMIN_HEADERS = {**JSON_HEADERS, "x-admin-key": ADMIN_API_KEY}     # Cabecera admin para /api/admin/*.

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
# 1) Health check (espera 404)
# -------------------------------
def test_health_check() -> bool:                                             # Verifica que el servidor responde.
    url = f"{BASE_URL}/__this_route_should_not_exist__"                      # Ruta inexistente a propósito.
    try:
        r = get(url)                                                         # Llama al backend.
        return r.status_code == 404                                          # 404 esperado indica que está vivo.
    except Exception:
        return False                                                         # Error de conexión → backend caído.

# -------------------------------
# 2) Import admin (crear invitado)
# -------------------------------
def test_admin_import() -> bool:                                             # Crea un invitado de prueba.
    guest_payload = {                                                        # Datos del invitado (ajustados a tu schema).
        "guest_code": TEST_GUEST_CODE,                                       # Código conocido para login clásico.
        "full_name": "Smoke Test Guest",                                     # Nombre visible.
        "email": TEST_GUEST_EMAIL,                                           # Email único.
        "phone": TEST_GUEST_PHONE,                                           # Teléfono único.
        "language": LANG_DEFAULT,                                            # Idioma (Enum).
        "max_accomp": 1,                                                     # Cupo total de acompañantes (int).
        "invite_type": "full"                                                # Enum válido: "full" o "ceremony".
    }
    # Aceptamos envolturas distintas; tu router usa "items".
    bodies = [{"items": [guest_payload]}, {"rows": [guest_payload]}, {"guests": [guest_payload]}]  # Variantes.
    last = None                                                              # Guarda el último error/respuesta.
    for body in bodies:                                                      # Intenta cada variante.
        r = post(f"{BASE_URL}/api/admin/import-guests", body, headers=ADMIN_HEADERS)  # Llamada POST admin.
        if r.status_code // 100 != 2:                                        # Si no es 2xx…
            last = f"HTTP {r.status_code}: {r.text}"                         # Guarda el error textual.
            continue                                                         # Prueba siguiente variante.
        try:
            j = r.json()                                                     # Parsea JSON.
        except Exception:
            return False                                                     # Sin JSON → falla.
        created = try_keys(j, ["created", "to_create", "inserted"]) or 0     # Detecta contador de creación.
        updated = try_keys(j, ["updated", "to_update"]) or 0                 # Detecta contador de actualización.
        ok = try_keys(j, ["ok", "success"])                                  # Algunas APIs devuelven ok/success.
        if ok is True or (created + updated) >= 1:                           # Condición de éxito flexible.
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
    payload = {"guest_code": TEST_GUEST_CODE, "email": TEST_GUEST_EMAIL}     # Tu schema espera email/phone (no email_or_phone).
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
def test_magic_link_flow() -> bool:                                          # Solicita enlace y canjea token.
    global SESSION_TOKEN                                                     # Necesitamos setear el token.
    req = {                                                                  # Payload de request-access.
        "full_name": "Smoke Test Guest",                                     # Debe coincidir con el import.
        "phone_last4": TEST_GUEST_PHONE[-4:],                                # Últimos 4 del teléfono importado.
        "email": TEST_MAGIC_EMAIL,                                           # Email donde “llegaría” el link.
        "consent": True,                                                     # Consentimiento (si aplica).
        "preferred_language": LANG_DEFAULT                                   # Idioma del correo.
    }
    r = post(f"{BASE_URL}/api/request-access", req, headers=JSON_HEADERS)    # Llama al endpoint.
    if r.status_code // 100 != 2:                                            # Si no es 2xx…
        print(f"   • Request-access failed: HTTP {r.status_code}: {r.text}") # Log del fallo.
        return False                                                          # Falla.
    if not os.path.exists(DB_PATH):                                          # Si no existe la DB…
        print("   • DB not found; cannot auto-fetch magic token.")           # Explica la limitación.
        return False                                                          # Falla (requiere copia manual del token).
    time.sleep(1)                                                            # Pequeña espera para persistencia.
    # Detecta el nombre de la columna de token (tu modelo usa magic_link_token).
    token_col = next((c for c in ["magic_link_token","magic_token","magic_jwt"] if db_has_column(DB_PATH,"guests",c)), None)
    if not token_col:                                                        # Si no hay ninguna columna válida…
        print("   • No magic token column in DB; skipping.")                 # Informa.
        return False                                                         # Falla.
    try:
        conn = sqlite3.connect(DB_PATH)                                      # Abre conexión SQLite.
        cur = conn.cursor()                                                  # Crea cursor.
        cur.execute(f"SELECT {token_col} FROM guests WHERE email = ?;", (TEST_GUEST_EMAIL,))  # Busca por email.
        row = cur.fetchone()                                                 # Lee primera fila.
        conn.close()                                                         # Cierra conexión.
    except Exception as e:                                                   # Errores SQL.
        print(f"   • DB read error: {e}")                                    # Log del error.
        return False                                                         # Falla.
    if not row or not row[0]:                                                # Si no hay token…
        print("   • Magic token not found in DB.")                           # Informa.
        return False                                                         # Falla.
    magic_token = row[0]                                                     # Extrae token.
    # Intenta canjear en cada ruta candidata.
    for ep in MAGIC_LOGIN_ENDPOINTS:                                         # Recorre rutas posibles.
        r2 = post(f"{BASE_URL}{ep}", {"token": magic_token}, headers=JSON_HEADERS)  # Llama a magic-login.
        if r2.status_code // 100 != 2:                                       # Si falla…
            continue                                                         # Prueba siguiente ruta.
        j = r2.json()                                                        # Parsea JSON.
        token = try_keys(j, ["access_token", "token"])                       # Busca token.
        if token:                                                            # Si existe…
            SESSION_TOKEN = token                                            # Guarda token de sesión.
            # Prueba reuso (debe fallar 401).
            r3 = post(f"{BASE_URL}{ep}", {"token": magic_token}, headers=JSON_HEADERS)  # Reutiliza token.
            if r3.status_code != 401:                                        # Esperamos 401.
                print(f"   • Reuse should be 401, got {r3.status_code}")     # Advierte si no falla.
            return True                                                      # Éxito del flujo.
    print("   • None of magic-login endpoints worked.")                      # Ninguna ruta funcionó.
    return False                                                             # Falla.

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
    payloads = [                                                               # Variantes permitidas por tu schema.
        {"attending": True, "companions": []},                                 # Vacío, válido.
        {"attending": True}                                                    # Mínimo absoluto.
    ]
    for p in payloads:                                                         # Prueba cada payload.
        r2 = post(f"{BASE_URL}/api/guest/me/rsvp", p, headers=auth)            # POST /rsvp.
        if r2.status_code // 100 == 2:                                         # Si es 2xx…
            return True                                                        # Éxito.
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
