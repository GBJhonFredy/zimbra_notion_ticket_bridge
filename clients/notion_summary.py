# clients/notion_summary.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from clients.notion_client import NotionTicketClient


PENDING_STATES = {"Pendiente por iniciar", "Pendiente de aprobación"}
IN_PROGRESS_STATES = {"En proceso", "Pausa"}
DONE_STATES = {"Finalizado", "Reasignado", "Cerrado sin respuesta"}

STATE_PROPERTY = "Estado"
DATE_PROPERTY = "Fecha Ingreso"
TICKET_PROPERTY = "Ticket"
TITLE_PROPERTY = "Asunto"


@dataclass
class TicketInfo:
    id: str
    ticket: str
    title: str
    estado: str
    fecha_ingreso: datetime | None


@dataclass
class NotionSummary:
    pending_count: int
    in_progress_count: int
    done_count: int
    stale_tickets: List[TicketInfo]
    all_pending: List[TicketInfo]
    all_in_progress: List[TicketInfo]
    all_done: List[TicketInfo]


def _get_property_value(page: Dict[str, Any], prop_name: str) -> Any:
    props = page.get("properties", {})
    return props.get(prop_name)


def _extract_rich_text(prop: Dict[str, Any] | None) -> str:
    if not prop:
        return ""

    prop_type = prop.get("type")

    if prop_type == "rich_text":
        return "".join(
            part.get("plain_text", "")
            for part in prop.get("rich_text", [])
        ).strip()

    if prop_type == "title":
        return "".join(
            part.get("plain_text", "")
            for part in prop.get("title", [])
        ).strip()

    return ""


def _extract_title(page: Dict[str, Any]) -> str:
    title_prop = _get_property_value(page, TITLE_PROPERTY)
    title = _extract_rich_text(title_prop)
    return title or page.get("id", "")


def _extract_ticket(page: Dict[str, Any]) -> str:
    ticket_prop = _get_property_value(page, TICKET_PROPERTY)
    return _extract_rich_text(ticket_prop)


def _extract_estado(page: Dict[str, Any]) -> str:
    prop = _get_property_value(page, STATE_PROPERTY)
    if not prop:
        return ""

    if prop["type"] == "status":
        return (prop["status"] or {}).get("name", "")

    if prop["type"] == "select":
        return (prop["select"] or {}).get("name", "")

    return ""


def _extract_fecha_ingreso(page: Dict[str, Any]) -> datetime | None:
    prop = _get_property_value(page, DATE_PROPERTY)
    if not prop:
        return None

    if prop["type"] == "date":
        date_info = prop["date"]
        if not date_info:
            return None

        start = date_info.get("start")
        if not start:
            return None

        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    return None


def _classify_ticket(page: Dict[str, Any]) -> TicketInfo:
    return TicketInfo(
        id=page.get("id", ""),
        ticket=_extract_ticket(page),
        title=_extract_title(page),
        estado=_extract_estado(page),
        fecha_ingreso=_extract_fecha_ingreso(page),
    )


def get_notion_summary(notion: NotionTicketClient) -> NotionSummary:
    pages = notion.fetch_all_tickets()

    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(days=2)

    pending: List[TicketInfo] = []
    in_progress: List[TicketInfo] = []
    done: List[TicketInfo] = []
    stale: List[TicketInfo] = []

    for page in pages:
        ticket = _classify_ticket(page)
        estado = ticket.estado

        if estado in PENDING_STATES:
            pending.append(ticket)
        elif estado in IN_PROGRESS_STATES:
            in_progress.append(ticket)
        elif estado in DONE_STATES:
            done.append(ticket)
        else:
            continue

        if ticket.fecha_ingreso and estado in (PENDING_STATES | IN_PROGRESS_STATES):
            if ticket.fecha_ingreso < stale_threshold:
                stale.append(ticket)

    return NotionSummary(
        pending_count=len(pending),
        in_progress_count=len(in_progress),
        done_count=len(done),
        stale_tickets=stale,
        all_pending=pending,
        all_in_progress=in_progress,
        all_done=done,
    )