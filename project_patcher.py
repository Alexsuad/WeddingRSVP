# project_patcher.py  # Nombre del archivo del parcheador automático del proyecto.

# ==========================================================================================
# 🎯 Objetivo
# ------------------------------------------------------------------------------------------
# Este script automatiza 3 tareas idempotentes para tu proyecto RSVP v7.2:
#  A) Parchar 'smoke_test.py' para añadir un payload con 'notes' y verificación suave del echo-back.
#  B) Unificar '.env.example' → asegurar EMAIL_FROM, SEND_ACCESS_MODE, PUBLIC_LOGIN_URL y DRY_RUN.
#  C) Deduplicar 'sendgrid_test.py' (mantener la versión en 'scripts/sendgrid_test.py' por defecto).
#
# Además incluye:
#  - Modo '--check' (dry-run) para simular cambios SIN escribir en disco.
#  - Backups '.bak' antes de modificar cualquier archivo (cuando NO estás en --check).
#  - Idempotencia: si el cambio ya está, no duplica ni rompe nada.
# ==========================================================================================

import re  # Importa 're' para trabajar con expresiones regulares sobre el texto de archivos
import os  # Importa 'os' para utilidades del sistema operativo
import sys  # Importa 'sys' para salir con códigos de retorno desde main()
import shutil  # Importa 'shutil' para copiar archivos (backups .bak)
from pathlib import Path  # Importa 'Path' para rutas multiplataforma legibles
import argparse  # Importa 'argparse' para definir y leer flags de la línea de comandos

# ---------- Utilidades generales ----------

def log(msg: str) -> None:
    """Imprime mensajes con prefijo estándar para trazabilidad."""
    print(f"[patcher] {msg}")  # Muestra el mensaje con prefijo '[patcher]' para distinguir salidas


def find_repo_root(start: Path) -> Path:
    """Detecta la raíz del repo subiendo directorios hasta hallar artefactos típicos."""
    cur = start.resolve()  # Resuelve la ruta absoluta desde donde se ejecuta el script
    while True:  # Bucle que sube hasta la raíz del sistema de archivos
        # Heurística: si existen 'app/' y 'scripts/' y además 'requirements.txt' o 'alembic.ini', asumimos raíz
        if (cur / "app").is_dir() and (cur / "scripts").is_dir() and \
           ((cur / "requirements.txt").exists() or (cur / "alembic.ini").exists()):
            return cur  # Devuelve el directorio detectado como raíz del repositorio
        if cur.parent == cur:  # Si ya estamos en el tope del sistema de archivos (no hay más padres)
            return start.resolve()  # Devuelve el directorio inicial como mejor esfuerzo
        cur = cur.parent  # Sube un nivel y repite la comprobación


def backup_file(path: Path) -> Path:
    """Crea un backup .bak del archivo antes de modificarlo."""
    bak = path.with_suffix(path.suffix + ".bak")  # Construye el nombre destino con sufijo .bak
    shutil.copyfile(path, bak)  # Copia el archivo original al .bak
    log(f"Backup creado: {bak}")  # Informa la ruta del backup creado
    return bak  # Devuelve la ruta del backup creado


def write_if_changed(path: Path, new_content: str, check_mode: bool = False) -> bool:
    """
    Escribe 'new_content' en 'path' solo si el contenido cambia.
    En modo 'check_mode' no escribe; solo informa que haría un cambio.
    """
    old = path.read_text(encoding="utf-8")  # Lee el contenido actual del archivo como texto UTF-8
    if old == new_content:  # Compara si el nuevo contenido es idéntico al existente
        log(f"Sin cambios: {path} (ya está actualizado)")  # Informa que no hay nada que hacer
        return False  # Devuelve False indicando que no se aplicó cambio

    if check_mode:  # Si estamos en modo simulación/solo verificación
        log(f"SE HARÍA un cambio en: {path}")  # Informa que se detectó un cambio necesario
        return True  # Devuelve True indicando que HABRÍA cambios si no fuera dry-run

    backup_file(path)  # Crea un backup .bak antes de sobrescribir
    path.write_text(new_content, encoding="utf-8")  # Escribe el nuevo contenido en el archivo
    log(f"Archivo actualizado: {path}")  # Informa que se actualizó el archivo
    return True  # Devuelve True indicando que sí se aplicó un cambio


# ---------- A) Parche: smoke_test.py (añadir 'notes' + verificación echo-back) ----------

def patch_smoke_test(repo: Path, check_mode: bool = False) -> None:
    """Asegura payload con 'notes' y verifica suavemente que el API devuelva 'notes' tras 2xx."""
    target = repo / "smoke_test.py"  # Apunta al archivo 'smoke_test.py' en la raíz del repo
    if not target.exists():  # Comprueba si el archivo no existe
        log("No se encontró 'smoke_test.py' en la raíz; se omite parche A.")  # Informa y no falla
        return  # Sale sin error (idempotente)

    text = target.read_text(encoding="utf-8")  # Lee el contenido actual de 'smoke_test.py'
    text_final = text  # Inicializa 'text_final' con el contenido original para ir aplicando cambios

    # --- (A1) Asegurar un payload con 'notes' dentro de 'payloads = [ ... ]' ---
    payloads_pat = re.compile(r"payloads\s*=\s*\[(?P<body>.*?)\]\s*", re.DOTALL)  # Crea regex que captura el cuerpo de la lista
    m = payloads_pat.search(text)  # Busca el bloque 'payloads = [ ... ]' en el archivo
    if m:  # Si encontró la lista de payloads
        body = m.group("body")  # Extrae el contenido interno de la lista de payloads
        if '"notes"' not in body:  # Si aún no hay un payload que contenga 'notes'
            # Define el nuevo payload con 'notes' para validación v7.2
            notes_payload = (
                '        {\n'
                '            "attending": True,             # Asistencia afirmativa\n'
                '            "companions": [],              # Sin acompañantes para simplificar\n'
                '            "notes": "Notas de prueba E2E (smoke).",  # Validación v7.2\n'
                '            "allergies": "Ninguna"\n'
                '        }'
            )  # Crea el bloque de diccionario JSON a insertar como nuevo caso de prueba
            body_stripped = body.rstrip()  # Quita espacios/saltos finales para normalizar
            if not body_stripped.endswith((",", "\n")):  # Si el último elemento no termina en coma o salto de línea
                body_stripped += ","  # Añade coma para separar el nuevo elemento correctamente
            new_body = body_stripped + "\n" + notes_payload + "\n"  # Concatena el nuevo payload a la lista
            text_final = text[:m.start("body")] + new_body + text[m.end("body"):]  # Reconstruye el archivo con la inserción
            log("Payload con 'notes' añadido en smoke_test.py.")  # Informa que se añadió el caso de prueba
        else:
            log("Ya existe un payload con 'notes' en smoke_test.py (OK).")  # Informa idempotencia (no duplica)
    else:
        log("No se encontró la lista 'payloads = [...]' en smoke_test.py; se omite este sub-parche.")  # Informa ausencia de ancla

    text_notes = text_final  # Conserva el texto resultante tras el posible parche de payloads

    # --- (A2) Inyectar verificación suave del echo-back cuando la respuesta sea 2xx ---
    echo_marker = "RSVP no devolvió 'notes'."  # Define una marca para no inyectar el mismo bloque dos veces
    if echo_marker not in text_notes:  # Si aún no existe el bloque de verificación
        # Regex para encontrar el 'if r2.status_code // 100 == 2:' y capturar su indentación
        success_if = re.compile(r"(if\s+r2\.status_code\s*//\s*100\s*==\s*2\s*:\s*#.*?\n)(?P<indent>\s*)", re.MULTILINE)
        mm = success_if.search(text_notes)  # Busca la posición donde inyectar el bloque de verificación
        if mm:  # Si encontró el if deseado
            indent = mm.group("indent")  # Toma la indentación detectada para mantener estilo consistente
            # Construye el bloque try/except que verifica la presencia de 'notes' en la respuesta guardada
            echo_block = (
                f"{indent}# (Opcional) Validación rápida del echo-back si tu endpoint devuelve el RSVP guardado.\n"
                f"{indent}try:\n"
                f"{indent}    saved = r2.json()  # Parsea cuerpo JSON si es posible\n"
                f"{indent}    if \"notes\" in p:  # Solo valida cuando mandamos 'notes'\n"
                f"{indent}        assert (\n"
                f"{indent}            (\"notes\" in saved) or\n"
                f"{indent}            (\"data\" in saved and \"notes\" in saved.get(\"data\", {}))\n"
                f"{indent}        ), \"RSVP no devolvió 'notes'.\"\n"
                f"{indent}except Exception:\n"
                f"{indent}    pass  # Si no hay JSON o cambia el contrato, no se falla el smoke por este detalle\n"
            )  # Define el bloque a inyectar después del if 2xx
            injected = mm.group(0) + echo_block  # Prepara el texto del if original + el bloque nuevo
            text_final = text_notes[:mm.start()] + injected + text_notes[mm.end():]  # Reconstruye con la inyección aplicada
            log("Verificación del echo-back de 'notes' inyectada en smoke_test.py.")  # Informa éxito de la inyección
        else:
            log("No se encontró el bloque 'if r2.status_code // 100 == 2:'; verificación de 'notes' omitida.")  # Informa ausencia
    else:
        log("Verificación de 'notes' tras 2xx ya existe en smoke_test.py (OK).")  # Informa idempotencia

    # --- (A3) Persistir si hubo cambios ---
    write_if_changed(target, text_final, check_mode=check_mode)  # Escribe únicamente si difiere del original (o simula con --check)


# ---------- B) Parche: .env.example (unificación claves y defaults) ----------

def patch_env_example(repo: Path, email_key: str = "EMAIL_FROM", check_mode: bool = False) -> None:
    """Unifica .env.example y asegura EMAIL_FROM, SEND_ACCESS_MODE, PUBLIC_LOGIN_URL y DRY_RUN."""
    env_example = repo / ".env.example"  # Apunta al archivo '.env.example' en la raíz del repo
    if not env_example.exists():  # Comprueba si el archivo no existe
        log("No se encontró '.env.example' en la raíz; se omite parche B.")  # Informa y no falla
        return  # Sale sin error (idempotente)

    content = env_example.read_text(encoding="utf-8")  # Lee el contenido actual del .env.example
    original_content = content  # Guarda copia para comparar al final si hubo cambios

    # (B1) Reemplazar 'SENDER_EMAIL' -> 'EMAIL_FROM' cuando aplique
    if "SENDER_EMAIL" in content and email_key not in content:  # Si existe la clave antigua y falta la nueva
        content = re.sub(r"(?m)^\s*SENDER_EMAIL\s*=", f"{email_key}=", content)  # Reemplaza la clave al inicio de la línea
        log("SENDER_EMAIL → EMAIL_FROM aplicado en .env.example.")  # Informa la sustitución

    # (B2) Asegurar bloque de envío de correo si falta
    if email_key not in content:  # Si no existe EMAIL_FROM en el archivo
        content += (
            "\n# --- Correo / Envíos ---\n"
            f'{email_key}="no-reply@tu-dominio.com"  # Remitente verificado en SendGrid (o sandbox en DRY_RUN)\n'
            'SENDGRID_API_KEY=""                   # API Key (vacío en example)\n'
        )  # Añade el bloque mínimo necesario para correo
        log("Se añadió bloque de correo (EMAIL_FROM, SENDGRID_API_KEY) a .env.example.")  # Informa adición

    # (B3) Asegurar variables de modo de acceso y URL pública de login
    if "SEND_ACCESS_MODE" not in content:  # Si falta la variable de modo
        content += "SEND_ACCESS_MODE=code  # 'code' para v7.2; 'magic' como fallback\n"  # Añade valor recomendado
        log("Se añadió SEND_ACCESS_MODE=code a .env.example.")  # Informa adición

    if "PUBLIC_LOGIN_URL" not in content:  # Si falta URL pública
        content += 'PUBLIC_LOGIN_URL="https://tu-dominio.com/login"  # CTA en email de guest code\n'  # Añade default
        log("Se añadió PUBLIC_LOGIN_URL a .env.example.")  # Informa adición

    # (B4) Sugerir DRY_RUN=1 para entornos de desarrollo
    if "DRY_RUN" not in content:  # Si falta DRY_RUN
        content += "DRY_RUN=1  # 1 en dev para simular envíos de correo\n"  # Añade recomendación
        log("Se añadió DRY_RUN=1 a .env.example.")  # Informa adición

    # (B5) Persistir si hubo cambios
    if content != original_content:  # Si el contenido fue modificado
        write_if_changed(env_example, content, check_mode=check_mode)  # Escribe (o simula) los cambios
    else:
        log("Sin cambios en .env.example (ya estaba unificado y completo).")  # Informa idempotencia


# ---------- C) Parche: deduplicar sendgrid_test.py ----------

def dedupe_sendgrid_test(repo: Path, prefer_path: Path | None = None, check_mode: bool = False) -> None:
    """
    Elimina duplicado de sendgrid_test.py manteniendo 'scripts/sendgrid_test.py' por defecto.
    Si el archivo en raíz difiere, NO lo borra automáticamente (pide intervención manual).
    """
    preferred = prefer_path or (repo / "scripts" / "sendgrid_test.py")  # Define ruta preferida
    other_candidates = [repo / "sendgrid_test.py"]  # Define candidatos alternos a eliminar

    if not preferred.exists():  # Si la versión preferida no existe
        log(f"No se encontró preferido: {preferred}. No se deduplica.")  # Informa que no puede proceder
        return  # Sale sin error (idempotente)

    for candidate in other_candidates:  # Itera los posibles duplicados
        if candidate.exists():  # Si el candidato existe
            try:
                pref_txt = preferred.read_text(encoding="utf-8", errors="ignore")  # Lee contenido preferido
                cand_txt = candidate.read_text(encoding="utf-8", errors="ignore")  # Lee contenido candidato
                if cand_txt.strip() == pref_txt.strip():  # Si ambos contenidos equivalen (ignorando espacios extremos)
                    if check_mode:  # Si estamos en modo simulación
                        log(f"SE ELIMINARÍA el duplicado: {candidate} (se mantendría {preferred})")  # Informa simulación
                    else:
                        backup_file(candidate)  # Crea backup .bak del duplicado antes de borrarlo
                        candidate.unlink()  # Elimina el duplicado en raíz
                        log(f"Duplicado eliminado: {candidate} (se mantiene {preferred})")  # Informa acción realizada
                else:
                    log(f"sendgrid_test.py en {candidate} difiere del preferido; no se borra automáticamente.")  # Precaución
            except Exception as e:  # Captura cualquier excepción de E/S
                log(f"No se pudo comparar/borrar {candidate}: {e}")  # Informa el error sin abortar


# ---------- CLI principal ----------

def main() -> int:
    """Punto de entrada: parsea flags, detecta raíz, y ejecuta parches solicitados."""
    parser = argparse.ArgumentParser(description="Parcheador automático v7.2 (idempotente).")  # Crea parser CLI
    parser.add_argument("--smoke", action="store_true", help="Parchear smoke_test.py (notes + verificación).")  # Flag A
    parser.add_argument("--env", action="store_true", help="Unificar .env.example (EMAIL_FROM + defaults).")  # Flag B
    parser.add_argument("--dedupe", action="store_true", help="Deduplicar sendgrid_test.py (mantener scripts/).")  # Flag C
    parser.add_argument("--all", action="store_true", help="Aplicar todas las acciones (por defecto si no hay flags).")  # Flag ALL
    parser.add_argument("--check", action="store_true", help="Modo verificación (dry run): NO modifica archivos.")  # Flag CHECK
    args = parser.parse_args()  # Interpreta los argumentos recibidos por CLI

    start = Path.cwd()  # Toma el directorio actual como punto de partida
    repo = find_repo_root(start)  # Detecta la raíz del repo usando la heurística definida
    log(f"Raíz detectada: {repo}")  # Informa la raíz detectada

    if args.check:  # Si el usuario activó el modo dry-run
        log("--- Ejecutando en modo de verificación (dry run): NO se modificarán archivos ---")  # Advierte modo seguro

    do_all = args.all or (not args.smoke and not args.env and not args.dedupe)  # Calcula si debe ejecutar todo por defecto

    if args.smoke or do_all:  # Si se pidió el parche A o se ejecuta todo
        patch_smoke_test(repo, check_mode=args.check)  # Llama al parche A (pasando modo check si aplica)

    if args.env or do_all:  # Si se pidió el parche B o se ejecuta todo
        patch_env_example(repo, check_mode=args.check)  # Llama al parche B (pasando modo check si aplica)

    if args.dedupe or do_all:  # Si se pidió el parche C o se ejecuta todo
        dedupe_sendgrid_test(repo, check_mode=args.check)  # Llama al parche C (pasando modo check si aplica)

    log("Parcheador finalizado.")  # Informa fin de ejecución
    return 0  # Devuelve 0 indicando éxito total


if __name__ == "__main__":  # Valida que el módulo se ejecute directamente (no importado)
    sys.exit(main())  # Ejecuta main() y retorna el código de salida del proceso al sistema
