# Dataclasses para representar configuracion tipada de la aplicacion.
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

# Ruta base del proyecto (carpeta raiz).
# Se usa para construir rutas absolutas a .env, logs y sqlite sin depender del cwd.
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    # Carga variables de entorno desde .env solo si el archivo existe.
    load_dotenv(env_path)


@dataclass
class ZimbraSettings:
    # Credenciales y endpoint IMAP para leer correos.
    email: str
    password: str
    host: str
    port: int


@dataclass
class NotionSettings:
    # Credenciales para escribir/leer tickets en Notion.
    token: str
    database_id: str


@dataclass
class AppSettings:
    # Parametros generales de ejecucion de la app.
    monitor_interval_seconds: int
    log_level: str
    # Rutas derivadas de BASE_DIR para mantener todo relativo al proyecto.
    base_dir: Path = BASE_DIR
    log_dir: Path = BASE_DIR / "logs"
    db_path: Path = BASE_DIR / "tickets.sqlite3"


@dataclass
class MunicipiosSettings:
    # Ruta del Excel usado para detectar municipios en asunto/cuerpo.
    excel_path: str


@dataclass
class Settings:
    # Objeto raiz que agrupa toda la configuracion.
    zimbra: ZimbraSettings
    notion: NotionSettings
    app: AppSettings
    municipios: MunicipiosSettings


def get_settings() -> Settings:
    # Construye configuracion Zimbra leyendo del entorno.
    # Si falta variable, usa defaults razonables para host/puerto.
    zimbra = ZimbraSettings(
        email=os.getenv("ZIMBRA_EMAIL", ""),
        password=os.getenv("ZIMBRA_PASSWORD", ""),
        host=os.getenv("ZIMBRA_HOST", "mail.1cero1.com"),
        port=int(os.getenv("ZIMBRA_PORT", "993")),
    )

    # Construye configuracion Notion. Si token/id estan vacios,
    # NotionTicketClient lanzara error al inicializarse.
    notion = NotionSettings(
        token=os.getenv("NOTION_TOKEN", ""),
        database_id=os.getenv("NOTION_DATABASE_ID", ""),
    )

    # Ajustes generales del monitor y logging.
    app = AppSettings(
        monitor_interval_seconds=int(os.getenv("MONITOR_INTERVAL_SECONDS", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    # Ruta del Excel con municipios; strip elimina espacios accidentales.
    municipios = MunicipiosSettings(
        excel_path=os.getenv("MUNICIPIOS_EXCEL_PATH", "").strip(),
    )

    # Devuelve objeto compuesto listo para importar en todo el proyecto.
    return Settings(zimbra=zimbra, notion=notion, app=app, municipios=municipios)


# Instancia global de configuracion para evitar recargar entorno en cada modulo.
settings = get_settings()
