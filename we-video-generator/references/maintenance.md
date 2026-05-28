# wechat-video-generator - 维护待办

## SKILL.md 重复章节清理（待处理）

SKILL.md 存在两处需修复的重复：

1. **"## 依赖" 重复**：第240行和第241行各有 `## 依赖`，需合并为一个
2. **"## 故障排除" 重复**：有两个相同的故障排除section（各含FFmpeg未找到、图片未找到两条），第二个是正确的，第一个是冗余的

**修复方法**（Python脚本）：
```python
import re
path = '/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/SKILL.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
# Remove first duplicate 故障排除 section (keep the second)
first_block = re.search(r'(## 故障排除\n\n\n### FFmpeg 未找到.*?(?=\n\n## 文件结构))', content, re.DOTALL)
if first_block:
    content = content[:first_block.start()] + content[first_block.end():]
# Fix duplicate 依赖
content = content.replace('## 依赖\n## 依赖', '## 依赖')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
```
