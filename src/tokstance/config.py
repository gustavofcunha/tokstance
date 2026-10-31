"""Environment configuration, official Brasilia timezone, file paths, and study constants."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
#brasilia official timezone utc minus 3
BRT_TZ = timezone(timedelta(hours=-3))

STANCE_OPTIONS = [
    "Contra",
    "A Favor",
    "Neutro",
    "Vídeo não relacionado ao target",
]

MIN_ERROR_REPORT_SECONDS = 10.0
FAST_ANNOTATION_TOLERANCE_SECONDS = 5.0

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 60.0
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128
MAX_USERNAME_LENGTH = 64
MAX_TEXT_FIELD_LENGTH = 512

DEFAULT_INVITE_TOKEN = os.getenv("TOKSTANCE_INVITE_TOKEN", "TOKSTANCE-2026")
DEFAULT_ADMIN_USERNAME = os.getenv("TOKSTANCE_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("TOKSTANCE_ADMIN_PASSWORD", "TokStance@Admin2026")


@dataclass(frozen=True)
class DataPaths:
    """Resolved file system paths for a TokStance study directory."""

    base_dir: Path
    videos_file: Path
    reserve_videos_file: Path
    results_file: Path
    assignments_file: Path
    config_file: Path
    log_file: Path
    errors_file: Path
    agreement_file: Path
    database_file: Path


def resolve_data_dir(custom_dir: Path | str | None = None) -> Path:
    """Resolve the active study data directory from explicit argument or environment."""
    if custom_dir is not None:
        return Path(custom_dir).resolve()
    env_dir = os.getenv("TOKSTANCE_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return (PROJECT_DIR / "data").resolve()


def resolve_data_paths(custom_dir: Path | str | None = None) -> DataPaths:
    """Build all canonical study file paths for the given data directory."""
    base = resolve_data_dir(custom_dir)
    return DataPaths(
        base_dir=base,
        videos_file=base / "videos.csv",
        reserve_videos_file=base / "videos_reserva.csv",
        results_file=base / "resultados_anotacao.csv",
        assignments_file=base / "atribuicoes.csv",
        config_file=base / "configuracao.json",
        log_file=base / "acessos_log.csv",
        errors_file=base / "erros_videos.csv",
        agreement_file=base / "concordancia.json",
        database_file=base / "tokstance.db",
    )


def now_brt() -> datetime:
    """Return the current timezone-aware datetime in Brasilia time (UTC-03:00)."""
    return datetime.now(BRT_TZ)


def format_brt_timestamp(moment: datetime | None = None) -> str:
    """Format a datetime in Brasilia time using the standard YYYY-MM-DD HH:MM:SS layout."""
    target_moment = moment.astimezone(BRT_TZ) if moment is not None else now_brt()
    return target_moment.strftime("%Y-%m-%d %H:%M:%S")


DEFAULT_PATHS = resolve_data_paths()
BASE_DIR = DEFAULT_PATHS.base_dir
VIDEOS_FILE = DEFAULT_PATHS.videos_file
RESERVE_VIDEOS_FILE = DEFAULT_PATHS.reserve_videos_file
RESULTS_FILE = DEFAULT_PATHS.results_file
ASSIGNMENTS_FILE = DEFAULT_PATHS.assignments_file
CONFIG_FILE = DEFAULT_PATHS.config_file
LOG_FILE = DEFAULT_PATHS.log_file
ERRORS_FILE = DEFAULT_PATHS.errors_file
AGREEMENT_FILE = DEFAULT_PATHS.agreement_file
DATABASE_FILE = DEFAULT_PATHS.database_file

