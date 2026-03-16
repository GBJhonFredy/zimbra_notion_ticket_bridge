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
        self.notion = notion_client
        self.pet = pet
        self.poll_interval_ms = poll_interval_ms
        self.rotate_interval_ms = rotate_interval_ms

        self._last_seen_ids: set[str] = set()
        self._last_summary: Optional[NotionSummary] = None

        self._ephemeral_queue: Deque[PetNotification] = deque()
        self._persistent_notifications: List[PetNotification] = []
        self._persistent_index = 0

        self._start_rotation()
        self._schedule_next_poll()

    # ---------------------------------------------------------
    # Scheduling
    # ---------------------------------------------------------
    def _schedule_next_poll(self) -> None:
        self.pet.root.after(self.poll_interval_ms, self._poll_notion)

    def _start_rotation(self) -> None:
        self._show_next_notification()
        self.pet.root.after(self.rotate_interval_ms, self._rotate_notifications)

    def _rotate_notifications(self) -> None:
        self._show_next_notification()
        self.pet.root.after(self.rotate_interval_ms, self._rotate_notifications)

    # ---------------------------------------------------------
    # Polling Notion
    # ---------------------------------------------------------
    def _poll_notion(self) -> None:
        try:
            summary = get_notion_summary(self.notion)
            self._last_summary = summary

            new_tickets = self._detect_new_tickets(summary)
            for ticket in new_tickets:
                self.enqueue_one_time(
                    "new_ticket",
                    self._build_new_ticket_message(ticket),
                )

            self._persistent_notifications = self._build_persistent_notifications(summary)

            if self._persistent_index >= len(self._persistent_notifications):
                self._persistent_index = 0

        except Exception as e:
            logger.exception("Error consultando Notion para la pet: %s", e)
            self.enqueue_one_time(
                "notion_error",
                "No pude actualizar Notion.\nRevisa conexión, token, permisos o estructura de la base.",
            )

        self._schedule_next_poll()

    # ---------------------------------------------------------
    # Public hooks
    # ---------------------------------------------------------
    def notify_new_mail(self, subject: str, ticket: str | None = None) -> None:
        ticket_line = f"Ticket: {ticket}\n" if ticket else ""
        self.enqueue_one_time(
            "new_mail",
            f"Nuevo correo recibido.\n{ticket_line}Asunto: {subject}",
        )

    def enqueue_one_time(self, state: str, message: str) -> None:
        self._ephemeral_queue.append(
            PetNotification(state=state, message=message, one_time=True)
        )

    # ---------------------------------------------------------
    # Rotation
    # ---------------------------------------------------------
    def _show_next_notification(self) -> None:
        if self._ephemeral_queue:
            item = self._ephemeral_queue.popleft()
            self.pet.set_state(item.state, item.message)
            return

        if self._persistent_notifications:
            item = self._persistent_notifications[self._persistent_index]
            self.pet.set_state(item.state, item.message)
            self._persistent_index = (self._persistent_index + 1) % len(self._persistent_notifications)
            return

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
        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append("Se registró un nuevo ticket.")
        lines.append("Conviene asignar fecha de entrega.")

        return "\n".join(lines)

    def _build_pending_item_message(self, ticket: TicketInfo) -> str:
        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append(f"Estado: {ticket.estado}")

        return "\n".join(lines)

    def _build_in_progress_item_message(self, ticket: TicketInfo) -> str:
        lines = []

        if ticket.ticket:
            lines.append(f"Ticket: {ticket.ticket}")

        lines.append(f"Solicitud: {ticket.title}")
        lines.append(f"Estado: {ticket.estado}")
        lines.append("La solicitud está en gestión.")

        return "\n".join(lines)

    def _build_stale_item_message(self, ticket: TicketInfo) -> str:
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
        current_ids = {t.id for t in summary.all_pending + summary.all_in_progress}

        if not self._last_seen_ids:
            self._last_seen_ids = current_ids
            return []

        new_ids = current_ids - self._last_seen_ids
        self._last_seen_ids = current_ids

        if not new_ids:
            return []

        return [
            t
            for t in (summary.all_pending + summary.all_in_progress)
            if t.id in new_ids
        ]

    @staticmethod
    def _days_since(dt: Optional[datetime]) -> int:
        if not dt:
            return 0
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)