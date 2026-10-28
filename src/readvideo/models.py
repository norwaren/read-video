"""Model resolution and download.

faster-whisper accepts either a model name ("small") or a local directory. A
local directory is strongly preferred: it is reproducible, works offline, and
avoids the Hugging Face hub lookup that fails behind flaky networks.
"""

from __future__ import annotations

import os
from pathlib import Path

from .asr import MODEL_ENV

# size -> (repo id, approximate download size in MB)
CATALOG: dict[str, tuple[str, int]] = {
    "tiny": ("Systran/faster-whisper-tiny", 75),
    "base": ("Systran/faster-whisper-base", 145),
    "small": ("Systran/faster-whisper-small", 461),
    "medium": ("Systran/faster-whisper-medium", 1530),
    "large-v3": ("Systran/faster-whisper-large-v3", 3090),
}


def resolve(ref: str | None) -> str:
    """Pick the model reference: explicit > $READ_VIDEO_MODEL > 'small'."""
    return ref or os.environ.get(MODEL_ENV) or "small"


def repo_for(size: str) -> str:
    if size in CATALOG:
        return CATALOG[size][0]
    if "/" in size:  # treat as an explicit hub repo id
        return size
    raise ValueError(f"unknown model size: {size}. Known: {', '.join(CATALOG)}")


def download(size: str = "small", dest: str | Path | None = None, workers: int = 8) -> Path:
    """Snapshot a faster-whisper model into `dest` (default: models/<size>)."""
    from huggingface_hub import snapshot_download

    repo = repo_for(size)
    target = Path(dest) if dest else Path("models") / f"faster-whisper-{size}"
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo, local_dir=str(target), max_workers=workers)
    return target
