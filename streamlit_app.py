# streamlit_app.py  # Archivo principal de la app administrativa (solo organizadores).

# =================================================================================  # Separador visual.
# 📊 DASHBOARD ADMINISTRATIVO • Boda D&C                                             # Título de la app.
# ---------------------------------------------------------------------------------  # Separador.
# - Visualiza KPIs clave (confirmados, pendientes, ocupación, asistentes).          # Descripción 1.
# - Filtra por texto, estado, lado, grupo, tipo de invitación, idioma y fechas.     # Descripción 2.
# - Muestra tablas y gráficas (distribuciones y evolución temporal).                 # Descripción 3.
# - Exporta datos filtrados a CSV y a Excel MULTI-HOJA (General/Confirmados/etc.).  # Descripción 4.
# - Acceso protegido por contraseña definida en .env (STREAMLIT_PASSWORD).          # Descripción 5.
# =================================================================================  # Fin cabecera.

# 🐍 Importaciones                                                                  # Sección de imports.
# ---------------------------------------------------------------------------------
import os  # Lectura de variables de entorno (.env) y configuración general del SO.
import io  # Buffers de memoria para generar CSV/Excel sin escribir a disco.
from datetime import datetime, date  # Tipos de fecha para KPIs y filtros de rango.
import pandas as pd  # Librería principal para manipular datos tabulares (DataFrame).
import streamlit as st  # Framework de UI para construir el dashboard.
from dotenv import load_dotenv  # Utilidad para cargar variables desde archivo .env.
from app.db import SessionLocal  # Factoría de sesiones de SQLAlchemy (conexión a BD).
from app.models import Guest  # Modelo ORM para consultar la tabla 'guests'.

# ⚙️ Configuración inicial                                                           # Preparación previa.
# ---------------------------------------------------------------------------------
load_dotenv()  # Carga variables desde .env en os.environ (ej. STREAMLIT_PASSWORD).

st.set_page_config(page_title="Dashboard • Boda D&C", layout="wide")  # ✅ Primera llamada Streamlit: define título/layout.

# 🛡️ Gate de autenticación (password único de administrador)                        # Control de acceso.
# ---------------------------------------------------------------------------------
if "authenticated" not in st.session_state:  # Verifica si existe el flag de sesión 'authenticated'.
    st.session_state.authenticated = False  # Inicializa el flag como no autenticado.

st.sidebar.header("🔑 Acceso")  # Título de la sección de acceso en la barra lateral.
password_input = st.sidebar.text_input(  # Campo para introducir la contraseña de administrador.
    "Contraseña de Administrador",  # Etiqueta visible para el usuario.
    type="password",  # Oculta caracteres mientras se escribe.
    placeholder="Ingresa la contraseña…",  # Placeholder para mejor UX.
)  # Cierra text_input.

if os.getenv("STREAMLIT_PASSWORD") is None:  # Comprueba que exista la variable de entorno requerida.
    st.sidebar.warning("No hay STREAMLIT_PASSWORD en el .env")  # Advierte si falta (ayuda a diagnosticar).

if not st.session_state.authenticated:  # Si aún no está autenticado…
    if password_input == os.getenv("STREAMLIT_PASSWORD"):  # Compara el input con la contraseña esperada.
        st.session_state.authenticated = True  # Marca como autenticado si coincide.
        st.sidebar.success("¡Acceso concedido!")  # Feedback positivo en la barra lateral.
        st.rerun()  # Fuerza rerender para cargar el contenido protegido inmediatamente.
    elif password_input:  # Si se escribió algo y no coincide…
        st.sidebar.error("Contraseña incorrecta.")  # Muestra un error de autenticación.
if not st.session_state.authenticated:  # Si sigue sin autenticación…
    st.info("Introduce la contraseña en la barra lateral para acceder al dashboard.")  # Mensaje informativo al usuario.
    st.stop()  # Detiene el resto de la ejecución (no muestra datos sin login).

# 💾 Carga de datos desde la BD (cacheada)                                           # Lectura de datos.
# ---------------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Cargando datos desde la base de datos...")  # Cachea por 5 minutos para eficiencia.
def load_data() -> pd.DataFrame:  # Define la función que retorna un DataFrame con los invitados.
    db = SessionLocal()  # Abre una nueva sesión de base de datos.
    try:  # Bloque try-finally para asegurar el cierre de la sesión.
        query = db.query(Guest).statement  # Construye el SQL subyacente a partir del modelo ORM.
        df = pd.read_sql(query, db.bind)  # Ejecuta el SQL y carga los resultados en un DataFrame de pandas.
    finally:  # Este bloque se ejecuta siempre, haya o no excepción.
        db.close()  # Cierra la sesión de base de datos para liberar recursos.
    return df  # Devuelve el DataFrame con los datos cargados.

# 🧪 Intento de carga con manejo de errores                                         # Robustez de conexión.
# ---------------------------------------------------------------------------------
try:  # Intenta obtener datos mediante la función cacheada.
    data = load_data()  # Llama a la función que accede a la BD.
    if data.empty:  # Verifica si el resultado está vacío.
        st.warning("La base de datos de invitados está vacía.")  # Advierte si no hay registros.
        st.stop()  # Detiene la app porque no hay nada que mostrar.
except Exception as e:  # Captura errores (conexión, esquema inexistente, etc.).
    st.error(f"No se pudo conectar a la base de datos: {e}")  # Muestra el error para depuración.
    st.stop()  # Detiene la ejecución para evitar fallos posteriores.

# 🧹 Normalizaciones y columnas derivadas                                            # Limpieza y preparación.
# ---------------------------------------------------------------------------------
df = data.copy()  # Trabaja sobre una copia para no modificar el cache base.
df["confirmed"] = df["confirmed"].astype("boolean")  # Asegura tipo booleano nativo con soporte NA.
df["num_adults"] = pd.to_numeric(df.get("num_adults", 0), errors="coerce").fillna(0).astype(int)  # Normaliza adultos a int.
df["num_children"] = pd.to_numeric(df.get("num_children", 0), errors="coerce").fillna(0).astype(int)  # Normaliza niños a int.
df["max_accomp"] = pd.to_numeric(df.get("max_accomp", 0), errors="coerce").fillna(0).astype(int)  # Normaliza cupos a int.
df["confirmed_at"] = pd.to_datetime(df.get("confirmed_at"))  # Convierte a datetime (NaT si vacío).
df["invite_type"] = df.get("invite_type", "ceremony").fillna("ceremony")  # Asegura valor en tipo de invitación.
df["language"] = df.get("language", "es").fillna("es")  # Asegura un idioma presente.
df["side"] = df.get("side").fillna("sin_lado")  # Reemplaza nulos por etiqueta 'sin_lado' para filtros.
df["group_id"] = df.get("group_id").fillna("")  # Reemplaza nulos por cadena vacía para búsquedas.

# 👥 Asistentes totales por grupo (solo confirmados suman en KPI específico)        # Derivados útiles.
# ---------------------------------------------------------------------------------
df["attendees_total"] = df["num_adults"] + df["num_children"]  # Calcula asistentes del grupo (adultos+niños).

# 🎯 KPIs globales (antes de aplicar filtros)                                       # Panorama general.
# ---------------------------------------------------------------------------------
total_invites = len(df)  # Total de invitaciones (grupos).
confirmed_count = int((df["confirmed"] == True).sum())  # Número de grupos confirmados.
rejected_count = int((df["confirmed"] == False).sum())  # Número de grupos que rechazaron.
pending_count = int(df["confirmed"].isna().sum())  # Número de grupos pendientes (NaN en 'confirmed').
attendees_confirmed = int(df.loc[df["confirmed"] == True, "attendees_total"].sum())  # Total de asistentes confirmados.
total_capacity = int((1 + df["max_accomp"]).sum())  # Capacidad teórica (titular + cupo asignado).
occupancy_pct = (attendees_confirmed / total_capacity * 100) if total_capacity else 0  # % de ocupación del evento.

# 🎨 Encabezado e indicadores principales                                            # Cabecera visual.
# ---------------------------------------------------------------------------------
st.title("💍 Dashboard • Boda de Daniela & Cristian")  # Título principal del dashboard.
st.caption(f"Evento: {os.getenv('EVENT_DATE_HUMAN', '22 Mayo 2026')}")  # Fecha amigable desde .env (fallback por defecto).
k1, k2, k3, k4, k5 = st.columns(5)  # Crea cinco columnas para KPIs.
k1.metric("👥 Invitaciones", total_invites)  # Muestra total de invitaciones.
k2.metric("✅ Confirmados", confirmed_count)  # Muestra total de confirmados.
k3.metric("❌ Rechazados", rejected_count)  # Muestra total de rechazados.
k4.metric("⏳ Pendientes", pending_count)  # Muestra total de pendientes.
k5.metric("🧮 Asistentes confirmados", attendees_confirmed)  # Muestra total de asistentes (adultos+niños) de confirmados.
st.progress(min(int(occupancy_pct), 100) / 100.0)  # Barra de progreso para % de ocupación (capado al 100%).
st.caption(f"Capacidad total ≈ {total_capacity} • Ocupación: {occupancy_pct:0.1f}%")  # Texto con detalle de ocupación.

st.markdown("---")  # Separador visual.

# 🧭 Filtros (aplicados a una copia)                                                # Controles de filtrado.
# ---------------------------------------------------------------------------------
st.sidebar.header("🎛️ Filtros")  # Título de la sección de filtros en la barra lateral.
filtered = df.copy()  # Trabaja sobre una copia que será filtrada (mantiene df intacto).

# Texto libre: nombre, email, código                                               # Filtro de búsqueda rápida.
q = st.sidebar.text_input("Buscar (nombre, email o código)")  # Input de texto para búsqueda parcial.
if q:  # Si hay término de búsqueda…
    mask = (  # Construye una máscara con OR lógicos sobre varias columnas.
        filtered["full_name"].str.contains(q, case=False, na=False)  # Coincidencia en nombre (case-insensitive).
        | filtered.get("email", pd.Series(dtype=str)).str.contains(q, case=False, na=False)  # Coincidencia en email.
        | filtered.get("guest_code", pd.Series(dtype=str)).str.contains(q, case=False, na=False)  # Coincidencia en código.
    )  # Cierra máscara booleana.
    filtered = filtered[mask]  # Aplica la máscara al DataFrame filtrado.

# Estado: Todos / Confirmados / Rechazados / Pendientes                            # Filtro por estado de confirmación.
status = st.sidebar.selectbox("Estado", ["Todos", "Confirmados", "Rechazados", "Pendientes"])  # Selector de estado.
if status == "Confirmados":  # Si elige Confirmados…
    filtered = filtered[filtered["confirmed"] == True]  # Filtra por confirmados.
elif status == "Rechazados":  # Si elige Rechazados…
    filtered = filtered[filtered["confirmed"] == False]  # Filtra por rechazados.
elif status == "Pendientes":  # Si elige Pendientes…
    filtered = filtered[filtered["confirmed"].isna()]  # Filtra por pendientes (NaN).

# Filtro por lado (bride/groom/sin_lado)                                           # Segmentación por lado de la boda.
side_opts = ["Todos"] + sorted(filtered["side"].dropna().unique().tolist())  # Construye opciones de lado.
side_sel = st.sidebar.selectbox("Lado", side_opts)  # Selector del lado.
if side_sel != "Todos":  # Si eligió un lado específico…
    filtered = filtered[filtered["side"] == side_sel]  # Aplica filtro por lado.

# Filtro por grupo familiar (group_id)                                             # Segmentación por grupo/etiqueta interna.
group_opts = ["Todos"] + sorted([g for g in filtered["group_id"].unique().tolist() if g])  # Opciones de grupo (omite vacíos).
group_sel = st.sidebar.selectbox("Grupo familiar", group_opts)  # Selector de grupo.
if group_sel != "Todos":  # Si seleccionó un grupo…
    filtered = filtered[filtered["group_id"] == group_sel]  # Aplica filtro por group_id.

# Filtro por tipo de invitación (ceremony/full)                                    # Segmentación por tipo de invitación.
type_opts = ["Todos"] + sorted(filtered["invite_type"].dropna().unique().tolist())  # Construye opciones a partir de datos.
type_sel = st.sidebar.selectbox("Tipo de invitación", type_opts)  # Selector de tipo.
if type_sel != "Todos":  # Si se selecciona una opción concreta…
    filtered = filtered[filtered["invite_type"] == type_sel]  # Aplica filtro por tipo.

# Filtro por idioma (ES/RO/EN)                                                     # Segmentación por idioma.
lang_opts = ["Todos"] + sorted(filtered["language"].dropna().unique().tolist())  # Construye opciones de idioma disponibles.
lang_sel = st.sidebar.selectbox("Idioma", lang_opts)  # Selector de idioma.
if lang_sel != "Todos":  # Si elige un idioma concreto…
    filtered = filtered[filtered["language"] == lang_sel]  # Aplica filtro por idioma.

# Filtro por rango de fechas de confirmación                                       # Filtro temporal de confirmaciones.
st.sidebar.markdown("**Rango de fecha de confirmación**")  # Título del filtro de rango.
min_date = pd.to_datetime(filtered["confirmed_at"].min()).date() if pd.notna(filtered["confirmed_at"]).any() else date.today()  # Fecha mínima disponible.
max_date = pd.to_datetime(filtered["confirmed_at"].max()).date() if pd.notna(filtered["confirmed_at"]).any() else date.today()  # Fecha máxima disponible.
start, end = st.sidebar.date_input(  # Control de rango de fechas (inicio/fin).
    "Desde / Hasta",  # Etiqueta del control.
    value=(min_date, max_date),  # Valor inicial por defecto (todo el rango).
    min_value=min_date,  # Mínimo permitido.
    max_value=max_date,  # Máximo permitido.
)  # Cierra date_input.
if isinstance(start, date) and isinstance(end, date):  # Asegura que ambos valores sean fechas válidas.
    mask_dates = (  # Máscara booleana para filtrar por rango de fechas.
        (filtered["confirmed_at"].notna())  # Considera solo filas con fecha no nula.
        & (filtered["confirmed_at"].dt.date >= start)  # Condición desde fecha inicio.
        & (filtered["confirmed_at"].dt.date <= end)  # Condición hasta fecha fin.
    )  # Cierra construcción de máscara.
    if (start, end) != (min_date, max_date):  # Solo aplica si el usuario cambió el rango inicial.
        filtered = filtered[mask_dates | filtered["confirmed"].isna()]  # Mantiene pendientes (sin fecha) fuera del filtro por fecha.

# 📋 Tabla de resultados filtrados                                                  # Visualización tabular.
# ---------------------------------------------------------------------------------
st.subheader(f"Invitados (resultado: {len(filtered)})")  # Encabezado con conteo tras filtros.
display_cols = [  # Lista ordenada de columnas a mostrar en la tabla (si existen).
    "full_name", "email", "phone", "guest_code", "language", "side", "group_id",  # Identificación y segmentación.
    "confirmed", "confirmed_at", "num_adults", "num_children", "menu_choice",  # Estado y cantidades.
    "allergies", "invite_type", "invited_to_ceremony", "max_accomp", "relationship",  # Preferencias y metadatos.
]  # Fin lista de columnas deseadas.
existing_cols = [c for c in display_cols if c in filtered.columns]  # Conserva solo las columnas que existen realmente.
st.dataframe(filtered[existing_cols], use_container_width=True)  # Renderiza la tabla responsiva con las columnas válidas.

st.markdown("---")  # Separador visual.

# 📈 Gráficas rápidas (distribuciones y serie temporal)                             # Visualizaciones simples.
# ---------------------------------------------------------------------------------
gc1, gc2, gc3 = st.columns(3)  # Crea tres columnas para tres gráficas paralelas.

with gc1:  # Columna 1: distribución por estado (Confirmados/Rechazados/Pendientes).
    st.markdown("**Distribución por estado**")  # Título de la gráfica.
    status_counts = (  # Prepara serie con conteo por estado legible.
        filtered["confirmed"].map({True: "Confirmados", False: "Rechazados"}).fillna("Pendientes").value_counts()
    )  # Obtiene conteos por categoría amigable.
    st.bar_chart(status_counts, use_container_width=True)  # Muestra la gráfica de barras.

with gc2:  # Columna 2: distribución por tipo de invitación.
    st.markdown("**Tipo de invitación (ceremony/full)**")  # Título de la gráfica.
    type_counts = filtered["invite_type"].value_counts()  # Serie con conteo por tipo de invitación.
    st.bar_chart(type_counts, use_container_width=True)  # Renderiza la gráfica de barras.

with gc3:  # Columna 3: distribución por idioma.
    st.markdown("**Idiomas**")  # Título de la gráfica.
    lang_counts = filtered["language"].value_counts()  # Serie con conteo por idioma.
    st.bar_chart(lang_counts, use_container_width=True)  # Renderiza la gráfica de barras.

# Serie temporal: confirmaciones por día                                            # Time-series simple.
st.markdown("### Confirmaciones por día")  # Título de la sección de serie temporal.
ts = filtered.dropna(subset=["confirmed_at"]).copy()  # Toma solo filas con fecha válida de confirmación.
if not ts.empty:  # Comprueba si hay datos para graficar.
    ts["date"] = ts["confirmed_at"].dt.date  # Extrae la parte de fecha (sin hora).
    daily = ts.groupby("date").size()  # Agrupa y cuenta confirmaciones por día.
    st.line_chart(daily, use_container_width=True)  # Renderiza la gráfica de línea.
else:  # Si no hay datos fechados…
    st.info("Aún no hay confirmaciones fechadas para graficar.")  # Mensaje informativo.

st.markdown("---")  # Separador visual.

# ⬇️ Exportaciones (CSV + Excel MULTI-HOJA)                                         # Descargas de datos.
# ---------------------------------------------------------------------------------
st.markdown("### Exportar datos filtrados")  # Encabezado de sección de exportaciones.
dl1, dl2 = st.columns(2)  # Dos columnas: una para CSV y otra para Excel.

# Exportación CSV (aplica filtros vigentes)                                        # Botón de CSV.
csv_buffer = io.StringIO()  # Crea un buffer de texto en memoria.
filtered.to_csv(csv_buffer, index=False, encoding="utf-8")  # Escribe el DataFrame filtrado al buffer CSV.
dl1.download_button(  # Crea el botón de descarga para CSV.
    label="⬇️ Descargar CSV (filtro aplicado)",  # Texto del botón.
    data=csv_buffer.getvalue(),  # Contenido del archivo en memoria.
    file_name=f"invitados_filtrados_{datetime.now().strftime('%Y%m%d')}.csv",  # Nombre del archivo con fecha.
    mime="text/csv",  # Tipo MIME de archivo CSV.
    use_container_width=True,  # Ocupa todo el ancho de la columna.
)  # Cierra el botón de descarga de CSV.

# Exportación Excel multi-hoja (General/Confirmados/Pendientes/Menús/Alergias)      # Botón de Excel.
excel_buffer = io.BytesIO()  # Crea un buffer binario en memoria para Excel.
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:  # Abre un escritor Excel sobre el buffer.
    filtered.to_excel(writer, index=False, sheet_name="General")  # Hoja con todos los datos filtrados.
    filtered[filtered["confirmed"] == True].to_excel(writer, index=False, sheet_name="Confirmados")  # Hoja de confirmados.
    filtered[filtered["confirmed"].isna()].to_excel(writer, index=False, sheet_name="Pendientes")  # Hoja de pendientes.
    if "menu_choice" in filtered.columns:  # Verifica si la columna de menús existe (compatibilidad con esquema).
        menu_summary = (  # Construye un resumen de distribución de menús (si hay datos).
            filtered[filtered["menu_choice"].notna()]  # Filtra filas con valor de menú.
            .groupby("menu_choice")  # Agrupa por tipo de menú.
            .size()  # Cuenta registros por cada tipo.
            .reset_index(name="count")  # Renombra la columna de conteo a 'count'.
        )  # Finaliza pipeline de resumen.
        menu_summary.to_excel(writer, index=False, sheet_name="Resumen_Menus")  # Escribe la hoja de menús.
    if "allergies" in filtered.columns:  # Verifica si existe la columna de alergias.
        allergies_flat = filtered[["full_name", "allergies"]].dropna()  # Toma solo filas con alergias informadas.
        allergies_flat.to_excel(writer, index=False, sheet_name="Alergias")  # Escribe la hoja de alergias.
dl2.download_button(  # Crea el botón de descarga del Excel.
    label="⬇️ Descargar Excel (multi-hoja)",  # Texto del botón.
    data=excel_buffer.getvalue(),  # Contenido binario del Excel generado en memoria.
    file_name=f"invitados_filtrados_{datetime.now().strftime('%Y%m%d')}.xlsx",  # Nombre del archivo con fecha.
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Tipo MIME de archivo Excel.
    use_container_width=True,  # Ocupa todo el ancho de su columna.
)  # Cierra el botón de descarga de Excel.

# ✅ Notas finales:                                                                  # Recordatorios.
# - Este dashboard lee directamente la BD; en producción puedes migrar a Postgres.  # Recomendación de despliegue.
# - Los filtros aplican a todo: tablas, gráficas y exportaciones.                   # Consistencia de filtros.
# - Ajusta EVENT_DATE_HUMAN en .env para mostrar fecha bonita del evento.           # Personalización del evento.
