import sqlite3
from pathlib import Path
from typing import Optional

from config.settings import settings


class TicketStorage:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        # Usa la ruta por defecto del settings o una ruta inyectada para pruebas.
        self.db_path = db_path or settings.app.db_path
        # Garantiza que la tabla exista antes de cualquier lectura/escritura.
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        # Abre una conexion nueva por operacion para evitar estado compartido.
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        # Crea tabla de correos procesados si no existe.
        # UNIQUE(message_id) impide duplicar el mismo correo.
        conn = self._get_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    ticket TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(message_id)
                );
                """
            )
            # Confirma cambios de DDL.
            conn.commit()
        finally:
            # Cierra siempre, incluso si falla commit/execute.
            conn.close()

    def is_processed(self, message_id: str) -> bool:
        # Consulta ligera: solo verifica existencia de una fila.
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT 1 FROM processed_emails WHERE message_id = ? LIMIT 1",
                (message_id,),
            )
            # Si hay resultado, ya fue procesado.
            return cur.fetchone() is not None
        finally:
            conn.close()

    def mark_processed(self, message_id: str, ticket: Optional[str]) -> None:
        # Guarda trazabilidad del correo procesado.
        # INSERT OR IGNORE evita error si por carrera ya existe ese message_id.
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_emails (message_id, ticket)
                VALUES (?, ?)
                """,
                (message_id, ticket),
            )
            conn.commit()
        finally:
            conn.close()
    
    def count_processed_today(self) -> int:
        # Cuenta filas creadas hoy en horario local; se usa para mostrar delta diario en UI.
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """
                SELECT COUNT(*)
                FROM processed_emails
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                """
            )
            row = cur.fetchone()
            # Convierte el COUNT(*) a int seguro.
            return int(row[0]) if row else 0
        finally:
            conn.close()

