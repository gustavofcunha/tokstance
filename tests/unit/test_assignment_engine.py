"""Unit tests for the target-balanced and overlap-aware assignment engine."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import make_assignments
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

