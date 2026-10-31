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
def test_carregar_videos_arquivo_ausente_levanta_file_not_found_error(
    tmp_path: Path,
) -> None:
    arquivo_ausente = tmp_path / "videos.csv"

    with pytest.raises(FileNotFoundError, match="videos.csv"):
        carregar_videos(arquivo_ausente)


@pytest.mark.unit
def test_carregar_videos_arquivo_vazio_levanta_value_error(tmp_path: Path) -> None:
    arquivo_vazio = tmp_path / "videos.csv"
    arquivo_vazio.write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError, match="videos.csv precisa conter ao menos um registro"
    ):
        carregar_videos(arquivo_vazio)


@pytest.mark.unit
def test_carregar_videos_coluna_obrigatoria_ausente_levanta_value_error(
    tmp_path: Path,
) -> None:
    arquivo_invalido = tmp_path / "videos.csv"
    pd.DataFrame([{"id": "101", "url": "https://www.tiktok.com/@u/video/101"}]).to_csv(
        arquivo_invalido, index=False
    )

    with pytest.raises(ValueError, match="target"):
        carregar_videos(arquivo_invalido)


@pytest.mark.unit
def test_carregar_videos_reserva_arquivo_ausente_levanta_file_not_found_error(
    caminhos_estudo,
) -> None:
    caminhos_estudo.arquivo_videos_reserva.unlink()

    with pytest.raises(FileNotFoundError, match="videos_reserva.csv"):
        validar_arquivos_entrada_obrigatorios(
            caminhos_estudo.arquivo_videos, caminhos_estudo.arquivo_videos_reserva
        )


@pytest.mark.unit
def test_carregar_videos_reserva_sem_colunas_opcionais_preenche_strings_vazias(
    tmp_path: Path,
) -> None:
    arquivo_reserva = tmp_path / "videos_reserva.csv"
    pd.DataFrame(
        [
            {
                "id": "901",
                "url": "https://www.tiktok.com/@r/video/901",
                "target": "Clima",
            }
        ]
    ).to_csv(arquivo_reserva, index=False)

    carregado = carregar_videos_reserva(arquivo_reserva)

    assert carregado.loc[0, "video_description"] == ""
    assert carregado.loc[0, "voice_to_text"] == ""
    assert carregado.loc[0, "video_duration"] == ""


@pytest.mark.unit
def test_limpar_usuarios_remove_duplicatas_e_preserva_ordem() -> None:
    entrada_bruta = " alice , bob\nalice,  carol \n\n bob , dave "

    normalizado = limpar_usuarios(entrada_bruta)

    assert normalizado == ["alice", "bob", "carol", "dave"]


@pytest.mark.unit
def test_carregar_configuracao_arquivo_ausente_cria_e_retorna_configuracao_padrao(
    tmp_path: Path,
) -> None:
    arquivo_config = tmp_path / "configuracao.json"

    carregada = carregar_configuracao(arquivo_config)

    assert arquivo_config.exists()
    assert carregada["administradores"] == ["admin"]
    assert carregada["rotuladores"] == []
    assert carregada["percentual_sobreposicao"] == 0.0


@pytest.mark.unit
def test_carregar_configuracao_json_corrompido_levanta_value_error(
    tmp_path: Path,
) -> None:
    arquivo_corrompido = tmp_path / "configuracao.json"
    arquivo_corrompido.write_text("{json invalido", encoding="utf-8")

    with pytest.raises(ValueError, match="configuracao.json inválido ou corrompido"):
        carregar_configuracao(arquivo_corrompido)


@pytest.mark.unit
def test_dividir_videos_principal_e_reserva_seleciona_balanceado_por_target(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)

    principais, reservas = dividir_videos_principal_e_reserva(videos, 2)

    assert len(principais) == 2
    assert len(reservas) == 2
    assert sorted(principais["target"].astype(str).str.strip().tolist()) == [
        "Clima",
        "Economia",
    ]
    assert set(principais["id"]).isdisjoint(set(reservas["id"]))
