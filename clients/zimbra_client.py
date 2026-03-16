import imaplib
import logging
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime
from datetime import datetime
from typing import Optional, List, Tuple

from config.settings import settings
from models.email_models import EmailMessageModel

logger = logging.getLogger(__name__)


class ZimbraClient:
    def __init__(self) -> None:
        self.host = settings.zimbra.host
        self.port = settings.zimbra.port
        self.email = settings.zimbra.email
        self.password = settings.zimbra.password
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> None:
        logger.info("Conectando a Zimbra IMAP %s:%s ...", self.host, self.port)
        self._imap = imaplib.IMAP4_SSL(self.host, self.port)
        resp, _ = self._imap.login(self.email, self.password)
        if resp != "OK":
            raise RuntimeError("No se pudo autenticar en Zimbra IMAP")
        logger.info("Conexión y login IMAP correctos.")

    def select_inbox(self) -> None:
        if not self._imap:
            raise RuntimeError("IMAP no conectado")

        resp, _ = self._imap.select("INBOX")
        if resp != "OK":
            raise RuntimeError("No se pudo seleccionar INBOX")

        logger.info("INBOX seleccionado correctamente.")

    def test_connection(self) -> None:
        try:
            self.connect()
            self.select_inbox()
            logger.info("Prueba de conexión a Zimbra OK.")
        finally:
            self.close()

    def close(self) -> None:
        if self._imap is not None:
            try:
                self._imap.close()
            except Exception:
                pass

            try:
                self._imap.logout()
            except Exception:
                pass

            self._imap = None
            logger.info("Conexión IMAP cerrada.")

    def _ensure_connected_and_inbox(self) -> None:
        if self._imap is None:
            self.connect()
        self.select_inbox()

    def _search(self, criteria: str) -> List[bytes]:
        if not self._imap:
            raise RuntimeError("IMAP no conectado")

        resp, data = self._imap.search(None, criteria)
        if resp != "OK":
            raise RuntimeError(f"Error al buscar mensajes con criterio {criteria}")

        return data[0].split()

    def _decode_header_str(self, raw: str) -> str:
        if not raw:
            return ""

        try:
            decoded = decode_header(raw)
            return str(make_header(decoded))
        except Exception:
            return raw

    def _fetch_message(self, msg_id: bytes) -> Tuple[bytes, Message]:
        if not self._imap:
            raise RuntimeError("IMAP no conectado")

        resp, data = self._imap.fetch(msg_id, "(RFC822)")
        if resp != "OK" or not data or not data[0]:
            raise RuntimeError(f"No se pudo obtener el mensaje {msg_id!r}")

        raw_email = data[0][1]
        msg = message_from_bytes(raw_email)
        return raw_email, msg

    def _get_body_text(self, msg: Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload is None:
                            continue

                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload is None:
                    return ""

                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
            except Exception:
                return ""

        return ""

    def get_recent_emails_from_support(
        self,
        from_address: str = "soporte@1cero1.com",
        limit: int = 10,
    ) -> List[EmailMessageModel]:
        """
        Devuelve hasta 'limit' correos recientes del remitente indicado.
        """
        try:
            self._ensure_connected_and_inbox()

            criteria = f'(FROM "{from_address}")'
            ids = self._search(criteria)
            logger.info("Encontrados %d mensajes de %s", len(ids), from_address)

            ids = ids[-limit:]

            emails: List[EmailMessageModel] = []

            for msg_id in ids:
                _, msg = self._fetch_message(msg_id)

                msg_id_header = (msg.get("Message-ID") or "").strip()
                from_header = msg.get("From", "")
                subject_header = msg.get("Subject", "")
                date_header = msg.get("Date", "")

                subject = self._decode_header_str(subject_header)
                body = self._get_body_text(msg)

                try:
                    date = parsedate_to_datetime(date_header)
                except Exception:
                    date = datetime.now()

                email_model = EmailMessageModel(
                    message_id=msg_id_header or msg_id.decode(errors="ignore"),
                    from_address=from_header,
                    subject=subject,
                    date=date,
                    body=body,
                )
                emails.append(email_model)

            return emails

        finally:
            self.close()