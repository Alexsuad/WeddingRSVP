# scripts/check_translations.py  # Script de utilidad para verificar paridad de traducciones.                  # Indica la ruta y propósito del script.

# ==========================================================================================                                                         # Separador visual de sección.
# 🔍 Verificador de paridad de claves i18n                                                                                                           # Título descriptivo.
# ------------------------------------------------------------------------------------------                                                         # Separador.
# Este script NO es parte del backend en producción.                                                                                                 # Aclaración de alcance.
# - Comprueba que todas las claves del idioma base ("en") existan también en "es" y "ro".                                                            # Descripción funcional.
# - También avisa si "es" o "ro" tienen claves extra que no estén en "en" (posibles typos/obsoletas).                                                # Detalle de utilidad.
# - Es robusto al layout: funciona si translations.py está en utils/translations.py o app/utils/translations.py.                                     # Nota de robustez.
# ==========================================================================================                                                         # Fin encabezado.

import sys                                      # Módulo del intérprete (para tocar sys.path).                                                      # Import sys.
from pathlib import Path                        # Manejo de rutas multiplataforma.                                                                  # Import Path.

# --- Asegurar que la RAÍZ del proyecto esté en sys.path ---                                                                                       # Sección: preparar PYTHONPATH.
ROOT = Path(__file__).resolve().parents[1]      # Calcula la carpeta raíz del repo (sube un nivel desde /scripts).                                 # ROOT = ../
sys.path.insert(0, str(ROOT))                   # Inserta la raíz al inicio del sys.path para que los imports absolutos funcionen.                   # Prepara import.

# --- Importar TRANSLATIONS con fallback de ruta ---                                                                                                # Sección: import robusto.
try:                                            # Intenta importar desde utils/translations.py (layout 1).                                          # Try import 1.
    from utils.translations import TRANSLATIONS # Import directo si existe carpeta utils/ en la raíz.                                                # Import A.
except ModuleNotFoundError:                     # Si no existe 'utils' como paquete...                                                               # Except A.
    try:                                        # Intenta importar desde app/utils/translations.py (layout 2).                                       # Try import 2.
        from app.utils.translations import TRANSLATIONS  # Import alternativo si translations vive bajo app/utils/.                                 # Import B.
    except ModuleNotFoundError as e:            # Si tampoco existe 'app.utils'...                                                                   # Except B.
        # Mensaje de error claro explicando cómo solucionarlo.                                                                                      # Comentario explicativo.
        raise SystemExit(                       # Interrumpe el script con salida limpia y mensaje.                                                  # Aborta con mensaje.
            "No pude importar TRANSLATIONS. Verifica que exista 'utils/translations.py' o 'app/utils/translations.py'.\n"
            f"sys.path[0:3]={sys.path[0:3]}  ROOT={ROOT}"  # Muestra pistas de depuración.                                                          # Pistas debug.
        ) from e

# --- Configuración del chequeo ---                                                                                                                 # Sección: parámetros de verificación.
BASE_LANG = "en"                                # Idioma base para comparar (fuente de verdad).                                                      # Base = en.
TARGET_LANGS = ["es", "ro"]                     # Idiomas a verificar contra el base.                                                                # Targets.

# --- Obtener el conjunto de claves del idioma base ---                                                                                             # Sección: claves base.
base_keys = set(TRANSLATIONS[BASE_LANG].keys()) # Conjunto de todas las claves del idioma base.                                                     # Keys en.

# --- Recorrer idiomas destino y calcular diferencias ---                                                                                           # Sección: comparación.
for lg in TARGET_LANGS:                         # Itera por cada idioma a verificar.                                                                 # Bucle idiomas.
    lg_keys = set(TRANSLATIONS[lg].keys())      # Conjunto de claves del idioma actual.                                                             # Keys lg.
    missing = base_keys - lg_keys               # Claves que faltan en 'lg' (están en en pero no en lg).                                            # Diferencia faltantes.
    extra = lg_keys - base_keys                 # Claves que sobran en 'lg' (están en lg pero no en en).                                            # Diferencia sobrantes.

    # --- Reporte en consola ordenado alfabéticamente ---                                                                                           # Sección: salida.
    print(f"[{lg}] faltan: {sorted(missing)}")  # Muestra las faltantes (añádelas en TRANSLATIONS[{lg}]).                                           # Print faltantes.
    print(f"[{lg}] extra:   {sorted(extra)}")   # Muestra las extra (revisa typos u obsoletas).                                                     # Print extra.
