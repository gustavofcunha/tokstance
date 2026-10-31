"""Reserve video replacement and overlap rebalancing state machine."""

import csv
from pathlib import Path

import pandas as pd

from tokstance.backend.domain.assignments import (
    assignment_identifier,
    persist_frame_if_changed,
)
from tokstance.backend.domain.models import (
    ERROR_COLUMNS,
    RESULT_COLUMNS,
    load_reserve_videos,
)
from tokstance.config import resolve_data_paths


def read_results(results_file: Path | None = None) -> pd.DataFrame:
    """Load and normalize completed stance annotations from resultados_anotacao.csv."""
    columns = list(RESULT_COLUMNS)
    target_path = (
        Path(results_file)
        if results_file is not None
        else resolve_data_paths().results_file
    )
    if not target_path.exists() or target_path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_csv(target_path, dtype=str)
        if df.empty:
            return pd.DataFrame(columns=columns)
        if set(columns).issubset(set(df.columns)):
            df = df[columns].fillna("")
            missing_ids = df["assignment_id"].astype(str).str.strip().eq("")
            df.loc[missing_ids, "assignment_id"] = df.loc[missing_ids].apply(
                lambda row: f"legacy:{row['labeler']}:{row['video_id']}",
                axis=1,
            )
            return df.drop_duplicates(subset=["assignment_id"], keep="last")
        if set(columns[:-2]).issubset(set(df.columns)):
            df["video_duration"] = ""
            df["assignment_id"] = df.apply(
                lambda row: f"legacy:{row['labeler']}:{row['video_id']}",
                axis=1,
            )
            return df[columns].fillna("").drop_duplicates(
                subset=["assignment_id"], keep="last"
            )
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        pass

    try:
        df = pd.read_csv(target_path, header=None, dtype=str)
        if df.empty:
            return pd.DataFrame(columns=columns)
        if df.shape[1] >= len(columns) - 2:
            fixed = df.iloc[:, : len(columns) - 2].copy()
            fixed["video_duration"] = ""
            fixed["assignment_id"] = fixed.apply(
                lambda row: f"legacy:{row['labeler']}:{row['video_id']}",
                axis=1,
            )
            fixed.columns = columns
            return fixed.fillna("").drop_duplicates(
                subset=["assignment_id"], keep="last"
            )
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        pass

    return pd.DataFrame(columns=columns)


def read_error_assignments(errors_file: Path | None = None) -> pd.DataFrame:
    """Load and normalize reported video error rows from erros_videos.csv."""
    columns = list(ERROR_COLUMNS)
    target_path = (
        Path(errors_file)
        if errors_file is not None
        else resolve_data_paths().errors_file
    )
    if not target_path.exists() or target_path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)

    with target_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return pd.DataFrame(columns=columns)

    if rows[0][:4] == columns[:4]:
        columns_in_file = rows.pop(0)
    else:
        columns_in_file = columns[:5]

    normalized = []
    for row in rows:
        if len(row) < 4:
            continue
        timestamp, video_id, url, labeler = row[:4]
        assignment_id = (
            row[4].strip()
            if len(row) >= 5 and row[4].strip()
            else f"legacy:{labeler}:{video_id}"
        )
        values = dict(zip(columns_in_file, row))
        values["assignment_id"] = assignment_id
        normalized.append({column: values.get(column, "") for column in columns})
    return pd.DataFrame(normalized, columns=columns)


def compute_available_reserves(
    reserve_videos: pd.DataFrame,
    assignments: pd.DataFrame,
    errors: pd.DataFrame,
) -> pd.DataFrame:
    """Filter reserve videos that have not yet been assigned or consumed by errors."""
    unique_reserves = reserve_videos.drop_duplicates(subset=["id"], keep="first")
    reserve_ids = set(unique_reserves["id"].astype(str))
    used_ids = set(
        assignments[assignments["video_id"].astype(str).isin(reserve_ids)][
            "video_id"
        ].astype(str)
    )
    used_ids.update(
        errors[errors["video_id"].astype(str).isin(reserve_ids)]["video_id"].astype(str)
    )
    return unique_reserves[~unique_reserves["id"].astype(str).isin(used_ids)]


def apply_reserve_replacements(
    assignments: pd.DataFrame,
    data_dir: Path | None = None,
) -> pd.DataFrame:
    """Replace reported broken videos with compatible reserve videos."""
    paths = resolve_data_paths(data_dir)
    if assignments.empty or not paths.errors_file.exists():
        return assignments

    errors = read_error_assignments(paths.errors_file)
    reserve_videos = load_reserve_videos(paths.reserve_videos_file).drop_duplicates(
        subset=["id"], keep="first"
    )
    if errors.empty:
        return assignments
    if reserve_videos.empty:
        pending_errors = errors["replacement_assignment_id"].astype(str).str.strip().eq("")
        errors.loc[pending_errors, "replacement_status"] = "SEM_RESERVA_DISPONIVEL"
        persist_frame_if_changed(errors, paths.errors_file, list(errors.columns))
        return assignments

    available_reserves = compute_available_reserves(reserve_videos, assignments, errors)
    results = read_results(paths.results_file)
    completed_assignment_ids = set(
        results.get("assignment_id", pd.Series(dtype=str)).astype(str).str.strip()
    )
    assignments_changed = False
    errors_changed = False

    for error_index, error in errors.iterrows():
        if str(error.get("replacement_assignment_id", "")).strip():
            continue
        assignment_id = str(error.get("assignment_id", "")).strip()
        original_video_id = str(error.get("video_id", "")).strip()
        prior_replacement = errors[
            errors["video_id"].astype(str).eq(original_video_id)
            & errors["replacement_assignment_id"].astype(str).ne("")
        ]
        existing_reserve_id = ""
        prior_status = ""
        if not prior_replacement.empty:
            original_video_id = str(prior_replacement.iloc[0]["video_id"]).strip()
            existing_reserve_id = str(
                prior_replacement.iloc[0]["replacement_video_id"]
            ).strip()
            prior_status = str(prior_replacement.iloc[0]["replacement_status"]).strip()

        matching_rows = assignments.index[
            assignments["assignment_id"].astype(str).eq(assignment_id)
        ]
        if matching_rows.empty:
            matching_rows = assignments.index[
                assignments["labeler"].astype(str).eq(str(error.get("labeler", "")))
                & assignments["video_id"].astype(str).eq(str(error.get("video_id", "")))
            ]
        if matching_rows.empty and existing_reserve_id:
            matching_rows = assignments.index[
                assignments["labeler"].astype(str).eq(str(error.get("labeler", "")))
                & assignments["video_id"].astype(str).eq(existing_reserve_id)
            ]
        if matching_rows.empty:
            continue

        source_index = matching_rows[0]
        if prior_status == "SUBSTITUIDO_OVERLAP_REBALANCEADO":
            errors.at[error_index, "replacement_video_id"] = existing_reserve_id
            errors.at[error_index, "replacement_url"] = str(
                assignments.at[source_index, "url"]
            )
            errors.at[error_index, "replacement_assignment_id"] = str(
                assignments.at[source_index, "assignment_id"]
            )
            errors.at[error_index, "replacement_status"] = prior_status
            errors_changed = True
            continue

        #resolve all assignment rows belonging to the same overlap group
        group_rows = assignments.index[
            assignments["video_id"].astype(str).eq(original_video_id)
        ]
        replacement_rows = (
            errors[
                errors["video_id"].astype(str).eq(original_video_id)
                & errors["replacement_assignment_id"].astype(str).ne("")
            ]["replacement_assignment_id"]
            .astype(str)
            .tolist()
        )
        if replacement_rows:
            group_rows = group_rows.union(
                assignments.index[
                    assignments["assignment_id"].astype(str).isin(replacement_rows)
                ]
            )
        if existing_reserve_id:
            group_rows = group_rows.union(
                assignments.index[
                    assignments["video_id"].astype(str).eq(existing_reserve_id)
                ]
            )
        group_rows = group_rows.sort_values()
        group_has_completed = any(
            str(assignments.at[index, "assignment_id"]).strip()
            in completed_assignment_ids
            for index in group_rows
        )
        source_target = str(assignments.at[source_index, "target"]).strip()
        if group_rows.empty:
            group_rows = matching_rows

        compatible_reserves = reserve_videos[
            reserve_videos["target"].astype(str).str.strip().eq(source_target)
        ]
        if existing_reserve_id:
            compatible_reserves = compatible_reserves[
                compatible_reserves["id"].astype(str).eq(existing_reserve_id)
            ]
        else:
            compatible_reserves = compatible_reserves[
                compatible_reserves["id"]
                .astype(str)
                .isin(available_reserves["id"].astype(str))
            ]

        if compatible_reserves.empty:
            if group_has_completed:
                errors.at[error_index, "replacement_status"] = (
                    "CRITICO_OVERLAP_INCONSISTENTE"
                )
            else:
                errors.at[error_index, "replacement_status"] = (
                    "SEM_RESERVA_DISPONIVEL"
                    if available_reserves.empty
                    else "SEM_RESERVA_COMPATIVEL"
                )
            errors_changed = True
            continue

        reserve = compatible_reserves.iloc[0]
        reserve_id = str(reserve["id"])
        rows_to_replace = matching_rows if group_has_completed else group_rows
        for replacement_index in rows_to_replace:
            labeler = str(assignments.at[replacement_index, "labeler"])
            version = str(assignments.at[replacement_index, "assignment_version"])
            replacement_assignment_id = assignment_identifier(
                version, labeler, reserve_id
            )
            if (
                str(assignments.at[replacement_index, "assignment_id"]).strip()
                in completed_assignment_ids
            ):
                continue
            assignments.at[replacement_index, "video_id"] = reserve_id
            for column in (
                "url",
                "target",
                "video_description",
                "voice_to_text",
                "video_duration",
            ):
                assignments.at[replacement_index, column] = reserve.get(column, "")
            assignments.at[replacement_index, "assignment_id"] = (
                replacement_assignment_id
            )
            assignments_changed = True

        labeler = str(assignments.at[source_index, "labeler"])
        version = str(assignments.at[source_index, "assignment_version"])
        replacement_assignment_id = assignment_identifier(version, labeler, reserve_id)
        errors.at[error_index, "replacement_video_id"] = reserve_id
        errors.at[error_index, "replacement_url"] = str(reserve["url"])
        errors.at[error_index, "replacement_assignment_id"] = replacement_assignment_id
        errors.at[error_index, "replacement_status"] = (
            "CRITICO_OVERLAP_INCONSISTENTE"
            if group_has_completed
            else "SUBSTITUIDO_OVERLAP"
        )
        if not group_has_completed and not existing_reserve_id:
            available_reserves = available_reserves[
                available_reserves["id"].astype(str).ne(reserve_id)
            ]
        errors_changed = True

    if assignments_changed:
        persist_frame_if_changed(
            assignments, paths.assignments_file, list(assignments.columns)
        )
    if errors_changed:
        persist_frame_if_changed(errors, paths.errors_file, list(errors.columns))
    return assignments

