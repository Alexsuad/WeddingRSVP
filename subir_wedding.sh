#!/usr/bin/env bash                                                     # Usa bash como intérprete
set -e                                                                  # Aborta si cualquier comando falla

# --- Parámetros del repo ------------------------------------------------------
OWNER="Alexsuad"                                                        # Tu usuario de GitHub
REPO="WeddingRSVP"                                                      # Nombre del repositorio
REMOTE_SSH="git@github.com:${OWNER}/${REPO}.git"                        # URL SSH del remoto

# --- 0) Ir a la raíz del proyecto --------------------------------------------
cd "$(dirname "$0")"                                                    # Entra a la carpeta donde está este script

# --- 1) Inicializar Git si hace falta -----------------------------------------
[ -d .git ] || git init                                                 # Crea .git/ si no existe
git add -A                                                              # Prepara todos los cambios
git commit -m "init: primer commit" 2>/dev/null || true                 # Hace commit si hay cambios; no falla si no hay

# --- 2) Asegurar rama principal 'main' ----------------------------------------
git branch -M main                                                      # Renombra/crea 'main'

# --- 3) Generar clave SSH si no existe ----------------------------------------
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then                               # Si no existe la clave ed25519
  ssh-keygen -t ed25519 -C "tu_email_github@ejemplo.com" -f "$HOME/.ssh/id_ed25519" -N ""  # Genera sin passphrase
fi                                                                       # Fin generación de clave

# --- 4) Cargar la clave al agente SSH -----------------------------------------
eval "$(ssh-agent -s)"                                                  # Inicia el agente SSH
ssh-add "$HOME/.ssh/id_ed25519"                                         # Añade la clave privada al agente

# --- 5) Mostrar la clave pública y pedir que la pegues en GitHub --------------
echo "------------------------------------------------------------------"   # Separador visual
echo "Copia esta clave pública y añádela en GitHub → Settings →"            # Instrucción para el usuario
echo "SSH and GPG keys → New SSH key"                                       # Ruta exacta en GitHub
echo "------------------------------------------------------------------"   # Separador
cat "$HOME/.ssh/id_ed25519.pub"                                            # Muestra la clave pública
echo "------------------------------------------------------------------"   # Separador
read -rp "Cuando la agregues en GitHub, pulsa Enter para continuar... " _   # Pausa hasta que confirmes

# --- 6) Configurar el remoto 'origin' por SSH ---------------------------------
if git remote get-url origin >/dev/null 2>&1; then                      # Si ya existe 'origin'
  git remote set-url origin "$REMOTE_SSH"                               # Actualiza la URL al SSH correcto
else
  git remote add origin "$REMOTE_SSH"                                   # Crea 'origin' apuntando al SSH
fi                                                                       # Fin configuración de remoto

# --- 7) Probar autenticación SSH (opcional pero útil) -------------------------
ssh -T git@github.com || true                                           # Intenta saludo con GitHub (no falla si pide confirmación)

# --- 8) Push inicial -----------------------------------------------------------
git push -u origin main                                                 # Sube 'main' y fija upstream

echo "✅ Listo: repo publicado en https://github.com/${OWNER}/${REPO}"  # Mensaje de éxito final
