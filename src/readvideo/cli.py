"""Command line interface: ``rv fetch|frames|transcribe|probe|model``."""

from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

from . import __version__, asr, media, models

EPILOG = """examples:
  readvideo probe clip.mp4
  readvideo frames "https://cdn.example/v.mp4?sig=..." --times 30,90 --out frames
  readvideo transcribe clip.m4a --hotwords "proper,nouns,here"
  readvideo model --size small --dest models/faster-whisper-small
  readvideo fetch "https://cdn.example/a.m4a?sig=..." --out media/clip.m4a

Help text stays ASCII on purpose: a Windows console on a cp1252 locale raises
UnicodeEncodeError when asked to print non-ASCII help.
"""


def _times(value: str) -> list[int]:
    try:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected comma separated seconds, got {value!r}") from exc


def _configure_stdio() -> None:
    """Make stdout/stderr UTF-8 with replacement instead of crashing on Windows.

    A cp1252 console raises UnicodeEncodeError when we print a path or a title
    that contains CJK characters. Reconfiguring keeps output readable and never
    turns a successful run into a traceback.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")


def _prog() -> str:
    """Name shown in --help: `python -m readvideo` must not print `__main__.py`."""
    name = Path(sys.argv[0]).name
    if name in {"__main__.py", "-c", ""}:
        return "readvideo"
    return Path(name).stem or "readvideo"


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog or _prog(),
        description="Read a video: grab still frames and transcribe speech.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"read-video {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe", help="show duration, size and stream info")
    p.add_argument("src", help="local path or http(s) URL")
    p.add_argument("--referer", default=media.DEFAULT_REFERER)
    p.add_argument(
        "--insecure-tls",
        action="store_true",
        help="skip ffmpeg certificate verification (needed behind TLS-intercepting proxies)",
    )

    p = sub.add_parser("frames", help="write one PNG per timestamp")
    p.add_argument("src", help="local path or http(s) URL")
    p.add_argument("--times", type=_times, default=[60, 200, 350, 500], help="seconds, e.g. 30,90")
    p.add_argument("--out", default="frames", help="output directory")
    p.add_argument("--width", type=int, default=1024, help="resize width, keeps aspect ratio")
    p.add_argument("--referer", default=media.DEFAULT_REFERER)
    p.add_argument(
        "--insecure-tls",
        action="store_true",
        help="skip ffmpeg certificate verification (needed behind TLS-intercepting proxies)",
    )

    p = sub.add_parser("transcribe", help="speech -> <prefix>.txt + <prefix>.srt")
    p.add_argument("media", help="audio or video file")
    p.add_argument("--model", default=None, help=f"model dir or size (default: ${asr.MODEL_ENV} or small)")
    p.add_argument("--out", default=None, help="output prefix (default: next to the media file)")
    p.add_argument("--language", default="zh")
    p.add_argument("--hotwords", default="", help="domain words that fix proper nouns")
    p.add_argument("--device", default="cpu")
    p.add_argument("--compute-type", default="int8")
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--beam-size", type=int, default=5)
    p.add_argument("--no-vad", action="store_true", help="disable voice activity detection")

    p = sub.add_parser("fetch", help="download a signed media URL")
    p.add_argument("url")
    p.add_argument("--out", required=True)
    p.add_argument("--referer", default=media.DEFAULT_REFERER)
    p.add_argument("--timeout", type=int, default=600)

    p = sub.add_parser("model", help="download a faster-whisper model locally")
    p.add_argument("--size", default="small", help="tiny|base|small|medium|large-v3 or a hub repo id")
    p.add_argument("--dest", default=None, help="target directory (default: models/faster-whisper-<size>)")
    p.add_argument("--workers", type=int, default=8)

    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)

    try:
        if args.command == "probe":
            result = media.probe(args.src, referer=args.referer, insecure_tls=args.insecure_tls)
            print(result.raw)
            return 0

        if args.command == "frames":
            written = media.frames(
                args.src,
                times=args.times,
                out_dir=args.out,
                width=args.width,
                referer=args.referer,
                insecure_tls=args.insecure_tls,
            )
            for path in written:
                print(f"{path}  {path.stat().st_size // 1024} KB")
            return 0

        if args.command == "fetch":
            target = media.download(args.url, args.out, referer=args.referer, timeout=args.timeout)
            print(f"saved {target}  {target.stat().st_size / 1048576:.2f} MB")
            return 0

        if args.command == "model":
            path = models.download(args.size, args.dest, args.workers)
            print(f"model ready: {path}")
            print(f'export {asr.MODEL_ENV}="{path}"')
            return 0

        if args.command == "transcribe":
            source = Path(args.media)
            prefix = Path(args.out) if args.out else source.with_suffix("")
            model_ref = models.resolve(args.model)
            print(f"model: {model_ref}", flush=True)
            transcript = asr.transcribe(
                source,
                model=model_ref,
                language=args.language,
                hotwords=args.hotwords,
                device=args.device,
                compute_type=args.compute_type,
                threads=args.threads,
                beam_size=args.beam_size,
                vad_filter=not args.no_vad,
            )
            txt, srt = asr.write_outputs(transcript, prefix)
            print(
                f"lang={transcript.language} p={transcript.language_probability:.2f} "
                f"segments={len(transcript.segments)} chars={transcript.chars}"
            )
            print(f"TXT {txt}")
            print(f"SRT {srt}")
            return 0
    except (media.MediaError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
