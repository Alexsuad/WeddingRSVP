# scripts/fix_routes.py  # Script para normalizar rutas/calls de navegación en toda la app.

import argparse  # Permite leer flags/argumentos desde la línea de comandos.
import re        # Proporciona expresiones regulares para buscar y reemplazar con precisión.
from pathlib import Path  # Facilita el recorrido recursivo de archivos en el proyecto.
from datetime import datetime  # Sirve para sellar backups con fecha/hora.
import sys      # Permite salir con códigos y escribir en stdout/stderr.

# --- Configuración de patrones a corregir (regex → reemplazo) ---
PATTERNS = [  # Lista de reglas, cada una con su regex y el replacement correspondiente.
    # Redirección antigua al "app_principal" → ahora debe ir al login multipágina.
    (re.compile(r'''st\.switch_page\(["']\.\./app_principal\.py["']\)'''), 'st.switch_page("pages/0_Login.py")'),
    # Variantes del login con emoji (con o sin prefijo "pages/").
    (re.compile(r'''st\.switch_page\(["'](?:pages/)?0_🔑_Login\.py["']\)'''), 'st.switch_page("pages/0_Login.py")'),
    # Variantes del formulario con emoji (con o sin prefijo "pages/").
    (re.compile(r'''st\.switch_page\(["'](?:pages/)?1_📝_Formulario_RSVP\.py["']\)'''), 'st.switch_page("pages/1_Formulario_RSVP.py")'),
    # Variantes de confirmado con emoji (con o sin prefijo "pages/").
    (re.compile(r'''st\.switch_page\(["'](?:pages/)?2_✅_Confirmado\.py["']\)'''), 'st.switch_page("pages/2_Confirmado.py")'),
    # Llamadas a confirmado sin carpeta (por si alguna quedó sin 'pages/').
    (re.compile(r'''st\.switch_page\(["']2_Confirmado\.py["']\)'''), 'st.switch_page("pages/2_Confirmado.py")'),
    # Modernización de rerun (API nueva).
    (re.compile(r'''st\.experimental_rerun\(\)'''), 'st.rerun()'),
]

# --- Configuración de qué archivos procesar ---
INCLUDE_EXTS = {".py"}  # Extensiones de archivo a analizar (solo Python).
EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}  # Carpetas a ignorar.

def should_skip(path: Path) -> bool:
    """Indica si un path debe omitirse (por estar en carpetas excluidas)."""  # Explica el propósito de la función.
    parts = set(p.name for p in path.parents)  # Construye un set con los nombres de todos los directorios padres.
    return any(d in parts for d in EXCLUDE_DIRS)  # Devuelve True si alguno de los directorios excluidos aparece en la ruta.

def process_file(path: Path, apply: bool, make_backup: bool) -> int:
    """Busca y reemplaza patrones en un archivo; retorna el número de cambios realizados."""  # Docstring descriptivo.
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")  # Lee el contenido del archivo como texto UTF-8.
    except Exception as e:
        print(f"[SKIP] No se pudo leer: {path} ({e})")  # Informa si no se puede leer el archivo.
        return 0  # No hay cambios si no se pudo abrir.

    original = text  # Guarda el contenido original para comparar después.
    total_changes = 0  # Contador de reemplazos efectuados en este archivo.

    for regex, repl in PATTERNS:  # Itera sobre cada patrón definido.
        def _log_sub(match: re.Match) -> str:
            """Callback para logging: muestra la línea que se cambiará y el reemplazo."""  # Docstring del callback.
            nonlocal total_changes  # Permite modificar la variable del scope externo.
            total_changes += 1  # Incrementa el contador de cambios.
            line_no = text.count("\n", 0, match.start()) + 1  # Calcula el número de línea del match.
            snippet = match.group(0)  # Captura el fragmento exacto que se reemplazará.
            print(f"[{path}] L{line_no}: {snippet}  -->  {repl}")  # Imprime un log legible del cambio.
            return repl  # Devuelve el texto de reemplazo que usará re.sub.

        text = regex.sub(_log_sub, text)  # Aplica el reemplazo con logging por cada ocurrencia encontrada.

    if total_changes and apply:  # Si hubo cambios y estamos en modo aplicar…
        if make_backup:  # Si se solicitó crear un backup…
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")  # Genera un sello temporal legible.
            backup_path = path.with_suffix(path.suffix + f".bak.{ts}")  # Define el nombre del archivo backup.
            try:
                backup_path.write_text(original, encoding="utf-8")  # Escribe el contenido original en el backup.
                print(f"[BACKUP] Copia creada: {backup_path}")  # Informa que se creó el backup.
            except Exception as e:
                print(f"[WARN] No se pudo crear backup para {path}: {e}")  # Advierte si falló la creación del backup.
        try:
            path.write_text(text, encoding="utf-8")  # Sobrescribe el archivo con el contenido ya modificado.
            print(f"[WRITE] Guardado: {path}")  # Confirma que el archivo fue guardado.
        except Exception as e:
            print(f"[ERROR] No se pudo escribir en {path}: {e}")  # Reporta un error de escritura.
            return 0  # Si no se pudo escribir, consideramos 0 cambios efectivos.

    return total_changes  # Devuelve la cantidad de cambios detectados/aplicados en este archivo.

def main():
    """Punto de entrada: recorre el proyecto y normaliza rutas/calls de navegación."""  # Docstring del main.
    parser = argparse.ArgumentParser(description="Normaliza rutas de Streamlit (switch_page/rerun) en todo el repo.")  # Crea parser CLI.
    parser.add_argument("--root", default=".", help="Carpeta raíz del proyecto (por defecto: .)")  # Permite indicar otra raíz.
    parser.add_argument("--apply", action="store_true", help="Aplica los cambios (si no, solo vista previa).")  # Flag de modo aplicar.
    parser.add_argument("--no-backup", action="store_true", help="No crear archivos .bak al aplicar cambios.")  # Flag para omitir backup.
    args = parser.parse_args()  # Parsea los argumentos proporcionados por el usuario.

    root = Path(args.root).resolve()  # Normaliza la ruta raíz a un Path absoluto.
    apply = bool(args.apply)  # Convierte el flag a booleano claro.
    make_backup = not bool(args.no_backup)  # Determina si se crearán backups (por defecto, sí).

    print(f"[INFO] Raíz: {root}")  # Muestra la raíz desde donde se realizará el barrido.
    print(f"[INFO] Modo: {'APLICAR' if apply else 'VISTA PREVIA'}")  # Indica si se aplican cambios o solo se listan.
    if apply:
        print(f"[INFO] Backups: {'SÍ' if make_backup else 'NO'}")  # Informa si se crearán backups en modo aplicar.

    total_files = 0  # Contará la cantidad de archivos inspeccionados.
    total_changes = 0  # Contará la cantidad total de cambios en todo el recorrido.

    for path in root.rglob("*"):  # Recorre recursivamente todos los paths a partir de la raíz.
        if path.is_dir():  # Si el path es una carpeta…
            if path.name in EXCLUDE_DIRS:  # …y es una carpeta a excluir…
                continue  # …la salta sin procesar su contenido.
            if should_skip(path):  # Si la ruta contiene alguno de los directorios excluidos…
                continue  # …también la omite.
            continue  # Si es una carpeta no excluida, continúa (los archivos se procesan abajo).
        if path.suffix not in INCLUDE_EXTS:  # Si la extensión del archivo no es .py…
            continue  # …no lo procesamos (centrado en código Python).
        if should_skip(path):  # Si el archivo está dentro de una carpeta excluida…
            continue  # …no lo procesamos.
        total_files += 1  # Incrementa el contador de archivos analizados.
        changes = process_file(path, apply=apply, make_backup=make_backup)  # Procesa el archivo y obtiene cambios.
        total_changes += changes  # Acumula la cantidad de reemplazos del archivo actual.

    print(f"[RESUMEN] Archivos analizados: {total_files}")  # Muestra cuántos archivos se inspeccionaron.
    print(f"[RESUMEN] Reemplazos detectados: {total_changes}")  # Muestra el número total de reemplazos.
    if not apply and total_changes:  # Si fue vista previa y hubo coincidencias…
        print("[TIP] Ejecuta con --apply para escribir los cambios. Añade --no-backup si no quieres .bak.")  # Sugerencia útil.

if __name__ == "__main__":  # Punto estándar de entrada cuando se ejecuta como script.
    try:
        main()  # Llama a la función principal para iniciar el proceso.
    except KeyboardInterrupt:
        sys.exit(130)  # Permite salir con Ctrl+C devolviendo un código de interrupción estándar.
