# ARCA

**ARCA** es una herramienta de automatización en Python para monitorear correos de soporte en **Zimbra** y registrar tickets automáticamente en **Notion**.

Su propósito es centralizar el flujo de entrada de tickets, reducir trabajo manual y mantener trazabilidad operativa desde una interfaz de escritorio.

---

## Características

- Conexión a buzón Zimbra por IMAP
- Lectura de correos desde un remitente específico
- Extracción de tickets desde asunto o cuerpo del correo
- Registro automático en base de datos de Notion
- Interfaz gráfica de escritorio
- Monitoreo continuo
- Trazabilidad visual mediante event stream
- Almacenamiento local para evitar reprocesar tickets

---

## Requisitos previos

Antes de iniciar, asegúrate de tener instalado:

- **Python 3.11 o superior**
- **Git** (opcional, si clonas el repositorio)
- Acceso válido a:
  - una cuenta de correo en **Zimbra**
  - una integración y base de datos en **Notion**

---

## Clonar el repositorio

Si aún no tienes el proyecto en tu máquina:

```bash
git clone https://github.com/GBJhonFredy/zimbra_notion_ticket_bridge.git
cd zimbra_notion_ticket_bridge
