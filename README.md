text
# ARCA

**ARCA** es una herramienta en Python para monitorear correos de soporte en **Zimbra** y registrar tickets automáticamente en **Notion**.

---

## 1. Requisitos previos

Antes de empezar, la persona debe tener instalado en su PC (Windows):

- Python 3.11 o superior
- Git
- Acceso a una cuenta Zimbra con IMAP habilitado
- Token de integración e ID de base de datos en Notion

> Para comprobar si tiene Python y Git, puede ejecutar en PowerShell o CMD:
>
> ```bash
> python --version
> git --version
> ```

---

## 2. Clonar el repositorio

Abrir **PowerShell** o **CMD** y ejecutar:

```bash
git clone https://github.com/GBJhonFredy/zimbra_notion_ticket_bridge.git
cd zimbra_notion_ticket_bridge
3. Crear y activar el entorno virtual (Windows)
Estos comandos están pensados para copiar y pegar tal cual en Windows.

3.1 Crear el entorno virtual
En la carpeta del proyecto (zimbra_notion_ticket_bridge), ejecutar:

bash
py -m venv .venv
Si por alguna razón py no funciona, puede probar:

bash
python -m venv .venv
3.2 Activar el entorno virtual
En PowerShell (recomendado), ejecutar:

powershell
.\.venv\Scripts\Activate.ps1
En CMD clásico (símbolo del sistema), ejecutar:

text
.\.venv\Scripts\activate.bat
Si en PowerShell aparece un error sobre ejecución de scripts, ejecutar PowerShell como Administrador y luego:

powershell
Set-ExecutionPolicy RemoteSigned
Aceptar el cambio, cerrar y abrir de nuevo PowerShell, entrar otra vez a la carpeta del proyecto y repetir:

powershell
.\.venv\Scripts\Activate.ps1
4. Instalar dependencias con Python
Con el entorno virtual activado, ejecutar estos comandos en orden:

bash
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
Si no funciona py, usar:

bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
5. Configurar variables de entorno (.env)
En la carpeta zimbra_notion_ticket_bridge, crear un archivo llamado .env con el siguiente contenido, cambiando los valores de ejemplo:

text
# =========================
# ZIMBRA
# =========================
ZIMBRA_HOST=mail.1cero1.com
ZIMBRA_PORT=993
ZIMBRA_EMAIL=tu_correo@1cero1.com
ZIMBRA_PASSWORD=tu_clave
ZIMBRA_SUPPORT_SENDER=soporte@1cero1.com

# =========================
# NOTION
# =========================
NOTION_TOKEN=tu_token_de_notion
NOTION_DATABASE_ID=tu_database_id

# =========================
# APP
# =========================
POLL_INTERVAL_SECONDS=20
TICKETS_DB_PATH=tickets.sqlite3
LOG_LEVEL=INFO
6. Ejecutar la aplicación con Python
Con el entorno virtual activado y el archivo .env ya creado, ejecutar:

bash
py main.py
Si no funciona py, usar:

bash
python main.py
Esto abrirá la interfaz gráfica de ARCA.

7. Controles dentro de la aplicación
Una vez abierta la ventana de ARCA:

Presionar la tecla 1 para iniciar el monitor.

Presionar la tecla 2 para detener el monitor.

Presionar la tecla Q para salir de la aplicación.

8. Resumen rápido de comandos (para copiar y pegar por bloques)
8.1 Preparar proyecto
bash
git clone https://github.com/GBJhonFredy/zimbra_notion_ticket_bridge.git
cd zimbra_notion_ticket_bridge
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
(Después de esto hay que crear el archivo .env con la configuración de Zimbra y Notion.)

8.2 Ejecutar ARCA
bash
py main.py
9. Notas adicionales
La aplicación procesará correos que lleguen a ZIMBRA_EMAIL y cuyo remitente sea ZIMBRA_SUPPORT_SENDER.

El token de Notion (NOTION_TOKEN) debe tener permisos sobre la base de datos NOTION_DATABASE_ID.

Si se cambia POLL_INTERVAL_SECONDS, hay que cerrar y volver a abrir la aplicación para aplicar el nuevo intervalo.
