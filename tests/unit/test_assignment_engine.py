"""Unit tests for the target-balanced and overlap-aware assignment engine."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import (
    assignment_identifier,
    assignment_version,
    bind_or_allocate_labeler_slot,
    make_assignments,
)
from tokstance.backend.domain.models import ASSIGNMENT_COLUMNS, load_videos


@pytest.mark.unit
def test_make_assignments_empty_labelers_returns_empty_dataframe(study_paths) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": [], "overlap_percent": 50.0}

    assigned = make_assignments(config, videos, persist=False)

    assert assigned.empty
    assert tuple(assigned.columns) == ASSIGNMENT_COLUMNS


@pytest.mark.unit
def test_make_assignments_zero_overlap_partitions_all_videos_without_duplication(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 0.0}

    assigned = make_assignments(config, videos, persist=False)
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
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 50.0}

    assigned = make_assignments(config, videos, persist=False)
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
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 100.0}

    assigned = make_assignments(config, videos, persist=False)
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
    config = {"labelers": ["alice"], "overlap_percent": 100.0}

    assigned = make_assignments(config, videos, persist=False)
    normalized_targets = assigned["target"].astype(str).str.strip().tolist()

    assert normalized_targets == ["Clima", "Clima", "Economia", "Economia"]


@pytest.mark.unit
def test_make_assignments_balances_per_target_allocation_across_labelers(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 0.0}

    assigned = make_assignments(config, videos, persist=False)
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
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 50.0}

    first_version = assignment_version(config, videos)
    second_version = assignment_version(config, videos)

    assert first_version == second_version
    assert first_version.startswith("v")
    assert len(first_version) == 13


@pytest.mark.unit
def test_assignment_version_changes_when_overlap_or_labeler_list_changes(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    base_config = {"labelers": ["alice", "bob"], "overlap_percent": 50.0}
    updated_overlap_config = {"labelers": ["alice", "bob"], "overlap_percent": 25.0}
    updated_labelers_config = {"labelers": ["alice", "carol"], "overlap_percent": 50.0}

    base_version = assignment_version(base_config, videos)
    overlap_version = assignment_version(updated_overlap_config, videos)
    labelers_version = assignment_version(updated_labelers_config, videos)

    assert base_version != overlap_version
    assert base_version != labelers_version


@pytest.mark.unit
def test_assignment_identifier_formats_version_labeler_and_video_id() -> None:
    identifier = assignment_identifier("v123456789abc", "alice", "7100000000000000001")

    assert identifier == "v123456789abc:alice:7100000000000000001"


@pytest.mark.unit
def test_bind_or_allocate_labeler_slot_replaces_unclaimed_placeholder_slot(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "slot_2"], "overlap_percent": 50.0}
    initial_assignments = make_assignments(config, videos, persist=False)

    updated_config, updated_assignments, bound_slot = bind_or_allocate_labeler_slot(
        "bob",
        config,
        initial_assignments,
        videos,
        claimed_users={"alice"},
    )

    assert bound_slot == "slot_2"
    assert updated_config["labelers"] == ["alice", "bob"]
    assert "slot_2" not in set(updated_assignments["labeler"])
    assert len(updated_assignments[updated_assignments["labeler"] == "bob"]) == 3


@pytest.mark.unit
def test_bind_or_allocate_labeler_slot_allocates_dynamic_queue_when_slots_are_full(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {
        "labelers": ["alice", "bob"],
        "overlap_percent": 50.0,
        "videos_per_labeler": 3,
    }
    initial_assignments = make_assignments(config, videos, persist=False)

    updated_config, updated_assignments, bound_slot = bind_or_allocate_labeler_slot(
        "professor_eval",
        config,
        initial_assignments,
        videos,
        claimed_users={"alice", "bob"},
    )

    assert bound_slot == "professor_eval"
    assert "professor_eval" in updated_config["labelers"]
    assert len(updated_assignments[updated_assignments["labeler"] == "professor_eval"]) == 3
    assert len(updated_assignments[updated_assignments["labeler"] == "alice"]) == 3


