---
name: wechat-video-generator
description: 为微信公众号创作者自动生成新闻短视频。只需提供标题、图片和文字内容，自动生成固定模板的视频。使用场景：每日新闻视频剪辑、公众号视频引流。布局：Logo y=120，主标题 y=218，副标题 y≈318，图片 y=480(38%高度)，文字 y=1238（直接贴背景图，无额外黑色遮罩）。
---

# WeChat Video Generator - 公众号新闻视频生成器

专为微信公众号设计的自动化视频生成工具。

## 核心特点

- ✅ **模板固定** - 样式已配置好，无需调整
- ✅ **内容分离** - 只需提供文字内容
- ✅ **一键生成** - 简单命令，快速出片
- ✅ **竖版视频** - 1080x1920，适合视频号
- ✅ **放大切换** - 图片放大淡出切换效果

## 工作流程

```
用户提供内容 → 填入content.json → 生成视频
```

## content.json 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `main_title` | ✅ | 新闻主标题（显示在顶部） |
| `sub_title` | ✅ | 新闻副标题（主标题下方） |
| `images` | ✅ | 3张图片路径（每张显示3秒） |
| `text_sections` | ✅ | 3段文字（底部显示） |
| `outro_text` | ❌ | 片尾文字（默认使用品牌信息） |

## 视频结构

```
[场景1] 3.1秒：图1正常2.9s → 图1放大淡出0.2s
[场景2] 3.1秒：图2正常2.9s → 图2放大淡出0.2s
[场景3] 2.8秒：图3正常2.8s
-------------------
总计：约9秒
```

## 布局参数（直接改脚本）

| 参数 | 脚本变量 | 当前值 | 说明 |
|------|---------|--------|------|
| `img_y` | 脚本变量 | **480** | 图片展示区域 Y 坐标（标题区 y=120~588，图片从 480 开始，在标题下方） |
| `img_h` | 脚本变量 | **int(h\*0.38)=730** | 图片高度占视频38%（约730px），图片底部 y=1210，与文字区 y=1238 有28px间隙，不遮挡文字 |
| `text_section_y` | `frame.paste(ti, (0, 1238), ti)` | 1238 | 底部文字区域 Y 坐标 |
| `crf` | 脚本变量 | **0** | 无损画质（CRF 0=绝对无损，适合素材质量高的情况；CRF 23=视觉无损+文件小，推荐日常使用） |

> **布局从上到下**：Logo y=120 → 主标题 y=218 → 副标题 y≈318 → 图片 y=480~1210（730px高，38%）→ 文字区 y=1238~1920（28px间隙，不遮挡）
> **注意**：`img_y=0` 会导致图片从屏幕最顶部开始放置，与标题区严重重叠，绝对不能设为0。

> 注意：`offset_y=100`，所以 logo 实际 Y=120，标题实际 Y=218。

## 视觉效果调优

### Logo 样式（当前：80×80，4px羽化边缘）

用户要求 Logo 更小 → 当前 80×80，边缘羽化 4px（crisp 风格）：

```python
l = ImageOps.fit(l, (80, 80), Image.Resampling.LANCZOS)  # 强制正方形裁剪
size = 80
center = size // 2
feather = 4  # 边缘羽化范围（像素），越小越 crisp
mask = Image.new('L', (size, size), 0)
for y in range(size):
    for x in range(size):
        dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
        if dist < center:
            if dist >= center - feather:
                alpha = int(255 * (center - dist) / feather)
            else:
                alpha = 255
            mask.putpixel((x, y), max(0, alpha))
l.putalpha(mask)
frame.paste(l, ((w - 80) // 2, 20 + offset_y), l)
```

**调整幅度**：改 `feather = 4` 的值——越大边缘越柔和，越小越 crisp（当前=4）。

### 文字位置调整

主标题/副标题 Y 坐标受两个变量控制：
- `offset_y = 100`（整体向下偏移量）
- 标题硬编码 Y = 118 → 实际 = 118 + 100 = 218

上移/下移修改这两个值即可同步调整。

### 编码质量（当前：CRF=0 + yuv444p）

无损画质组合：**CRF=0 + yuv444p**
- `CRF=0` = 绝对无损（文件约 1.6MB/9秒）
- `yuv444p` = 完整色彩采样，不丢色（比 yuv420p 多占用约 33% 文件大小）
- 两者组合 = 最高保真度，适合素材质量高的情况

日常快速生成可用 CRF=23 + yuv444p（~530KB/9秒，视觉无损）。

> ⚠️ 改完编码参数后，视频文件可能从 530KB 跳到 1.6MB，这是正常的。

### 文字区域无额外遮罩

底部文字直接贴在背景图上（背景图本身是深色底的图片），**没有**额外的一整块黑色遮罩。如果看到文字区是"一整块黑"，说明：
1. 背景图在 text_section_y=1238 以下区域本身就是深色
2. 或者看的是旧版缓存视频（重新生成即可）



### 通过 pipeline 调用

```bash
python3 ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "主题" --skip 1 2 3 4 5
```

Pipeline 会自动将视频复制到项目目录。

### 独立调用脚本（视频输出到 WeChatVideo输出/）

**⚠️ 重要：函数签名参数名是 `content_json`, `images_dir`, `output_file`** — 不是 `content`, `images`, `output`！

**⚠️ 重要：不要用 shell 变量拼接调用，用 Python import！**

❌ 错误方式（含中文路径变量展开失败）：
```bash
PROJECT="/mnt/c/Users/Administrator/Desktop/项目目录"
python3 ~/.hermes/skills/wechat-video-generator/scripts/run_video_generator.py "$PROJECT/05_content.json" ...
```

✅ 正确方式（Python import 绕过 shell 变量展开）：
```python
import sys
sys.path.insert(0, '/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts')
from run_video_generator import generate_video

project = '/mnt/c/Users/Administrator/Desktop/OpenClaw\\u751f\\u6210\\u6587\\u7ae0/20260521_090345_google\\u53d1\\u5e03\\u4f1a'
result = generate_video(
    content_json=project + '/05_content.json',
    images_dir=project + '/images_good',
    output_file=project + '/06_video.mp4'
)
print(result)
```

### 通过 pipeline 调用

```bash
python3 ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "主题" --skip 1 2 3 4 5
```

Pipeline 会自动将视频复制到项目目录。

## ⚠️ 铁律：修改脚本参数必须先确认

**绝对禁止在用户未明确同意的情况下擅自修改视频脚本参数。**

历史上曾多次发生助手未经用户同意修改 CRF、yuv 色彩空间、图片布局等关键参数的事情。每次都需要用户主动提出才能发现，属于本末倒置。

**正确流程**：
1. 向用户说明当前参数值和可选方案
2. 等待用户明确回复（如"好"、"用 CRF 0"）
3. 才能动手修改
4. 修改后读回验证，告知用户完成

这条规则优先级高于所有其他优化建议。

## 依赖

```bash
pip install Pillow -q -i https://mirrors.aliyun.com/pypi/simple/
```

FFmpeg 必须安装并加入 PATH（Linux/WSL: `/usr/bin/ffmpeg`，Windows: `C:\ffmpeg\...\ffmpeg.exe`）。

## ⚠️ 重要：脚本完整性验证（每次修改后必做）

`wechat_video_generator.py` 历史上曾被静默截断（.hermes 版本在 2950 行处中断，缺少 ffmpeg 调用），后来完整重建。**任何编辑后立即验证**：

```bash
wc -l ~/.hermes/skills/wechat-video-generator/scripts/wechat_video_generator.py
# 完整脚本应 ≥ 400 行（当前约 419 行）
# 如果 < 300 行 = 被截断，需要重建
```

**完整脚本判断标准**：以 `create_bg` 函数开始，到视频输出到 `WeChatVideo输出/` 结束。检查末尾是否有 ffmpeg concat 调用。

## ⚠️ 重要：脚本多副本同步规则

`.hermes`、`.openclaw`、`.trae-cn` 三处均存有 `wechat_video_generator.py`。**以 `.openclaw` 为完整性参考**（之前 .hermes 被截断时 .openclaw 完整）：

1. 编辑 `.hermes` 版本（主工作副本）
2. 验证行数 ≥ 400
3. 同步到其他副本：

```bash
# 验证完整性后再同步
hermes_scripts=~/.hermes/skills/wechat-video-generator/scripts
openclaw_scripts=~/.openclaw/workspace/skills/wechat-video-generator/scripts

# 如果 .hermes 完整且 .openclaw 过期，以 .hermes 为准
# 如果 .hermes 被截断（< 300 行），以 .openclaw 为准重建 .hermes
cp "$openclaw_scripts/wechat_video_generator.py" "$hermes_scripts/wechat_video_generator.py"

# 再同步到 .trae-cn
trae_scripts=~/.trae-cn/skills/wechat-video-generator/scripts
cp "$hermes_scripts/wechat_video_generator.py" "$trae_scripts/wechat_video_generator.py"
```

> 注意：`run_video_generator.py` 是 pipeline 专用入口；`wechat_video_generator.py` 是独立调用入口。两者不要混淆。

## 跨平台环境检测

脚本自动检测 `windows` / `wsl` / `linux` 三种环境，字体统一使用微软雅黑。

## 已知限制

1. **封面模糊/颗粒感：大概率是源图分辨率不足**：原图 1200×675（16:9）拉伸到 1080×768 图片区域后放大 0.9x，显示时会有明显颗粒感。**解决**：使用 1920×1080 以上的高清截图/配图，清晰度大幅提升。这是 source material 问题，不是脚本 bug。
2. **content.json 微调后重新生成视频**：Pipeline Step 6 成功后自动往项目目录部署 `重新生成视频.py`。用户双击该脚本，或在脚本所在目录 `python 重新生成视频.py`，会自动读取最新的 `05_content.json` 重新生成视频，无需每次喊助手。该脚本支持 Windows / WSL / Linux 三种环境自动检测。
3. **content.json 必须含 images 字段**：Pipeline 自动填入，独立调用时需手动填写3张图片路径。
4. **Step 5 JSON生成失败**：MiniMax 返回空时，手动构造 `05_content.json`，用 `--skip 1 2 3 4 5` 跳过前5步直接生成视频。
5. **WSL 下 patch/grep 工具失效**：对 Windows 挂载的 .py 文件做 patch 时，工具会报 "Found N matches" 或 "no match"。解决：用子任务（`delegate_task`）来处理文件编辑，或用 Python 脚本按字节替换。
6. **WSL 下脚本执行无回显但文件正常生成**：subprocess 调用时 stdout/stderr 偶尔被吞，exit code 0 但没有任何输出。视频文件却正常生成。验证方法：`ls -la /mnt/c/Users/Administrator/Desktop/WeChatVideo输出/`。根本原因：ffmpeg/PIL 在 WSL 下对 `/mnt/c/...` 路径的输出重定向行为异常。
7. **Logo 非正方形导致圆形遮罩偏移**：如果原 logo 不是正方形，用 `thumbnail` 缩放会保持宽高比，导致圆形 alpha 遮罩对不齐。已改用强制 `resize` 到正方形解决。
8. **视频发暗/偏色**：当前 `yuv444p`（完整色彩），平台二次转码时可能有偏色风险。如上传视频号/抖音后变暗/偏色，改用 `yuv420p` 兼容性更好。
9. **通过 `run_video_generator.py` 调用时文件已存在则跳过**：该脚本检查 `os.path.exists(output_file)` 为真时直接返回成功，不重新生成。解决：手动 `rm` 输出文件后再跑。
10. **zoom 动效帧（2.8秒）中 text_section 缺失**：`create_bg()` 在帧生成时被调用一次（含 logo + 顶部文字 + 底部文字），图片 paste 覆盖其上。但 zoom 帧循环里只 paste 了图片，底部文字没有重画到 composed 上，导致 zoom 过程中文字消失约 2.8 秒。这是结构性设计问题，需要重构帧生成逻辑才能彻底解决。临时方案：设置 img_h ≤ 38%，使底部文字区（y=1238）在 zoom 动效结束后才出现。**当前 img_h=38%，避开了文字区，用户无感知。**
7. **WSL 下 `patch` 工具对 .py 文件静默失效**：写验证显示"Post-write verification failed"，文件内容不符（常因连续空行导致字节数不匹配）。解决：用 Python 脚本直接读写文件内容，或用 `sed -i` 替换。验证方式：读取相关行确认改动已生效。

## 故障排除

### FFmpeg 未找到
**解决**: 确认 ffmpeg 在 PATH 中。

### 图片未找到
**解决**: 检查图片绝对路径，跨平台路径不要混用 `\\` 和 `/`。

### PIL 绘图报错 y1 < y2
**解决**: `draw_round` 已内置尺寸保护，检查 `r` 值是否异常。

## 文件结构

```
wechat-video-generator/
├── SKILL.md
├── scripts/wechat_video_generator.py   # 主脚本（唯一脚本）
├── templates/ai_not_cool_v4.json       # 视频样式模板
└── assets/
    ├── backgrounds/ai_not_cool_bg.jpg  # 背景图
    ├── logos/ai_not_cool_logo.jpg     # Logo
    └── music/ai_not_cool_bgm.mp3      # 背景音乐
```
