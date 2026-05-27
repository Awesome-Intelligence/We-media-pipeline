# We自媒体创作平台

自媒体内容一站式创作平台，输入主题自动生成文章、配图和短视频。

## 功能特性

- **新闻搜索**：基于 Tavily API 搜索最新资讯
- **文章生成**：输入关键词自动生成微信公众号风格文章
- **配图搜索**：自动匹配主题相关图片
- **文档导出**：Markdown 转 Word 文档
- **视频生成**：基于文章内容自动生成短视频脚本

## 快速开始

### 环境要求

- Python 3.8+
- 网络环境支持访问 Tavily、Pexels API

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key

1. 启动服务：`python web-platform/server.py`
2. 打开 <http://localhost:8080>
3. 点击左侧「设置」，填写以下 API Key：
   - **Tavily API Key**（新闻搜索）：<https://tavily.com> 注册获取
   - **Pexels API Key**（配图搜索）：<https://pexels.com/api> 注册获取

### 启动服务

```bash
cd web-platform
python server.py
```

访问 <http://localhost:8080> 即可使用。

## 项目结构

```
We-media-pipeline/
├── web-platform/           # Web 前端和后端服务
│   ├── index.html          # 前端页面
│   ├── server.py           # 后端 API 服务
│   └── 自媒体输出/          # 输出目录
├── news-search/            # 新闻搜索技能
├── image-search-baidu/     # 百度图片搜索技能
├── markdown-to-word/      # Markdown 转 Word 技能
└── wechat-video-generator/ # 视频生成技能
```

## 工作流程

1. 输入创作主题，选择时间范围
2. 自动搜索相关新闻资讯
3. 基于新闻生成公众号文章
4. 自动匹配主题配图
5. 导出 Word 文档
6. 生成短视频脚本并合成视频

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

