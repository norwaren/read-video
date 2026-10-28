# read-video

[![CI](https://github.com/norwaren/read-video/actions/workflows/ci.yml/badge.svg)](https://github.com/norwaren/read-video/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![ffmpeg](https://img.shields.io/badge/requires-ffmpeg-green.svg)](https://ffmpeg.org/)

**把视频变成能读的东西**：抽帧看画面，whisper 转语音，输出逐字稿 + 字幕 + 关键帧。

A tiny CLI that turns a video into readable material:

```
视频 / 链接
   ├─ readvideo fetch       → 媒体文件（音轨或视频轨，支持签名直链）
   ├─ readvideo frames      → 关键帧 PNG（远程 URL 也能抽，不下载整片）
   └─ readvideo transcribe  → 逐字稿 .txt + 字幕 .srt
```

- [为什么再造一个轮子](#为什么再造一个轮子)
- [安装](#安装)
- [快速开始](#快速开始)
- [实测](#实测)
- [命令](#命令)
- [热词：质量的决定因素](#热词质量的决定因素)
- [能力边界](#能力边界)
- [给 AI agent 用](#给-ai-agent-用)
- [设计思路与可开的分支](docs/design.md)
- [把项目交给 AI 用的提示词](docs/ai-prompt.md)
- [FAQ](#faq)
- [参考与致谢](#参考与致谢)

## 为什么再造一个轮子

不是重复造轮子，是绕开三个真实存在的坑：

| 坑 | 现成工具的现状 | 这里的做法 |
|---|---|---|
| `whisper-ctranslate2 --model <路径>` | CLI 只接受模型名（`tiny`/`small`/…），本地模型目录直接报 `invalid choice` | 直接调 `faster-whisper` 的 Python API，路径和模型名都吃 |
| faster-whisper × `av` 版本冲突 | 新版本 faster-whisper 调 `av.open(..., metadata_errors=...)`，旧版 `av` 没有这个参数 → `TypeError` | 音频先用 ffmpeg 解码成 `f32le`，再喂 numpy 数组，**完全不经过 `av`** |
| 抖音 / TikTok 直链 | `yt-dlp` 的 douyin 提取器要求 cookies，未登录报 `Fresh cookies ... are needed` | `readvideo fetch` 处理带签名的 CDN 直链（自动带 `Referer`/`UA`），配合 [`docs/douyin.md`](docs/douyin.md) 的抓流步骤 |

顺带的好处：下载只用标准库 `urllib`，**零额外 HTTP 依赖**。

## 安装

需要 **Python 3.10+** 和 **ffmpeg**（`ffmpeg -version` 能跑即可）。

```bash
git clone https://github.com/norwaren/read-video
cd read-video
pip install -e .
```

或用 uv 免安装直接跑：

```bash
uv run --with faster-whisper --with numpy --module readvideo --help
```

### 拉模型（推荐，一次即可）

```bash
readvideo model --size small --dest models/faster-whisper-small
```

然后指过去（不设也行，默认按名字在线拉）：

```bash
# Windows PowerShell
$env:READ_VIDEO_MODEL = "D:\path\to\models\faster-whisper-small"
# bash / zsh
export READ_VIDEO_MODEL="$HOME/models/faster-whisper-small"
```

> ⚠️ **Windows PowerShell 用户注意**：`rv` 是 PowerShell 的内置别名（`Remove-Variable`），
> 会盖住同名命令，敲 `rv` 报 `Remove-Variable: 找不到与参数名称"version"匹配的参数`。
> 用长名 `readvideo` 就行，或者临时 `Remove-Item Alias:rv` / 直接调 `rv.exe`。
> CI 里也是踩了这个坑才改成 `readvideo`。

| size | 体积 | 中文口播 | 速度（CPU int8） |
|---|---|---|---|
| `tiny` | 75 MB | 勉强 | 最快 |
| `base` | 145 MB | 一般 | 快 |
| **`small`** | **461 MB** | **够用（默认）** | 1 小时音频约 6–8 分钟 |
| `medium` | 1.5 GB | 明显更准 | 慢 3 倍 |
| `large-v3` | 3 GB | 最准 | 很慢，建议上 GPU |

## 快速开始

```bash
# 1. 看看这个文件/链接是什么
readvideo probe media/clip.mp4

# 2. 抽帧：60s、200s、350s 各一张
readvideo frames media/clip.mp4 --times 60,200,350 --out frames

# 3. 转写：中文 + 领域热词
readvideo transcribe media/clip.m4a --hotwords "绝密航天,红狼,威龙,碎头"
```

输出：

```
media/clip.txt          纯台词，一行一段
media/clip.srt          带时间轴，可直接挂播放器 / 剪辑软件
frames/f-060.png ...    关键帧
```

远程 URL 同样能抽帧 —— ffmpeg 用 range 请求只取需要的那几段，不会下整片：

```bash
readvideo frames "https://cdn.example/video.mp4?sig=..." --times 30,90 --out frames
```

## 实测

真机跑一遍（Windows 11 / CPU int8 / 8 线程），不是编的。

**输入**：抖音网页版一支 246 秒的 AI 漫剧（《缅北温柔陷阱》第 22 集）。

| 步骤 | 命令 | 结果 | 耗时 |
|---|---|---|---|
| 下载音轨 | `readvideo fetch` | 5.70 MB m4a | 约 3 秒 |
| 抽帧 | `readvideo frames --times 20,90,160,220` | 4 张 900px PNG | 0.2 秒 / 帧 |
| 转写 | `readvideo transcribe --hotwords "缅北,诈骗园区,…"` | 101 段 / 819 字 + SRT | **50 秒**（≈ 5× 实时） |

### 画面字幕 vs ASR 输出

同一支视频、同一时刻：左边是抽帧读到的**画面硬字幕**，右边是 whisper 的**转写结果**。

| 画面字幕 | ASR 输出 | 时刻 |
|---|---|---|
| 这又是哪个想跑的 | 这又是哪个想跑的? | 01:17 |
| 我这哪能跟你们729比 | 我这儿哪能跟你们七二九比 | 01:27 |
| 你们那边主要做啥业务啊 | 诶,哥们,你们那边主要做啥业务啊? | 00:00 |

![抽帧 87s：画面字幕「这又是哪个想跑的」](examples/frames/f-087.png)

![抽帧 90s：画面字幕「我这哪能跟你们729比」](examples/frames/f-090.png)

两条一起看，正好说明各自的用处：**语音那条给完整台词和标点，画面那条给排版和原始写法**。
差别也有规律 —— 数字会被转成汉字（`729` → `七二九`），人名和专有名词靠 `--hotwords` 纠。

### 转写样本

```
诶,哥们,你们那边主要做啥业务啊?
眼睛倒了,下个月业绩怎么办还不知道?怎么睡?
你瞧着吧,一会儿这帮人只要到了工作区,准会变得无精打采
那一会儿我和老朱挑出来一两个,敲打敲打
没用!
```

完整产物在 [`examples/demo/`](examples/demo)（音频 5.7 MB 未入库，`.txt` / `.srt` 已入库）。

## 命令

| 命令 | 作用 | 关键参数 |
|---|---|---|
| `readvideo probe <src>` | 打印时长 / 大小 / 流信息 | `--referer` |
| `readvideo frames <src>` | 按秒抽帧 | `--times 30,90`、`--out`、`--width`、`--insecure-tls` |
| `readvideo transcribe <media>` | 转写为 txt + srt | `--model`、`--hotwords`、`--language`、`--no-vad` |
| `readvideo fetch <url>` | 下载签名直链 | `--out`、`--referer`、`--timeout` |
| `readvideo model` | 下载 faster-whisper 模型 | `--size`、`--dest`、`--workers` |

`<src>` 可以是本地路径，也可以是 `http(s)` URL。

`readvideo transcribe` 还支持 `--device cuda`（需 CUDA 版 ctranslate2）、`--compute-type`、
`--threads`、`--beam-size`，默认值是 CPU + int8 + 8 线程。

## 热词：质量的决定因素

同一段音频、同一个 `small` 模型，只差 `--hotwords`：

| 无热词 | `--hotwords "野排,碎头,补枪"` |
|---|---|
| 野牌 | 野排 |
| 睡头 | 碎头 |
| 没崩溜 | 没绷住 |

**先把领域专有名词想清楚** —— 人名、技能名、地图名、平台黑话，全塞进去。
这一步的收益比换更大的模型还大。

## 能力边界

| 维度 | 能做到 | 局限 |
|---|---|---|
| 语音 | 中文口播 ≈ 95% 可用 | 黑话 / 方言 / 多人抢话会错 |
| 画面 | 抽帧后能读出画面里所有文字（字幕、PPT、UI） | 是**采样**不是连续观看，1 秒闪过的字幕会漏 |
| 音乐 / 音效 | — | 读不到 |

**适合**：口播、讲解、课程、访谈、PPT / 文档演示。
**不适合**：快剪卡点、纯音乐、无台词的动作片。

配合视觉模型使用时，典型流程是：`transcribe` 拿台词 → `frames` 拿画面文字 → 合并成一份摘要。

## 给 AI agent 用

[`SKILL.md`](SKILL.md) 是给 agent 的技能描述，兼容 Claude Code / Codex / Cursor / DeepSeek Harness
等所有读 `SKILL.md` 的宿主。放进 skills 目录即可，agent 遇到「读视频」任务会自动加载。

[`AGENTS.md`](AGENTS.md) 是本仓库的开发约定（给改代码的 agent 看）。

**想让 AI 直接帮你读视频？** 不用让它读源码 —— [`docs/ai-prompt.md`](docs/ai-prompt.md)
里有两段复制即用的提示词：

- **一句话版**：临时任务，把视频链接贴进去就完事
- **完整系统提示词**：塞进 system prompt / `AGENTS.md`，AI 就长期具备装好、跑通、排错的能力

```
用 read-video（命令 rv）帮我读这个视频，出一份中文摘要：
<链接>
要求：先 probe 确认、抽帧看画面字幕、带热词转写、最后按时间轴分段总结。
```

前提是 AI 能执行命令（有 shell）。纯对话界面用不了 —— 得先让有环境的机器转成 `.txt` / `.srt`。

## FAQ

**Q：为什么不直接内置 `yt-dlp`？**
A：`yt-dlp` 已经很成熟，B站/YouTube 用 `yt-dlp -f bestaudio` 下好再 `readvideo transcribe` 更稳。
只有它覆盖不了的场景（比如需要浏览器态的签名直链）才值得自己写，`docs/douyin.md` 就是这个场景。

**Q：一定要浏览器吗？**
A：只有抖音这类"直链带签名、音视频分离"的平台需要。本地文件、B站、YouTube 都不需要。

**Q：GPU 能用吗？**
A：`--device cuda --compute-type float16`。需要装 CUDA 版 ctranslate2，见 faster-whisper 文档。

**Q：能出双语字幕吗？**
A：现在只出单语。做法是跑两次 `--language zh` / `--language en`，或者翻译 `.srt`（没内置）。

**Q：为什么不用 `av` 解码？**
A：见[上面](#为什么再造一个轮子)那张表 —— faster-whisper 1.x 和旧 `av` 有参数不兼容，
用 ffmpeg 解码顺手还少了 C 扩展的安装麻烦。

**Q：模型下载很慢怎么办？**
A：`readvideo model` 走 `huggingface_hub`，自带分片和续传。国内网络可先设 `HF_ENDPOINT=https://hf-mirror.com`。

**Q：抽帧报 `Peer certificate failed verification`？**
A：你机器上有 TLS 中间人（杀软、企业代理、抓包工具在换证书），ffmpeg 走 schannel 时校验不过。
加 `--insecure-tls` 跳过证书校验，或者把 ffmpeg 加进杀软白名单。默认不开这个开关 ——
关掉证书校验意味着放弃中间人防护，得你自己明确选择。

## 参考与致谢

本项目的骨架、文档结构参考了这些项目（均可商用 / MIT）：

| 来源 | 借了什么 |
|---|---|
| [simonw/llm](https://github.com/simonw/llm) | 目录结构：`pyproject.toml` + `ruff.toml` + `tests/` + `docs/` + `AGENTS.md` |
| [openai/whisper](https://github.com/openai/whisper) | `CHANGELOG.md` / `.gitattributes` / 测试组织方式 |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 推理引擎本身；`CONTRIBUTING.md` 的写法 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 平台下载的现实约束（为什么抖音必须另走一条路） |
| [Keep a Changelog](https://keepachangelog.com/) | `CHANGELOG.md` 格式 |
| [ruff](https://github.com/astral-sh/ruff) / [hatch](https://github.com/pypa/hatch) | lint 与打包 |

音频解码、抽帧、SRT 生成、CLI 设计、抖音抓流步骤为本项目原创。

## License

[MIT](LICENSE) © 2026 norwaren
