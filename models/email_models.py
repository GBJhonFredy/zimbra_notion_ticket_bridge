# Dataclass simple para transportar un correo ya parseado por el cliente IMAP.
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EmailMessageModel:
    # ID unico del correo (Message-ID del header o fallback al id IMAP).
    message_id: str
    # Valor del header From tal como llega del servidor.
    from_address: str
    # Asunto ya decodificado (utf-8/charset compatible).
    subject: str
    # Fecha del correo convertida a datetime.
    date: datetime
    # Cuerpo de texto plano extraido del mensaje.
    body: str
