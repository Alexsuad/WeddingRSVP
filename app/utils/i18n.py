# app/utils/i18n.py                                                               # Ubicación del módulo central de i18n (nuevo o reemplazo).

from __future__ import annotations                                                # Habilita anotaciones pospuestas para compatibilidad (Python 3.8+).

# =================================================================================
# 🔤 Resolución de idioma: payload > DB > Accept-Language > heurística email > default
# =================================================================================

SUPPORTED_LANGS = {"es", "en", "ro"}                                             # Conjunto de idiomas soportados por el sistema.

def _base_lang(code: str | None) -> str | None:                                  # Normaliza un código de idioma potencialmente regional.
    """Normaliza 'es-ES', 'en-GB', 'ro-RO' a 'es'/'en'/'ro'; None si no está soportado."""  # Explica el comportamiento esperado.
    if not code:                                                                  # Si no hay valor...
        return None                                                               # ...retorna None (sin candidato).
    code = code.strip().lower()                                                   # Limpia espacios y pasa a minúsculas.
    if not code:                                                                  # Si quedó vacío tras limpiar...
        return None                                                               # ...no hay valor útil, retorna None.
    primary = code.split(",")[0].split(";")[0].strip()                            # Toma el primer item antes de coma o ;q= (para headers).
    primary = primary.split("-")[0]                                               # Se queda con el subtipo primario (ej. 'es' de 'es-ES').
    return primary if primary in SUPPORTED_LANGS else None                        # Devuelve base si está soportado; si no, None.

def _from_accept_language(header: str | None) -> str | None:                      # Extrae idioma desde 'Accept-Language'.
    """Devuelve el primer idioma soportado declarado en Accept-Language; None si no hay match."""  # Parser simple (suficiente para MVP).
    return _base_lang(header)                                                      # Reusa normalización para obtener 'es'/'en'/'ro' o None.

def _heuristic_lang_from_email(email: str | None) -> str | None:                  # Heurística conservadora por TLD de email.
    """
    Infiere 'ro' si el email termina en '.ro' y 'es' si termina en '.es'.
    Si no hay certeza, devuelve None para no pisar el fallback ('es').
    """                                                                            # Documenta reglas e intención de no forzar 'en'.
    if not email:                                                                  # Si no se pasó email...
        return None                                                                 # ...no se puede inferir, retorna None.
    e = email.strip().lower()                                                      # Normaliza email.
    if e.endswith(".ro"):                                                          # Si termina en .ro...
        return "ro"                                                                # ...elige rumano.
    if e.endswith(".es"):                                                          # Si termina en .es...
        return "es"                                                                # ...elige español.
    return None                                                                    # Otros TLD (.com/.net/...) → no inferir.

def resolve_lang(                                                                 # Interfaz pública para resolver idioma final.
    payload_lang: str | None,                                                      # Idioma explícito del payload (puede venir como 'es-ES').
    guest_lang: str | None,                                                        # Idioma preferido guardado en DB para el invitado.
    accept_language_header: str | None = None,                                     # Cabecera HTTP 'Accept-Language' (opcional).
    email: str | None = None,                                                      # Email para heurística por TLD (opcional).
    default: str = "es",                                                           # Fallback consistente del proyecto (acordado: 'es').
) -> str:                                                                          # Devuelve siempre un idioma soportado ('es'/'en'/'ro').
    """Resuelve y devuelve siempre un idioma soportado ('es'/'en'/'ro')."""        # Docstring de la función.
    cand = _base_lang(payload_lang)                                                # 1) Normaliza candidato del payload.
    if cand:                                                                       # Si es válido...
        return cand                                                                # ...respeta lo solicitado por el cliente.

    cand = _base_lang(guest_lang)                                                  # 2) Normaliza el idioma persistido en DB.
    if cand:                                                                       # Si es válido...
        return cand                                                                # ...usa preferencia del invitado.

    cand = _from_accept_language(accept_language_header)                           # 3) Intenta con Accept-Language del navegador.
    if cand:                                                                       # Si hay match soportado...
        return cand                                                                # ...úsalo como tercera prioridad.

    cand = _heuristic_lang_from_email(email)                                       # 4) Heurística conservadora por TLD (.es/.ro).
    if cand:                                                                       # Si hay inferencia con certeza...
        return cand                                                                # ...aplícalo.

    return default if default in SUPPORTED_LANGS else "es"                         # 5) Fallback estable ('es'), garantizando soporte.
