"""Deterministic assignment version hashing and queue allocation engine."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tokstance.backend.domain.models import ASSIGNMENT_COLUMNS
from tokstance.config import resolve_data_paths


def assignment_version(config: dict[str, Any], videos: pd.DataFrame) -> str:
    """Compute a deterministic 12-hex SHA-256 version identifier for a dataset and round config."""
    video_signature = videos[["id", "url", "target"]].to_csv(
        index=False,
        lineterminator="\n",
    )
    config_signature = json.dumps(
        {
            "labelers": list(config.get("labelers", [])),
            "overlap_percent": float(config.get("overlap_percent", 0.0)),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(
        f"{video_signature}\n{config_signature}".encode("utf-8")
    ).hexdigest()
    return f"v{digest[:12]}"


def assignment_identifier(version: str, labeler: str, video_id: str) -> str:
    """Build the canonical unique identifier for a single labeler-video assignment."""
    return f"{version}:{labeler}:{video_id}"


def persist_frame_if_changed(
    frame: pd.DataFrame,
    file_path: Path,
    columns: list[str] | tuple[str, ...],
) -> None:
    """Write a DataFrame to CSV only when its serialized content differs from disk."""
    target_path = Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    content = frame.reindex(columns=list(columns)).to_csv(index=False)
    if target_path.exists() and target_path.read_text(encoding="utf-8") == content:
        return
    target_path.write_text(content, encoding="utf-8")


def make_assignments(
    config: dict[str, Any],
    videos: pd.DataFrame,
    persist: bool = True,
    assignments_file: Path | None = None,
) -> pd.DataFrame:
    """Generate target-balanced and contiguous-target annotation queues for all labelers."""
    labelers = list(config.get("labelers", []))
    overlap_percent = max(0.0, min(100.0, float(config.get("overlap_percent", 0.0))))
    version = assignment_version(config, videos)
    columns = list(ASSIGNMENT_COLUMNS)

    if not labelers or len(videos) == 0:
        return pd.DataFrame(columns=columns)

    #interleave videos across normalized targets before slicing overlap
    target_buckets: dict[str, list[int]] = {}
    target_order: list[str] = []
    for video_index, raw_target in enumerate(videos["target"].astype(str).tolist()):
        target_key = raw_target.strip()
        if target_key not in target_buckets:
            target_buckets[target_key] = []
            target_order.append(target_key)
        target_buckets[target_key].append(video_index)

    balanced_video_order: list[int] = []
    while any(target_buckets[target_key] for target_key in target_order):
        for target_key in target_order:
            if target_buckets[target_key]:
                balanced_video_order.append(target_buckets[target_key].pop(0))

    overlap_count = int((overlap_percent / 100.0) * len(videos))
    overlap_indices = balanced_video_order[:overlap_count]
    individual_indices = balanced_video_order[overlap_count:]

    labeler_target_counts = {
        labeler: {target_key: 0 for target_key in target_order}
        for labeler in labelers
    }
    labeler_totals = {labeler: 0 for labeler in labelers}
    individual_assignments: dict[int, str] = {}

    for video_index in individual_indices:
        target_key = str(videos.iloc[video_index]["target"]).strip()
        selected_labeler = min(
            labelers,
            key=lambda candidate: (
                labeler_target_counts[candidate][target_key],
                labeler_totals[candidate],
                labelers.index(candidate),
            ),
        )
        individual_assignments[video_index] = selected_labeler
        labeler_target_counts[selected_labeler][target_key] += 1
        labeler_totals[selected_labeler] += 1

    raw_pairs: list[tuple[str, int]] = []
    for video_index in overlap_indices:
        for labeler in labelers:
            raw_pairs.append((labeler, video_index))
    raw_pairs.extend(
        (labeler, video_index)
        for video_index, labeler in individual_assignments.items()
    )

    #group each labeler queue into contiguous target blocks
    target_rank = {target_key: rank for rank, target_key in enumerate(target_order)}
    raw_pairs.sort(
        key=lambda item: (
            labelers.index(item[0]),
            target_rank[str(videos.iloc[item[1]]["target"]).strip()],
            item[1],
        )
    )

    rows = [
        {
            "assignment_version": version,
            "assignment_id": assignment_identifier(
                version, labeler, str(videos.iloc[video_index]["id"])
            ),
            "labeler": labeler,
            "video_id": str(videos.iloc[video_index]["id"]),
            "url": videos.iloc[video_index]["url"],
            "target": videos.iloc[video_index]["target"],
            "video_description": videos.iloc[video_index].get("video_description", ""),
            "voice_to_text": videos.iloc[video_index].get("voice_to_text", ""),
            "video_duration": videos.iloc[video_index].get("video_duration", ""),
        }
        for labeler, video_index in raw_pairs
    ]
    result = pd.DataFrame(rows, columns=columns)
    result = result.drop_duplicates(subset=["labeler", "video_id"], keep="last").reset_index(
        drop=True
    )
    if persist:
        target_file = (
            Path(assignments_file)
            if assignments_file is not None
            else resolve_data_paths().assignments_file
        )
        persist_frame_if_changed(result, target_file, columns)
    return result
