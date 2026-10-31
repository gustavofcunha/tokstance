"""Shared pytest fixtures for isolated study directories, synthetic datasets, and clocks."""

from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from tokstance.config import BRT_TZ, DataPaths, resolve_data_paths


class DeterministicClock:
    """Controllable clock anchored in Brasilia time for deterministic test execution."""

    def __init__(self, initial_moment: datetime | None = None) -> None:
        self._current = initial_moment or datetime(2026, 10, 31, 12, 0, 0, tzinfo=BRT_TZ)
        self._monotonic = 1000.0

    def now(self) -> datetime:
        """Return the current simulated Brasilia datetime."""
        return self._current

    def monotonic(self) -> float:
        """Return the current simulated monotonic timestamp in seconds."""
        return self._monotonic

    def advance(self, seconds: float) -> None:
        """Advance both wall-clock and monotonic time by the given number of seconds."""
        self._current = self._current + timedelta(seconds=float(seconds))
        self._monotonic += float(seconds)


DEFAULT_SYNTHETIC_VIDEOS = [
    {
        "id": "7100000000000000001",
        "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
        "target": " Clima ",
        "video_description": "Debate sobre mudancas climaticas",
        "voice_to_text": "Precisamos reduzir emissoes agora",
        "video_duration": "25.0",
    },
    {
        "id": "7100000000000000002",
        "url": "https://www.tiktok.com/@creator2/video/7100000000000000002",
        "target": "Clima",
        "video_description": "Analise neutra de indicadores ambientais",
        "voice_to_text": "Os dados mostram variacoes regionais",
        "video_duration": "30.0",
    },
    {
        "id": "7100000000000000003",
        "url": "https://www.tiktok.com/@creator3/video/7100000000000000003",
        "target": "Economia",
        "video_description": "Opiniao sobre taxa de juros",
        "voice_to_text": "A taxa de juros precisa cair",
        "video_duration": "20.0",
    },
    {
        "id": "7100000000000000004",
        "url": "https://www.tiktok.com/@creator4/video/7100000000000000004",
        "target": "Economia",
        "video_description": "Resumo de inflacao mensal",
        "voice_to_text": "O indice ficou estavel neste mes",
        "video_duration": "22.0",
    },
]

DEFAULT_SYNTHETIC_RESERVES = [
    {
        "id": "7900000000000000001",
        "url": "https://www.tiktok.com/@reserve1/video/7900000000000000001",
        "target": "Clima",
        "video_description": "Video reserva sobre clima",
        "voice_to_text": "Reserva tematica de clima",
        "video_duration": "24.0",
    },
    {
        "id": "7900000000000000002",
        "url": "https://www.tiktok.com/@reserve2/video/7900000000000000002",
        "target": "Economia",
        "video_description": "Video reserva sobre economia",
        "voice_to_text": "Reserva tematica de economia",
        "video_duration": "26.0",
    },
]


def write_synthetic_study_files(
    base_dir: Path,
    videos: list[dict[str, Any]] | None = None,
    reserves: list[dict[str, Any]] | None = None,
    config_payload: dict[str, Any] | None = None,
) -> DataPaths:
    """Populate an isolated directory with synthetic CSV and JSON study files."""
    base_dir.mkdir(parents=True, exist_ok=True)
    paths = resolve_data_paths(base_dir)

    video_rows = videos if videos is not None else DEFAULT_SYNTHETIC_VIDEOS
    reserve_rows = reserves if reserves is not None else DEFAULT_SYNTHETIC_RESERVES
    pd.DataFrame(video_rows).to_csv(paths.videos_file, index=False)
    pd.DataFrame(reserve_rows).to_csv(paths.reserve_videos_file, index=False)

    effective_config = config_payload or {
        "admins": ["admin"],
        "labelers": ["alice", "bob"],
        "overlap_percent": 50,
        "invite_token": "TOKSTANCE-2026",
    }
    paths.config_file.write_text(
        json.dumps(effective_config, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return paths


@pytest.fixture()
def deterministic_clock() -> DeterministicClock:
    """Provide a controllable clock anchored in Brasilia time (UTC-03:00)."""
    return DeterministicClock()


@pytest.fixture()
def study_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DataPaths:
    """Provide an isolated temporary study directory wired into TOKSTANCE_DATA_DIR."""
    study_dir = tmp_path / "study_data"
    monkeypatch.setenv("TOKSTANCE_DATA_DIR", str(study_dir))
    return write_synthetic_study_files(study_dir)

