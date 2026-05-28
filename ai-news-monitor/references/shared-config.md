# API Key 共享说明

## Tavily API Key

ai-news-monitor 和 we-media-pipeline 共用同一个 Tavily API Key。

**快速复用 pipeline 的 key**（无需重复配置）：

```python
import json
with open('/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json') as f:
    key = json.load(f)['tavily_api_key']
# 然后传给脚本
```

**配置文件位置**：
- `~/.hermes/skills/ai-news-monitor/config.json` — 本技能专用
- `~/.hermes/skills/we-media-pipeline/config.json` — pipeline 用

## 输出路径

- 简报输出：`~/Desktop/AI资讯/{日期}_AI资讯简报.md`
- 日志/调试：stdout（直接打印）
