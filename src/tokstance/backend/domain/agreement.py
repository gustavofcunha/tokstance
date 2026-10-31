"""Weighted stance distance matrix and ordinal Krippendorff alpha calculation."""

from typing import Any

import pandas as pd

from tokstance.config import STANCE_OPTIONS, format_brt_timestamp

LABEL_DISTANCE: dict[frozenset[str], float] = {
    frozenset(("Contra", "Neutro")): 1.0,
    frozenset(("Neutro", "A Favor")): 1.0,
    frozenset(("Contra", "A Favor")): 4.0,
    frozenset(("Vídeo não relacionado ao target", "Contra")): 3.0,
    frozenset(("Vídeo não relacionado ao target", "Neutro")): 3.0,
    frozenset(("Vídeo não relacionado ao target", "A Favor")): 3.0,
}


def label_distance(left: str, right: str) -> float:
    """Return the weighted pairwise distance between two stance labels."""
    if left == right:
        return 0.0
    return LABEL_DISTANCE.get(frozenset((str(left), str(right))), 0.0)


def calculate_agreement(results: pd.DataFrame) -> dict[str, Any]:
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

    labels_by_video = (
        results[results["stance"].isin(STANCE_OPTIONS)]
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

