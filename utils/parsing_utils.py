import re
from typing import Optional


# Regex de ticket:
# - "ticket " es opcional
# - captura obligatoria: SOP seguido de letras/numeros
# Ejemplos validos: "ticket SOP123", "sopABC999"
TICKET_REGEX = re.compile(
    r"(?:ticket\s+)?(SOP[A-Z0-9]+)",
    re.IGNORECASE,
)


def extract_ticket(text: str) -> Optional[str]:
    """
    Busca patrones tipo 'ticket SOP1003261455JF' o 'SOP1003261455JF'.
    """
    # Si no hay texto, no hay nada que buscar.
    if not text:
        return None
    # Busca la primera coincidencia en todo el texto.
    match = TICKET_REGEX.search(text)
    # Si no matchea, se retorna None para que el caller decida que hacer.
    if not match:
        return None
    # Retorna el ticket normalizado en mayusculas para estandarizar en Notion/SQLite.
    return match.group(1).upper()
