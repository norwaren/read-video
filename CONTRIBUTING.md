# Contributing

Thanks for looking. This project is small on purpose: one CLI, one job.

## 快速开始

```bash
git clone https://github.com/norwaren/read-video
cd read-video
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

需要 `ffmpeg` / `ffprobe` 在 PATH 上（测试会用它生成合成音频，不需要真视频）。

```bash
ruff check .
pytest -q
```

## 提 PR 之前

1. `ruff check .` 干净，`pytest -q` 全绿。
2. 新行为要有测试。测试**不联网**：用 `tests/conftest.py` 里的 `sine_wav` / `testsrc_mp4` 合成素材。
3. 不要提交媒体文件、模型文件、`models/`、`media/`、`frames/`（已进 `.gitignore`）。
4. 中文、英文注释都行，代码标识符保持英文。

## 想加平台支持？

抖音的抓流步骤在 `docs/douyin.md`。B站/YouTube 建议**不要**在仓库里内置下载器——
`yt-dlp` 已经很成熟，正确做法是文档里写清楚「先 `yt-dlp -f bestaudio`，再 `readvideo transcribe`」。
除非有 yt-dlp 覆盖不了的平台，否则不引入新依赖。

## 报 bug 请带这些

- `readvideo --version` 和 `python -V`
- 完整命令行（URL 请打码签名参数）
- 完整报错
- 媒体的 `readvideo probe` 输出（如果拿得到）

## 提交信息

`feat:` / `fix:` / `docs:` / `test:` / `chore:` 前缀，一句话说清改了什么。
