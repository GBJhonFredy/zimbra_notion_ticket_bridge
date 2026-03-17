import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    # Libreria de toast nativo para Windows 11.
    from win11toast import toast
except ImportError:
    # Si no existe dependencia, se mantiene fallback silencioso.
    toast = None  # type: ignore


def notify_new_ticket(ticket: str, subject: str) -> None:
    # Log de entrada para auditoria de notificaciones.
    logger.info("Intentando mostrar notificación para ticket %s", ticket)

    # Si la libreria no esta instalada, no rompe el flujo principal.
    if toast is None:
        logger.warning("win11toast no está disponible; notificación omitida.")
        return

    # Solo intenta toast en sistemas Windows.
    if not sys.platform.startswith("win"):
        logger.warning("Sistema no Windows; no se muestran notificaciones.")
        return

    # Construye titulo y mensaje de la notificacion.
    title = f"Nuevo ticket registrado: {ticket}"
    # Recorta asunto para evitar payloads demasiado largos en el toast.
    msg = subject[:200]

    try:
        # Lanza la notificacion de sistema.
        toast(
            title,
            msg,
            on_click=None,  # podríamos luego abrir Notion
            duration="short",
        )
        logger.info("Notificación mostrada para ticket %s", ticket)
    except Exception:
        # No detiene el procesamiento de tickets si falla la UI de notificaciones.
        logger.exception("Error al mostrar notificación de Windows.")
