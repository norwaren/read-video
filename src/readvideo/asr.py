"""Speech-to-text built on faster-whisper.

Audio is decoded to raw float32 PCM by ffmpeg before it reaches the model. That
avoids `av` entirely, so the `TypeError: open() got an unexpected keyword
argument 'metadata_errors'` failure that hits newer faster-whisper builds with
older `av` wheels cannot happen here.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .media import MediaError, _tool

MODEL_ENV = "READ_VIDEO_MODEL"
SAMPLE_RATE = 16000


@dataclass(slots=True)
class Transcript:
    language: str
    language_probability: float
    segments: list[tuple[float, float, str]]

    @property
    def text(self) -> str:
        return "\n".join(text for _, _, text in self.segments)

    @property
    def chars(self) -> int:
        return sum(len(text) for _, _, text in self.segments)


def fmt_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm.

    Works in whole milliseconds so that rounding carries correctly across
    second/minute boundaries (59.9996s -> 00:01:00,000, not 00:00:60,000).
    """
    if seconds < 0:
        raise ValueError("timestamp must be >= 0")
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def to_srt(segments: list[tuple[float, float, str]]) -> str:
    blocks = []
    for index, (start, end, text) in enumerate(segments, 1):
        blocks.append(f"{index}\n{fmt_timestamp(start)} --> {fmt_timestamp(end)}\n{text}\n")
    return "\n".join(blocks)


def decode_audio(media: str | Path) -> object:
    """Decode any ffmpeg-readable file to a mono 16 kHz float32 numpy array."""
    import numpy as np

    path = Path(media)
    if not path.exists():
        raise MediaError(f"no such file: {path}")

    with tempfile.NamedTemporaryFile(suffix=".f32", delete=False) as handle:
        raw = Path(handle.name)
    try:
        proc = subprocess.run(
            [
                _tool("ffmpeg"), "-y", "-loglevel", "error", "-i", str(path),
                "-f", "f32le", "-acodec", "pcm_f32le",
                "-ar", str(SAMPLE_RATE), "-ac", "1", str(raw),
            ],
            capture_output=True,
            text=True,
            errors="replace",
        )
        if proc.returncode != 0:
            raise MediaError(f"ffmpeg could not decode {path}: {(proc.stderr or '').strip()}")
        return np.fromfile(raw, dtype=np.float32)
    finally:
        raw.unlink(missing_ok=True)


def transcribe(
    media: str | Path,
    *,
    model: str,
    language: str = "zh",
    hotwords: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
    threads: int = 8,
    beam_size: int = 5,
    vad_filter: bool = True,
) -> Transcript:
    """Run faster-whisper over `media` and return the transcript."""
    from faster_whisper import WhisperModel

    if Path(model).exists():
        os.environ.setdefault("HF_HUB_OFFLINE", "1")

    audio = decode_audio(media)
    engine = WhisperModel(model, device=device, compute_type=compute_type, cpu_threads=threads)
    raw_segments, info = engine.transcribe(
        audio,
        language=language,
        vad_filter=vad_filter,
        beam_size=beam_size,
        initial_prompt=hotwords or None,
    )
    segments = [(seg.start, seg.end, seg.text.strip()) for seg in raw_segments]
    return Transcript(
        language=info.language,
        language_probability=info.language_probability,
        segments=segments,
    )


def write_outputs(transcript: Transcript, prefix: str | Path) -> tuple[Path, Path]:
    base = Path(prefix)
    base.parent.mkdir(parents=True, exist_ok=True)
    txt_path = Path(f"{base}.txt")
    srt_path = Path(f"{base}.srt")
    txt_path.write_text(transcript.text, encoding="utf-8")
    srt_path.write_text(to_srt(transcript.segments), encoding="utf-8")
    return txt_path, srt_path
