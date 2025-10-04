# Makefile                                                                                          # Nombre del archivo que 'make' usa por defecto para ejecutar tareas

# =========================
# ⚙️ Configuración general
# =========================
SHELL := /bin/bash                                                                                   # Fuerza a usar bash como shell para compatibilidad en comandos
.ONESHELL:                                                                                           # Hace que cada receta se ejecute en una sola shell (mantiene variables locales por receta)
.SHELLFLAGS := -eu -o pipefail -c                                                                    # 'set -e' (salir en error), '-u' (error en variables no definidas), 'pipefail' (propaga error en pipes)

# =========================
# 📁 Rutas y variables base
# =========================
PROJECT_DIR ?= /home/nalex/Proyectos/backend_starter                                                 # Ruta raíz del proyecto (ajústala si el proyecto se mueve)
VENV_ACT := $$( [ -f "$(PROJECT_DIR)/.venv/bin/activate" ] && echo ". $(PROJECT_DIR)/.venv/bin/activate" || echo "true")  # Activa venv si existe; si no, no falla
DB_FILE := $(PROJECT_DIR)/wedding.db                                                                 # Ruta absoluta a la base de datos SQLite
DATABASE_URL := sqlite:///${DB_FILE}                                                                 # URL de conexión usada por backend/scripts apuntando a la misma DB
API_HOST := 127.0.0.1                                                                                # Host local para la API FastAPI
API_PORT := 8000                                                                                     # Puerto de la API (Uvicorn/FastAPI)
UI_PORT := 8501                                                                                      # Puerto de Streamlit
API_BASE_URL := http://$(API_HOST):$(API_PORT)                                                       # URL base de la API usada por scripts de importación
ENTRY_URL := http://localhost:$(UI_PORT)                                                             # URL de entrada de la app de Streamlit

# =========================
# 🔐 Variables sensibles
# =========================
# Nota: No pongas claves aquí. Cárgalas en la terminal antes de ejecutar (ej: export ADMIN_API_KEY="...").
ADMIN_API_KEY ?=                                                                                     # Clave admin para el importador (si viene vacía, algunas tareas la avisarán)
SENDGRID_API_KEY ?=                                                                                  # Clave para enviar correos con SendGrid (solo para tareas de envío real)
EMAIL_FROM ?=                                                                                         # Remitente de correos (para tareas de envío real)
RSVP_URL ?=                                                                                           # URL pública de RSVP (para plantillas de correo)
EVENT_DATE_HUMAN ?=                                                                                   # Fecha “humana” del evento (para plantillas de correo)
DRY_RUN ?= 1                                                                                          # Por defecto en simulación (1=simular, 0=enviar real); respétalo en tareas de correo

# =========================
# 🧪 Utilidades internas
# =========================
define _echo_ok
	printf "\033[32m✔ %s\033[0m\n" "$(1)"                                                            # Función interna: imprime mensajes OK en verde
endef

define _echo_warn
	printf "\033[33m⚠ %s\033[0m\n" "$(1)"                                                            # Función interna: imprime avisos en amarillo
endef

define _echo_err
	printf "\033[31m✘ %s\033[0m\n" "$(1)"                                                            # Función interna: imprime errores en rojo
endef

define _require_cmd
	if ! command -v $(1) >/dev/null 2>&1; then $(call _echo_err,"Falta el comando: $(1)"); exit 1; fi  # Verifica que un binario exista; si no, aborta
endef

define _require_file
	if [ ! -f "$(1)" ]; then $(call _echo_err,"No existe el archivo: $(1)"); exit 1; fi                # Verifica que un archivo exista; si no, aborta
endef

define _require_env
	if [ -z "$($(1))" ]; then $(call _echo_err,"Variable requerida vacía: $(1)"); exit 1; fi           # Verifica que una variable de entorno/Make esté definida; si no, aborta
endef

# =========================
# 🆘 Ayuda / índice
# =========================
.PHONY: help                                                                                          # 'help' no genera archivos; siempre se ejecuta
help:                                                                                                 # Muestra la lista de tareas disponibles
	@echo "Tareas disponibles:"                                                                       # Encabezado de ayuda
	@echo "  make up            - Levantar backend (Uvicorn/FastAPI) en $(API_BASE_URL)"              # Explica 'up'
	@echo "  make ui            - Abrir frontend (Streamlit) en :$(UI_PORT)"                          # Explica 'ui'
	@echo "  make stop          - Cerrar backend y Streamlit"                                         # Explica 'stop'
	@echo "  make ports         - Ver si 8000/8501 están ocupados"                                    # Explica 'ports'
	@echo "  make openapi       - Comprobar que /openapi.json responde 200"                           # Explica 'openapi'
	@echo "  make health        - Comprobar API y DB (consulta COUNT)"                                # Explica 'health'
	@echo "  make reset-demo    - Borrar DB, subir API y reimportar data/invitados_demo.csv"          # Explica 'reset-demo'
	@echo "  make import-demo   - Importar solo invitados_demo.csv (requiere API arriba)"             # Explica 'import-demo'
	@echo "  make dry-run-demo  - Validar CSV sin escribir en DB (requiere API arriba)"               # Explica 'dry-run-demo'
	@echo "  make count         - Mostrar cuántos invitados hay en DB"                                # Explica 'count'
	@echo "  make smoke         - Alembic upgrade + smoke_test.py (sanidad ORM/DB)"                   # Explica 'smoke'
	@echo "  make mock-api      - Levantar servidor mock para probar importación sin backend real"    # Explica 'mock-api'
	@echo "  make send-sim      - Simular envío de invitaciones (DRY_RUN=1)"                          # Explica 'send-sim'
	@echo "  make send-real     - Envío real de invitaciones (DRY_RUN=0 y claves cargadas)"           # Explica 'send-real'
	@echo "  make logs          - Ver rápido el último log de API si se lanzó en background"          # Explica 'logs'

# =========================
# 🧹 Arranque / parada
# =========================
.PHONY: stop                                                                                          # 'stop' siempre se ejecuta (mata procesos)
stop:                                                                                                 # Cierra servidores si quedaron activos
	$(call _require_cmd,pkill)                                                                        # Asegura que pkill exista
	pkill -f "uvicorn" || true                                                                        # Mata cualquier proceso Uvicorn (ignora error si no hay)
	pkill -f "streamlit run" || true                                                                  # Mata cualquier proceso Streamlit (ignora error si no hay)
	$(call _echo_ok,"Servidores detenidos (Uvicorn/Streamlit)")                                       # Mensaje de confirmación

.PHONY: up                                                                                            # 'up' siempre se ejecuta (levanta backend)
up:                                                                                                   # Levanta API con Uvicorn en primer plano (cierra con CTRL+C)
	$(call _require_cmd,uvicorn)                                                                      # Verifica que Uvicorn esté instalado
	cd "$(PROJECT_DIR)"                                                                               # Cambia a la carpeta del proyecto
	eval $(VENV_ACT)                                                                                  # Activa el entorno virtual si existe
	export DATABASE_URL="$(DATABASE_URL)";                                                            # Exporta la URL de la DB para el proceso
	uvicorn app.main:app --reload --host $(API_HOST) --port $(API_PORT)                               # Lanza la API (recarga automática)

.PHONY: ui                                                                                            # 'ui' siempre se ejecuta (levanta frontend)
ui:                                                                                                   # Arranca Streamlit en el puerto configurado
	$(call _require_cmd,streamlit)                                                                    # Verifica que Streamlit esté instalado
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	streamlit run streamlit_rsvp_app.py --server.port $(UI_PORT)                                      # Ejecuta Streamlit (CTRL+C para cerrar)

.PHONY: ports                                                                                         # 'ports' siempre se ejecuta (diagnóstico)
ports:                                                                                                # Muestra si los puertos 8000/8501 están ocupados
	$(call _require_cmd,ss)                                                                           # Verifica que 'ss' exista (socket statistics)
	ss -ltnp | grep -E ":$(API_PORT)|:$(UI_PORT)" || echo "Puertos libres ✅"                         # Lista puertos abiertos o indica que están libres

# =========================
# ✅ Comprobaciones rápidas
# =========================
.PHONY: openapi                                                                                       # 'openapi' comprueba la API
openapi:                                                                                              # Verifica que /openapi.json responde 200
	$(call _require_cmd,curl)                                                                         # Requiere curl para hacer la petición
	curl -fsS "$(API_BASE_URL)/openapi.json" >/dev/null && $(call _echo_ok,"API OK en /openapi.json") # Hace GET silencioso; si responde 200: OK

.PHONY: count                                                                                         # 'count' consulta la DB
count:                                                                                                # Muestra COUNT(*) de la tabla guests
	$(call _require_cmd,sqlite3)                                                                      # Requiere sqlite3 para ejecutar la consulta
	$(call _require_file,$(DB_FILE))                                                                  # Exige que exista el archivo de DB
	sqlite3 "$(DB_FILE)" "SELECT COUNT(*) FROM guests;" | sed 's/^/TOTAL invitados: /'                # Ejecuta SELECT COUNT(*) y lo rotula

.PHONY: health                                                                                        # 'health' hace check API + DB
health:                                                                                               # Verifica API y que la DB responde a una consulta básica
	$(MAKE) openapi                                                                                   # Reutiliza la verificación de OpenAPI
	$(MAKE) count                                                                                     # Reutiliza la verificación de conteo en DB
	$(call _echo_ok,"Health OK (API / DB)")                                                           # Mensaje de estado saludable

# =========================
# ♻️ Reset + Import demo
# =========================
.PHONY: reset-demo                                                                                    # 'reset-demo' compone varias acciones
reset-demo:                                                                                           # Borra DB, levanta API en background e importa invitados_demo.csv
	$(MAKE) stop                                                                                      # Asegura que nada esté ocupando la DB o los puertos
	rm -f "$(DB_FILE)"                                                                                # Elimina la base de datos para empezar de cero
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	export DATABASE_URL="$(DATABASE_URL)";                                                            # Exporta la URL de DB para la API
	nohup uvicorn app.main:app --host $(API_HOST) --port $(API_PORT) > /tmp/api.log 2>&1 &            # Arranca la API en segundo plano y guarda log en /tmp/api.log
	for i in {1..20}; do                                                                              # Espera activa máximo ~10s a que la API responda
	  sleep 0.5; curl -fsS "$(API_BASE_URL)/openapi.json" >/dev/null && break || true;                # Prueba /openapi.json hasta que esté lista
	done                                                                                              # Fin del bucle de espera
	curl -fsS "$(API_BASE_URL)/openapi.json" >/dev/null || ( $(call _echo_err,"API no responde"); exit 1 )  # Si tras esperar no responde, aborta
	$(MAKE) import-demo                                                                               # Llama a la tarea de importación del CSV demo
	$(MAKE) count                                                                                     # Muestra el total importado para confirmar

.PHONY: import-demo                                                                                   # 'import-demo' importa el CSV
import-demo:                                                                                          # Importa data/invitados_demo.csv vía la API admin
	$(call _require_env,ADMIN_API_KEY)                                                                # Exige que ADMIN_API_KEY esté definido en el entorno
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	API_BASE_URL="$(API_BASE_URL)" \                                                                  # Define URL base para el script
	ADMIN_API_KEY="$(ADMIN_API_KEY)" \                                                                # Pasa la clave admin para autenticar el importador
	python scripts/import_guests.py data/invitados_demo.csv --sep=, --encoding=utf-8 --batch=200      # Ejecuta el importador en lotes de 200 (formato CSV estándar)

.PHONY: dry-run-demo                                                                                  # 'dry-run-demo' valida sin escribir
dry-run-demo:                                                                                         # Valida el CSV de demo sin modificar la DB
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	API_BASE_URL="$(API_BASE_URL)" \                                                                  # Define URL base para el script
	ADMIN_API_KEY="$(ADMIN_API_KEY)" \                                                                # Usa la clave admin (si requiere autorización de validación)
	python scripts/import_guests.py data/invitados_demo.csv --dry-run                                 # Ejecuta en modo simulación (no escribe en DB)

# =========================
# 🧪 Migraciones / smoke
# =========================
.PHONY: smoke                                                                                         # 'smoke' prueba rápida ORM/DB
smoke:                                                                                                # Aplica migraciones y corre el smoke test
	$(call _require_cmd,alembic)                                                                      # Verifica que Alembic esté instalado
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	export DATABASE_URL="$(DATABASE_URL)";                                                            # Exporta la URL de la DB para las migraciones
	alembic upgrade head                                                                              # Aplica todas las migraciones pendientes
	python smoke_test.py                                                                              # Corre el chequeo rápido para validar ORM/DB

# =========================
# 🧪 Mock server (para pruebas del importador sin backend real)
# =========================
.PHONY: mock-api                                                                                      # 'mock-api' levanta un servidor falso
mock-api:                                                                                             # Levanta un FastAPI simulado para probar el importador
	$(call _require_file,$(PROJECT_DIR)/scripts/mock_admin_import_server.py)                          # Verifica que exista el script mock
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	python scripts/mock_admin_import_server.py                                                        # Ejecuta el servidor mock (suele usar :9000)

# =========================
# 📧 Envíos de correo
# =========================
.PHONY: send-sim                                                                                      # 'send-sim' simula envíos
send-sim:                                                                                             # Simula el envío de invitaciones (no manda correos reales)
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	export DRY_RUN=1;                                                                                 # Fuerza modo simulación para no enviar nada
	python scripts/send_invites.py                                                                    # Ejecuta el script de envíos (simulado)

.PHONY: send-real                                                                                     # 'send-real' envía de verdad (con cuidado)
send-real:                                                                                             # Envía correos reales (requiere claves y DRY_RUN=0)
	$(call _require_env,SENDGRID_API_KEY)                                                             # Exige clave de SendGrid
	$(call _require_env,EMAIL_FROM)                                                                   # Exige remitente
	$(call _require_env,RSVP_URL)                                                                     # Exige URL pública de RSVP
	$(call _require_env,EVENT_DATE_HUMAN)                                                             # Exige fecha “humana” del evento
	cd "$(PROJECT_DIR)"; eval $(VENV_ACT);                                                            # Entra al proyecto y activa venv
	export DRY_RUN=0;                                                                                 # Desactiva simulación para enviar de verdad
	python scripts/send_invites.py                                                                    # Ejecuta el script de envíos (real)

# =========================
# 📝 Logs rápidos (API en background)
# =========================
.PHONY: logs                                                                                          # 'logs' muestra el log del arranque en background
logs:                                                                                                 # Muestra las últimas líneas del log /tmp/api.log si existe
	if [ -f /tmp/api.log ]; then tail -n 50 /tmp/api.log; else $(call _echo_warn,"No hay /tmp/api.log"); fi  # Muestra tail o avisa si no existe
