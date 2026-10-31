"""Deterministic assignment version hashing and queue allocation engine."""

import hashlib
import json
from typing import Any

import pandas as pd


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

