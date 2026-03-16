from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EmailMessageModel:
    message_id: str
    from_address: str
    subject: str
    date: datetime
    body: str
