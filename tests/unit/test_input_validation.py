"""Unit tests for dataset schema validation, user list normalization, and study configuration."""

from pathlib import Path

import pandas as pd
import pytest

from tokstance.backend.domain.models import (
    clean_users,
    load_config,
    load_reserve_videos,
    load_videos,
    validate_required_input_files,
)


@pytest.mark.unit
def test_load_videos_missing_file_raises_file_not_found_error(tmp_path: Path) -> None:
    missing_file = tmp_path / "videos.csv"

    with pytest.raises(FileNotFoundError, match="videos.csv"):
        load_videos(missing_file)


@pytest.mark.unit
def test_load_videos_empty_file_raises_value_error(tmp_path: Path) -> None:
    empty_file = tmp_path / "videos.csv"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="videos.csv precisa conter ao menos um registro"):
        load_videos(empty_file)


@pytest.mark.unit
def test_load_videos_missing_required_column_raises_value_error(tmp_path: Path) -> None:
    invalid_file = tmp_path / "videos.csv"
    pd.DataFrame([{"id": "101", "url": "https://www.tiktok.com/@u/video/101"}]).to_csv(
        invalid_file, index=False
    )

    with pytest.raises(ValueError, match="target"):
        load_videos(invalid_file)


@pytest.mark.unit
def test_load_reserve_videos_missing_file_raises_file_not_found_error(
    study_paths,
) -> None:
    study_paths.reserve_videos_file.unlink()

    with pytest.raises(FileNotFoundError, match="videos_reserva.csv"):
        validate_required_input_files(
            study_paths.videos_file, study_paths.reserve_videos_file
        )


@pytest.mark.unit
def test_load_reserve_videos_without_optional_columns_fills_empty_strings(
    tmp_path: Path,
) -> None:
    reserve_file = tmp_path / "videos_reserva.csv"
    pd.DataFrame(
        [
            {
                "id": "901",
                "url": "https://www.tiktok.com/@r/video/901",
                "target": "Clima",
            }
        ]
    ).to_csv(reserve_file, index=False)

    loaded = load_reserve_videos(reserve_file)

    assert loaded.loc[0, "video_description"] == ""
    assert loaded.loc[0, "voice_to_text"] == ""
    assert loaded.loc[0, "video_duration"] == ""


@pytest.mark.unit
def test_clean_users_deduplicates_and_preserves_first_seen_order() -> None:
    raw_input = " alice , bob\nalice,  carol \n\n bob , dave "

    normalized = clean_users(raw_input)

    assert normalized == ["alice", "bob", "carol", "dave"]


@pytest.mark.unit
def test_load_config_missing_file_creates_and_returns_default_configuration(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "configuracao.json"

    loaded = load_config(config_file)

    assert config_file.exists()
    assert loaded["admins"] == ["admin"]
    assert loaded["labelers"] == []
    assert loaded["overlap_percent"] == 0.0


@pytest.mark.unit
def test_load_config_corrupted_json_raises_value_error(tmp_path: Path) -> None:
    corrupted_file = tmp_path / "configuracao.json"
    corrupted_file.write_text("{invalid json payload", encoding="utf-8")

    with pytest.raises(ValueError, match="configuracao.json inválido ou corrompido"):
        load_config(corrupted_file)

