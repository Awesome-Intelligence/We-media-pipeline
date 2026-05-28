---
name: ai-news-monitor
description: 获取最新AI资讯，支持多源聚合、中文翻译、HTML简报输出。监控 OpenAI、Google DeepMind、Anthropic、Meta AI、xAI 等头部AI公司的最新动态，自动生成双语HTML资讯简报。
triggers:
  - "最新AI资讯"
  - "AI新闻"
  - "获取AI资讯"
  - "AI动态"
---

# AI News Monitor - AI资讯监控

定时/手动获取头部AI公司的最新资讯，翻译成中文后输出为HTML简报。

## 核心功能

- **多源监控**：OpenAI / Google DeepMind / Anthropic / Meta AI / xAI / Mistral AI
- **双语HTML**：默认英文，点击顶部按钮切换中文
- **中文翻译**：调用MiniMax API，翻译标题+摘要，页面内实时切换
- **定时推送**：可设置cron定时运行

## 语言切换

HTML页面顶部有 **🇺🇸 English** / **🇨🇳 中文** 切换按钮：

- 默认显示英文原版（加载快，无需翻译API）
- 点击"中文"按钮，页面内实时切换为翻译内容
- 若未配置MiniMax API Key，"中文"按钮置灰，提示"翻译不可用"
- 原始HTML文件同时包含英文和中文数据，切换时无需重新请求

## 快速开始

### 手动获取今日资讯

```bash
python3 ~/.hermes/skills/ai-news-monitor/scripts/fetch_ai_news.py
```

### 输出文件

默认保存到 `/mnt/c/Users/Administrator/Desktop/AI资讯/`

```
~/Desktop/AI资讯/
└── 2026-05-19_AI资讯简报.html   ← 双语HTML版（默认）
```

## 脚本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--days` | 搜索最近N天资讯 | 3 |
| `--max-results` | 每来源最多结果数 | 5 |
| `--output` | 输出目录路径 | `/mnt/c/Users/Administrator/Desktop/AI资讯` |
| `--tavily-key` | Tavily API Key（新闻搜索） | config.json |
| `--minimax-key` | MiniMax API Key（中文翻译） | config.json |

## 配置文件

路径：`~/.hermes/skills/ai-news-monitor/config.json`（Tavily Key 也已同步写入 `~/.hermes/.env`，等效生效）

```json
{
  "tavily_api_key": "tvly-dev-***",
  "minimax_api_key": "sk-cp-***",
  "default_days": 3,
  "default_max_results": 5,
  "output_dir": "/mnt/c/Users/Administrator/Desktop/AI资讯"
}
```

## API Key 申请

| 服务 | 说明 | 申请地址 |
|------|------|---------|
| Tavily | 新闻搜索，每月1000次免费 | https://tavily.com |
| MiniMax | 中文翻译，与公众号pipeline共用 | https://platform.minimaxi.com |

## HTML简报样式

- 深蓝渐变头部，含统计信息和语言切换按钮（🇺🇸/🇨🇳）
- 按来源分组，卡片式布局
- 每条资讯含：英文标题+中文标题（切换显示）、英文摘要+中文摘要
- `data-en`/`data-cn` 属性存储双语内容，JS 切换无需刷新页面
- 支持在浏览器中直接打开查看

## 环境说明

- [WSL/Windows 双环境路径参考](references/wsl-windows-env.md) — Hermes Windows 安装 + WSL bash 调用方式
