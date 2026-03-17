# ui/pet_controller.py
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Deque, List

from clients.notion_client import NotionTicketClient
from clients.notion_summary import get_notion_summary, NotionSummary, TicketInfo
from ui.pet import PetWindow

logger = logging.getLogger(__name__)


@dataclass
class PetNotification:
    # Estructura de mensaje para la mascota.
    # one_time=True: se muestra una vez y se elimina (cola efimera).
    state: str
    message: str
    one_time: bool = False


class PetController:
    """
    Motor de notificaciones rotativas:
    - rota cada 20 segundos
    - one_time se muestra una sola vez
    - persistentes siguen rotando
    """

    def __init__(
        self,
        notion_client: NotionTicketClient,
        pet: PetWindow,
        poll_interval_ms: int = 30_000,
        rotate_interval_ms: int = 20_000,
    ) -> None:
        # Dependencias externas: cliente Notion + vista de mascota.
        self.notion = notion_client
        self.pet = pet
        # Cadencias: consulta Notion y rotacion visual.
        self.poll_interval_ms = poll_interval_ms
        self.rotate_interval_ms = rotate_interval_ms

        # Set de ids vistos para detectar altas nuevas sin repetir historicos.
        self._last_seen_ids: set[str] = set()
        # Ultimo resumen calculado (util para debug/telemetria futura).
        self._last_summary: Optional[NotionSummary] = None

        # Cola FIFO de mensajes temporales (errores, nuevos tickets).
        self._ephemeral_queue: Deque[PetNotification] = deque()
        # Lista circular de mensajes persistentes (pendientes/en proceso/stale).
        self._persistent_notifications: List[PetNotification] = []
        self._persistent_index = 0

        # Inicia loop de rotacion y primer scheduler de polling.
        self._start_rotation()
        self._schedule_next_poll()

    # ---------------------------------------------------------
    # Scheduling
    # ---------------------------------------------------------
    def _schedule_next_poll(self) -> None:
        # Programa una nueva consulta a Notion despues del intervalo.
        self.pet.root.after(self.poll_interval_ms, self._poll_notion)

    def _start_rotation(self) -> None:
        # Muestra inmediatamente un mensaje y agenda siguientes rotaciones.
        self._show_next_notification()
        self.pet.root.after(self.rotate_interval_ms, self._rotate_notifications)

    def _rotate_notifications(self) -> None:
        # Se ejecuta periodicamente para cambiar estado visible de la mascota.
        self._show_next_notification()
        self.pet.root.after(self.rotate_interval_ms, self._rotate_notifications)

    # ---------------------------------------------------------
    # Polling Notion
    # ---------------------------------------------------------
    def _poll_notion(self) -> None:
        try:
            # Trae resumen completo de tickets y guarda snapshot.
            summary = get_notion_summary(self.notion)
            self._last_summary = summary

            # Detecta ids recien aparecidos respecto a la ultima consulta.
            new_tickets = self._detect_new_tickets(summary)
            for ticket in new_tickets:
                # Cada nuevo ticket se encola como mensaje efimero (prioridad alta).
                self.enqueue_one_time(
                    "new_ticket",
                    self._build_new_ticket_message(ticket),
                )

            # Reconstruye lista persistente con el estado actual de Notion.
            self._persistent_notifications = self._build_persistent_notifications(summary)

            # Si el indice quedo fuera de rango por cambios de longitud, reinicia a 0.
            if self._persistent_index >= len(self._persistent_notifications):
                self._persistent_index = 0

        except Exception as e:
            # Si Notion falla, notifica al usuario sin detener el loop.
            logger.exception("Error consultando Notion para la pet: %s", e)
            self.enqueue_one_time(
                "notion_error",
                "No pude actualizar Notion.\nRevisa conexión, token, permisos o estructura de la base.",
            )

        # Reagenda siguiente consulta pase lo que pase.
        self._schedule_next_poll()

    # ---------------------------------------------------------
    # Public hooks
    # ---------------------------------------------------------
    def notify_new_mail(self, subject: str, ticket: str | None = None) -> None:
        # Hook publico para encolar aviso de correo nuevo con ticket opcional.
        ticket_line = f"Ticket: {ticket}\n" if ticket else ""
        self.enqueue_one_time(
            "new_mail",
            f"Nuevo correo recibido.\n{ticket_line}Asunto: {subject}",
        )

    def enqueue_one_time(self, state: str, message: str) -> None:
        # Inserta al final de la cola efimera (orden FIFO).
        self._ephemeral_queue.append(
            PetNotification(state=state, message=message, one_time=True)
        )

    # ---------------------------------------------------------
    # Rotation
    # ---------------------------------------------------------
    def _show_next_notification(self) -> None:
        # Prioridad 1: mensajes efimeros.
        if self._ephemeral_queue:
            item = self._ephemeral_queue.popleft()
            self.pet.set_state(item.state, item.message)
            return

        # Prioridad 2: mensajes persistentes en rotacion circular.
        if self._persistent_notifications:
            item = self._persistent_notifications[self._persistent_index]
            self.pet.set_state(item.state, item.message)
            self._persistent_index = (self._persistent_index + 1) % len(self._persistent_notifications)
            return

        # Fallback cuando no hay nada pendiente por mostrar.
        self.pet.set_state(
            "ok",
            "Todo al día.\nNo tienes solicitudes pendientes ni en proceso.",
        )

    # ---------------------------------------------------------
    # Builders
    # ---------------------------------------------------------
    def _build_persistent_notifications(self, summary: NotionSummary) -> List[PetNotification]:
        items: List[PetNotification] = []

        # Pendientes individuales
        # Recorre cada ticket pendiente y crea tarjeta individual.
        for ticket in summary.all_pending:
            items.append(
                PetNotification(
                    state="pending_item",
                    message=self._build_pending_item_message(ticket),
                )
            )

        # Resumen pendientes
        if summary.pending_count > 0:
            items.append(
                PetNotification(
                    state="pending_summary",
                    message=(
                        f"Tienes {summary.pending_count} solicitud(es) pendiente(s).\n"
                        f"Conviene revisar priorización y fecha de entrega."
                    ),
                )
            )

        # En proceso individuales
        # Recorre tickets en ejecucion para mostrarlos uno a uno.
        for ticket in summary.all_in_progress:
            items.append(
                PetNotification(
                    state="in_progress_item",
                    message=self._build_in_progress_item_message(ticket),
                )
            )

        # Resumen en proceso
        if summary.in_progress_count > 0:
            items.append(
                PetNotification(
                    state="in_progress_summary",
                    message=(
                        f"Tienes {summary.in_progress_count} solicitud(es) en proceso.\n"
                        f"El perrito pintor asume que el frente sigue en ejecución controlada."
                    ),
                )
            )

        # Antiguas / para priorizar
        # Recorre tickets stale para generar alertas de priorizacion.
        for ticket in summary.stale_tickets:
            items.append(
                PetNotification(
                    state="stale_item",
                    message=self._build_stale_item_message(ticket),
                )
            )

        # Finalizadas
        if summary.done_count > 0:
            items.append(
                PetNotification(
                    state="done_summary",
                    message=(
                        f"Tienes {summary.done_count} solicitud(es) finalizada(s).\n"
                        f"Buen cierre operativo. Ya hay algo para celebrar sin convocar comité."
                    ),
                )
            )

        return items

    def _build_new_ticket_message(self, ticket: TicketInfo) -> str:
        # Construye mensaje multilinea incremental.
        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append("Se registró un nuevo ticket.")
        lines.append("Conviene asignar fecha de entrega.")

        return "\n".join(lines)

    def _build_pending_item_message(self, ticket: TicketInfo) -> str:
        # Mensaje corto por ticket pendiente.
        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append(f"Estado: {ticket.estado}")

        return "\n".join(lines)

    def _build_in_progress_item_message(self, ticket: TicketInfo) -> str:
        # Mensaje por ticket en proceso con sugerencia contextual.
        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append(f"Estado: {ticket.estado}")
        lines.append("La solicitud está en gestión.")

        return "\n".join(lines)

    def _build_stale_item_message(self, ticket: TicketInfo) -> str:
        # Calcula antiguedad para reforzar priorizacion.
        dias = self._days_since(ticket.fecha_ingreso)

        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append(f"Estado: {ticket.estado}")
        lines.append(f"Antigüedad: {dias} día(s)")
        lines.append("Esta solicitud requiere priorización.")

        return "\n".join(lines)

    # ---------------------------------------------------------
    # Detection helpers
    # ---------------------------------------------------------
    def _detect_new_tickets(self, summary: NotionSummary) -> List[TicketInfo]:
        # Considera como "activos" pendientes + en proceso.
        current_ids = {t.id for t in summary.all_pending + summary.all_in_progress}

        # Primera corrida: inicializa baseline, sin disparar falsos "nuevos" historicos.
        if not self._last_seen_ids:
            self._last_seen_ids = current_ids
            return []

        # Diferencia de sets = ids que aparecieron desde la ultima consulta.
        new_ids = current_ids - self._last_seen_ids
        self._last_seen_ids = current_ids

        if not new_ids:
            return []

        # Filtra y devuelve objetos TicketInfo de los ids nuevos detectados.
        return [
            t
            for t in (summary.all_pending + summary.all_in_progress)
            if t.id in new_ids
        ]

    @staticmethod
    def _days_since(dt: Optional[datetime]) -> int:
        # Devuelve dias transcurridos en UTC con piso en 0.
        if not dt:
            return 0
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)