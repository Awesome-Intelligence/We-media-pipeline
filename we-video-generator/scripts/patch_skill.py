import sys

path = '/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/SKILL.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''## 注意事项

1. **图片数量** - 必须提供3张图片
2. **文字数量** - 必须提供3段文字
3. **图片尺寸** - 建议 1080x640 或更高
4. **文字长度** - 每段建议 30-50 字'''

new = '''## 注意事项

1. **图片数量** - 必须提供3张图片
2. **文字数量** - 必须提供3段文字
3. **图片尺寸** - 建议 1080x640 或更高
4. **文字长度** - 每段建议 30-50 字

## 实战调用方式（2026-05-19）

### 独立生成视频的正确姿势

直接调用 `wechat_video_generator.py` 时，视频固定输出到 `桌面/WeChatVideo输出/{主标题}.mp4`，不会输出到调用方指定路径。**正确流程**：

```bash
# 1. 先生成视频
python3 /mnt/c/.../wechat_video_generator.py /path/to/content.json

# 2. 手动复制到目标位置
cp "桌面/WeChatVideo输出/{主标题}.mp4" /path/to/目标文件夹/
```

### content.json 必须包含 images 字段

Pipeline（`run_pipeline.py`）会自动填入 `images` 字段，但**独立调用脚本时必须手动填写**：

```json
{
  "main_title": "...",
  "sub_title": "...",
  "images": [
    "/abs/path/to/img1.webp",
    "/abs/path/to/img2.webp",
    "/abs/path/to/img3.webp"
  ],
  "text_sections": ["段1", "段2", "段3"]
}
```

### 布局参数（已调优）

| 参数 | 值 | 说明 |
|------|-----|------|
| `img_y` | `480` | 图片展示区域 Y 坐标 |
| `text_section_y` | `1250` | text section Y 坐标 |

修改这两个值需同时改脚本（`wechat_video_generator.py`）和文档（本文档 layout 节）。'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched SKILL.md successfully')
else:
    print('Pattern not found in SKILL.md')
    idx = content.find('## 注意事项')
    if idx >= 0:
        print(f"Found at index {idx}:")
        print(repr(content[idx:idx+500]))
    sys.exit(1)
