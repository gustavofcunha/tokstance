"""Unit tests for weighted stance distance, Krippendorff alpha, and fast annotation alerts."""

import pandas as pd
import pytest

from tokstance.backend.domain.agreement import calculate_agreement, label_distance


@pytest.mark.unit
def test_label_distance_returns_zero_for_identical_stance_labels() -> None:
    assert label_distance("Contra", "Contra") == 0.0
    assert label_distance("A Favor", "A Favor") == 0.0
    assert label_distance("Neutro", "Neutro") == 0.0
    assert (
        label_distance(
            "Vídeo não relacionado ao target",
            "Vídeo não relacionado ao target",
        )
        == 0.0
    )


@pytest.mark.unit
def test_label_distance_is_symmetric_and_respects_domain_weights() -> None:
    assert label_distance("Contra", "A Favor") == 4.0
    assert label_distance("A Favor", "Contra") == 4.0
    assert label_distance("Contra", "Neutro") == 1.0
    assert label_distance("Neutro", "A Favor") == 1.0
    assert label_distance("Vídeo não relacionado ao target", "Contra") == 3.0
    assert label_distance("A Favor", "Vídeo não relacionado ao target") == 3.0


@pytest.mark.unit
def test_calculate_agreement_returns_none_alpha_when_no_video_has_multiple_annotations() -> None:
    single_annotations = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )

    summary = calculate_agreement(single_annotations)

    assert summary["alfa"] is None
    assert summary["videos_com_multiplas_anotacoes"] == 0
    assert summary["videos_com_discordancia"] == []


@pytest.mark.unit
def test_calculate_agreement_returns_unit_alpha_for_perfect_multi_video_consensus() -> None:
    consensus_annotations = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "Contra"},
            {"video_id": "102", "labeler": "alice", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )

    summary = calculate_agreement(consensus_annotations)

    assert summary["alfa"] == 1.0
    assert summary["videos_com_multiplas_anotacoes"] == 2
    assert summary["anotacoes_consideradas"] == 4
    assert summary["videos_com_discordancia"] == []


@pytest.mark.unit
def test_calculate_agreement_penalizes_polar_disagreement_more_heavily_than_neutral_shift() -> None:
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

    neutral_summary = calculate_agreement(neutral_shift)
    polar_summary = calculate_agreement(polar_divergence)

    assert neutral_summary["videos_com_discordancia"][0]["discordancia_ordinal"] == 1.0
    assert polar_summary["videos_com_discordancia"][0]["discordancia_ordinal"] == 4.0
    assert polar_summary["alfa"] < neutral_summary["alfa"]

