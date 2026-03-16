import logging
from datetime import datetime
from typing import Dict, Any

from notion_client import Client

from config.settings import settings

logger = logging.getLogger(__name__)


class NotionTicketClient:
    def __init__(self) -> None:
        if not settings.notion.token:
            raise ValueError("NOTION_TOKEN no está configurado en el .env")
        if not settings.notion.database_id:
            raise ValueError("NOTION_DATABASE_ID no está configurado en el .env")

        self.client = Client(auth=settings.notion.token)
        self.database_id = settings.notion.database_id

    def test_connection(self) -> Dict[str, Any]:
        logger.info("Probando conexión a Notion y acceso a la base de datos...")
        result = self.client.databases.retrieve(database_id=self.database_id)
        logger.info("Conexión a Notion OK, base de datos accesible.")
        return result

    def create_ticket_page(
        self,
        ticket: str,
        subject: str,
        created_at: datetime,
        estado: str = "Pendiente por iniciar",
        municipio: str | None = None,
    ) -> Dict[str, Any]:

        """
        Crea un registro en la base 'Jhon Gil' con columnas:
        - Asunto (title)
        - Ticket (rich_text)
        - Fecha Ingreso (date)
        - Estado (select)
        """
        logger.info("Creando ticket en Notion: %s", ticket)
        properties = {
            "Asunto": {
                "title": [
                    {
                        "text": {
                            "content": subject[:2000],
                        }
                    }
                ]
            },
            "Ticket": {
                "rich_text": [
                    {
                        "text": {
                            "content": ticket,
                        }
                    }
                ]
            },
            "Fecha Ingreso": {
                "date": {
                    "start": created_at.isoformat(),
                }
            },
            "Estado": {
                "status": {
                    "name": estado,
                }
            },
        }

        if municipio:
            properties["Municipio"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": municipio,
                        }
                    }
                ]
            }

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
        }
        page = self.client.pages.create(**payload)
        logger.info("Ticket creado en Notion con id %s", page.get("id"))
        return page
