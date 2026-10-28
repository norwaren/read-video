"""Media acquisition: download signed URLs, probe, and extract still frames.

Everything here shells out to ffmpeg/ffprobe and uses only the standard library
for HTTP, so there is no requests/httpx dependency.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
)
DEFAULT_REFERER = "https://www.douyin.com/"
CHUNK = 1 << 20


class MediaError(RuntimeError):
    """Raised when a media operation cannot be completed."""


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _tool(name: str) -> str:
    override = os.environ.get(f"RV_{name.upper()}")
    if override:
        return override
    exe = f"{name}.exe" if os.name == "nt" else name
    found = shutil.which(exe) or shutil.which(name)
    if not found:
        raise MediaError(
            f"{name} not found on PATH. Install ffmpeg first: https://ffmpeg.org/download.html"
        )
    return found


def _tls_args(insecure: bool) -> list[str]:
    """`-tls_verify 0` is needed behind TLS-intercepting antivirus/proxies.

    Off by default: it disables certificate checks, so it must be opt-in.
    """
    return ["-tls_verify", "0"] if insecure else []



@dataclass(slots=True)
class ProbeResult:
    duration: float | None
    size: int | None
    raw: str

    def as_dict(self) -> dict[str, float | int | None]:
        return {"duration": self.duration, "size": self.size}


def _source_args(src: str, referer: str) -> list[str]:
    if is_url(src):
        headers = f"Referer: {referer}\r\nUser-Agent: {USER_AGENT}"
        return ["-headers", headers, "-i", src]
    path = Path(src)
    if not path.exists():
        raise MediaError(f"no such file: {path}")
    return ["-i", str(path)]


def download(
    url: str,
    out: str | Path,
    *,
    referer: str = DEFAULT_REFERER,
    timeout: int = 600,
    progress: bool = False,
) -> Path:
    """Download a (possibly signed) media URL to `out`.

    Signed CDN links usually need the site `Referer`, otherwise they answer 403.
    """
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": referer})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, target.open("wb") as fh:
            total = 0
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                fh.write(chunk)
                total += len(chunk)
                if progress and total % (10 * CHUNK) < CHUNK:
                    print(f"  ... {total / 1048576:.1f} MB", flush=True)
    except urllib.error.HTTPError as exc:  # 403 = expired signature, 404 = gone
        raise MediaError(f"HTTP {exc.code} for {url} — signed links expire, re-capture it") from exc
    except urllib.error.URLError as exc:
        raise MediaError(f"network error for {url}: {exc.reason}") from exc
    return target


def probe(src: str, *, referer: str = DEFAULT_REFERER, insecure_tls: bool = False) -> ProbeResult:
    """Return container duration/size plus the raw ffprobe output."""
    args = [
        _tool("ffprobe"), "-v", "error",
        *_tls_args(insecure_tls),
        "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height",
        "-of", "default=nw=1",
        *_source_args(src, referer),
    ]
    proc = subprocess.run(args, capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        raise MediaError((proc.stderr or "ffprobe failed").strip())

    duration = size = None
    for line in proc.stdout.splitlines():
        if line.startswith("duration="):
            with contextlib.suppress(ValueError):
                duration = float(line.split("=", 1)[1])
        elif line.startswith("size="):
            with contextlib.suppress(ValueError):
                size = int(line.split("=", 1)[1])
    return ProbeResult(duration=duration, size=size, raw=proc.stdout.strip())


def frames(
    src: str,
    *,
    times: list[int],
    out_dir: str | Path,
    width: int = 1024,
    referer: str = DEFAULT_REFERER,
    insecure_tls: bool = False,
) -> list[Path]:
    """Write one PNG per timestamp (seconds). Works on local files and remote URLs."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    source = _source_args(src, referer)
    tls = _tls_args(insecure_tls)
    written: list[Path] = []

    for sec in times:
        if sec < 0:
            raise MediaError(f"negative timestamp: {sec}")
        target = directory / f"f-{sec:03d}.png"
        proc = subprocess.run(
            [
                _tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
                *tls,
                "-ss", str(sec), *source,
                "-frames:v", "1", "-vf", f"scale={width}:-1", str(target),
            ],
            capture_output=True,
            text=True,
            errors="replace",
        )
        if proc.returncode != 0 or not target.exists():
            detail = (proc.stderr or "ffmpeg failed").strip().splitlines()
            hint = ""
            if detail and "certificate" in detail[0].lower():
                hint = " (try --insecure-tls behind a TLS-intercepting proxy)"
            raise MediaError(
                f"could not extract frame at {sec}s: {detail[0] if detail else '?'}{hint}"
            )
        written.append(target)
    return written
