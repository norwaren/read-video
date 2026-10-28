# 抖音 / TikTok 网页版抓流

抖音网页版的媒体是**音视频分离**的，且直链带签名和时效。yt-dlp 的 douyin 提取器要求 cookies，未登录直接报：

```
ERROR: [Douyin] <id>: Fresh cookies (not necessarily logged in) are needed
```

所以走浏览器抓真实请求。

## 步骤

### 1. 打开并关掉登录弹窗

```
https://www.douyin.com/
```

未登录会立刻弹「登录后免费畅享高清视频」。关掉它 —— 标题右侧有个 `cursor=pointer` 的元素就是关闭按钮。

不用登录也能播：页面上的 `<video>` 会拿到 `readyState: 4`。

### 2. 点开一个视频

卡片是 `div` 加点击事件，**不是 `<a>`**，选不到 ref。用坐标点击：

```js
await page.mouse.click(196, 200);   // 第一张卡片封面
```

成功后 URL 变成：

```
https://www.douyin.com/jingxuan?modal_id=7697621631518166282
```

### 3. 确认播放中

```js
[...document.querySelectorAll('video')].map(v => ({
  duration: v.duration, readyState: v.readyState, paused: v.paused,
  w: v.videoWidth, h: v.videoHeight,
}))
// [{ duration: 246.1, readyState: 4, paused: false, w: 1280, h: 720 }, ...]
```

`readyState: 4` 且 `paused: false` = 真的在跑。

### 4. 抓直链

浏览器网络面板过滤 `media-audio|media-video`，会看到：

```
https://v11-weba.douyinvod.com/.../media-video-hvc1/?a=6383&br=3220&...&temp=1
https://v11-weba.douyinvod.com/.../media-audio-und-mp4a/?a=6383&br=189&...&temp=1
```

| 路径片段 | 含义 |
|---|---|
| `media-audio-und-mp4a` | 纯音轨，189 kbps，转写够用、体积小 |
| `media-video-hvc1` | 视频轨，H.265 |

两条 URL 是**同一支视频**的两半，通常相邻出现（音轨紧跟视频轨）。

### 5. 下载

```bash
python rv.py fetch "<音轨URL>" --out media/clip.m4a --referer https://www.douyin.com/
python rv.py frames "<视频轨URL>" --times 60,200,350 --out media/frames
```

- 带 `Referer` 和浏览器 `User-Agent`，否则可能 403。
- **URL 会过期**（`dy_q`、`l` 等参数是时间戳签名），抓完立刻下。

## 注意事项

- **别用浏览器截图抽帧**：登录弹窗会周期性重弹，截出来全是二维码。ffmpeg 直连 URL 抽帧没有这个问题。
- **预加载会迷惑你**：页面会预加载下一条视频，`document.querySelectorAll('video')` 里可能出现两个不同时长的元素。用 `duration` 对齐你想分析的那支。
- **首页是"精选"**：`www.douyin.com/` 会 302 到 `/jingxuan`，内容按分类 tab 组织，不是无限下滑的信息流。

## 其他平台

| 平台 | 建议 |
|---|---|
| B站 | `yt-dlp`，多数视频有 CC 字幕轨，能直接抓文本 |
| YouTube | `yt-dlp --write-auto-sub`，命中字幕就不用转写 |
| 通用 | `yt-dlp -f bestaudio` 下音轨，再 `rv.py transcribe` |
