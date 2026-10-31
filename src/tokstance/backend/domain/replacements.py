"""Reserve video replacement and overlap rebalancing state machine."""

import csv
from pathlib import Path

import pandas as pd

from tokstance.backend.domain.assignments import (
    assignment_identifier,
    make_assignments,
    persist_frame_if_changed,
)
from tokstance.backend.domain.models import (
    ERROR_COLUMNS,
    RESULT_COLUMNS,
    load_reserve_videos,
    load_videos,
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

        #promote an already annotated individual video when overlap group has partial progress
        if group_has_completed and not existing_reserve_id:
            video_counts = assignments.groupby(assignments["video_id"].astype(str))[
                "assignment_id"
            ].transform("size")
            completed_video_ids = assignments.loc[
                assignments["assignment_id"].astype(str).isin(completed_assignment_ids),
                "video_id",
            ].astype(str)
            candidate_rows = assignments.index[
                video_counts.eq(1)
                & assignments["video_id"].astype(str).ne(original_video_id)
                & assignments["video_id"].astype(str).isin(completed_video_ids)
                & assignments["target"].astype(str).str.strip().eq(source_target)
                & assignments["labeler"].astype(str).ne(str(error.get("labeler", "")))
            ]
            if not candidate_rows.empty:
                candidate_index = candidate_rows[0]
                candidate_video_id = str(assignments.at[candidate_index, "video_id"])
                candidate = assignments.loc[candidate_index].copy()
                source_labeler = str(assignments.at[source_index, "labeler"])
                source_version = str(
                    assignments.at[source_index, "assignment_version"]
                )
                source_replacement_id = assignment_identifier(
                    source_version, source_labeler, candidate_video_id
                )
                rows_to_promote = [
                    index
                    for index in group_rows
                    if str(assignments.at[index, "assignment_id"]).strip()
                    not in completed_assignment_ids
                ]
                if source_index not in rows_to_promote:
                    rows_to_promote.append(source_index)
                for promotion_index in rows_to_promote:
                    promotion_labeler = str(
                        assignments.at[promotion_index, "labeler"]
                    )
                    promotion_version = str(
                        assignments.at[promotion_index, "assignment_version"]
                    )
                    assignments.at[promotion_index, "video_id"] = candidate_video_id
                    for column in (
                        "url",
                        "target",
                        "video_description",
                        "voice_to_text",
                        "video_duration",
                    ):
                        assignments.at[promotion_index, column] = candidate[column]
                    assignments.at[promotion_index, "assignment_id"] = (
                        assignment_identifier(
                            promotion_version, promotion_labeler, candidate_video_id
                        )
                    )
                errors.at[error_index, "replacement_video_id"] = candidate_video_id
                errors.at[error_index, "replacement_url"] = str(candidate["url"])
                errors.at[error_index, "replacement_assignment_id"] = (
                    source_replacement_id
                )
                errors.at[error_index, "replacement_status"] = (
                    "SUBSTITUIDO_OVERLAP_REBALANCEADO"
                )
                assignments_changed = True
                errors_changed = True
                continue

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


def load_assignments(
    config: dict,
    videos: pd.DataFrame,
    data_dir: Path | None = None,
) -> pd.DataFrame:
    """Load persisted assignments for the active version and apply reserve replacements."""
    paths = resolve_data_paths(data_dir)
    base_assignments = make_assignments(
        config, videos, persist=False, assignments_file=paths.assignments_file
    )
    assignments = base_assignments
    if paths.assignments_file.exists() and not base_assignments.empty:
        try:
            persisted = pd.read_csv(paths.assignments_file, dtype=str).fillna("")
            has_schema = set(base_assignments.columns).issubset(persisted.columns)
            same_version = set(persisted.get("assignment_version", [])) == {
                base_assignments.iloc[0]["assignment_version"]
            }
            if has_schema and same_version and len(persisted) >= len(base_assignments):
                assignments = persisted[base_assignments.columns].copy()
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            pass

    if not assignments.empty and not assignments.equals(base_assignments):
        persist_frame_if_changed(
            assignments, paths.assignments_file, list(base_assignments.columns)
        )
    elif not paths.assignments_file.exists():
        persist_frame_if_changed(
            base_assignments, paths.assignments_file, list(base_assignments.columns)
        )
    return apply_reserve_replacements(assignments, data_dir=paths.base_dir)


def ensure_errors_schema(data_dir: Path | None = None) -> None:
    """Normalize erros_videos.csv on disk to the canonical schema."""
    paths = resolve_data_paths(data_dir)
    if not paths.errors_file.exists() or paths.errors_file.stat().st_size == 0:
        return
    errors = read_error_assignments(paths.errors_file)
    persist_frame_if_changed(errors, paths.errors_file, list(errors.columns))


def ensure_results_schema(data_dir: Path | None = None) -> None:
    """Normalize resultados_anotacao.csv on disk and backfill missing durations or IDs."""
    paths = resolve_data_paths(data_dir)
    columns = list(RESULT_COLUMNS)
    if not paths.results_file.exists() or paths.results_file.stat().st_size == 0:
        return
    try:
        df = pd.read_csv(paths.results_file, dtype=str).fillna("")
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return
    videos = load_videos(paths.videos_file).set_index("id")
    if "video_duration" not in df.columns:
        df["video_duration"] = ""
    if "assignment_id" not in df.columns:
        df["assignment_id"] = df.apply(
            lambda row: f"legacy:{row['labeler']}:{row['video_id']}",
            axis=1,
        )
    for index, row in df.iterrows():
        if not str(row.get("video_duration", "")).strip():
            video_key = str(row.get("video_id", ""))
            if video_key in videos.index:
                df.at[index, "video_duration"] = str(
                    videos.loc[video_key, "video_duration"]
                )
    df = df.reindex(columns=[column for column in columns if column in df.columns])
    df.to_csv(paths.results_file, index=False)


