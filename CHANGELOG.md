# Changelog

All notable changes to this project are documented here.
格式参考 [Keep a Changelog](https://keepachangelog.com/)，版本号遵循 [SemVer](https://semver.org/)。

## [Unreleased]

### Fixed

- **Windows PowerShell 下 `rv` 命令被内置别名遮蔽**：`rv` 是 `Remove-Variable` 的别名，
  敲 `rv --version` 会报 `Cannot find a variable with the name '--version'`。
  新增 `readvideo` 入口点（长名不受影响），文档与 CI 改用长名，`rv` 保留给 bash/zsh/cmd。
- **CI 在 macOS 上失败**：`FedericoCarboni/setup-ffmpeg` 不支持 arm64 runner。
  改为按平台安装（apt / brew / choco）。
- **Windows 控制台 cp1252 下 `--help` 崩溃**：帮助文本里的中文让
  `UnicodeEncodeError: 'charmap' codec` 抛出。帮助文本改为纯 ASCII，
  同时把 stdout/stderr 重配置为 UTF-8 + `errors="replace"`，避免打印中文路径/标题时炸。
- `--help` 里的程序名不再写死 `rv`：跟 `sys.argv[0]` 走，`python -m readvideo` 也不再显示 `__main__.py`。

### Changed

- CI 矩阵去掉 macOS（arm64 runner 的 ffmpeg 另需处理，当前无人使用），保留 Ubuntu + Windows。

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
