# services/monitor_service.py
import logging
import time
from typing import Callable, Optional

from config.settings import settings
from clients.zimbra_client import ZimbraClient
from services.ticket_processor import TicketProcessor

logger = logging.getLogger(__name__)

OnEvent = Callable[[str], None]


class MonitorService:
    def __init__(self, on_event: Optional[OnEvent] = None, stop_event=None) -> None:
        self.interval = settings.app.monitor_interval_seconds
        self._running = False
        self.on_event = on_event
        self.stop_event = stop_event
        self._processed_count = 0

    def _emit(self, msg: str) -> None:
        logger.info(msg)
        if self.on_event:
            self.on_event(msg)

    def run_loop(self) -> None:
        self._running = True
        processor = TicketProcessor()

        self._emit(f"Monitor iniciado. Intervalo: {self.interval} segundos.")

        while self._running and (self.stop_event is None or not self.stop_event.is_set()):
            try:
                self._emit("Leyendo correos nuevos...")
                client = ZimbraClient()
                emails = client.get_recent_emails_from_support()
                if emails:
                    antes_count = processor.storage.count_processed_today()

                    processor.process_emails(emails)

                    despues_count = processor.storage.count_processed_today()
                    nuevos = max(despues_count - antes_count, 0)
                    self._processed_count += nuevos

                    self._emit(f"Procesados {nuevos} nuevos tickets.")
                    if self.on_event:
                        self.on_event(f"TICKET_COUNT:{self._processed_count}")
                else:
                    self._emit("No hay correos nuevos.")
            except Exception:
                logger.exception("Error en ciclo de monitoreo automático")
                self._emit("ERROR: ocurrió un problema en el ciclo de monitoreo.")

            time.sleep(self.interval)

        self._emit("Monitor detenido.")
        self._running = False
