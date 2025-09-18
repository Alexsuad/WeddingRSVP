# scripts/import_guests.py
# =============================================================================
# 🚚 Importador masivo de invitados hacia el backend (endpoint admin).
# - Valida/normaliza el archivo (xlsx/csv) con load_and_validate_guest_list().
# - Convierte el DataFrame a records (df_to_records) y envía en lotes a:
#     POST /api/admin/import-guests
# - Requiere ADMIN_API_KEY (cabecera: x-admin-key).
# =============================================================================

import os
import sys
import json
import argparse
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path # ✅ AJUSTE: Importamos Path para construir la ruta.

# ==============================================================================
# ✅ AJUSTE CRÍTICO: Añadir la raíz del proyecto al path de Python ANTES de nada.
# ------------------------------------------------------------------------------
# Esto soluciona el 'ModuleNotFoundError' al permitir que este script
# y cualquier módulo que importe (como load_guests) encuentren la carpeta 'app'.
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Carga .env temprano ---
load_dotenv()

# --- Import robusto del validador, funcione donde se ejecute ---
# Ahora que el path está corregido, este bloque funcionará sin problemas.
try:
    from load_guests import load_and_validate_guest_list, df_to_records
    HAS_DF_TO_RECORDS = True
except (ImportError, ModuleNotFoundError): # Capturamos errores específicos
    from load_guests import load_and_validate_guest_list
    HAS_DF_TO_RECORDS = False

# --- Config por entorno (sin cambios) ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "supersecreto123")

ENDPOINT = f"{API_BASE_URL.rstrip('/')}/api/admin/import-guests"

# --- Funciones _post_batch y main (sin cambios) ---
def _post_batch(records: list[dict], timeout: int = 60) -> dict:
    """Envía un lote al endpoint admin y devuelve el JSON de respuesta (o error claro)."""
    headers = {
        "Content-Type": "application/json",
        "x-admin-key": ADMIN_API_KEY,
    }
    payload = {"items": records}
    resp = requests.post(ENDPOINT, headers=headers, data=json.dumps(payload), timeout=timeout)
    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"HTTP {resp.status_code} - {detail}")
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="Importador masivo de invitados.")
    parser.add_argument("file", help="Ruta al archivo .xlsx/.xls o .csv")
    parser.add_argument("--sheet", default=None, help="Nombre de hoja en Excel (opcional)")
    parser.add_argument("--sep", default=",", help="Separador para CSV (por defecto ',')")
    parser.add_argument("--encoding", default="utf-8", help="Encoding para CSV (por defecto utf-8)")
    parser.add_argument("--batch", type=int, default=200, help="Tamaño de lote (por defecto 200)")
    parser.add_argument("--strict", action="store_true", help="Falla si hay cualquier error de validación")
    parser.add_argument("--dry-run", action="store_true", help="Solo valida y muestra vista previa; no importa")
    args = parser.parse_args()

    file_path = args.file
    print(f"📥 Cargando archivo: {file_path}")

    try:
        df, errors = load_and_validate_guest_list(
            file_path,
            strict=args.strict,
            sheet_name=args.sheet,
            csv_sep=args.sep,
            csv_encoding=args.encoding,
        )
    except Exception as e:
        print(f"❌ Error al validar: {e}")
        sys.exit(1)

    if errors:
        print("⚠️  Advertencias/errores detectados en validación:")
        print(" - " + "\n - ".join(errors))

    if df.empty:
        print("⛔ No hay registros para importar (DataFrame vacío).")
        sys.exit(1)

    if HAS_DF_TO_RECORDS:
        records = df_to_records(df)
    else:
        records = df.to_dict(orient="records")

    print(f"📦 Registros preparados para importar: {len(records)}")

    if args.dry_run:
        print("🧪 DRY-RUN activo: no se enviará nada al backend.")
        print("🔎 Vista previa (primeros 3 registros):")
        print(json.dumps(records[:3], indent=2, ensure_ascii=False))
        sys.exit(0)

    batch_size = max(1, args.batch)
    total = len(records)
    created = updated = skipped = 0
    all_errors: list[str] = []

    print(f"➡️  Importando en lotes de {batch_size} hacia {ENDPOINT}")
    for i in range(0, total, batch_size):
        chunk = records[i:i + batch_size]
        try:
            result = _post_batch(chunk)
            created += int(result.get("created", 0))
            updated += int(result.get("updated", 0))
            skipped += int(result.get("skipped", 0))
            errs = result.get("errors", []) or []
            if errs:
                all_errors.extend(errs)
            print(f"   ✓ Lote {i//batch_size + 1}: +{result.get('created',0)} creados, "
                  f"+{result.get('updated',0)} actualizados, +{result.get('skipped',0)} omitidos")
        except Exception as e:
            msg = f"Lote {i//batch_size + 1} (filas {i+1}-{min(i+batch_size, total)}): {e}"
            print(f"   ✗ {msg}")
            all_errors.append(msg)
            skipped += len(chunk)

    print("\n✅ Resumen de importación:")
    print(json.dumps(
        {"created": created, "updated": updated, "skipped": skipped, "errors": all_errors},
        indent=2, ensure_ascii=False
    ))

    if all_errors:
        print("\n⚠️  Hubo errores/omisiones. Revisa el detalle arriba.")

if __name__ == "__main__":
    main()