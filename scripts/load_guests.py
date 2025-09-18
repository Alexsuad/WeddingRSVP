# scripts/load_guests.py
# Carga y validación robusta con normalizaciones y reporte de errores por lote.

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd

# ==============================================================================
# ✅ Bootstrap de imports: asegura que 'utils' sea importable desde /scripts
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from utils.invite import normalize_invite_type  # <- AQUÍ está el helper real
except Exception as e:
    raise ImportError(
        "No pude importar 'utils.invite.normalize_invite_type'. "
        "Verifica que exista utils/__init__.py y ejecuta el comando desde la raíz del proyecto."
    ) from e
# ==============================================================================


# --- Constantes de Configuración ---
REQUIRED_COLUMNS: List[str] = [
    "full_name", "email", "phone", "language", "max_accomp", "invite_type",
]
VALID_LANGUAGES = {"es", "en", "ro"}
VALID_SIDES = {"bride", "groom"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Helpers de normalización/validación ---
def normalize_phone(phone: str) -> str:
    """Deja solo dígitos y un '+' inicial si existe. Colapsa múltiples '+'. Quita espacios/guiones."""
    if not isinstance(phone, str):
        return ""
    raw = re.sub(r"[^\d+]", "", phone.strip())
    raw = re.sub(r"^\++", "+", raw)
    return raw


def is_valid_phone_e164ish(phone: str) -> bool:
    """
    Acepta '+NNNN...' (8 a 15 dígitos totales) o solo dígitos (8 a 15).
    No valida región estricta (para eso usaríamos 'phonenumbers').
    """
    if not phone:
        return False
    if phone.startswith("+"):
        digits = re.sub(r"\D", "", phone[1:])
    else:
        digits = re.sub(r"\D", "", phone)
    return 8 <= len(digits) <= 15


def _read_table(
    file_path: str, *, sheet_name: Optional[str] = None, csv_sep: str = ",", csv_encoding: str = "utf-8"
) -> pd.DataFrame:
    """Lee .xlsx/.xls o .csv con dtype=str y fillna('')."""
    if file_path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path, dtype=str, sheet_name=sheet_name).fillna("")
    elif file_path.lower().endswith(".csv"):
        return pd.read_csv(file_path, dtype=str, sep=csv_sep, encoding=csv_encoding).fillna("")
    else:
        # Intento flexible: primero Excel, si falla intenta CSV
        try:
            return pd.read_excel(file_path, dtype=str, sheet_name=sheet_name).fillna("")
        except Exception:
            return pd.read_csv(file_path, dtype=str, sep=csv_sep, encoding=csv_encoding).fillna("")


# --- Función Principal de Validación ---
def load_and_validate_guest_list(
    file_path: str,
    strict: bool = True,
    *,
    sheet_name: Optional[str] = None,
    csv_sep: str = ",",
    csv_encoding: str = "utf-8",
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Devuelve (df_validado, errores). Si strict=True y hay errores, lanza ValueError.
    Permite elegir sheet_name en Excel y separador/encoding en CSV.
    """
    # --- 1) Carga ---
    try:
        df = _read_table(file_path, sheet_name=sheet_name, csv_sep=csv_sep, csv_encoding=csv_encoding)
    except FileNotFoundError:
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo '{file_path}': {e}")

    # --- 1.1) Normalización de encabezados ---
    df.columns = df.columns.str.strip().str.lower()
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    # 'guest_code' es opcional
    if "guest_code" not in df.columns:
        missing_cols = [c for c in missing_cols if c != "guest_code"]
    if missing_cols:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing_cols)}")

    errors: List[str] = []
    validated_rows = []

    # --- 2) Validación fila a fila ---
    for idx, row in df.iterrows():
        row_num = idx + 2

        full_name = row.get("full_name", "").strip()
        language = (row.get("language", "") or "").strip().lower()

        # ✅ Normaliza invite_type con el helper centralizado
        invite_type_ui = normalize_invite_type(row.get("invite_type"))          # Normaliza a valores de UI: 'full' o 'reception'.
        invite_type = "full" if invite_type_ui == "full" else "ceremony"        # Traduce a los valores que espera el backend: 'full' o 'ceremony'.


        # ✅ Email vacío => None
        email = (row.get("email", "") or "").strip()
        if not email:
            email = None

        phone = normalize_phone(row.get("phone", ""))

        # Opcionales
        side = (row.get("side", "") or "").strip().lower()
        if side and side not in VALID_SIDES:
            side = ""

        relationship = (row.get("relationship", "") or "").strip()
        if len(relationship) > 120:
            relationship = relationship[:120]

        group_id = (row.get("group_id", "") or "").strip()
        if len(group_id) > 80:
            group_id = group_id[:80]

        # Reglas
        if not full_name:
            errors.append(f"Fila {row_num}: 'full_name' está vacío.")
        if language not in VALID_LANGUAGES:
            errors.append(f"Fila {row_num}: idioma '{row.get('language')}' no válido. Use: es, en, ro.")

        if not email and not phone:
            errors.append(f"Fila {row_num}: debe proveer email o phone (al menos uno).")

        if email and not EMAIL_RE.match(email):
            errors.append(f"Fila {row_num}: email '{email}' parece inválido.")

        if phone and not is_valid_phone_e164ish(phone):
            errors.append(f"Fila {row_num}: phone '{phone}' no parece válido (8–15 dígitos).")

        # max_accomp
        try:
            max_accomp = int((row.get("max_accomp", 0) or "0").strip())
            if not (0 <= max_accomp <= 10):
                errors.append(f"Fila {row_num}: max_accomp '{max_accomp}' fuera de rango (0–10).")
        except Exception:
            errors.append(f"Fila {row_num}: max_accomp inválido, debe ser entero >= 0.")
            max_accomp = 0

        # Recolecta fila normalizada
        normalized = row.copy()
        normalized["full_name"] = full_name
        normalized["language"] = language
        normalized["invite_type"] = invite_type
        normalized["email"] = email
        normalized["phone"] = phone
        normalized["max_accomp"] = max_accomp
        normalized["side"] = side
        normalized["relationship"] = relationship
        normalized["group_id"] = group_id

        # guest_code es opcional: si viene en el CSV se respeta; si no, lo generará el backend
        validated_rows.append(normalized)

    clean_df = pd.DataFrame(validated_rows)

    # --- 3) Duplicados útiles de detectar (warning) ---
    for col in ["email", "phone"]:
        non_empty = clean_df[clean_df[col].notna()]
        if not non_empty.empty:
            dups = non_empty[non_empty[col].duplicated(keep=False)].sort_values(col)
            if not dups.empty:
                idxs = ", ".join(map(str, (dups.index + 2)))
                errors.append(f"Posibles duplicados en '{col}': filas {idxs}")

    if strict and errors:
        raise ValueError("Errores de validación:\n- " + "\n- ".join(errors))

    return clean_df, errors


# --- Helper opcional: DataFrame -> records (list[dict]) listo para importador admin ---
EXPORT_COLUMNS = [
    "full_name", "email", "phone", "language", "max_accomp", "invite_type",
    "side", "relationship", "group_id", "guest_code",
]

def df_to_records(df: pd.DataFrame) -> List[dict]:
    """Devuelve solo las columnas esperadas por el importador admin, listas para JSON."""
    existing_export_cols = [col for col in EXPORT_COLUMNS if col in df.columns]
    return df[existing_export_cols].to_dict(orient="records")


if __name__ == "__main__":
    # Este módulo está pensado para ser importado por scripts/import_guests.py
    print("load_guests.py: módulo utilitario. Úsalo desde scripts/import_guests.py")
