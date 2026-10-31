"""Testes unitarios para o motor de atribuicoes balanceado por target e sobreposicao."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import (
    gerar_atribuicoes,
    identificador_atribuicao,
    versao_atribuicao,
    vincular_ou_alocar_vaga_rotulador,
)
from tokstance.backend.domain.models import COLUNAS_ATRIBUICAO, carregar_videos


@pytest.mark.unit
def test_make_assignments_empty_labelers_returns_empty_dataframe(study_paths) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": [], "percentual_sobreposicao": 50.0}

    assigned = gerar_atribuicoes(config, videos, persistir=False)

    assert assigned.empty
    assert tuple(assigned.columns) == COLUNAS_ATRIBUICAO


@pytest.mark.unit
def test_make_assignments_zero_overlap_partitions_all_videos_without_duplication(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}

    assigned = gerar_atribuicoes(config, videos, persistir=False)
    alice_ids = set(assigned[assigned["labeler"] == "alice"]["video_id"])
    bob_ids = set(assigned[assigned["labeler"] == "bob"]["video_id"])

    assert len(alice_ids) == 2
    assert len(bob_ids) == 2
    assert alice_ids.isdisjoint(bob_ids)
    assert alice_ids.union(bob_ids) == set(videos["id"])


@pytest.mark.unit
def test_make_assignments_fifty_percent_overlap_shares_half_and_splits_remainder(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}

    assigned = gerar_atribuicoes(config, videos, persistir=False)
    alice_ids = set(assigned[assigned["labeler"] == "alice"]["video_id"])
    bob_ids = set(assigned[assigned["labeler"] == "bob"]["video_id"])

    assert len(alice_ids) == 3
    assert len(bob_ids) == 3
    assert len(alice_ids.intersection(bob_ids)) == 2
    assert alice_ids.union(bob_ids) == set(videos["id"])


@pytest.mark.unit
def test_make_assignments_hundred_percent_overlap_assigns_full_corpus_to_every_labeler(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 100.0}

    assigned = gerar_atribuicoes(config, videos, persistir=False)
    alice_ids = list(assigned[assigned["labeler"] == "alice"]["video_id"])
    bob_ids = list(assigned[assigned["labeler"] == "bob"]["video_id"])

    assert len(alice_ids) == 4
    assert alice_ids == bob_ids


@pytest.mark.unit
def test_make_assignments_groups_each_labeler_queue_into_contiguous_target_blocks() -> None:
    videos = pd.DataFrame(
        [
            {"id": "1", "url": "https://tiktok.com/@a/video/1", "target": "Clima"},
            {"id": "2", "url": "https://tiktok.com/@a/video/2", "target": "Economia"},
            {"id": "3", "url": "https://tiktok.com/@a/video/3", "target": " Clima "},
            {"id": "4", "url": "https://tiktok.com/@a/video/4", "target": "Economia"},
        ]
    )
    config = {"rotuladores": ["alice"], "percentual_sobreposicao": 100.0}

    assigned = gerar_atribuicoes(config, videos, persistir=False)
    normalized_targets = assigned["target"].astype(str).str.strip().tolist()

    assert normalized_targets == ["Clima", "Clima", "Economia", "Economia"]


@pytest.mark.unit
def test_make_assignments_balances_per_target_allocation_across_labelers(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}

    assigned = gerar_atribuicoes(config, videos, persistir=False)
    alice_targets = sorted(
        assigned[assigned["labeler"] == "alice"]["target"].astype(str).str.strip().tolist()
    )
    bob_targets = sorted(
        assigned[assigned["labeler"] == "bob"]["target"].astype(str).str.strip().tolist()
    )

    assert alice_targets == ["Clima", "Economia"]
    assert bob_targets == ["Clima", "Economia"]


@pytest.mark.unit
def test_assignment_version_is_deterministic_for_identical_inputs(study_paths) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}

    first_version = versao_atribuicao(config, videos)
    second_version = versao_atribuicao(config, videos)

    assert first_version == second_version
    assert first_version.startswith("v")
    assert len(first_version) == 13


@pytest.mark.unit
def test_assignment_version_changes_when_overlap_or_labeler_list_changes(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    base_config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}
    updated_overlap_config = {
        "rotuladores": ["alice", "bob"],
        "percentual_sobreposicao": 25.0,
    }
    updated_labelers_config = {
        "rotuladores": ["alice", "carol"],
        "percentual_sobreposicao": 50.0,
    }

    base_version = versao_atribuicao(base_config, videos)
    overlap_version = versao_atribuicao(updated_overlap_config, videos)
    labelers_version = versao_atribuicao(updated_labelers_config, videos)

    assert base_version != overlap_version
    assert base_version != labelers_version


@pytest.mark.unit
def test_assignment_identifier_formats_version_labeler_and_video_id() -> None:
    identifier = identificador_atribuicao("v123456789abc", "alice", "7100000000000000001")

    assert identifier == "v123456789abc:alice:7100000000000000001"


@pytest.mark.unit
def test_bind_or_allocate_labeler_slot_replaces_unclaimed_placeholder_slot(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {"rotuladores": ["alice", "vaga_2"], "percentual_sobreposicao": 50.0}
    initial_assignments = gerar_atribuicoes(config, videos, persistir=False)

    updated_config, updated_assignments, bound_slot = vincular_ou_alocar_vaga_rotulador(
        "bob",
        config,
        initial_assignments,
        videos,
        usuarios_reivindicados={"alice"},
    )

    assert bound_slot == "vaga_2"
    assert updated_config["rotuladores"] == ["alice", "bob"]
    assert "vaga_2" not in set(updated_assignments["labeler"])
    assert len(updated_assignments[updated_assignments["labeler"] == "bob"]) == 3


@pytest.mark.unit
def test_bind_or_allocate_labeler_slot_allocates_dynamic_queue_when_slots_are_full(
    study_paths,
) -> None:
    videos = carregar_videos(study_paths.arquivo_videos)
    config = {
        "rotuladores": ["alice", "bob"],
        "percentual_sobreposicao": 50.0,
        "videos_por_rotulador": 3,
    }
    initial_assignments = gerar_atribuicoes(config, videos, persistir=False)

    updated_config, updated_assignments, bound_slot = vincular_ou_alocar_vaga_rotulador(
        "professor_eval",
        config,
        initial_assignments,
        videos,
        usuarios_reivindicados={"alice", "bob"},
    )

    assert bound_slot == "professor_eval"
    assert "professor_eval" in updated_config["rotuladores"]
    assert len(updated_assignments[updated_assignments["labeler"] == "professor_eval"]) == 3
    assert len(updated_assignments[updated_assignments["labeler"] == "alice"]) == 3
