"""Testes unitarios para distancias configuraveis entre rotulos, alfa de Krippendorff e alertas."""

import pandas as pd
import pytest

from tokstance.backend.domain.agreement import (
    calcular_concordancia,
    distancia_rotulos,
    encontrar_anotacoes_rapidas,
    filtrar_por_versao_atribuicao,
    tabela_atribuicoes_por_versao,
    versoes_atribuicao,
)
from tokstance.backend.domain.models import (
    DISTANCIAS_ROTULOS_PADRAO,
    gerar_combinacoes_rotulos,
)


@pytest.mark.unit
def test_label_distance_returns_zero_for_identical_labels() -> None:
    custom_distances = {"Baixo|Médio": 1.5, "Baixo|Alto": 4.0, "Médio|Alto": 2.0}

    assert distancia_rotulos("Baixo", "Baixo", custom_distances) == 0.0
    assert distancia_rotulos("Contra", "Contra", DISTANCIAS_ROTULOS_PADRAO) == 0.0


@pytest.mark.unit
def test_label_distance_is_symmetric_and_reads_configured_penalties() -> None:
    assert distancia_rotulos("Contra", "A Favor", DISTANCIAS_ROTULOS_PADRAO) == 3.0
    assert distancia_rotulos("A Favor", "Contra", DISTANCIAS_ROTULOS_PADRAO) == 3.0
    assert distancia_rotulos("Contra", "Neutro", DISTANCIAS_ROTULOS_PADRAO) == 1.0
    assert distancia_rotulos("Neutro", "A Favor", DISTANCIAS_ROTULOS_PADRAO) == 1.0
    assert (
        distancia_rotulos(
            "Vídeo não relacionado ao target", "Contra", DISTANCIAS_ROTULOS_PADRAO
        )
        == 2.0
    )
    assert (
        distancia_rotulos(
            "A Favor", "Vídeo não relacionado ao target", DISTANCIAS_ROTULOS_PADRAO
        )
        == 2.0
    )


@pytest.mark.unit
def test_generate_label_combinations_builds_all_pairs_for_custom_task_options() -> None:
    custom_options = ["Leve", "Moderado", "Grave"]
    configured_penalties = {"Leve|Grave": 5.0, "Leve|Moderado": 1.5}

    pairs = gerar_combinacoes_rotulos(
        custom_options,
        distancias_existentes=configured_penalties,
        penalidade_padrao=2.0,
    )

    assert pairs == {
        "Leve|Moderado": 1.5,
        "Leve|Grave": 5.0,
        "Moderado|Grave": 2.0,
    }


@pytest.mark.unit
def test_calculate_agreement_returns_none_alpha_when_no_video_has_multiple_annotations(
    study_paths,
) -> None:
    single_annotations = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )

    summary = calcular_concordancia(single_annotations)

    assert summary["alfa"] is None
    assert summary["videos_com_multiplas_anotacoes"] == 0
    assert summary["videos_com_discordancia"] == []


@pytest.mark.unit
def test_calculate_agreement_returns_unit_alpha_for_perfect_consensus_on_custom_task() -> None:
    custom_config = {
        "opcoes_posicao": ["Tóxico", "Não Tóxico", "Incerto"],
        "distancias_rotulos": {
            "Tóxico|Não Tóxico": 4.0,
            "Tóxico|Incerto": 1.5,
            "Não Tóxico|Incerto": 1.5,
        },
    }
    consensus_annotations = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Tóxico"},
            {"video_id": "101", "labeler": "bob", "stance": "Tóxico"},
            {"video_id": "102", "labeler": "alice", "stance": "Não Tóxico"},
            {"video_id": "102", "labeler": "bob", "stance": "Não Tóxico"},
        ]
    )

    summary = calcular_concordancia(
        consensus_annotations, configuracao=custom_config
    )

    assert summary["alfa"] == 1.0
    assert summary["videos_com_multiplas_anotacoes"] == 2
    assert summary["anotacoes_consideradas"] == 4
    assert summary["videos_com_discordancia"] == []


@pytest.mark.unit
def test_calculate_agreement_uses_configured_penalties_for_disagreement_severity(
    study_paths,
) -> None:
    neutral_shift = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "Neutro"},
            {"video_id": "102", "labeler": "alice", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )
    polar_divergence = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "A Favor"},
            {"video_id": "102", "labeler": "alice", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )

    neutral_summary = calcular_concordancia(neutral_shift)
    polar_summary = calcular_concordancia(polar_divergence)

    assert neutral_summary["videos_com_discordancia"][0]["discordancia_ordinal"] == 1.0
    assert polar_summary["videos_com_discordancia"][0]["discordancia_ordinal"] == 3.0
    assert polar_summary["alfa"] < neutral_summary["alfa"]


@pytest.mark.unit
def test_calculate_agreement_ranks_outlier_annotator_highest_in_penalty_list(
    study_paths,
) -> None:
    results = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "Neutro"},
            {"video_id": "101", "labeler": "carol", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "Neutro"},
            {"video_id": "102", "labeler": "carol", "stance": "A Favor"},
        ]
    )

    summary = calcular_concordancia(results)
    penalties = summary["rotuladores_com_maior_discordancia"]

    assert penalties[0]["rotulador"] == "carol"
    assert penalties[0]["penalidade"] == 3.0
    assert penalties[-1]["rotulador"] == "bob"
    assert penalties[-1]["penalidade"] == 2.0


@pytest.mark.unit
def test_find_fast_annotations_flags_submissions_faster_than_duration_minus_tolerance() -> None:
    videos = pd.DataFrame(
        [
            {"id": "101", "video_duration": "25.0"},
            {"id": "102", "video_duration": "30.0"},
        ]
    )
    results = pd.DataFrame(
        [
            {
                "video_id": "101",
                "labeler": "alice",
                "tempo_analise_segundos": "12.0",
                "video_duration": "25.0",
            },
            {
                "video_id": "102",
                "labeler": "bob",
                "tempo_analise_segundos": "8.0",
                "video_duration": "30.0",
            },
        ]
    )

    alerts = encontrar_anotacoes_rapidas(
        results, videos, tolerancia_segundos=5.0
    )

    assert len(alerts) == 2
    assert alerts[0]["rotulador"] == "bob"
    assert alerts[0]["diferenca_segundos"] == 22.0
    assert alerts[1]["rotulador"] == "alice"
    assert alerts[1]["diferenca_segundos"] == 13.0


@pytest.mark.unit
def test_find_fast_annotations_ignores_submissions_within_tolerance_threshold() -> None:
    videos = pd.DataFrame([{"id": "101", "video_duration": "25.0"}])
    results = pd.DataFrame(
        [
            {
                "video_id": "101",
                "labeler": "alice",
                "tempo_analise_segundos": "21.5",
                "video_duration": "25.0",
            }
        ]
    )

    alerts = encontrar_anotacoes_rapidas(
        results, videos, tolerancia_segundos=5.0
    )

    assert alerts == []


@pytest.mark.unit
def test_assignment_versions_lists_active_version_first_and_excludes_legacy_prefix() -> None:
    assignments = pd.DataFrame([{"assignment_version": "v_active_003"}])
    results = pd.DataFrame(
        [
            {"assignment_id": "v_old_001:alice:101"},
            {"assignment_id": "legacy:bob:102"},
        ]
    )
    errors = pd.DataFrame([{"assignment_id": "v_old_002:carol:103"}])

    versions = versoes_atribuicao(assignments, results, errors)

    assert versions == ["v_active_003", "v_old_002", "v_old_001"]


@pytest.mark.unit
def test_filter_by_assignment_version_and_table_reconstruct_historical_round() -> None:
    assignments = pd.DataFrame(
        [
            {
                "assignment_version": "v_active_002",
                "assignment_id": "v_active_002:alice:101",
                "labeler": "alice",
                "video_id": "101",
            }
        ]
    )
    results = pd.DataFrame(
        [
            {"assignment_id": "v_old_001:alice:101", "labeler": "alice", "video_id": "101"},
            {"assignment_id": "v_active_002:alice:101", "labeler": "alice", "video_id": "101"},
        ]
    )
    errors = pd.DataFrame(
        [{"assignment_id": "v_old_001:bob:102", "labeler": "bob", "video_id": "102"}]
    )

    filtered_results = filtrar_por_versao_atribuicao(results, "v_old_001")
    reconstructed = tabela_atribuicoes_por_versao(
        assignments, results, errors, "v_old_001"
    )

    assert len(filtered_results) == 1
    assert len(reconstructed) == 2
