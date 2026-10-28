from __future__ import annotations

from pathlib import Path

import pytest

from readvideo import media

from .conftest import requires_ffmpeg


@requires_ffmpeg
def test_probe_reports_duration(sine_wav: Path) -> None:
    result = media.probe(str(sine_wav))
    assert result.duration == pytest.approx(3.0, abs=0.1)
    assert result.size and result.size > 1000
    assert "duration=" in result.raw


@requires_ffmpeg
def test_probe_insecure_tls_is_opt_in(sine_wav: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--insecure-tls must only add ffmpeg flags when asked, and local files must still work."""
    captured: list[list[str]] = []
    real_run = media.subprocess.run

    def spy(args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(list(args))
        return real_run(args, **kwargs)

    monkeypatch.setattr(media.subprocess, "run", spy)
    media.probe(str(sine_wav))
    assert "-tls_verify" not in captured[-1]

    captured.clear()
    media.probe(str(sine_wav), insecure_tls=True)
    assert "-tls_verify" in captured[-1]


@requires_ffmpeg
def test_frames_writes_requested_count(testsrc_mp4: Path, tmp_path: Path) -> None:
    written = media.frames(str(testsrc_mp4), times=[0, 1], out_dir=tmp_path / "frames", width=160)
    assert len(written) == 2
    for path in written:
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
    assert written[0].name == "f-000.png"


@requires_ffmpeg
def test_frames_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(media.MediaError):
        media.frames(str(tmp_path / "nope.mp4"), times=[1], out_dir=tmp_path)


def test_is_url() -> None:
    assert media.is_url("https://example.com/a.mp4")
    assert not media.is_url("C:/videos/a.mp4")


def test_tool_error_mentions_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media.shutil, "which", lambda _: None)
    with pytest.raises(media.MediaError, match="ffmpeg"):
        media._tool("ffmpeg")


def test_tool_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RV_FFMPEG", "/custom/ffmpeg")
    assert media._tool("ffmpeg") == "/custom/ffmpeg"


def test_tls_args_default_off() -> None:
    assert media._tls_args(False) == []
    assert media._tls_args(True) == ["-tls_verify", "0"]
