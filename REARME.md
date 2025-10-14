# 📑 Documento Maestro – RSVP Boda Jenny & Cristian

**Versión:** 6.1  
**Fecha:** Septiembre 2025  
**Estado:** Actualizado (con flujo Magic Link, i18n, correo y carga de invitados)

---

## 1. Objetivo General del Sistema

Construir una solución híbrida y automatizada que permita a los invitados de la boda de Jenny y Cristian confirmar su asistencia de forma **segura**, **sencilla** y **multilenguaje**.

El sistema combina:

- **WordPress (WP):** página principal con información estática.
- **Streamlit:** aplicación multipágina de RSVP para invitados y panel admin.
- **FastAPI (Backend):** lógica de negocio, autenticación, carga de invitados y notificaciones.

---

## 2. Arquitectura y Flujo de Usuario

### 2.1 Componentes del Sistema

- **Web Principal (WordPress):**

  - Alojada en `https://suarezsiicawedding.com`.
  - Contiene historia, galería, dress code, etc.
  - Única interacción → botón **“Confirma tu Asistencia”** (redirige a Streamlit).

- **Aplicación RSVP (Streamlit):**

  - Alojada en `https://rsvp.suarezsiicawedding.com`.
  - Flujo multipágina: Solicitar Acceso (Magic Link) → Login → Formulario RSVP → Confirmado.
  - UI/UX alineada con diseño visual de la web en WP.
  - Internacionalización: **EN (default)**, ES, RO.

- **Backend (FastAPI):**
  - API centralizada para invitado y admin.
  - Seguridad basada en JWT y claves `x-admin-key`.
  - Endpoints para login, recuperación, solicitud de acceso, importación masiva y envío de correos.

---

### 2.2 Flujo de Identificación y Acceso

1. Invitado visita la web principal (WP) y hace clic en **“Confirmar Asistencia”**.
2. Es redirigido a la app Streamlit.
3. La app ofrece **dos formas de acceso**:
   - **Magic Link (recomendado):**
     - Página `Solicitar Acceso` pide:
       - Nombre completo (como en la invitación).
       - Últimos 4 dígitos de teléfono.
       - Email donde recibirá notificaciones.
     - El backend valida → envía correo con un enlace único (`JWT` corto).
     - Invitado hace clic en el enlace → entra directo al formulario RSVP.
   - **Login clásico (guest_code + email/teléfono).**
4. Invitado completa el formulario RSVP (asistencia, acompañantes, alergias).
5. Invitado recibe página de **Confirmación** + correo de confirmación.

---

### 2.3 Gestión de Sesión

- **Tokens JWT**:
  - Guardados en `st.session_state` (no en navegador).
  - Adjuntos en cada request al backend.
- **Cerrar Sesión:** limpia el token y vuelve al login.
- **Magic Link:** token único, corto y con expiración de 15 min.

---

## 3. Requisitos Funcionales (Streamlit RSVP)

### 3.1 Página 0: Login

- Inputs: `guest_code` + (email o teléfono).
- Llama a `POST /api/login`.
- Si correcto → guarda token en `st.session_state` → redirige a Formulario RSVP.

### 3.2 Página 01: Solicitar Acceso (Magic Link)

- Inputs: nombre completo + últimos 4 dígitos de teléfono + email.
- Consentimiento para recibir comunicaciones.
- Llama a `POST /api/request-access`.
- Envío de correo multilenguaje con **enlace mágico**.

### 3.3 Página 01: Recuperar Código

- Inputs: email o teléfono.
- Llama a `POST /api/recover-code`.
- Respuesta genérica para seguridad.
- Previene abuso con **rate limit**.

### 3.4 Página 1: Formulario RSVP

- Protegida (requiere token).
- Carga datos con `GET /api/guest/me`.
- Datos precargados:
  - `full_name`, `language`, `max_accomp`, `confirmed`.
- Inputs dinámicos:
  - Confirmación de asistencia.
  - Número de acompañantes (adultos/niños).
  - Restricciones alimenticias.
- Envío con `POST /api/guest/me/rsvp`.

### 3.5 Página 2: Confirmado

- Mensaje según respuesta (asiste / no asiste).
- Resumen de los datos enviados.
- Botones: **Editar respuesta** y **Cerrar sesión**.

---

## 4. Backend – API y Seguridad

### 4.1 Endpoints principales

- **Invitado:**
  - `POST /api/login`
  - `POST /api/recover-code`
  - `POST /api/request-access`
  - `GET /api/guest/me`
  - `POST /api/guest/me/rsvp`
- **Admin:**
  - `POST /api/admin/import-guests`
  - Protegido con `x-admin-key`.

### 4.2 Seguridad

- **JWT Tokens**: login y magic link.
- **Rate-limit**: `/login` y `/recover-code`.
- **Webhook secret**: para integraciones externas.

---

## 5. Correo & Notificaciones

- Servicio: **SendGrid** (API Key en `.env`).
- Modo `DRY_RUN=1` para pruebas.
- Plantillas:
  - **Invitación / Confirmación / Magic Link.**
- **Multilenguaje (EN, ES, RO):**
  - Se selecciona según campo `language` del invitado.
- Posible integración futura: **Telegram bot** (si no hay email).

---

## 6. Carga de Invitados

### 6.1 Scripts CLI

- **`scripts/load_guests.py`:**

  - Lee Excel/CSV.
  - Valida formato (email, phone, language, invite_type).
  - Reporta duplicados y errores.

- **`scripts/import_guests.py`:**
  - Llama a `load_guests.py`.
  - Envía data validada a `/api/admin/import-guests`.
  - Hace upsert (create/update) con `guest_code` único.

### 6.2 Backend

- `app/routers/admin.py` → procesa importación.
- `models.Guest`: con `guest_code`, `email`, `phone`, `language`, `max_accomp`, `invite_type`.
- Si falta `guest_code` → se genera automáticamente.

---

## 7. Internacionalización (i18n)

- Implementado en `utils/translations.py`.
- Idiomas: **English (default)**, Español, Rumano.
- Claves añadidas:
  - `request.*` (Magic Link).
  - `recover.*` (Recuperar código).
- `utils/lang_selector.py`: componente UI para seleccionar idioma.

---

## 8. Estructura del Proyecto (Actual)

backend/
├── app/
│ ├── routers/
│ │ ├── auth_routes.py
│ │ ├── admin.py
│ ├── models.py
│ ├── schemas.py
│ ├── auth.py
│ ├── mailer.py
│ ├── db.py
│
├── scripts/
│ ├── load_guests.py
│ ├── import_guests.py
│ ├── send_invites.py
│
├── utils/
│ ├── translations.py
│ ├── lang_selector.py
│ ├── nav.py
│
├── streamlit_app.py
├── pages/
│ ├── 0_Login.py
│ ├── 01_Solicitar_Acceso.py
│ ├── 01_Recuperar_Codigo.py
│ ├── 1_Formulario_RSVP.py
│ ├── 2_Confirmado.py
│
├── .env
├── requirements.txt

---

## 9. Próximos Pasos (Post-MVP)

- Mejorar plantillas HTML de correos (alineadas con branding).
- Implementar interfaz de administración en Streamlit (estadísticas, exportación).
- Soporte opcional para recordatorios automáticos.
- Evaluar integración con **Telegram/WhatsApp** para invitados sin correo.
- Añadir manejo de ambigüedad en identificación (ej: homónimos).

---

## 10. Conclusión

La versión **v6.1** representa un sistema **listo para MVP**, con soporte para:

- Acceso clásico y Magic Link.
- Validación robusta de invitados.
- Correos multilenguaje.
- Carga masiva desde Excel/CSV.
- Internacionalización y diseño alineados con WP.

La arquitectura es escalable, segura y lista para evolucionar hacia un panel admin avanzado y notificaciones multicanal.

---
