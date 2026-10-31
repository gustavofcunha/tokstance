"""Weighted stance distance matrix and ordinal Krippendorff alpha calculation."""

from typing import Any

import pandas as pd

from tokstance.config import (
    FAST_ANNOTATION_TOLERANCE_SECONDS,
    format_brt_timestamp,
)

LABEL_DISTANCE: dict[frozenset[str], float] = {
    frozenset(("Contra", "Neutro")): 1.0,
    frozenset(("Neutro", "A Favor")): 1.0,
    frozenset(("Contra", "A Favor")): 4.0,
    frozenset(("Vídeo não relacionado ao target", "Contra")): 3.0,
    frozenset(("Vídeo não relacionado ao target", "Neutro")): 3.0,
    frozenset(("Vídeo não relacionado ao target", "A Favor")): 3.0,
}


def label_distance(left: str, right: str) -> float:
    """Return the weighted pairwise distance between two task labels."""
    if left == right:
        return 0.0
    return LABEL_DISTANCE.get(frozenset((str(left), str(right))), 1.0)


def calculate_agreement(
    results: pd.DataFrame,
    allowed_options: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Compute distance-weighted Krippendorff alpha and per-labeler disagreement penalties."""
    if results.empty or "stance" not in results.columns:
        return {
            "metrica": "Alfa de Krippendorff (ordinal)",
            "alfa": None,
            "videos_com_multiplas_anotacoes": 0,
            "anotacoes_consideradas": 0,
            "videos_com_discordancia": [],
            "labelers_com_maior_discordancia": [],
            "updated_at": format_brt_timestamp(),
        }

    valid_mask = results["stance"].astype(str).str.strip().ne("")
    if allowed_options:
        valid_mask = valid_mask & results["stance"].isin(list(allowed_options))
    labels_by_video = (
        results[valid_mask]
        .groupby("video_id")["stance"]
        .apply(list)
    )
    usable = labels_by_video[labels_by_video.map(len) >= 2]

    if usable.empty:
        return {
            "metrica": "Alfa de Krippendorff (ordinal)",
            "alfa": None,
            "videos_com_multiplas_anotacoes": 0,
            "anotacoes_consideradas": 0,
            "videos_com_discordancia": [],
            "labelers_com_maior_discordancia": [],
            "updated_at": format_brt_timestamp(),
        }

    #statistical correction for pairwise observed and expected disagreement
    observed_disagreement = 0.0
    pair_count = 0
    disagreement_videos: list[dict[str, Any]] = []
    for video_id, labels in usable.items():
        distances = [
            label_distance(labels[left_idx], labels[right_idx])
            for left_idx in range(len(labels))
            for right_idx in range(left_idx + 1, len(labels))
        ]
        observed_disagreement += sum(distances)
        pair_count += len(distances)
        if any(distance > 0 for distance in distances):
            disagreement_videos.append(
                {
                    "video_id": str(video_id),
                    "anotacoes": labels,
                    "discordancia_ordinal": round(sum(distances) / len(distances), 4),
                }
            )

    all_labels = [label for labels in usable for label in labels]
    expected_disagreement = sum(
        label_distance(all_labels[left_idx], all_labels[right_idx])
        for left_idx in range(len(all_labels))
        for right_idx in range(left_idx + 1, len(all_labels))
    )
    expected_pairs = len(all_labels) * (len(all_labels) - 1) / 2
    if pair_count == 0:
        alpha = None
    elif expected_disagreement == 0:
        alpha = 1.0 if observed_disagreement == 0 else None
    else:
        alpha = 1.0 - (observed_disagreement / pair_count) / (
            expected_disagreement / expected_pairs
        )

    disagreement_videos.sort(
        key=lambda item: item["discordancia_ordinal"], reverse=True
    )

    labeler_disagreements: dict[str, float] = {}
    valid_results = results[results["video_id"].isin(usable.index)]
    for _, video_results in valid_results.groupby("video_id"):
        labels = video_results["stance"].tolist()
        for row in video_results.itertuples():
            other_labels = [label for label in labels if label != row.stance]
            if other_labels:
                score = sum(
                    label_distance(row.stance, label) for label in other_labels
                ) / len(other_labels)
                labeler_disagreements[row.labeler] = (
                    labeler_disagreements.get(row.labeler, 0.0) + score
                )

    labelers = [
        {"labeler": labeler, "penalidade": round(score, 2)}
        for labeler, score in labeler_disagreements.items()
    ]
    labelers.sort(key=lambda item: item["penalidade"], reverse=True)
    return {
        "metrica": "Concordância ponderada por distância",
        "alfa": round(alpha, 6) if alpha is not None else None,
        "videos_com_multiplas_anotacoes": int(len(usable)),
        "anotacoes_consideradas": int(len(all_labels)),
        "videos_com_discordancia": disagreement_videos,
        "labelers_com_maior_discordancia": labelers,
        "updated_at": format_brt_timestamp(),
    }


def find_fast_annotations(
    results: pd.DataFrame,
    videos: pd.DataFrame,
    tolerance_seconds: float = FAST_ANNOTATION_TOLERANCE_SECONDS,
) -> list[dict[str, Any]]:
    """Detect annotations completed faster than video duration minus tolerance."""
    if results.empty or videos.empty:
        return []
    durations = videos.set_index(videos["id"].astype(str))["video_duration"].to_dict()
    alerts: list[dict[str, Any]] = []
    for row in results.itertuples():
        raw_duration = getattr(row, "video_duration", "") or durations.get(
            str(row.video_id), ""
        )
        try:
            duration = float(raw_duration)
            analysis_time = float(row.tempo_analise_segundos)
        except (TypeError, ValueError):
            continue
        if analysis_time < duration - float(tolerance_seconds):
            alerts.append(
                {
                    "video_id": str(row.video_id),
                    "labeler": str(row.labeler),
                    "video_duration": round(duration, 2),
                    "tempo_analise_segundos": round(analysis_time, 2),
                    "diferenca_segundos": round(duration - analysis_time, 2),
                }
            )
    return sorted(alerts, key=lambda item: item["diferenca_segundos"], reverse=True)


def assignment_versions(
    assignments: pd.DataFrame,
    results: pd.DataFrame,
    errors: pd.DataFrame,
) -> list[str]:
    """List the active assignment version followed by historical versions in reverse order."""
    versions: list[str] = []
    current_version: str | None = None
    if not assignments.empty and "assignment_version" in assignments.columns:
        versions.extend(
            assignments["assignment_version"].dropna().astype(str).tolist()
        )
        current_version = versions[0] if versions else None
    for frame in (results, errors):
        if not frame.empty and "assignment_id" in frame.columns:
            versions.extend(
                frame["assignment_id"]
                .astype(str)
                .str.split(":", n=1)
                .str[0]
                .tolist()
            )
    available = {
        version for version in versions if version and version != "legacy"
    }
    if current_version:
        available.discard(current_version)
    return ([current_version] if current_version else []) + sorted(
        available, reverse=True
    )


def filter_by_assignment_version(
    frame: pd.DataFrame,
    version: str | None,
) -> pd.DataFrame:
    """Filter results or error rows belonging to a specific assignment version prefix."""
    if frame.empty or not version or "assignment_id" not in frame.columns:
        return frame.copy()
    return frame[
        frame["assignment_id"].astype(str).str.startswith(f"{version}:")
    ].copy()


def assignment_table_for_version(
    assignments: pd.DataFrame,
    results: pd.DataFrame,
    errors: pd.DataFrame,
    version: str | None,
) -> pd.DataFrame:
    """Return active assignment rows or reconstruct historical rows for an older version."""
    if (
        version
        and not assignments.empty
        and version in set(assignments["assignment_version"].astype(str))
    ):
        return assignments[
            assignments["assignment_version"].astype(str).eq(version)
        ].copy()
    return pd.concat(
        [
            filter_by_assignment_version(results, version),
            filter_by_assignment_version(errors, version),
        ],
        ignore_index=True,
    )


