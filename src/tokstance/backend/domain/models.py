"""Core domain models, dataclasses, and tabular schema definitions."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tokstance.config import DEFAULT_INVITE_TOKEN, resolve_data_paths

VIDEO_REQUIRED_COLUMNS = ("id", "url", "target")
VIDEO_OPTIONAL_COLUMNS = ("video_description", "voice_to_text", "video_duration")
VIDEO_COLUMNS = VIDEO_REQUIRED_COLUMNS + VIDEO_OPTIONAL_COLUMNS

ASSIGNMENT_COLUMNS = (
    "labeler",
    "video_id",
    "url",
    "target",
    "video_description",
    "voice_to_text",
    "video_duration",
    "assignment_version",
    "assignment_id",
    "overlap_group_id",
)

RESULT_COLUMNS = (
    "timestamp",
    "labeler",
    "video_id",
    "url",
    "target",
    "stance",
    "tempo_analise_segundos",
    "video_duration",
    "assignment_id",
)

ERROR_COLUMNS = (
    "timestamp",
    "video_id",
    "url",
    "labeler",
    "assignment_id",
    "replacement_video_id",
    "replacement_url",
    "replacement_assignment_id",
    "replacement_status",
)

LOG_COLUMNS = (
    "timestamp",
    "usuario",
    "acao",
    "tempo_desde_login_segundos",
)


@dataclass(frozen=True)
class VideoRecord:
    """Immutable representation of a primary or reserve TikTok video item."""

    video_id: str
    url: str
    target: str
    video_description: str = ""
    voice_to_text: str = ""
    video_duration: str = ""


@dataclass
class StudyConfig:
    """Normalized configuration for an annotation round."""

    admins: list[str] = field(default_factory=lambda: ["admin"])
    labelers: list[str] = field(default_factory=list)
    videos_per_labeler: int = 10
    overlap_percent: float = 0.0
    tarefa: str = "Detecção de Posição"
    invite_token: str = DEFAULT_INVITE_TOKEN

    def to_dict(self) -> dict[str, Any]:
        """Serialize study configuration to a JSON-compatible dictionary."""
        return {
            "admins": list(self.admins),
            "labelers": list(self.labelers),
            "videos_per_labeler": int(self.videos_per_labeler),
            "overlap_percent": float(self.overlap_percent),
            "tarefa": str(self.tarefa),
            "invite_token": str(self.invite_token),
        }


@dataclass(frozen=True)
class UserAccount:
    """Registered user account with role and assigned slot metadata."""

    username: str
    password_hash: str
    role: str
    assigned_slot: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class AnnotationRecord:
    """Completed stance annotation submitted by a labeler."""

    timestamp: str
    labeler: str
    video_id: str
    url: str
    target: str
    stance: str
    tempo_analise_segundos: float
    video_duration: str
    assignment_id: str


@dataclass(frozen=True)
class VideoErrorRecord:
    """Reported unavailable video event and its reserve replacement outcome."""

    timestamp: str
    video_id: str
    url: str
    labeler: str
    assignment_id: str
    replacement_video_id: str = ""
    replacement_url: str = ""
    replacement_assignment_id: str = ""
    replacement_status: str = ""


def load_videos(videos_file: Path | None = None) -> pd.DataFrame:
    """Load and validate the primary videos.csv dataset."""
    target_path = Path(videos_file) if videos_file is not None else resolve_data_paths().videos_file
    if not target_path.exists():
        raise FileNotFoundError(
            f"\n[ERRO CRÍTICO] Arquivo '{target_path.name}' ausente. A execução foi abortada."
        )
    if target_path.stat().st_size == 0:
        raise ValueError("videos.csv precisa conter ao menos um registro de vídeo.")
    try:
        videos = pd.read_csv(target_path, dtype=str).fillna("")
    except pd.errors.EmptyDataError as exc:
        raise ValueError("videos.csv precisa conter ao menos um registro de vídeo.") from exc

    if videos.empty:
        raise ValueError("videos.csv precisa conter ao menos um registro de vídeo.")
    missing = set(VIDEO_REQUIRED_COLUMNS).difference(videos.columns)
    if missing:
        raise ValueError(
            f"videos.csv não possui as colunas obrigatórias: {', '.join(sorted(missing))}"
        )
    for column in VIDEO_OPTIONAL_COLUMNS:
        if column not in videos.columns:
            videos[column] = ""
    return videos.fillna("")


def clean_users(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalize a comma- or newline-delimited user list preserving first-seen order."""
    if isinstance(value, (list, tuple, set)):
        raw_text = "\n".join(str(item) for item in value)
    else:
        raw_text = str(value or "")
    candidates = raw_text.replace(",", "\n").splitlines()
    return list(dict.fromkeys(user.strip() for user in candidates if user.strip()))


def load_reserve_videos(reserve_videos_file: Path | None = None) -> pd.DataFrame:
    """Load and validate the reserve videos_reserva.csv dataset."""
    target_path = (
        Path(reserve_videos_file)
        if reserve_videos_file is not None
        else resolve_data_paths().reserve_videos_file
    )
    if not target_path.exists():
        raise FileNotFoundError(
            f"\n[ERRO CRÍTICO] Arquivo '{target_path.name}' ausente. A execução foi abortada."
        )
    if target_path.stat().st_size == 0:
        raise ValueError("videos_reserva.csv precisa conter ao menos um registro de vídeo.")
    try:
        reserve_videos = pd.read_csv(target_path, dtype=str).fillna("")
    except pd.errors.EmptyDataError as exc:
        raise ValueError("videos_reserva.csv precisa conter ao menos um registro de vídeo.") from exc

    if reserve_videos.empty:
        raise ValueError("videos_reserva.csv precisa conter ao menos um registro de vídeo.")
    missing = set(VIDEO_REQUIRED_COLUMNS).difference(reserve_videos.columns)
    if missing:
        raise ValueError(
            f"videos_reserva.csv não possui as colunas obrigatórias: {', '.join(sorted(missing))}"
        )
    for column in VIDEO_OPTIONAL_COLUMNS:
        if column not in reserve_videos.columns:
            reserve_videos[column] = ""
    return reserve_videos.fillna("")


def validate_required_input_files(
    videos_file: Path | None = None,
    reserve_videos_file: Path | None = None,
) -> None:
    """Ensure both primary and reserve video datasets exist and satisfy schema requirements."""
    load_videos(videos_file)
    load_reserve_videos(reserve_videos_file)


def save_config(
    config: dict[str, Any] | StudyConfig,
    config_file: Path | None = None,
) -> None:
    """Persist study configuration JSON to disk."""
    target_path = Path(config_file) if config_file is not None else resolve_data_paths().config_file
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.to_dict() if isinstance(config, StudyConfig) else dict(config)
    with target_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def load_config(config_file: Path | None = None) -> dict[str, Any]:
    """Load and normalize study configuration from configuracao.json."""
    target_path = Path(config_file) if config_file is not None else resolve_data_paths().config_file
    if not target_path.exists():
        default_config = StudyConfig().to_dict()
        save_config(default_config, target_path)
        return default_config

    try:
        with target_path.open(encoding="utf-8") as handle:
            raw_config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("configuracao.json inválido ou corrompido.") from exc

    if not isinstance(raw_config, dict):
        raise ValueError("configuracao.json inválido ou corrompido.")

    raw_config["admins"] = clean_users(raw_config.get("admins", []))
    raw_config["labelers"] = clean_users(raw_config.get("labelers", []))
    raw_config["videos_per_labeler"] = int(raw_config.get("videos_per_labeler", 10))
    raw_config["overlap_percent"] = float(raw_config.get("overlap_percent", 0.0))
    raw_config["tarefa"] = str(raw_config.get("tarefa", "Detecção de Posição"))
    invite_token = str(raw_config.get("invite_token") or DEFAULT_INVITE_TOKEN).strip()
    raw_config["invite_token"] = invite_token or DEFAULT_INVITE_TOKEN
    return raw_config


