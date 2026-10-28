# AGENTS.md

给 AI agent 的操作说明（Claude Code / Codex / Cursor / DeepSeek Harness 等）。
人类读者请直接看 `README.md`。

## 这个仓库是什么

`read-video` 是一个把视频转成可读材料的 CLI：抽帧 + 语音转写。
核心实现在 `src/readvideo/`，入口命令是 `readvideo`（短别名 `rv`，但 Windows PowerShell 里
`rv` 是 `Remove-Variable` 的内置别名，脚本和 CI 一律用 `readvideo`）。

## 目录导航

| 路径 | 作用 |
|---|---|
| `src/readvideo/cli.py` | argparse 子命令，唯一的入口 |
| `src/readvideo/media.py` | 下载 / probe / 抽帧，只依赖标准库 + ffmpeg |
| `src/readvideo/asr.py` | 音频解码 + faster-whisper 封装 + SRT 生成 |
| `src/readvideo/models.py` | 模型解析与下载 |
| `tests/` | pytest；用 ffmpeg 合成素材，**不联网** |
| `SKILL.md` | agent 技能描述，可直接放进 skills 目录 |
| `docs/douyin.md` | 抖音抓流的浏览器操作细节 |

## 改代码前必读

- **不要引入新的 HTTP 依赖**：下载用 `urllib`。这个仓库刻意保持零额外依赖。
- **不要用 `av` 解码音频**：走 `ffmpeg → f32le → numpy`，否则会撞上 faster-whisper 的
  `av` 版本冲突（`metadata_errors`）。
- **测试必须离线**：素材由 `tests/conftest.py` 用 ffmpeg `lavfi` 合成。
- **中文注释可以，标识符用英文。**

## 常用命令

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

## 验证改动

```bash
# 合成一段素材，跑通全链路（不联网）
ffmpeg -f lavfi -i sine=frequency=440:duration=3 /tmp/t.wav
readvideo transcribe /tmp/t.wav --model small   # 需要模型；CI 不跑这一步
readvideo frames   /tmp/t.wav --times 0 --out /tmp/f
```

## 提交规范

`feat:` / `fix:` / `docs:` / `test:` / `chore:` 前缀。不要提交媒体、模型、`models/`。
