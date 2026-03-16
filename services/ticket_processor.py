import logging
from typing import List

from models.email_models import EmailMessageModel
from utils.parsing_utils import extract_ticket
from utils.storage_utils import TicketStorage
from clients.notion_client import NotionTicketClient
from utils.notifications import notify_new_ticket
from utils.municipios import detect_municipio



logger = logging.getLogger(__name__)


class TicketProcessor:
    def __init__(self) -> None:
        self.storage = TicketStorage()
        self.notion = NotionTicketClient()

    def process_emails(self, emails: List[EmailMessageModel]) -> None:
        for e in emails:
            logger.info("Procesando email %s | %s", e.message_id, e.subject)

            if self.storage.is_processed(e.message_id):
                logger.info("Email %s ya procesado, se omite.", e.message_id)
                continue

            ticket = extract_ticket(e.subject) or extract_ticket(e.body)
            if not ticket:
                logger.info("No se encontró ticket en email %s, se marca como procesado sin ticket.", e.message_id)
                self.storage.mark_processed(e.message_id, None)
                continue

            logger.info("Ticket detectado: %s", ticket)

            municipio = detect_municipio(f"{e.subject}\n{e.body}") or ""
            if municipio:
                logger.info("Municipio detectado: %s", municipio)
            else:
                logger.info("No se detectó municipio en el correo.")

            # Crear página en Notion
            self.notion.create_ticket_page(
                ticket=ticket,
                subject=e.subject,
                created_at=e.date,
                estado="Pendiente por iniciar",
                municipio=municipio or None,
            )

            notify_new_ticket(ticket, e.subject)


            # Marcar como procesado
            self.storage.mark_processed(e.message_id, ticket)
            logger.info("Email %s marcado como procesado.", e.message_id)
