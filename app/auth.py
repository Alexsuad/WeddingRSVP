# app/auth.py  # Ruta y nombre del archivo del módulo de autenticación.  # Indica el archivo actual.

# =================================================================================
# 🔐 MÓDULO DE AUTENTICACIÓN (JWT)                                               # Describe el propósito del módulo.
# ---------------------------------------------------------------------------------
# - Crea y verifica JSON Web Tokens para sesión (access) y Magic Link (magic).    # Explica las dos clases de tokens.
# - Usa python-jose (jose.jwt) para firmar/decodificar JWT.                        # Indica la librería usada.
# - Mantiene compatibilidad con tu implementación previa de create_access_token.   # Aclara la retrocompatibilidad.
# =================================================================================

# 🐍 Importaciones
import os                                                     # Acceso a variables de entorno (.env).
from datetime import datetime, timedelta                      # Manejo de tiempos de emisión/expiración.
from typing import Dict, Any, Optional, Union                 # Tipos para anotar parámetros y retornos.
from jose import jwt, JWTError                                # Implementación de JWT (python-jose).

# ⚙️ Configuración de seguridad (desde .env con defaults seguros)
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")            # Clave para firmar JWT (usa valor real en producción).
ALGORITHM = os.getenv("ALGORITHM", "HS256")                   # Algoritmo de firmado (HS256 por defecto).
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # Expiración access (minutos).
MAGIC_LINK_EXPIRE_MINUTES  = int(os.getenv("MAGIC_LINK_EXPIRE_MINUTES",  "15"))      # Expiración magic link (minutos).

# 🔒 Validación mínima de config crítica (mantiene tu fail-fast, pero con defaults arriba)
if not SECRET_KEY:                                            # Si por alguna razón queda vacío (devs pueden sobreescribir)...
    raise ValueError("SECRET_KEY no está configurado.")       # Falla rápido con mensaje claro.
if not ALGORITHM:                                             # Si no hay algoritmo...
    raise ValueError("ALGORITHM no está configurado.")        # Falla rápido con mensaje claro.

# 🕒 Helpers internos de tiempo
def _utcnow() -> datetime:                                    # Define un helper para la hora UTC actual.
    return datetime.utcnow()                                   # Devuelve datetime en UTC.

# 🧰 Helper interno: firmar payload como JWT
def _encode(payload: Dict[str, Any]) -> str:                   # Encapsula la firma del token.
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)  # Firma con clave y algoritmo configurados.

# =================================================================================
# ✨ CREACIÓN DE TOKENS
# =================================================================================

def create_access_token(                                      # Define creación de access token (retrocompatible).
    data: Optional[Dict[str, Any]] = None,                    # Soporta el uso antiguo: pasar un dict arbitrario.
    *,                                                        # Obliga a nombrar los parámetros siguientes (keyword-only).
    subject: Optional[str] = None,                            # Nuevo uso recomendado: subject (p. ej., guest_code).
    extra: Optional[Dict[str, Any]] = None                    # Datos extra opcionales a inyectar en el payload.
) -> str:                                                     # Devuelve el JWT como cadena.
    """
    Crea un token de acceso (tipo 'access').
    - Uso nuevo recomendado: create_access_token(subject="GUEST_CODE", extra={...})
    - Uso legado compatible: create_access_token({"sub":"...", ...})
    """                                                       # Docstring explicativo.
    now = _utcnow()                                           # Obtiene la hora actual en UTC.
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) # Calcula la expiración del token.
    payload: Dict[str, Any] = {                               # Construye el payload base del JWT.
        "iat": int(now.timestamp()),                          # 'iat' = issued at (segundos).
        "exp": int(exp.timestamp()),                          # 'exp' = expiration (segundos).
    }                                                         # Cierra el diccionario base.

    if subject is not None:                                   # Si se usa el modo nuevo con 'subject'...
        payload.update({                                      # Amplía el payload con claims estándar.
            "sub": subject,                                   # 'sub' identifica al sujeto (guest_code).
            "type": "access",                                 # Tipo de token: 'access'.
        })                                                    # Cierra update.
    if data:                                                  # Si se pasó un dict (modo legado)...
        payload.update(data)                                  # Mezcla los datos legados en el payload.
        payload.setdefault("type", "access")                  # Asegura 'type'='access' si no estaba presente.
    if extra:                                                 # Si hay extras...
        payload.update(extra)                                 # Los inyecta al payload final.

    return _encode(payload)                                   # Firma y devuelve el JWT.

def create_magic_token(guest_code: str, email: str) -> str:   # Define creación de token de Magic Link.
    """Crea un token corto de tipo 'magic' para login por enlace."""  # Docstring.
    now = _utcnow()                                           # Hora actual.
    exp = now + timedelta(minutes=MAGIC_LINK_EXPIRE_MINUTES)  # Expiración corta (por defecto 15 min).
    payload = {                                               # Payload específico de magic link.
        "sub": guest_code,                                    # Sujet: guest_code del invitado.
        "type": "magic",                                      # Tipo de token: 'magic'.
        "email": email,                                       # Email destino (para trazabilidad/validación adicional).
        "iat": int(now.timestamp()),                          # Momento de emisión.
        "exp": int(exp.timestamp()),                          # Momento de expiración.
    }                                                         # Cierra payload.
    return _encode(payload)                                   # Firma y devuelve el JWT.

# =================================================================================
# 🔎 DECODIFICACIÓN/VERIFICACIÓN
# =================================================================================

def decode_access_token(token: str) -> Dict[str, Any]:        # Decodifica y valida un access token.
    """Decodifica un token y verifica que sea de tipo 'access'. Lanza JWTError/ValueError si no es válido."""  # Docstring.
    data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Decodifica y valida firma/expiración.
    if data.get("type") != "access":                          # Comprueba claim de tipo.
        raise ValueError("Invalid token type for access token")  # Lanza error si el tipo no corresponde.
    return data                                               # Devuelve el payload.

def decode_magic_token(token: str) -> Dict[str, Any]:         # Decodifica y valida un magic token.
    """Decodifica un token y verifica que sea de tipo 'magic'. Lanza JWTError/ValueError si no es válido."""  # Docstring.
    data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Decodifica y valida firma/expiración.
    if data.get("type") != "magic":                           # Comprueba claim de tipo.
        raise ValueError("Invalid token type for magic token")   # Lanza error si no corresponde.
    return data                                               # Devuelve el payload.

def verify_access_token(token: str) -> dict | None:           # Mantiene tu función de verificación existente.
    """
    Verifica la validez de un token (firma + expiración).     # Docstring de alto nivel.
    Devuelve el payload si es válido o None si la validación falla. # Comportamiento retrocompatible.
    """                                                       # Cierra docstring.
    try:                                                      # Abre bloque try/except para captura segura.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Decodifica con verificación estándar.
        return payload                                        # Si todo va bien, retorna el payload.
    except JWTError:                                          # Ante cualquier error de decodificación/verificación...
        return None                                           # Devuelve None (compatibilidad con tu implementación previa).
