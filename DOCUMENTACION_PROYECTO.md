# Documentacion Tecnica y Didactica - ARCA

Este documento explica el proyecto completo en modo ensenanza: que hace cada archivo, que metodos usa, como se recorren los datos y por que se toman ciertas decisiones.

## 1. Vision General

ARCA automatiza este flujo:
1. Lee correos de soporte desde Zimbra (IMAP).
2. Extrae el codigo de ticket (ejemplo: SOP123...).
3. Detecta municipio en el texto del correo (si existe en Excel).
4. Crea un registro en Notion con estado inicial.
5. Guarda en SQLite que ese correo ya fue procesado (deduplicacion).
6. Muestra estado en UI (panel principal + mascota flotante).

## 2. Estructura del Proyecto

- `main.py`: punto de entrada.
- `config/settings.py`: carga de variables de entorno.
- `clients/`: clientes externos (Zimbra y Notion).
- `services/`: logica de monitoreo y procesamiento.
- `models/`: modelos de datos.
- `utils/`: funciones auxiliares (regex, sqlite, notificaciones, municipios).
- `ui/`: interfaz principal y mascota.
- `ARCA.bat`: arranque rapido en Windows.

---

## 3. Flujo End-to-End (de punta a punta)

### Paso 1: Inicio de la app
Archivo: `main.py`
- `main()` crea la UI principal con `create_app()`.
- Crea la mascota con `PetWindow()`.
- Crea cliente Notion con `NotionTicketClient()`.
- Inicia `PetController(...)` para refrescar estado de Notion cada 30s y rotar mensajes cada 20s.
- Ejecuta `root.mainloop()` para dejar viva la interfaz.

### Paso 2: Monitoreo de correos
Archivo: `ui/app.py` + `services/monitor_service.py`
- En UI, la tecla `1` llama `start_monitor()`.
- `start_monitor()` crea `MonitorService(on_event=..., stop_event=...)` en un hilo.
- `MonitorService.run_loop()` entra en bucle:
  1. `client = ZimbraClient()`
  2. `emails = client.get_recent_emails_from_support()`
  3. `processor.process_emails(emails)`
  4. Actualiza contador de procesados del dia.
  5. Emite eventos a UI (`TICKET_COUNT:N`, mensajes de estado).

### Paso 3: Procesamiento de cada correo
Archivo: `services/ticket_processor.py`
Por cada email:
1. Revisa si ya estaba procesado: `self.storage.is_processed(e.message_id)`.
2. Extrae ticket con regex:
   - primero en asunto: `extract_ticket(e.subject)`
   - si no hay, en cuerpo: `extract_ticket(e.body)`
3. Si no hay ticket, marca el correo como procesado y sigue con el siguiente.
4. Detecta municipio: `detect_municipio(f"{e.subject}\n{e.body}")`.
5. Crea pagina en Notion: `self.notion.create_ticket_page(...)`.
6. Muestra toast de Windows: `notify_new_ticket(ticket, e.subject)`.
7. Marca en SQLite: `self.storage.mark_processed(e.message_id, ticket)`.

### Paso 4: Consulta de estado en Notion para la mascota
Archivo: `ui/pet_controller.py` + `clients/notion_summary.py`
- Cada 30s, `PetController._poll_notion()` llama `get_notion_summary(self.notion)`.
- Esa funcion clasifica tickets en:
  - pendientes
  - en proceso
  - finalizados
  - antiguos (stale > 2 dias en pendiente/en proceso)
- Luego `PetController` construye notificaciones persistentes y temporales.
- Cada 20s rota el mensaje visible en la mascota.

---

## 4. Documentacion Archivo por Archivo

## 4.1 main.py
Responsabilidad:
- Ensambla UI principal + mascota + controlador de notificaciones.

Metodo:
- `main()`.

Idea clave:
- Este archivo no procesa correos directamente, solo inicializa componentes.

## 4.2 config/settings.py
Responsabilidad:
- Cargar `.env` y exponer configuracion tipada con dataclasses.

Clases:
- `ZimbraSettings`: email, password, host, port.
- `NotionSettings`: token, database_id.
- `AppSettings`: intervalo de monitoreo, log level, rutas base/log/db.
- `MunicipiosSettings`: ruta del Excel.
- `Settings`: contenedor general.

Funcion:
- `get_settings()` lee variables de entorno y retorna `Settings`.
- `settings = get_settings()` deja una instancia global lista para importar.

## 4.3 models/email_models.py
Responsabilidad:
- Estructura de un correo normalizado para el pipeline.

Modelo:
- `EmailMessageModel` con:
  - `message_id`
  - `from_address`
  - `subject`
  - `date`
  - `body`

## 4.4 clients/zimbra_client.py
Responsabilidad:
- Hablar con Zimbra via IMAP SSL y convertir correos en `EmailMessageModel`.

Metodos importantes:
- `connect()`: login IMAP.
- `select_inbox()`: selecciona `INBOX`.
- `test_connection()`: prueba de conectividad.
- `close()`: cierra conexion segura.
- `_search(criteria)`: busca mensajes por criterio IMAP.
- `_fetch_message(msg_id)`: trae RFC822 completo.
- `_decode_header_str(raw)`: decodifica Subject/headers con charset.
- `_get_body_text(msg)`: extrae texto plano en multipart o simple.
- `get_recent_emails_from_support(from_address, limit)`: metodo principal.

Ejemplo didactico:
- Se construye criterio IMAP: `(FROM "soporte@1cero1.com")`.
- Se toman los ultimos `limit` IDs.
- Se recorre cada ID y se arma un objeto `EmailMessageModel`.
- Al final siempre se llama `close()` en `finally`.

## 4.5 clients/notion_client.py
Responsabilidad:
- Crear registros en Notion y consultar toda la base.

Metodos:
- `__init__()`: valida `NOTION_TOKEN` y `NOTION_DATABASE_ID`.
- `test_connection()`: `databases.retrieve(...)`.
- `create_ticket_page(...)`: crea pagina con propiedades:
  - Asunto (title)
  - Ticket (rich_text)
  - Fecha Ingreso (date)
  - Estado (status)
  - Prioridad (multi_select = Media)
  - Municipio (opcional)
- `_get_first_data_source_id()`: para API nueva de Notion.
- `_query_database_compat(...)`: compatibilidad `databases.query` o `data_sources.query`.
- `fetch_all_tickets()`: pagina resultados hasta completar todo.

Ejemplo didactico:
- Se arma `properties` como diccionario.
- Se envia `self.client.pages.create(**payload)`.
- Para listar todo, usa bucle con `has_more` y `next_cursor`.

## 4.6 clients/notion_summary.py
Responsabilidad:
- Convertir paginas Notion en resumen operacional.

Constantes:
- `PENDING_STATES`
- `IN_PROGRESS_STATES`
- `DONE_STATES`

Dataclasses:
- `TicketInfo`
- `NotionSummary`

Funciones clave:
- `_extract_rich_text(...)`, `_extract_estado(...)`, `_extract_fecha_ingreso(...)`: extraen valores segun tipo Notion.
- `_classify_ticket(page)`: normaliza una pagina a `TicketInfo`.
- `get_notion_summary(notion)`: clasifica y calcula conteos + stale.

Ejemplo didactico:
- Recorre `pages` una por una.
- Evalua estado y mete cada ticket en su lista correspondiente.
- Si fecha es menor que `now - 2 dias` y estado pendiente/en proceso, entra en `stale_tickets`.

## 4.7 services/monitor_service.py
Responsabilidad:
- Ejecutar ciclo periodico de lectura/procesamiento.

Metodos:
- `_emit(msg)`: log + callback opcional a UI.
- `run_loop()`: bucle principal del monitor.

Recorrido en `run_loop()`:
1. Crear `TicketProcessor`.
2. Emitir "Monitor iniciado".
3. Mientras este corriendo:
   - leer correos
   - contar procesados antes
   - procesar
   - contar procesados despues
   - calcular delta y actualizar contador acumulado
   - enviar evento `TICKET_COUNT`
4. Si falla algo, captura excepcion y sigue el bucle.

## 4.8 services/ticket_processor.py
Responsabilidad:
- Regla de negocio para transformar correos en tickets Notion.

Metodo principal:
- `process_emails(emails)`.

Recorrido exacto:
- Recorre `emails` con `for e in emails`.
- Aplica deduplicacion por `message_id`.
- Extrae ticket por regex.
- Detecta municipio.
- Crea ticket Notion con estado inicial `Pendiente por iniciar`.
- Dispara notificacion local.
- Guarda trazabilidad en SQLite.

## 4.9 utils/parsing_utils.py
Responsabilidad:
- Extraer ID de ticket con regex.

Detalles:
- Regex compilada: `(?:ticket\s+)?(SOP[A-Z0-9]+)` con ignore case.
- Funcion `extract_ticket(text)` retorna ticket en uppercase o `None`.

Ejemplos:
- `ticket sop1001aa` -> `SOP1001AA`
- `SOPABC999` -> `SOPABC999`
- `sin ticket` -> `None`

## 4.10 utils/storage_utils.py
Responsabilidad:
- Persistencia local SQLite para deduplicacion.

Tabla:
- `processed_emails`
  - `message_id` unico
  - `ticket`
  - `created_at`

Metodos:
- `_ensure_schema()`: crea tabla si no existe.
- `is_processed(message_id)`: consulta existencia.
- `mark_processed(message_id, ticket)`: `INSERT OR IGNORE`.
- `count_processed_today()`: conteo por fecha local.

Ejemplo didactico:
- Antes de procesar: `is_processed(...)`.
- Despues de crear en Notion: `mark_processed(...)`.
- Esto evita tickets duplicados por reinicios o reprocesos.

## 4.11 utils/notifications.py
Responsabilidad:
- Toasts en Windows 11.

Funcion:
- `notify_new_ticket(ticket, subject)`.

Comportamiento:
- Si `win11toast` no esta disponible, solo loguea warning.
- Si no es Windows, omite notificacion.
- Si todo esta bien, muestra toast con titulo y asunto truncado.

## 4.12 utils/municipios.py
Responsabilidad:
- Cargar municipios desde Excel y detectar menciones en texto.

Funciones:
- `_cargar_municipios_desde_excel()`: lee todas las hojas y toma columna `Municipio`.
- `_ensure_cache()`: guarda set normalizado en memoria.
- `_formatear_municipio(nombre)`: normaliza capitalizacion.
- `detect_municipio(texto)`: busca substring y retorna municipio o `None`.

Ejemplo didactico:
- Texto: "cliente de jamundi reporta falla".
- Si "jamundi" esta en el Excel, retorna "Jamundi" (capitalizado).

## 4.13 ui/app.py
Responsabilidad:
- Interfaz principal con estado del monitor, eventos y contexto.

Elementos clave:
- `create_app()` arma toda la ventana Tkinter.
- `EventStream.add_event(...)` agrega filas de eventos con color por nivel.
- Teclas:
  - `1`: iniciar monitor
  - `2`: detener monitor
  - `q`: salir

Flujo de eventos en UI:
1. `MonitorService` envia mensajes con callback `on_event`.
2. Mensajes van a `event_queue`.
3. `drain_queue()` lee cola cada 200ms.
4. Actualiza labels (contador, ultimo evento, estado global) y stream.

Checks de conectividad:
- `check_zimbra()` hace lectura corta de correo.
- `check_notion()` usa `test_connection()`.

## 4.14 ui/pet.py
Responsabilidad:
- Ventana flotante de mascota + tarjeta de mensaje.

Metodo clave:
- `set_state(state, message)` cambia imagen, badge y texto.

Detalles utiles:
- Carga imagenes desde `assets/`.
- Soporta arrastre de mascota y tarjeta.
- Reubica tarjeta automaticamente junto a la mascota.

## 4.15 ui/pet_controller.py
Responsabilidad:
- Motor de notificaciones de la mascota.

Conceptos:
- Cola efimera (`_ephemeral_queue`): mensajes one-time.
- Lista persistente (`_persistent_notifications`): mensajes que rotan.

Metodos clave:
- `_poll_notion()`: pide resumen y detecta nuevos tickets.
- `_show_next_notification()`: prioridad a cola efimera; si no, rota persistentes; si no hay nada, muestra "Todo al dia".
- `_build_persistent_notifications(summary)`: construye mensajes por estado.
- `_detect_new_tickets(summary)`: compara IDs actuales vs IDs vistos.

Regla importante:
- En primera lectura, `_last_seen_ids` se inicializa y NO dispara "nuevo ticket" historico.

## 4.16 ARCA.bat
Responsabilidad:
- Iniciar app en Windows usando Python del entorno virtual.

Acciones:
1. Va al directorio del script.
2. Ejecuta `.venv\Scripts\python.exe main.py`.
3. Hace `pause` para que no cierre la consola al instante.

## 4.17 .env.example
Responsabilidad:
- Plantilla de variables de entorno.

Campos:
- Zimbra: email/password/host/port.
- Notion: token/database id.
- App: intervalo y logs.
- Excel: ruta de municipios.

---

## 5. Reglas de Negocio Importantes

1. Deduplicacion por `message_id`:
- Un correo solo se procesa una vez.

2. Ticket obligatorio para crear en Notion:
- Si no hay `SOP...`, el correo se marca como procesado pero no crea pagina.

3. Estado inicial en Notion:
- Siempre `Pendiente por iniciar` al crear.

4. Prioridad fija inicial:
- Siempre `Media` al crear.

5. Municipio opcional:
- Solo se envia si fue detectado.

---

## 6. Ejemplo Guiado Completo

Correo entrante:
- Subject: `Solicitud SOP1003261455JF`
- Body: `Cliente de Jamundi reporta incidencia`
- Message-ID: `<abc123@mail>`

Recorrido:
1. `ZimbraClient` lo obtiene y arma `EmailMessageModel`.
2. `TicketProcessor` valida que `<abc123@mail>` no este procesado.
3. `extract_ticket(...)` retorna `SOP1003261455JF`.
4. `detect_municipio(...)` retorna `Jamundi`.
5. `NotionTicketClient.create_ticket_page(...)` crea pagina.
6. `notify_new_ticket(...)` muestra toast.
7. `TicketStorage.mark_processed(...)` guarda `<abc123@mail>`.
8. Si vuelve a aparecer ese correo, `is_processed(...)` evita duplicado.

---

## 7. Dependencias Clave (requirements)

- `notion-client`: API de Notion.
- `python-dotenv`: carga de `.env`.
- `pandas` + `openpyxl`: lectura de Excel de municipios.
- `win11toast` + `pywin32`: notificaciones Windows.

---

## 8. Observaciones Tecnicas para Mejorar

1. El archivo `README.md` esta desformateado y mezcla bloques sin cerrar.
2. `ui/app.py` tiene varias funciones internas; podria dividirse en modulos de UI para mantenimiento.
3. Conviene parametrizar nombres de propiedades Notion por `.env` para evitar acoplamiento a esquema fijo.
4. El estado del monitor en UI y el polling de mascota son dos ciclos distintos; hay que mantenerlos sincronizados en cambios futuros.

---

## 9. Mini Glosario

- IMAP: protocolo para leer correos en servidor.
- Notion Database: tabla donde se guardan tickets.
- Stale ticket: ticket pendiente/en proceso con antiguedad mayor a 2 dias.
- Deduplicacion: evitar procesar dos veces el mismo correo.

Fin del documento.
