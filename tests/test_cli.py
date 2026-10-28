from __future__ import annotations

import pytest

from readvideo import models
from readvideo.asr import MODEL_ENV
from readvideo.cli import build_parser


def test_version_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0


def test_frames_defaults() -> None:
    args = build_parser().parse_args(["frames", "clip.mp4"])
    assert args.times == [60, 200, 350, 500]
    assert args.width == 1024


def test_times_parsing() -> None:
    args = build_parser().parse_args(["frames", "clip.mp4", "--times", "30, 90,120"])
    assert args.times == [30, 90, 120]


def test_times_rejects_garbage() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["frames", "clip.mp4", "--times", "abc"])


def test_model_resolution_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MODEL_ENV, "D:/m")
    assert models.resolve(None) == "D:/m"
    assert models.resolve("small") == "small"


def test_repo_for_known_and_custom() -> None:
    assert models.repo_for("small") == "Systran/faster-whisper-small"
    assert models.repo_for("org/custom-model") == "org/custom-model"
    with pytest.raises(ValueError):
        models.repo_for("gigantic")


def test_help_is_ascii_only() -> None:
    """Regression: a cp1252 console crashed on non-ASCII help (UnicodeEncodeError)."""
    help_text = build_parser().format_help()
    assert help_text.isascii(), "help output must stay ASCII"
    help_text.encode("cp1252")  # must not raise


def test_subcommand_help_is_ascii_only() -> None:
    for command in ("probe", "frames", "transcribe", "fetch", "model"):
        text = build_parser()._subparsers._group_actions[0].choices[command].format_help()
        assert text.isascii(), f"{command} help must stay ASCII"
        text.encode("cp1252")


def test_prog_name_follows_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/readvideo"])
    assert build_parser().prog == "readvideo"
