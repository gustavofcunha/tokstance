"""Unit tests for reserve video replacement and overlap rebalancing rules."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import make_assignments
from tokstance.backend.domain.models import ERROR_COLUMNS, RESULT_COLUMNS, load_videos
from tokstance.backend.domain.replacements import (
    apply_reserve_replacements,
    ensure_results_schema,
    load_assignments,
    read_error_assignments,
    read_results,
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


@pytest.mark.unit
def test_apply_reserve_replacements_promotes_completed_individual_video_when_overlap_partially_annotated(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 50.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    alice_overlap = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_overlap = assignments[
        (assignments["labeler"] == "bob")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    alice_individual = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000002")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_overlap["video_id"]),
                "url": str(alice_overlap["url"]),
                "target": str(alice_overlap["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "21.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_overlap["assignment_id"]),
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "labeler": "alice",
                "video_id": str(alice_individual["video_id"]),
                "url": str(alice_individual["url"]),
                "target": str(alice_individual["target"]),
                "stance": "A Favor",
                "tempo_analise_segundos": "28.0",
                "video_duration": "30.0",
                "assignment_id": str(alice_individual["assignment_id"]),
            },
        ],
        columns=list(RESULT_COLUMNS),
    ).to_csv(study_paths.results_file, index=False)
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_overlap["video_id"]),
                "url": str(bob_overlap["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_overlap["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    persisted_errors = read_error_assignments(study_paths.errors_file)

    assert (
        persisted_errors.loc[0, "replacement_status"]
        == "SUBSTITUIDO_OVERLAP_REBALANCEADO"
    )
    assert persisted_errors.loc[0, "replacement_video_id"] == "7100000000000000002"
    assert "7100000000000000002" in set(updated[updated["labeler"] == "bob"]["video_id"])


@pytest.mark.unit
def test_apply_reserve_replacements_propagates_promoted_video_to_all_pending_group_members(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob", "carol"], "overlap_percent": 50.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    alice_overlap = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_overlap = assignments[
        (assignments["labeler"] == "bob")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    alice_individual = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000002")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_overlap["video_id"]),
                "url": str(alice_overlap["url"]),
                "target": str(alice_overlap["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "21.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_overlap["assignment_id"]),
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "labeler": "alice",
                "video_id": str(alice_individual["video_id"]),
                "url": str(alice_individual["url"]),
                "target": str(alice_individual["target"]),
                "stance": "Neutro",
                "tempo_analise_segundos": "25.0",
                "video_duration": "30.0",
                "assignment_id": str(alice_individual["assignment_id"]),
            },
        ],
        columns=list(RESULT_COLUMNS),
    ).to_csv(study_paths.results_file, index=False)
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_overlap["video_id"]),
                "url": str(bob_overlap["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_overlap["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    carol_videos = set(updated[updated["labeler"] == "carol"]["video_id"])

    assert "7100000000000000002" in carol_videos
    assert "7100000000000000001" not in carol_videos


@pytest.mark.unit
def test_apply_reserve_replacements_emits_critico_overlap_inconsistente_when_no_promotion_candidate_exists(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 100.0}
    assignments = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    alice_overlap = assignments[
        (assignments["labeler"] == "alice")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_overlap = assignments[
        (assignments["labeler"] == "bob")
        & (assignments["video_id"] == "7100000000000000001")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_overlap["video_id"]),
                "url": str(alice_overlap["url"]),
                "target": str(alice_overlap["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "22.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_overlap["assignment_id"]),
            }
        ],
        columns=list(RESULT_COLUMNS),
    ).to_csv(study_paths.results_file, index=False)
    _write_error_rows(
        study_paths.errors_file,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_overlap["video_id"]),
                "url": str(bob_overlap["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_overlap["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    updated = apply_reserve_replacements(assignments, data_dir=study_paths.base_dir)
    persisted_errors = read_error_assignments(study_paths.errors_file)

    assert (
        persisted_errors.loc[0, "replacement_status"] == "CRITICO_OVERLAP_INCONSISTENTE"
    )
    assert "7100000000000000001" in set(
        updated[updated["labeler"] == "alice"]["video_id"]
    )
    assert "7900000000000000001" in set(updated[updated["labeler"] == "bob"]["video_id"])


@pytest.mark.unit
def test_load_assignments_reuses_persisted_assignments_when_version_matches(
    study_paths,
) -> None:
    videos = load_videos(study_paths.videos_file)
    config = {"labelers": ["alice", "bob"], "overlap_percent": 50.0}
    initial = make_assignments(
        config, videos, persist=True, assignments_file=study_paths.assignments_file
    )
    failing_row = initial[
        (initial["labeler"] == "alice")
        & (initial["video_id"] == "7100000000000000001")
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

    loaded = load_assignments(config, videos, data_dir=study_paths.base_dir)

    assert "7900000000000000001" in set(loaded["video_id"])


@pytest.mark.unit
def test_ensure_results_schema_backfills_missing_video_duration_and_legacy_assignment_id(
    study_paths,
) -> None:
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": "7100000000000000001",
                "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
                "target": "Clima",
                "stance": "Contra",
                "tempo_analise_segundos": "20.0",
            }
        ]
    ).to_csv(study_paths.results_file, index=False)

    ensure_results_schema(data_dir=study_paths.base_dir)
    migrated = read_results(study_paths.results_file)

    assert migrated.loc[0, "video_duration"] == "25.0"
    assert migrated.loc[0, "assignment_id"] == "legacy:alice:7100000000000000001"


