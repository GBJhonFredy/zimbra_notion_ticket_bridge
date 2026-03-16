import re
from typing import Optional


TICKET_REGEX = re.compile(
    r"(?:ticket\s+)?(SOP[A-Z0-9]+)",
    re.IGNORECASE,
)


def extract_ticket(text: str) -> Optional[str]:
    """
    Busca patrones tipo 'ticket SOP1003261455JF' o 'SOP1003261455JF'.
    """
    if not text:
        return None
    match = TICKET_REGEX.search(text)
    if not match:
        return None
    return match.group(1).upper()
