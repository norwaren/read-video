# Changelog

All notable changes to this project are documented here.
格式参考 [Keep a Changelog](https://keepachangelog.com/)，版本号遵循 [SemVer](https://semver.org/)。

## [Unreleased]

## [0.1.0] - 2026-10-27

首个可用版本。

### Added

- `rv transcribe` — 用 faster-whisper 把音视频转成 `.txt` + `.srt`，支持 `--hotwords` 纠正专有名词。
- `rv frames` — 按时间点抽帧；本地文件和远程 URL 都支持（远程走 ffmpeg range 请求，不下载整片）。
- `rv fetch` — 下载带签名的 CDN 直链，自动带 `Referer` / `User-Agent`。
- `rv probe` — 打印时长、大小和流信息。
- `rv model` — 把 faster-whisper 模型快照到本地，支持离线使用。
- `SKILL.md` — 给 agent 用的技能描述（Claude Code / Codex / DeepSeek Harness 兼容）。
- `docs/douyin.md` — 抖音网页版抓流步骤：关登录弹窗、点卡片、抓 `media-audio` 直链。

### Notes

- 音频解码走 `ffmpeg → f32le → numpy`，绕开 faster-whisper 的 `av` 版本冲突
  （`TypeError: open() got an unexpected keyword argument 'metadata_errors'`）。
- `rv frames --insecure-tls` / `rv probe --insecure-tls`：给 TLS 中间人环境（杀软/代理换证书）的逃生开关，默认关闭。
- `RV_FFMPEG` / `RV_FFPROBE` 环境变量可指定二进制路径。
- 只在抖音网页版的一支视频上做过端到端验证；B站 / YouTube 走 `yt-dlp` 更稳，未内置。
