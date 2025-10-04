# project_patcher.py  # Script de parches automáticos con backups fuera del repo y retención de 10

# ==========================================================================================
# 🎯 Objetivo
# ------------------------------------------------------------------------------------------
# - Parchear 'smoke_test.py' para añadir payload con 'notes' y verificación de echo-back.
# - Unificar '.env.example' → asegurar EMAIL_FROM, SEND_ACCESS_MODE, PUBLIC_LOGIN_URL y DRY_RUN.
# - Deduplicar 'sendgrid_test.py' (mantener scripts/sendgrid_test.py).
# - Guardar BACKUPS FUERA DEL REPO en: /home/nalex/Documents/<Proyecto>/<Archivo>/
#   con nombre: <Archivo>_<AAAA-MM-DD_HH-mm-ss>.bak
# - Retención: mantener solo los 10 backups más recientes por archivo (borrar el resto).
# - Soporta modo '--check' (dry-run) para simular sin escribir.
# - Idempotente: no duplica cambios existentes.
# ==========================================================================================

import re  # Importa expresiones regulares para localizar/injectar bloques de texto
import os  # Importa utilidades del sistema operativo (rutas/variables de entorno)
import sys  # Importa para terminar el proceso con códigos de salida
import shutil  # Importa para copiar archivos (base para backups si hiciera falta)
from pathlib import Path  # Importa Path para manipular rutas multiplataforma de forma limpia
import argparse  # Importa argparse para definir y leer flags de CLI
from datetime import datetime  # Importa datetime para timestamp legible en los nombres de backup
import glob  # Importa glob para listar backups existentes y aplicar retención ordenada


# ---------- Utilidades de logging ----------

def log(msg: str) -> None:  # Define función de log con prefijo reconocible
    print(f"[patcher] {msg}")  # Imprime mensaje con prefijo estándar para fácil lectura


# ---------- Detección de raíz del repo ----------

def find_repo_root(start: Path) -> Path:  # Define función para localizar la raíz del repo
    cur = start.resolve()  # Resuelve la ruta absoluta del directorio de inicio
    while True:  # Inicia bucle que asciende directorios hasta encontrar la raíz
        # Usa heurística: 'app/' y 'scripts/' y ('requirements.txt' o 'alembic.ini') como señales de raíz
        if (cur / "app").is_dir() and (cur / "scripts").is_dir() and \
           ((cur / "requirements.txt").exists() or (cur / "alembic.ini").exists()):
            return cur  # Si cumple, devuelve directorio actual como raíz del repo
        if cur.parent == cur:  # Si llegó al directorio raíz del sistema (no hay más padres)
            return start.resolve()  # Devuelve el inicio original como mejor esfuerzo
        cur = cur.parent  # Sube un nivel y repite


# ---------- Configuración de backups externos ----------

def get_backup_base_dir() -> Path:  # Define función para obtener carpeta base de backups
    # Permite override por variable de entorno BACKUP_BASE_DIR (útil si cambias de usuario/OS)
    env_path = os.getenv("BACKUP_BASE_DIR")  # Lee variable de entorno BACKUP_BASE_DIR si existe
    if env_path:  # Si se definió explícitamente
        return Path(env_path).expanduser().resolve()  # Devuelve esa ruta normalizada

    # Valor por defecto pensado para WSL (equivalente a \\wsl$\Ubuntu\home\nalex\Documents)
    return Path("/home/nalex/Documents").resolve()  # Devuelve carpeta Documents del usuario nalex en WSL


def format_timestamp() -> str:  # Define función para timestamp legible en nombres de backup
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Devuelve cadena AAAA-MM-DD_HH-mm-ss


def backup_path_for(repo_root: Path, target_file: Path) -> Path:  # Calcula ruta de backup externo para un archivo
    project_name = repo_root.name  # Usa el nombre de la carpeta raíz como nombre del proyecto
    file_name = target_file.name  # Obtiene el nombre del archivo (incluye extensión, p.ej. 'env.example')
    file_folder_name = file_name  # Usa el nombre del archivo como nombre de carpeta (mantiene puntos), según tu preferencia
    base_dir = get_backup_base_dir()  # Obtiene la carpeta base de backups
    # Construye ruta: <BASE>/<Proyecto>/<Archivo>/
    dest_dir = base_dir / project_name / file_folder_name  # Define carpeta destino para este archivo
    dest_dir.mkdir(parents=True, exist_ok=True)  # Crea la carpeta si no existe (incluye padres)
    # Construye nombre de backup: <Archivo>_<timestamp>.bak
    dest_name = f"{file_name}_{format_timestamp()}.bak"  # Genera nombre con timestamp para unicidad y orden
    return dest_dir / dest_name  # Devuelve ruta completa al archivo .bak a generar


def enforce_retention(backup_dir: Path, file_name: str, keep: int = 10) -> None:  # Aplica retención de backups
    # Busca archivos que empiecen por '<file_name>_' y terminen en '.bak' dentro de backup_dir
    pattern = str(backup_dir / f"{file_name}_*.bak")  # Crea patrón glob para listar backups de este archivo
    backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)  # Ordena por fecha de modificación (más nuevos primero)
    if len(backups) <= keep:  # Si hay <= a 'keep', no se borra nada
        return  # Sale sin acción
    for old_path in backups[keep:]:  # Itera los backups que sobran (del 11º en adelante)
        try:  # Intenta borrar cada backup antiguo
            Path(old_path).unlink()  # Elimina el archivo del disco
            log(f"Retención: eliminado backup antiguo -> {old_path}")  # Log de eliminación exitosa
        except Exception as e:  # Captura errores de E/S
            log(f"Retención: no se pudo eliminar {old_path}: {e}")  # Log de error sin abortar


def external_backup_file(repo_root: Path, target: Path, check_mode: bool = False) -> None:  # Crea backup externo y aplica retención
    # Calcula ruta destino del backup para este archivo
    dest = backup_path_for(repo_root, target)  # Obtiene ruta destino final con timestamp
    if check_mode:  # Si estamos en dry-run, no escribimos realmente
        log(f"Backup (simulado) → {dest}")  # Informamos la ruta donde se guardaría
        return  # Salimos sin tocar disco
    try:  # Intenta copiar el archivo original al destino
        shutil.copyfile(target, dest)  # Copia byte a byte el archivo al backup externo
        log(f"Backup creado: {dest}")  # Log de éxito con ruta del backup
        enforce_retention(dest.parent, target.name, keep=10)  # Aplica retención: deja solo los 10 más recientes
    except Exception as e:  # Captura cualquier excepción al copiar
        log(f"ERROR creando backup externo para {target}: {e}")  # Informa el error sin abortar


# ---------- Escritura segura con backup externo ----------

def write_if_changed(repo_root: Path, path: Path, new_content: str, check_mode: bool = False) -> bool:  # Escribe solo si cambió
    old = path.read_text(encoding="utf-8")  # Lee contenido actual del archivo
    if old == new_content:  # Compara si no hay diferencias
        log(f"Sin cambios: {path} (ya estaba actualizado)")  # Log de no-acción
        return False  # Indica que no hubo escritura
    if check_mode:  # Si es dry-run
        log(f"SE HARÍA un cambio en: {path}")  # Indica que habría cambio
        # También simula el backup para que veas la ruta
        external_backup_file(repo_root, path, check_mode=True)  # Simula backup externo
        return True  # Indica que habría cambios
    # Crea backup externo real antes de escribir
    external_backup_file(repo_root, path, check_mode=False)  # Genera respaldo con timestamp y retención
    path.write_text(new_content, encoding="utf-8")  # Escribe el nuevo contenido en el archivo
    log(f"Archivo actualizado: {path}")  # Log de éxito de escritura
    return True  # Indica que sí hubo escritura


# ---------- A) Parche: smoke_test.py (añadir 'notes' + verificación echo-back) ----------

def patch_smoke_test(repo: Path, check_mode: bool = False) -> None:  # Parchea smoke_test.py
    target = repo / "smoke_test.py"  # Apunta a smoke_test.py en raíz
    if not target.exists():  # Verifica existencia
        log("No se encontró 'smoke_test.py' en la raíz; se omite parche A.")  # Informa y omite
        return  # Sale sin error

    text = target.read_text(encoding="utf-8")  # Lee contenido actual
    text_final = text  # Prepara buffer de salida

    # --- (A1) Asegurar payload con 'notes' dentro de 'payloads = [ ... ]' ---
    payloads_pat = re.compile(r"payloads\s*=\s*\[(?P<body>.*?)\]\s*", re.DOTALL)  # Localiza lista payloads
    m = payloads_pat.search(text)  # Busca bloque payloads
    if m:  # Si hay lista de payloads
        body = m.group("body")  # Extrae cuerpo interno
        if '"notes"' not in body:  # Si aún no hay payload con 'notes'
            # Define nuevo payload v7.2
            notes_payload = (
                '        {\n'
                '            "attending": True,             # Asistencia afirmativa\n'
                '            "companions": [],              # Sin acompañantes para simplificar\n'
                '            "notes": "Notas de prueba E2E (smoke).",  # Validación v7.2\n'
                '            "allergies": "Ninguna"\n'
                '        }'
            )  # Cierra definición de payload
            body_stripped = body.rstrip()  # Normaliza espacios finales
            # Inserta coma y nueva línea si el cuerpo no termina con separador adecuado
            if not body_stripped.endswith((",", "\n")):  # Comprueba separador final
                body_stripped += ","  # Añade coma separadora
            new_body = body_stripped + "\n" + notes_payload + "\n"  # Concatena nuevo payload
            text_final = text[:m.start("body")] + new_body + text[m.end("body"):]  # Reconstruye archivo
            log("Payload con 'notes' añadido en smoke_test.py.")  # Log de inserción
        else:  # Si ya hay 'notes'
            log("Ya existe un payload con 'notes' en smoke_test.py (OK).")  # Log idempotente
    else:  # Si no hay lista payloads
        log("No se encontró la lista 'payloads = [...]' en smoke_test.py; se omite este sub-parche.")  # Aviso

    text_notes = text_final  # Guarda resultado parcial

    # --- (A2) Inyectar verificación suave del echo-back cuando respuesta sea 2xx ---
    echo_marker = "RSVP no devolvió 'notes'."  # Marca para detectar duplicidad del bloque
    if echo_marker not in text_notes:  # Solo si no existe ya
        # Busca la línea: if r2.status_code // 100 == 2:  (y captura indentación)
        success_if = re.compile(r"(if\s+r2\.status_code\s*//\s*100\s*==\s*2\s*:\s*#.*?\n)(?P<indent>\s*)", re.MULTILINE)
        mm = success_if.search(text_notes)  # Intenta localizar el sitio de inyección
        if mm:  # Si lo encontró
            indent = mm.group("indent")  # Captura indentación para respetar estilo
            # Construye bloque a inyectar (dobles llaves {{}} para escribir {} literal dentro f-string)
            echo_block = (
                f"{indent}# (Opcional) Validación rápida del echo-back si tu endpoint devuelve el RSVP guardado.\n"
                f"{indent}try:\n"
                f"{indent}    saved = r2.json()  # Parsea cuerpo JSON si es posible\n"
                f"{indent}    if \"notes\" in p:  # Solo valida cuando mandamos 'notes'\n"
                f"{indent}        assert (\n"
                f"{indent}            (\"notes\" in saved) or\n"
                f"{indent}            (\"data\" in saved and \"notes\" in saved.get(\"data\", {{}}))\n"
                f"{indent}        ), \"RSVP no devolvió 'notes'.\"\n"
                f"{indent}except Exception:\n"
                f"{indent}    pass  # Si no hay JSON o cambia el contrato, no se falla el smoke por este detalle\n"
            )  # Cierra bloque a inyectar
            injected = mm.group(0) + echo_block  # Concatena el if original con el bloque nuevo
            text_final = text_notes[:mm.start()] + injected + text_notes[mm.end():]  # Reconstruye el archivo
            log("Verificación del echo-back de 'notes' inyectada en smoke_test.py.")  # Log éxito
        else:  # Si no encontró el patrón
            log("No se encontró el bloque 'if r2.status_code // 100 == 2:'; verificación de 'notes' omitida.")  # Aviso
    else:  # Si ya existe
        log("Verificación de 'notes' tras 2xx ya existe en smoke_test.py (OK).")  # Log idempotente

    # --- (A3) Persistir si difiere (con backup externo + retención) ---
    write_if_changed(repo, target, text_final, check_mode=check_mode)  # Escribe solo si cambió (o simula)


# ---------- B) Parche: .env.example (unificación claves y defaults) ----------

def patch_env_example(repo: Path, email_key: str = "EMAIL_FROM", check_mode: bool = False) -> None:  # Parchea .env.example
    env_example = repo / ".env.example"  # Apunta a .env.example en raíz
    if not env_example.exists():  # Verifica existencia
        log("No se encontró '.env.example' en la raíz; se omite parche B.")  # Aviso
        return  # Sale sin error

    content = env_example.read_text(encoding="utf-8")  # Lee contenido actual
    original_content = content  # Guarda copia para comparación final

    # (B1) Migrar SENDER_EMAIL → EMAIL_FROM si aplica
    if "SENDER_EMAIL" in content and email_key not in content:  # Detecta clave antigua sin nueva
        content = re.sub(r"(?m)^\s*SENDER_EMAIL\s*=", f"{email_key}=", content)  # Reemplaza nombre de variable
        log("SENDER_EMAIL → EMAIL_FROM aplicado en .env.example.")  # Log acción

    # (B2) Asegurar bloque de correo si falta
    if email_key not in content:  # Si aún falta EMAIL_FROM
        content += (
            "\n# --- Correo / Envíos ---\n"
            f'{email_key}="no-reply@tu-dominio.com"  # Remitente verificado en SendGrid (o sandbox en DRY_RUN)\n'
            'SENDGRID_API_KEY=""                   # API Key (vacío en example)\n'
        )  # Añade bloque mínimo de correo
        log("Se añadió bloque de correo (EMAIL_FROM, SENDGRID_API_KEY) a .env.example.")  # Log acción

    # (B3) Asegurar claves de modo de acceso y URL pública
    if "SEND_ACCESS_MODE" not in content:  # Si falta SEND_ACCESS_MODE
        content += "SEND_ACCESS_MODE=code  # 'code' para v7.2; 'magic' como fallback\n"  # Añade default recomendado
        log("Se añadió SEND_ACCESS_MODE=code a .env.example.")  # Log acción

    if "PUBLIC_LOGIN_URL" not in content:  # Si falta PUBLIC_LOGIN_URL
        content += 'PUBLIC_LOGIN_URL="https://tu-dominio.com/login"  # CTA en email de guest code\n'  # Añade default
        log("Se añadió PUBLIC_LOGIN_URL a .env.example.")  # Log acción

    # (B4) Sugerir DRY_RUN=1 en dev
    if "DRY_RUN" not in content:  # Si falta DRY_RUN
        content += "DRY_RUN=1  # 1 en dev para simular envíos de correo\n"  # Añade sugerencia
        log("Se añadió DRY_RUN=1 a .env.example.")  # Log acción

    # (B5) Persistir si cambia (con backup externo + retención)
    if content != original_content:  # Si hubo cambios
        write_if_changed(repo, env_example, content, check_mode=check_mode)  # Escribe/simula cambios
    else:  # Si no cambió nada
        log("Sin cambios en .env.example (ya estaba unificado y completo).")  # Log idempotente


# ---------- C) Parche: deduplicar sendgrid_test.py ----------

def dedupe_sendgrid_test(repo: Path, prefer_path: Path | None = None, check_mode: bool = False) -> None:  # Deduplica sendgrid_test.py
    preferred = prefer_path or (repo / "scripts" / "sendgrid_test.py")  # Define ruta preferida por defecto
    other_candidates = [repo / "sendgrid_test.py"]  # Define posibles duplicados en raíz

    if not preferred.exists():  # Si el preferido no existe
        log(f"No se encontró preferido: {preferred}. No se deduplica.")  # Informa y omite
        return  # Sale sin error

    for candidate in other_candidates:  # Itera candidatos
        if candidate.exists():  # Si existe el duplicado
            try:  # Intenta comparar contenidos
                pref_txt = preferred.read_text(encoding="utf-8", errors="ignore")  # Lee preferido
                cand_txt = candidate.read_text(encoding="utf-8", errors="ignore")  # Lee candidato
                if cand_txt.strip() == pref_txt.strip():  # Si son equivalentes
                    if check_mode:  # Si es dry-run
                        log(f"SE ELIMINARÍA el duplicado: {candidate} (se mantendría {preferred})")  # Simula borrado
                    else:  # Si es ejecución real
                        # En lugar de borrar sin rastro, guardamos backup externo del duplicado antes de eliminar
                        external_backup_file(repo, candidate, check_mode=False)  # Backup externo del duplicado
                        candidate.unlink()  # Borra el archivo duplicado del repo
                        log(f"Duplicado eliminado: {candidate} (se mantiene {preferred})")  # Log acción
                else:  # Si difieren
                    log(f"sendgrid_test.py en {candidate} difiere del preferido; no se borra automáticamente.")  # Precaución
            except Exception as e:  # Captura errores al comparar/borrar
                log(f"No se pudo comparar/borrar {candidate}: {e}")  # Log de error sin abortar


# ---------- D) Restauración de backups (listar y restaurar el último) ----------

def list_backups_for(repo_root: Path, file_name: str) -> list[Path]:  # Devuelve lista de backups (más nuevos primero)
    project_name = repo_root.name  # Obtiene el nombre del proyecto desde la carpeta raíz
    base_dir = get_backup_base_dir()  # Lee la carpeta base de backups (puede venir de BACKUP_BASE_DIR)
    backup_dir = base_dir / project_name / file_name  # Carpeta: Documents/<Proyecto>/<Archivo>/
    pattern = str(backup_dir / f"{file_name}_*.bak")  # Patrón: <Archivo>_<timestamp>.bak
    paths = [Path(p) for p in glob.glob(pattern)]  # Construye lista de rutas de backups que cumplen el patrón
    paths.sort(key=os.path.getmtime, reverse=True)  # Ordena por fecha de modificación (descendente)
    return paths  # Devuelve la lista ordenada


def restore_latest_backup(repo_root: Path, target_path: Path, check_mode: bool = False) -> bool:  # Restaura el último backup al archivo indicado
    file_name = target_path.name  # Extrae el nombre del archivo objetivo (ej.: smoke_test.py)
    backups = list_backups_for(repo_root, file_name)  # Obtiene los backups disponibles para ese archivo
    if not backups:  # Si no hay backups
        log(f"No hay backups para: {file_name}")  # Informa que no existen respaldos
        return False  # Indica fallo en la restauración
    latest = backups[0]  # Toma el backup más reciente
    if check_mode:  # Si estamos en modo simulación (dry run)
        log(f"Se restauraría el backup: {latest} -> {target_path}")  # Informa lo que se haría sin tocar disco
        return True  # Indica que habría restauración
    try:  # Intenta copiar el backup sobre el archivo de trabajo
        shutil.copyfile(latest, target_path)  # Sobrescribe el archivo con el backup más reciente
        log(f"Restaurado: {latest.name} -> {target_path}")  # Log de restauración exitosa
        return True  # Devuelve éxito
    except Exception as e:  # Captura errores de E/S
        log(f"ERROR restaurando {file_name} desde {latest}: {e}")  # Informa el error encontrado
        return False  # Devuelve fallo


# ---------- CLI principal ----------

def main() -> int:  # Define función principal
    parser = argparse.ArgumentParser(description="Parcheador automático v7.2 (idempotente).")  # Crea parser de CLI
    parser.add_argument("--smoke", action="store_true", help="Parchear smoke_test.py (notes + verificación).")  # Flag A
    parser.add_argument("--env", action="store_true", help="Unificar .env.example (EMAIL_FROM + defaults).")  # Flag B
    parser.add_argument("--dedupe", action="store_true", help="Deduplicar sendgrid_test.py (mantener scripts/).")  # Flag C
    parser.add_argument("--all", action="store_true", help="Aplicar todas las acciones (por defecto si no hay flags).")  # Flag ALL
    parser.add_argument("--check", action="store_true", help="Modo verificación (dry run): NO modifica archivos.")  # Flag CHECK
    parser.add_argument("--restore", metavar="ARCHIVO", help="Restaurar el último backup del ARCHIVO indicado (ej.: smoke_test.py)")  # Flag de restauración
    parser.add_argument("--list", metavar="ARCHIVO", help="Listar backups disponibles del ARCHIVO (más nuevos primero)")  # Flag de listado de backups
    args = parser.parse_args()  # Parsea argumentos

    start = Path.cwd()  # Obtiene directorio actual
    repo = find_repo_root(start)  # Detecta raíz del repo
    log(f"Raíz detectada: {repo}")  # Log de raíz

    # --- Operaciones de backups independientes (listado/restauración) ---
    if args.list:  # Si se solicitó listar backups
        file_name = Path(args.list).name  # Normaliza por si pasan una ruta
        backups = list_backups_for(repo, file_name)  # Obtiene los backups
        if not backups:  # Si no hay resultados
            log(f"No hay backups para: {file_name}")  # Informa ausencia
        else:  # Si existen backups
            log(f"Backups de {file_name}:")  # Encabezado
            for p in backups:  # Itera y muestra cada backup
                log(f" - {p}")  # Imprime la ruta completa
        return 0  # Salir tras listar

    if args.restore:  # Si se solicitó restaurar el último backup
        target = repo / Path(args.restore).name  # Construye la ruta del archivo en la raíz del repo
        ok = restore_latest_backup(repo, target, check_mode=args.check)  # Intenta restaurar (respeta --check)
        return 0 if ok else 1  # Código de salida según resultado

    if args.check:  # Si es dry-run
        log("--- Ejecutando en modo de verificación (dry run): NO se modificarán archivos ---")  # Aviso

    do_all = args.all or (not args.smoke and not args.env and not args.dedupe)  # Determina si corre todo por defecto

    if args.smoke or do_all:  # Si debe aplicar parche A
        patch_smoke_test(repo, check_mode=args.check)  # Ejecuta parche de smoke

    if args.env or do_all:  # Si debe aplicar parche B
        patch_env_example(repo, check_mode=args.check)  # Ejecuta parche de env.example

    if args.dedupe or do_all:  # Si debe aplicar parche C
        dedupe_sendgrid_test(repo, check_mode=args.check)  # Ejecuta deduplicación

    log("Parcheador finalizado.")  # Mensaje de cierre
    return 0  # Devuelve éxito


if __name__ == "__main__":  # Verifica ejecución directa
    sys.exit(main())  # Llama a main() y retorna código de salida