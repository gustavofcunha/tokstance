"""Unit tests for reserve video replacement and overlap rebalancing rules."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import make_assignments
from tokstance.backend.domain.models import ERROR_COLUMNS, load_videos
from tokstance.backend.domain.replacements import (
    apply_reserve_replacements,
    read_error_assignments,
)


def _write_error_rows(errors_file, rows: list[dict[str, str]]) -> None:
    pd.DataFrame(rows, columns=list(ERROR_COLUMNS)).to_csv(errors_file, index=False)


@pytest.mark.unit
def test_apply_reserve_replacements_replaces_individual_video_with_compatible_target_reserve(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 0.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    failing_row = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    persisted_errors = read_error_assignments(study_paths.errors_file)

    assert persisted_errors.loc[0, "replacement_video_id"] == "7900000000000000001"
    assert persisted_errors.loc[0, "replacement_status"] == "SUBSTITUIDO_OVERLAP"
    assert "7900000000000000001" in set(
        updated[updated["labeler"] == "alice"]["video_id"]
    )


@pytest.mark.unit
def test_apply_reserve_replacements_does_not_reuse_consumed_reserve_across_distinct_failures(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 0.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    first_clima = assignments[assignments["video_id"] == "7100000000000000001"].iloc[0]
    second_clima = assignments[assignments["video_id"] == "7100000000000000002"].iloc[0]
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(first_clima["video_id"]),
                "url": str(first_clima["url"]),
                "labeler": str(first_clima["labeler"]),
                "assignment_id": str(first_clima["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "video_id": str(second_clima["video_id"]),
                "url": str(second_clima["url"]),
                "labeler": str(second_clima["labeler"]),
                "assignment_id": str(second_clima["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            },
        ],
    )

    apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    persisted_errors = read_error_assignments(study_paths.errors_file)

    assert persisted_errors.loc[0, "replacement_video_id"] == "7900000000000000001"
    assert persisted_errors.loc[1, "replacement_video_id"] == ""
    assert persisted_errors.loc[1, "replacement_status"] == "SEM_RESERVA_COMPATIVEL"


@pytest.mark.unit
def test_apply_reserve_replacements_records_sem_reserva_compativel_when_target_not_in_reserves(
    study_paths,
) -> None:
    pd.DataFrame(
        [
            {
                "id": "7900000000000000099",
                "url": "https://www.tiktok.com/@reserve/video/7900000000000000099",
                "target": "Esportes",
            }
        ]
    ).to_csv(study_paths.reserve_videos_file, index=False)
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice"], "overlap_percent": 0.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    failing_row = assignments.iloc[0]
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    persisted_errors = read_error_assignments(study_paths.errors_file)

    assert persisted_errors.loc[0, "replacement_status"] == "SEM_RESERVA_COMPATIVEL"


@pytest.mark.unit
def test_apply_reserve_replacements_records_sem_reserva_disponivel_when_all_reserves_are_exhausted(
    study_paths,
) -> None:
    pd.DataFrame(
        [
            {
                "id": "7100000000000000001",
                "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
                "target": "Clima",
            }
        ]
    ).to_csv(study_paths.reserve_videos_file, index=False)
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice"], "overlap_percent": 0.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    failing_row = assignments.iloc[0]
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(failing_row["video_id"]),
                "url": str(failing_row["url"]),
                "labeler": "alice",
                "assignment_id": str(failing_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    persisted_errors = read_error_assignments(study_paths.errors_file)

    assert persisted_errors.loc[0, "replacement_status"] == "SEM_RESERVA_DISPONIVEL"


@pytest.mark.unit
def test_apply_reserve_replacements_shares_single_reserve_across_unannotated_overlap_group(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 100.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    alice_row = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(alice_row["video_id"]),
                "url": str(alice_row["url"]),
                "labeler": "alice",
                "assignment_id": str(alice_row["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    alice_videos = set(updated[updated["labeler"] == "alice"]["video_id"])
    bob_videos = set(updated[updated["labeler"] == "bob"]["video_id"])

    assert "7900000000000000001" in alice_videos
    assert "7900000000000000001" in bob_videos
    assert "7100000000000000001" not in alice_videos
    assert "7100000000000000001" not in bob_videos

