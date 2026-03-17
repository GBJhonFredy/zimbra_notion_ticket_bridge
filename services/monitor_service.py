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
        # Intervalo de polling configurable por .env.
        self.interval = settings.app.monitor_interval_seconds
        # Flag interno de ejecucion del loop.
        self._running = False
        # Callback de salida para informar eventos a la UI.
        self.on_event = on_event
        # Event opcional para detener hilo de forma coordinada.
        self.stop_event = stop_event
        # Contador acumulado de tickets procesados durante la sesion.
        self._processed_count = 0

    def _emit(self, msg: str) -> None:
        # Emite tanto a logs como a la UI (si hay callback).
        logger.info(msg)
        if self.on_event:
            self.on_event(msg)

    def run_loop(self) -> None:
        # Marca monitor activo y crea processor una sola vez por ciclo de vida.
        self._running = True
        processor = TicketProcessor()

        self._emit(f"Monitor iniciado. Intervalo: {self.interval} segundos.")

        # Bucle principal: se repite hasta que _running sea False o se dispare stop_event.
        while self._running and (self.stop_event is None or not self.stop_event.is_set()):
            try:
                self._emit("Leyendo correos nuevos...")
                # Cliente Zimbra para traer lote reciente de correos.
                client = ZimbraClient()
                emails = client.get_recent_emails_from_support()
                if emails:
                    # Conteo antes/despues para calcular cuantos se procesaron en este tick.
                    antes_count = processor.storage.count_processed_today()

                    # Procesa lista de correos (for interno en TicketProcessor).
                    processor.process_emails(emails)

                    despues_count = processor.storage.count_processed_today()
                    nuevos = max(despues_count - antes_count, 0)
                    self._processed_count += nuevos

                    self._emit(f"Procesados {nuevos} nuevos tickets.")
                    if self.on_event:
                        # Evento especial parseable por la UI para actualizar metrica numerica.
                        self.on_event(f"TICKET_COUNT:{self._processed_count}")
                else:
                    self._emit("No hay correos nuevos.")
            except Exception:
                # Nunca rompe el loop por un error puntual; informa y continua.
                logger.exception("Error en ciclo de monitoreo automático")
                self._emit("ERROR: ocurrió un problema en el ciclo de monitoreo.")

            # Espera bloqueante hasta el siguiente ciclo de polling.
            time.sleep(self.interval)

        # Estado final cuando el loop termina.
        self._emit("Monitor detenido.")
        self._running = False
