from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

# Ruta base del proyecto (carpeta raíz)
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


@dataclass
class ZimbraSettings:
    email: str
    password: str
    host: str
    port: int


@dataclass
class NotionSettings:
    token: str
    database_id: str


@dataclass
class AppSettings:
    monitor_interval_seconds: int
    log_level: str
    base_dir: Path = BASE_DIR
    log_dir: Path = BASE_DIR / "logs"
    db_path: Path = BASE_DIR / "tickets.sqlite3"


@dataclass
class MunicipiosSettings:
    excel_path: str


@dataclass
class Settings:
    zimbra: ZimbraSettings
    notion: NotionSettings
    app: AppSettings
    municipios: MunicipiosSettings


def get_settings() -> Settings:
    zimbra = ZimbraSettings(
        email=os.getenv("ZIMBRA_EMAIL", ""),
        password=os.getenv("ZIMBRA_PASSWORD", ""),
        host=os.getenv("ZIMBRA_HOST", "mail.1cero1.com"),
        port=int(os.getenv("ZIMBRA_PORT", "993")),
    )

    notion = NotionSettings(
        token=os.getenv("NOTION_TOKEN", ""),
        database_id=os.getenv("NOTION_DATABASE_ID", ""),
    )

    app = AppSettings(
        monitor_interval_seconds=int(os.getenv("MONITOR_INTERVAL_SECONDS", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    municipios = MunicipiosSettings(
        excel_path=os.getenv("MUNICIPIOS_EXCEL_PATH", "").strip(),
    )

    return Settings(zimbra=zimbra, notion=notion, app=app, municipios=municipios)


settings = get_settings()
