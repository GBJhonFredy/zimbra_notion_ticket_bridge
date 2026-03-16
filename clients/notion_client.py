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
        Crea un registro en la base con columnas:
        - Asunto (title)
        - Ticket (rich_text)
        - Fecha Ingreso (date)
        - Estado (status)
        - Prioridad (multi_select) -> siempre 'Media'
        """
        logger.info("Creando ticket en Notion: %s", ticket)

        properties: Dict[str, Any] = {
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
            "Prioridad": {
                "multi_select": [
                    {"name": "Media"}
                ]
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

    def _get_first_data_source_id(self) -> str:
        """
        Compatibilidad con la API nueva de Notion, donde las consultas
        se hacen sobre data sources y no directamente sobre databases.
        """
        db = self.client.databases.retrieve(database_id=self.database_id)

        data_sources = db.get("data_sources", [])
        if not data_sources:
            raise RuntimeError(
                "La base de datos no expone data_sources. "
                "Verifica permisos de la integración y la versión del SDK/API."
            )

        first = data_sources[0]
        data_source_id = first.get("id")
        if not data_source_id:
            raise RuntimeError("No fue posible obtener el data_source_id de Notion.")

        return data_source_id

    def _query_database_compat(self, start_cursor: str | None = None) -> Dict[str, Any]:
        """
        Intenta usar databases.query (SDK viejo).
        Si no existe, usa data_sources.query (SDK/API nueva).
        """
        databases_endpoint = getattr(self.client, "databases", None)
        if databases_endpoint and hasattr(databases_endpoint, "query"):
            payload: Dict[str, Any] = {"database_id": self.database_id}
            if start_cursor:
                payload["start_cursor"] = start_cursor
            return databases_endpoint.query(**payload)

        data_sources_endpoint = getattr(self.client, "data_sources", None)
        if data_sources_endpoint and hasattr(data_sources_endpoint, "query"):
            data_source_id = self._get_first_data_source_id()
            payload = {"data_source_id": data_source_id}
            if start_cursor:
                payload["start_cursor"] = start_cursor
            return data_sources_endpoint.query(**payload)

        raise RuntimeError(
            "El SDK de Notion instalado no soporta ni databases.query ni data_sources.query."
        )

    def fetch_all_tickets(self) -> list[dict[str, Any]]:
        """
        Devuelve todas las páginas de la base de datos de tickets en Notion.
        Compatible con SDKs viejos y nuevos.
        """
        logger.info("Obteniendo todos los tickets desde Notion...")
        results: list[dict[str, Any]] = []

        response = self._query_database_compat()
        results.extend(response.get("results", []))

        while response.get("has_more"):
            next_cursor = response.get("next_cursor")
            if not next_cursor:
                break

            response = self._query_database_compat(start_cursor=next_cursor)
            results.extend(response.get("results", []))

        logger.info("Se obtuvieron %d tickets desde Notion.", len(results))
        return results