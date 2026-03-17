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
        # Storage local para deduplicar por message_id.
        self.storage = TicketStorage()
        # Cliente Notion para crear paginas de ticket.
        self.notion = NotionTicketClient()

    def process_emails(self, emails: List[EmailMessageModel]) -> None:
        # Recorre cada correo recibido por el monitor.
        for e in emails:
            logger.info("Procesando email %s | %s", e.message_id, e.subject)

            # Paso 1: deduplicacion por message_id.
            if self.storage.is_processed(e.message_id):
                logger.info("Email %s ya procesado, se omite.", e.message_id)
                continue

            # Paso 2: intenta extraer ticket desde asunto, y si no hay, desde el body.
            ticket = extract_ticket(e.subject) or extract_ticket(e.body)
            # Si no hay ticket, marca procesado para no reintentar indefinidamente.
            if not ticket:
                logger.info("No se encontró ticket en email %s, se marca como procesado sin ticket.", e.message_id)
                self.storage.mark_processed(e.message_id, None)
                continue

            logger.info("Ticket detectado: %s", ticket)

            # Paso 3: detecta municipio buscando coincidencias en asunto+cuerpo.
            municipio = detect_municipio(f"{e.subject}\n{e.body}") or ""
            if municipio:
                logger.info("Municipio detectado: %s", municipio)
            else:
                logger.info("No se detectó municipio en el correo.")

            # Paso 4: crea pagina en Notion con estado inicial de flujo.
            self.notion.create_ticket_page(
                ticket=ticket,
                subject=e.subject,
                created_at=e.date,
                estado="Pendiente por iniciar",
                municipio=municipio or None,
            )

            # Paso 5: notificacion local para el operador.
            notify_new_ticket(ticket, e.subject)


            # Paso 6: persistencia final para no duplicar el mismo correo en proximos ciclos.
            self.storage.mark_processed(e.message_id, ticket)
            logger.info("Email %s marcado como procesado.", e.message_id)
