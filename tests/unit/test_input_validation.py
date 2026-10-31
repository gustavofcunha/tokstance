"""Testes unitarios para validacao de esquema de datasets, normalizacao de usuarios e configuracao."""

from pathlib import Path

import pandas as pd
import pytest

from tokstance.backend.domain.models import (
    carregar_configuracao,
    carregar_videos,
    carregar_videos_reserva,
    dividir_videos_principal_e_reserva,
    limpar_usuarios,
    validar_arquivos_entrada_obrigatorios,
)


@pytest.mark.unit
def test_load_videos_missing_file_raises_file_not_found_error(tmp_path: Path) -> None:
    missing_file = tmp_path / "videos.csv"

    with pytest.raises(FileNotFoundError, match="videos.csv"):
        carregar_videos(missing_file)


@pytest.mark.unit
def test_load_videos_empty_file_raises_value_error(tmp_path: Path) -> None:
    empty_file = tmp_path / "videos.csv"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="videos.csv precisa conter ao menos um registro"):
        carregar_videos(empty_file)


@pytest.mark.unit
def test_load_videos_missing_required_column_raises_value_error(tmp_path: Path) -> None:
    invalid_file = tmp_path / "videos.csv"
    pd.DataFrame([{"id": "101", "url": "https://www.tiktok.com/@u/video/101"}]).to_csv(
        invalid_file, index=False
    )

    with pytest.raises(ValueError, match="target"):
        carregar_videos(invalid_file)


@pytest.mark.unit
def test_load_reserve_videos_missing_file_raises_file_not_found_error(
    study_paths,
) -> None:
    study_paths.arquivo_videos_reserva.unlink()

    with pytest.raises(FileNotFoundError, match="videos_reserva.csv"):
        validar_arquivos_entrada_obrigatorios(
            study_paths.arquivo_videos, study_paths.arquivo_videos_reserva
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

    loaded = carregar_videos_reserva(reserve_file)

    assert loaded.loc[0, "video_description"] == ""
    assert loaded.loc[0, "voice_to_text"] == ""
    assert loaded.loc[0, "video_duration"] == ""


@pytest.mark.unit
def test_clean_users_deduplicates_and_preserves_first_seen_order() -> None:
    raw_input = " alice , bob\nalice,  carol \n\n bob , dave "

    normalized = limpar_usuarios(raw_input)

    assert normalized == ["alice", "bob", "carol", "dave"]


@pytest.mark.unit
def test_load_config_missing_file_creates_and_returns_default_configuration(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "configuracao.json"

    loaded = carregar_configuracao(config_file)

    assert config_file.exists()
    assert loaded["administradores"] == ["admin"]
    assert loaded["rotuladores"] == []
    assert loaded["percentual_sobreposicao"] == 0.0


@pytest.mark.unit
def test_load_config_corrupted_json_raises_value_error(tmp_path: Path) -> None:
    corrupted_file = tmp_path / "configuracao.json"
    corrupted_file.write_text("{invalid json payload", encoding="utf-8")

    with pytest.raises(ValueError, match="configuracao.json inválido ou corrompido"):
        carregar_configuracao(corrupted_file)


@pytest.mark.unit
def test_dividir_videos_principal_e_reserva_seleciona_balanceado_por_target(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)

    principais, reservas = dividir_videos_principal_e_reserva(videos, 2)

    assert len(principais) == 2
    assert len(reservas) == 2
    assert sorted(principais["target"].astype(str).str.strip().tolist()) == [
        "Clima",
        "Economia",
    ]
    assert set(principais["id"]).isdisjoint(set(reservas["id"]))

