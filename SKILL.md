---
name: read-video
description: 读取视频内容并输出摘要 —— 画面（抽帧看字/场景）、语音（whisper 转写逐字稿）、页面文案与评论。适用于抖音/B站/YouTube/本地视频文件。当用户说「这个视频讲了什么」「把视频转成文字」「提取台词/字幕」「总结视频」时加载。
whenToUse: 用户给出视频链接或文件，要求总结内容、提取台词/字幕、或判断视频讲了什么。
---

# read-video

用 `rv` 把视频变成可读文本 + 关键帧，然后写摘要。

前置：`pip install -e .`（仓库根目录），`ffmpeg` 在 PATH 上，模型已就位
（`rv model --size small` 或设 `READ_VIDEO_MODEL`）。

## 能力边界（先说实话）

| 维度 | 能做到 | 局限 |
|---|---|---|
| 语音 | 中文口播 ≈ 95% 可用 | 黑话/方言/抢话会错，靠 `--hotwords` 救 |
| 画面 | 抽帧 + 视觉理解，能读画面里所有文字 | **采样**不是连续观看，1 秒闪过的字幕会漏 |
| 文案 | 页面标题/描述/话题/作者 | — |
| 评论 | DOM 抓取 | 需展开"更多" |
| 音乐/音效 | 读不到 | 只有人声能转 |

**强项**：口播、讲解、课程、PPT/文档演示。**弱项**：快剪卡点、纯音乐、无台词动作片。

## 命令

```bash
rv probe "<src>"                          # 时长/编码，先确认能读
rv fetch "<URL>" --out media/clip.m4a     # 下载签名直链
rv frames "<src>" --times 60,200,350 --out media/frames
rv transcribe media/clip.m4a --out media/clip \
    --hotwords "专有名词1,专有名词2"
```

`<src>` 可以是本地文件或 `http(s)` URL；`frames` 吃远程 URL 时不会下载整片。

## 平台分派

| 平台 | 走法 |
|---|---|
| 抖音 | 浏览器播放 → 抓签名直链（yt-dlp 要 cookies，别用）。详见 `docs/douyin.md` |
| B站/YouTube | 先 `yt-dlp -f bestaudio`，再 `rv transcribe`；有独立字幕轨就直接抓文本，省掉转写 |
| 本地文件 | 直接 `transcribe` + `frames` |

## 抖音流程（实测）

1. 打开 `https://www.douyin.com/`，会弹登录框。
2. 关弹窗：找「登录后免费畅享高清视频」，点标题右侧 `cursor=pointer` 的元素。
3. 点封面卡片（卡片不是 `<a>`，用坐标点击）。URL 变成 `?modal_id=<aweme_id>`。
4. 确认在播：`document.querySelectorAll('video')` 里有 `readyState:4 && paused:false`。
5. 抓直链：浏览器网络面板过滤 `media-audio|media-video`。
   - `media-audio-und-mp4a` = 纯音轨（转写够用，体积小）
   - `media-video-hvc1` = 视频轨（抽帧用）
   - **签名有时效，抓完立刻下**
6. `rv fetch` 下音轨 → `rv frames` 抽帧 → `rv transcribe` 转写。

## 热词是质量关键

同一段音频、同一个 `small` 模型：

| 不加热词 | 加 `野排,碎头,补枪` 后 |
|---|---|
| 野牌 | **野排** |
| 睡头 | **碎头** |
| 没崩溜 | 没绷住 |

先想清楚领域专有名词：人名、技能名、地图名、平台黑话，全塞进 `--hotwords`。

## 输出格式

```
## 视频内容摘要
**类型 / 时长 / 作者**

### 一句话
### 结构（分段 + 时间轴）
### 关键信息（数据、结论、观点）
### 质量说明（哪些词可能错）
```

## 已知坑

| 现象 | 解法 |
|---|---|
| yt-dlp 报 `Fresh cookies are needed` | 抖音要登录态，改抓浏览器直链 |
| 截图全是登录二维码 | 弹窗会自动重弹，抽帧走 `rv frames` 直连 URL |
| HF API 502 / 模型下到一半断 | `rv model` 走 `huggingface_hub`，自带分片续传；国内可设 `HF_ENDPOINT=https://hf-mirror.com` |
| `TypeError: ... 'metadata_errors'` | faster-whisper 锁旧版 `av`；本项目用 ffmpeg→f32le→numpy 绕开 |
| 签名 URL 403 | 链接过期了，回浏览器重新抓一条 |
| 抽帧报 `Invalid argument` | 输入只有音轨没有视频流；抽帧必须用视频轨 |
| 抽帧报 `Peer certificate failed verification` | 有 TLS 中间人（杀软/代理）；加 `--insecure-tls` 或把 ffmpeg 加白名单 |

## 调参

| 旋钮 | 效果 |
|---|---|
| `--model medium` | 明显更准，慢 3 倍，模型 1.5GB |
| `--hotwords` | 专有名词准确率决定性因素 |
| `--times` 密度 | 快剪视频加密到 5–10s 一帧 |
| `--beam-size 5` | 默认；降到 1 提速，质量略降 |
| `--no-vad` | 关掉静音切分，处理连续说话/音乐底噪 |
