from __future__ import annotations

import pytest

from readvideo.asr import fmt_timestamp, to_srt


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00:00,000"),
        (0.5, "00:00:00,500"),
        (61.25, "00:01:01,250"),
        (3661.001, "01:01:01,001"),
        (59.999, "00:00:59,999"),
        (59.9996, "00:01:00,000"),  # rounding must carry into seconds, not print 1000 ms
    ],
)
def test_fmt_timestamp(seconds: float, expected: str) -> None:
    assert fmt_timestamp(seconds) == expected


def test_fmt_timestamp_rejects_negative() -> None:
    with pytest.raises(ValueError):
        fmt_timestamp(-1)


def test_to_srt_shape() -> None:
    srt = to_srt([(0.0, 1.5, "第一行"), (1.5, 3.0, "第二行")])
    lines = srt.splitlines()
    assert lines[0] == "1"
    assert lines[1] == "00:00:00,000 --> 00:00:01,500"
    assert lines[2] == "第一行"
    assert "2" in lines


def test_transcript_text_and_chars() -> None:
    from readvideo.asr import Transcript

    transcript = Transcript(language="zh", language_probability=0.99, segments=[(0, 1, "你好"), (1, 2, "世界")])
    assert transcript.text == "你好\n世界"
    assert transcript.chars == 4
