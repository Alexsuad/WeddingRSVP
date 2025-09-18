# app/utils/invite.py                                                                        # Declara la ruta y nombre del módulo (nuevo archivo).

def normalize_invite_type(raw: str | None) -> str:                                           # Define función para normalizar la invitación a valores lógicos.
    """
    Normaliza invite_type hacia dos categorías lógicas:                                       # Explica objetivo de la función.
    - "full": Ceremonia + Recepción                                                           # Define significado de "full".
    - "reception": Solo Recepción                                                             # Define significado de "reception".
                                                                                              # Línea en blanco para legibilidad.
    Acepta los valores que ya se usan en tu BD/Excel:                                         # Indica compatibilidad hacia atrás.
    - "full"     -> "full"                                                                    # Mantiene "full".
    - "ceremony" -> "reception"  (tu regla: si no es FULL, es solo Recepción)                 # Mapea "ceremony" a solo recepción.
    Cualquier otro valor/None -> "reception" (fail-safe)                                      # Aclara el fallback seguro.
    """                                                                                        # Cierra docstring.
    val = (raw or "").strip().lower()                                                         # Limpia el valor de entrada (None/espacios/mayúsculas).
    if val == "full":                                                                         # Comprueba si es "full".
        return "full"                                                                         # Devuelve "full" sin cambios.
    if val == "ceremony":                                                                     # Comprueba si es "ceremony".
        return "reception"                                                                    # Mapea a "reception" según la regla de negocio.
    return "reception"                                                                        # Fallback por defecto: solo recepción.


def is_invited_to_ceremony(raw: str | None) -> bool:                                          # Define helper booleano para "invita a ceremonia".
    """
    True solo cuando el invitado está invitado a ceremonia (caso "full").                     # Explica retorno.
    """                                                                                        # Cierra docstring.
    return normalize_invite_type(raw) == "full"                                               # Devuelve True si la invitación normalizada es "full".
