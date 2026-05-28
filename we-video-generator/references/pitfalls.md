# 视频生成已知问题与修复

## 1. patch 工具对 CRLF 文件失效

**问题**：`patch` 工具对 WSL 挂载的 Windows 文件（`/mnt/c/...`）失效，报 `Post-write verification failed`。

**根因**：Windows CRLF 行尾 vs patch 的 LF 匹配，导致验证回滚。

**修复**：用 Python 字节替换：
```python
path = '/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts/wechat_video_generator.py'
with open(path, 'rb') as f:
    content = f.read()
content = content.replace(b"'-crf', '18'", b"'-crf', '16'")
with open(path, 'wb') as f:
    f.write(content)
```

## 2. 脚本多副本不一致

**问题**：`.hermes`、`.openclaw`、`.trae-cn` 三处均存有脚本，修改一处后未同步会导致混淆。

**现象**：2026-05-19 发现 `.hermes` 版本截断于 2950 行（`return frame` 后无内容），缺失主循环；`.openclaw` 完整但无 CRF 18；`.trae-cn` 只有 313 行。

**同步命令**：
```bash
cp ~/.hermes/skills/wechat-video-generator/scripts/wechat_video_generator.py \
   ~/.openclaw/workspace/skills/wechat-video-generator/scripts/wechat_video_generator.py
cp ~/.hermes/skills/wechat-video-generator/scripts/wechat_video_generator.py \
   ~/.trae-cn/skills/wechat-video-generator/scripts/wechat_video_generator.py
```

## 3. 文件截断的判断方法

**问题**：`wc -l` 显示大数字，但文件可能在函数中途截断，看起来完整实则损坏。

**判断技巧**：
```bash
# 检查文件末尾
tail -5 ~/.hermes/skills/wechat-video-generator/scripts/wechat_video_generator.py
# 正常结尾应有 shutil.rmtree 或 print；截断文件末尾通常是 return frame 或空行

# 对比完整副本行数
wc -l ~/.openclaw/workspace/skills/wechat-video-generator/scripts/wechat_video_generator.py
```

## 4. content.json 必须含 images 字段

**问题**：缺少 `images` 时脚本输出 `Creating 0 scenes` 后静默失败（ffmpeg concat 报错）。

**修复**：
```json
{
  "images": ["/absolute/path/to/img1.webp", "/absolute/path/to/img2.webp", "/absolute/path/to/img3.webp"]
}
```

## 5. 视频输出目录

**已修复（2026-05-22）**：视频现已正确输出到项目目录，而非 `WeChatVideo输出/`。

**技术修复**：在 `wechat_video_generator.py` 中新增 `_CLI_OUTPUT` 解析 `sys.argv[2]`，优先使用该参数作为输出路径。`run_video_generator.py` 调用时传入第3个参数 `output_file`。因此通过 pipeline 生成的视频现在写入项目目录。

**注意**：`OUTPUT_DIR` 变量仍然存在但不再控制最终输出位置，仅用于 fallback。

## 6. 布局参数（2026-05-22 最终调优值）

| 参数 | 值 | 说明 |
|------|-----|------|
| `img_y` | **480** | 图片展示区 Y 坐标（标题区 y=120~588，图片从480开始，在标题下方，不重叠） |
| `img_h` | **int(h\*0.35)=672px** | 图片高度占视频35%，避免过高遮挡文字区 |
| `text_section_y` | 1238 | text section Y 坐标 |
| `logo_y` | 20+offset_y=120 | Logo Y 坐标 |
| `offset_y` | 100 | 全局偏移量 |
| `zoom_scale` | 9.0 | Ken Burns 放大倍数 |
| `zoom_d` | 0.2s | 放大持续时间 |
| `crf` | **0** | 无损画质（绝对无损，约1.6MB/9s） |
| `pix_fmt` | **yuv444p** | 完整色彩采样，不丢色（比yuv420p大33%，色彩保真最高） |

> **文字区域无额外遮罩**：底部文字（y=1238起）直接贴在背景图上。如看到"一整块纯黑"，是背景图本身在对应区域为深色，或旧缓存视频。
>
> ⚠️ `yuv444p + CRF=0` 组合平台二次转码时可能偏色/变暗（如上传视频号后变差）。如遇此问题，切回 `yuv420p`。

## 7. Logo 圆润方案（2026-05-19 更新）

当前使用**径向渐变圆形遮罩**，替代有锯齿的 `ellipse` 填色方案：

```python
# 逐像素计算圆心距，中心 alpha=255，边缘 alpha=0，无级过渡
for y in range(size):
    for x in range(size):
        dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
        if dist <= center:
            alpha = int(255 * (1 - dist / center))
            mask.putpixel((x, y), max(0, alpha))
```

注意：此段代码依赖前面的 `ImageOps.fit(l, (80, 80), LANCZOS)` 将 logo 裁成正方形。

## 8. 视频发暗发虚

**原因**：9倍 Ken Burns 放大插值会导致发虚，背景图亮度不足也会有影响。

**当前设置**：CRF=0，yuv444p，Ken Burns zoom_scale=9.0。

**如仍不理想**：检查 `assets/backgrounds/ai_not_cool_bg.jpg` 亮度是否充足，或调低 zoom_scale。

## 9. WSL 下脚本执行无回显

**问题**：subprocess 调用时 stdout/stderr 偶尔被吞，文件却正常生成。

**验证**：通过 `ls -la` 检查输出目录时间戳确认执行成功。

## 10. 上传视频号/抖音后画质变差、颜色暗淡

**现象**：本地视频清晰色彩正常，上传到微信视频号/抖音后变暗、偏色、模糊。

**当前设置**：yuv444p + CRF=0（最高保真）。**已知风险**：平台二次转码时 4:4:4 色度抽样处理不当，可能导致偏色/暗淡/细节丢失。

**如果出现平台偏色问题**，切换到 yuv420p：
```python
# 替换 yuv444p → yuv420p
sed -i "s/'yuv444p'/'yuv420p'/g" wechat_video_generator.py
```

| 编码参数 | 平台兼容性 | 适用场景 |
|---------|-----------|---------|
| `yuv444p` + `CRF=0` | 风险（平台转码可能偏色） | 本地/高保真场景 |
| `yuv420p` + `CRF=23` | **好（所有平台通用）** | 上传视频号/抖音 |

**验证当前 pix_fmt**：
```bash
ffprobe -v quiet -print_format json -show_streams output.mp4 | python3 -c "
import json,sys; d=json.load(sys.stdin)
v=[s for s in d['streams'] if s.get('codec_type')=='video']
if v: print('pix_fmt:', v[0].get('pix_fmt'))
"
```

## 11. 封面模糊：源图分辨率不足

**现象**：封面放大后有明显颗粒感/模糊感。

**根因**：原图 1200×675（16:9）经裁剪匹配 1080:768 比例后，拉伸到 1080×607 再显示，放大 0.9x 导致颗粒感。这是 **source material 问题，不是脚本 bug**。

**解决**：使用 1920×1080 以上的高清截图/配图。

## 12. 视频覆盖层叠加顺序

**问题**：新布局 `img_y=470` 时，图片紧贴在标题下方（Y=470~1238），文字区在 Y=1238 开始。需确认 logo/标题不会被图片遮挡。

**当前逻辑**：`create_bg` 中背景→Logo→标题→副标题→图片→文字→Logo 顺序叠加。图片（y=480）粘贴在背景上方，Logo/标题粘贴在图片上方，所以 Logo/标题不会被图片遮挡。

## 13. `run_video_generator.py` 调用方式：用 Python import，不要用 shell 变量拼接

**问题**：通过 `bash -c 'python3 script.py "$VAR"'` 调用时，含中文路径的变量展开失败，报 `content.json not found` 且路径为空。

**正确方式**：用 Python 直接 import 调用：
```python
import sys, os
sys.path.insert(0, '/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts')
from run_video_generator import generate_video

project = '/mnt/c/Users/Administrator/Desktop/OpenClaw\\u751f\\u6210\\u6587\\u7ae0/20260521_090345_google\\u53d1\\u5e03\\u4f1a'
result = generate_video(
    content=project + '/05_content.json',
    images=project + '/images_good',
    output=project + '/06_video.mp4'
)
print(result)
```
不要用 `bash -c 'python3 ... "$PATH"'` 拼接变量传中文路径——WSL 下变量展开会失败。用 Python import 绕过 shell。

## 14. WSL "幽灵文件"：`ls` 可见但 Python 无法访问

**现象**：`ls -la` 显示目录有文件，`os.listdir()` 返回 `[]`，`os.path.exists()` 返回 `False`，但 `stat` 可以查到文件 inode。Python 和 bash 看到的内容不一致。

**根因**：WSL 内部文件系统（`/tmp`、`/images_good/` 在 WSL 根目录）与 Windows 共享目录（`/mnt/c/Users/...`）属于不同的挂载视图。文件在 WSL 内部文件系统创建时，权限 `rw-------`（600），Windows UID 映射与 WSL root UID 不同。Python 进程通过 Windows 路径视角（`/mnt/c/...`）无法穿透到 WSL 内部文件系统的目录。

**诊断**：
```python
import os
d = '/path/to/images_good'
st = os.stat(d)
print(f'nlink: {st.st_nlink}, mode: {oct(st.st_mode)}')
# nlink=1 说明是独立文件系统（非 /mnt/c）
# nlink=2 说明在 /mnt/c 下，属于正常共享目录
```

**解决**：所有图片文件都必须创建在 `/mnt/c/Users/...` 路径下，通过 `cp -r /images_good/. /mnt/c/.../images_good/` 将 WSL 内部文件迁移到共享目录。不要在 `/tmp`、`/images_good/`（WSL 根目录）等独立文件系统创建后期望从 Windows 路径访问。

## 15. 诊断技巧：区分"代码遮罩"还是"背景图自身深色"

当用户反馈"底部文字区是一整块黑色"时，不要假设代码有遮罩 bug。用 PIL 分析背景图各区域 RGB：

```python
from PIL import Image
img = Image.open('/path/to/background.jpg')
w, h = img.size

def region_mean(img, y0, y1):
    pixels = list(img.crop((0, y0, w, y1)).getdata())
    r = sum(p[0] for p in pixels) / len(pixels)
    g = sum(p[1] for p in pixels) / len(pixels)
    b = sum(p[2] for p in pixels) / len(pixels)
    return r, g, b

scale = h / 1920
regions = [
    ('图片顶 24-26%', int(h*0.24), int(h*0.26)),
    ('图片底 58-62%', int(h*0.58), int(h*0.62)),
    ('文字区顶 62-66%', int(h*0.62), int(h*0.66)),
    ('底部 90-100%', int(h*0.90), h),
]
for name, y0, y1 in regions:
    r, g, b = region_mean(img, y0, y1)
    print(f'{name} (y={int(y0/scale)}-{int(y1/scale)}): RGB({r:.0f},{g:.0f},{b:.0f})')
```

**判断标准**：
- RGB ≈ (50,50,50) 或更低 → 背景图自身是深色/黑色，不是遮罩
- RGB 明显更高（如 150+）→ 背景图在该区域是浅色，可能是遮罩 bug

**实测案例（2026-05-22）**：用户 look.png 分析显示文字区顶部（y≈1250）RGB=(53,55,57) 已是深灰，底部 RGB=(19,19,19) 接近纯黑。这是背景图自身设计（深色渐变到底），不是代码遮罩。解决方案：更换背景图或调小 img_h。
