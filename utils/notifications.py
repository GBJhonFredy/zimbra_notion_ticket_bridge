import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from win11toast import toast
except ImportError:
    toast = None  # type: ignore


def notify_new_ticket(ticket: str, subject: str) -> None:
    logger.info("Intentando mostrar notificación para ticket %s", ticket)

    if toast is None:
        logger.warning("win11toast no está disponible; notificación omitida.")
        return

    if not sys.platform.startswith("win"):
        logger.warning("Sistema no Windows; no se muestran notificaciones.")
        return

    title = f"Nuevo ticket registrado: {ticket}"
    msg = subject[:200]

    try:
        toast(
            title,
            msg,
            on_click=None,  # podríamos luego abrir Notion
            duration="short",
        )
        logger.info("Notificación mostrada para ticket %s", ticket)
    except Exception:
        logger.exception("Error al mostrar notificación de Windows.")
