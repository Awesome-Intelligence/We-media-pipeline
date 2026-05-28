# We自媒体创作平台

自媒体内容一站式创作平台，输入主题自动生成文章、配图和短视频。

## 功能特性

- **新闻搜索**：基于 Tavily API 搜索最新资讯
- **文章生成**：输入关键词自动生成微信公众号风格文章
- **配图搜索**：自动匹配主题相关图片
- **文档导出**：Markdown 转 Word 文档
- **视频生成**：基于文章内容自动生成短视频脚本
- **风格学习**：从公众号文章学习写作风格供文章生成使用

## 快速开始

### 环境要求

- Python 3.8+
- 网络环境支持访问 Tavily、Pexels API

### 安装依赖

```bash
pip install requests
```

### 配置 API Key

**配置文件位置**: 项目根目录 `config.json`

编辑 `config.json`，填入你的 API Key：

```json
{
  "tavily_api_key": "your_tavily_key_here",
  "minimax_api_key": "your_minimax_key_here",
  "pexels_api_key": "your_pexels_key_here",
  "default_output_dir": "output",
  "style_dir": "",
  "news_search": {
    "default_days": 7,
    "default_results": 10
  }
}
```

**配置优先级**（API Key）：
1. 项目配置 `config.json`（优先）
2. 环境变量
3. 技能本地配置

### 启动服务

```bash
cd web-platform
python server.py
```

访问 <http://localhost:8080> 即可使用。

## 项目结构

```
we-media-pipeline/
├── config.json                 # 项目全局配置
├── styles/                     # 风格文件存储目录
│   └── {主题}/
│       └── style.md           # 学习到的风格
├── web-platform/              # Web 前端和后端服务
│   ├── index.html             # 前端页面
│   ├── server.py              # 后端 API 服务
│   ├── 自媒体输出/            # 输出目录
│   └── debug_server.py        # 调试服务器
├── article-fetcher/           # 文章抓取与风格学习
│   ├── config.json            # 风格保存路径配置
│   └── scripts/
├── article-writer/             # 文章生成
│   ├── config.json            # 风格读取路径配置
│   └── references/
│       └── style-guide.md     # 内置默认风格
├── news-searcher/              # 新闻搜索技能
├── image-searcher/             # 百度图片搜索技能
├── article-formatter/          # Markdown 转 Word 技能
├── we-video-generator/        # 视频生成技能（已重命名）
└── shared/
    └── config_loader.py       # 共享配置加载逻辑
```

## 工作流程

1. 输入创作主题，选择时间范围
2. 自动搜索相关新闻资讯
3. 基于新闻生成公众号文章
4. 自动匹配主题配图
5. 导出 Word 文档
6. 生成短视频脚本并合成视频

## 风格联动机制

`article-fetcher` 和 `article-writer` 可在保持独立性的同时实现风格共享。

### 设计原则

| 原则 | 说明 |
|------|------|
| **独立导入** | 每个 skill 都可以单独导入 OpenClaw |
| **灵活配置** | 通过配置文件指定风格存储和读取路径 |
| **默认路径** | 未配置时使用项目内置默认值 |

### 配置层级

| 级别 | 配置文件 | 用途 |
|------|----------|------|
| 项目全局 | `config.json` | `style_dir` 指定风格存储目录 |
| Fetcher 本地 | `article-fetcher/config.json` | 覆盖风格保存路径 |
| Writer 本地 | `article-writer/config.json` | 指定风格读取路径 |

### 配置优先级

**风格目录 (style_dir)**：
1. 项目 `config.json` 中的 `style_dir`
2. Skill 本地 `config.json` 中的 `style_dir`
3. 默认值：`{项目根目录}/styles`

**风格读取路径**：
1. Writer 本地 `config.json` 中的 `style_source`
2. 项目 `config.json` 中的 `style_dir`
3. Skill 内置 `references/style-guide.md`

### 使用流程

**Fetcher 学习风格**：
```
用户：学习这篇文章，主题是AI创业
    ↓
将风格保存到 {style_dir}/{主题}/style.md
```

**Writer 生成文章**：
```
用户：生成一篇关于AI创业的文章
    ↓
尝试读取 {style_dir}/{主题}/style.md
    ↓
如果存在 → 使用学习的风格
如果不存在 → 使用内置 style-guide.md
```

### 配置示例

**使用默认路径**（全部留空）：
- fetcher 保存到 `styles/{主题}/style.md`
- writer 从相同位置读取

**自定义风格目录**：
```json
// config.json
{
  "style_dir": "E:\\MyStyles"
}
```
- fetcher 保存到 `E:\MyStyles/{主题}/style.md`
- writer 从相同位置读取

### 代码使用

```python
from shared.config_loader import get_style_dir, get_style_path

style_dir = get_style_dir()                    # 获取风格目录
style_path = get_style_path("AI创业")           # 获取特定主题的风格文件
```

### 注意事项

1. **相对路径**：`style_dir` 配置为相对路径时会相对于项目根目录解析
2. **绝对路径**：建议使用绝对路径以避免歧义
3. **回退机制**：writer 如果找不到学习的风格，会自动回退到内置风格

## API 端口

| 端点                    | 方法       | 功能      |
| --------------------- | -------- | ------- |
| `/`                   | GET      | 前端页面    |
| `/api/config`         | GET/POST | 读取/保存配置 |
| `/api/news/search`    | POST     | 搜索新闻    |
| `/api/images/search`  | POST     | 搜索配图    |
| `/api/word/export`    | POST     | 导出 Word |
| `/api/video/generate` | POST     | 生成视频    |

## 技术栈

- 前端：原生 HTML/CSS/JavaScript，Notion 风格 UI
- 后端：Python 标准库 http.server

## 更新日志

### 2024
- 完成目录重命名统一（wechat → we）
- `wechat-media-publish-pipeline` → `we-media-pipeline`
- `wechat-video-generator` → `we-video-generator`