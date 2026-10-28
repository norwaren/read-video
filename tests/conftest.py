from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


requires_ffmpeg = pytest.mark.skipif(not has_ffmpeg(), reason="ffmpeg/ffprobe not installed")


@pytest.fixture(scope="session")
def sine_wav(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """3 second mono sine wave, 16 kHz."""
    if not has_ffmpeg():
        pytest.skip("ffmpeg not installed")
    path = tmp_path_factory.mktemp("media") / "sine.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=3", str(path)],
        check=True,
    )
    return path


@pytest.fixture(scope="session")
def testsrc_mp4(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """2 second test pattern video with a tone, H.264 + AAC."""
    if not has_ffmpeg():
        pytest.skip("ffmpeg not installed")
    path = tmp_path_factory.mktemp("media") / "testsrc.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )
    return path
