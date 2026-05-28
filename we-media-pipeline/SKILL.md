---
name: we-media-pipeline
description: 微信公众号文章自动生成流程。协调7个技能完成从新闻搜索到Word文档、视频的完整流程：Step1新闻搜索→Step2生成文章→Step2.5去AI化(可选)→Step3配图→Step4导出Word→Step5生成content.json→Step6生成视频。支持配置文件管理API密钥，无需每次设置环境变量。
triggers:
  - "帮我写公众号文章"
  - "生成公众号文章"
  - "写一篇...文章"
  - "公众号文章生成"
---

# 微信公众号文章生成流程

**触发词**: "帮我写公众号文章"、"生成公众号文章"、"写一篇...文章"

协调7个技能，一键生成完整文章+视频。支持配置文件管理API密钥，无需每次设置环境变量。

## 执行流程

```
用户主题 → 搜索新闻 → 生成文章 → 搜索配图 → 导出Word → 生成content.json → 生成视频
```

---

## 快速开始

### 1. 配置API密钥（一次性）

编辑配置文件：`/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json`

```json
{
  "tavily_api_key": "tvly-xxxxxxxxxxxxxxxx",
  "minimax_api_key": "sk-cp-xxxxxxxxxxxxxxxx",
  "default_output_dir": "/mnt/e/Desktop/自媒体输出"
}
```

**实际输出路径**：`/mnt/e/Desktop/自媒体输出/`（注意是 `e:` 盘符，非 `c:` 盘的旧路径）

**获取API密钥：**
- **Tavily API Key**（新闻搜索）：https://tavily.com/ - 免费版每月1,000次调用
- **MiniMax API Key**（文章生成）：https://platform.minimaxi.com/ - MiniMax-M2.7 模型

**注意**：图片搜索已改用百度图片搜索，无需 Pexels API Key。

### 2. 检查配置

```bash
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py --check
```

### 3. 运行流程

```bash
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币"
```

---

## 详细步骤

### 步骤1：搜索新闻（news-searcher）

**调用技能**: `news-searcher`

**作用**: 搜索主题相关最新新闻

**输入**:
- 用户提供的主题
- Tavily API Key（从配置文件读取）

**输出**: `01_research.md`（新闻资料）

**成功标准**:
- 文件已保存
- 包含AI摘要
- 包含5-10篇新闻

---

### 步骤2：生成文章（article-writer）

**调用技能**: `article-writer`（内部实现调用 MiniMax LLM）

**作用**: 根据新闻资料生成微信风格文章

**重要**: **必须调用 MiniMax LLM 生成文章**，使用 `article-writer` 技能的完整规范作为 system prompt。禁止跳过此步骤或用手动 write_file 替代。

**实现方式**:
- 直接在 `step2_generate_article()` 函数内调用 MiniMax API（Anthropic SDK 兼容模式）
- 将 article-writer 技能的完整规范（references/style-guide.md）作为 system prompt 的一部分
- 不允许出现"暂停等待人工输入"的逻辑分支

**MiniMax API 调用方式**:
- Base URL: `https://api.minimaxi.com/anthropic`
- Model: `MiniMax-M2.7`
- 使用 `anthropic` Python SDK
- ⚠️ API Key 必须从 `config.json` 的 `minimax_api_key` 字段读取，**禁止硬编码**！运行时动态读取，禁止在代码里写死字符串。详见 `references/minimax-api-call.md`。

**输入**:
- 步骤1的新闻资料 (`01_research.md`)

**输出**: `02_article.md`（文章正文）

**成功标准**:
- 符合 article-writer 技能规定的风格要求
- 包含6个配图占位符 `[[IMG: 英文描述]]`
- **包含内容署名**（见下方结构要求）
- 1500-2500字

**文章头部必须包含以下三行（直接放在标题下方、正文上方）：**
```
内容编辑丨{署名}
内容审核丨{署名}

正文...
```
这三个元素是 Word 文档的标准署名格式，缺少则后续无法补回。

---

### 步骤2.5：文章去AI化（humanize-ai-text，可选）

**调用技能**: `humanize-ai-text`

**触发条件**: 使用 `--humanize` 参数

**作用**: 将步骤2生成的 AI 风格文章，去除 AI 写作特征，变得更像真人写的

**输入**:
- 步骤2的文章 (`02_article.md`)

**输出**: 覆盖 `02_article.md`（in-place）

**成功标准**:
- 文章保留原意，但语言更自然
- 去除：AI 高频词、促销语言、em dash 滥用、弯引号、chatbot 语气等

**使用方式**:
```bash
# 普通模式（自动修复弯引号/markdown/copula等）
python scripts/run_pipeline.py "主题" --humanize

# 激进模式（主动简化 -ing 分句，减少 em dash）
python scripts/run_pipeline.py "主题" --humanize --humanize-aggressive
```

**注意**: humanize 失败不会中断 pipeline，会继续使用原始文章。

---

### 步骤3：搜索配图（image-searcher）

**调用技能**: `image-searcher`

**作用**: 为文章配图（使用百度图片搜索）

**下载策略（两层文件夹）**:
- `images-all/` — 所有下载成功的图片（含低质量/无效），用于溯源全量保存，不删除
- `images_good/` — PIL 分辨率检查后 ≥800x600 的图片，供视频生成使用

**流程**:
1. 优先下载 Tavily 新闻图片（**达到30张即停**，避免大数量时耗时过长）
2. 新闻图片下载完后，用百度图片继续补充，同样以30张为上限

**图片数量上限**: `GOOD_TARGET = 30`，新闻图片阶段每下一张检查一次计数，达到30张立即停止；百度补充阶段同样以30张为上限。

**输入**:
- 步骤2的配图描述（中文）

**输出**: `images-all/` + `images_good/`

**成功标准**:
- 图片数量少时（<30张）：全部下载完成后再去百度补充
- 图片数量多时（≥30张）：达到30张即停止，无需等待全部下载
- **两层文件夹**：
  - `images-all/` — 所有下载成功的图片（含0x0等无效文件），用于溯源
  - `images_good/` — 只放分辨率 ≥800x600 的图片，供视频生成使用
- 图片与描述基本匹配

**注意**: 使用百度图片搜索，支持中文关键词，能搜到 Pexels 搜不到的国内内容、名人、品牌等。

---

### 步骤4：导出Word（article-formatter）

**调用技能**: `article-formatter`

**作用**: 生成Word文档

**输入**:
- 步骤2的文章
- 步骤3的配图

**输出**: `04_{标题}.docx`

**成功标准**:
- Word文档生成
- 图片已插入
- 表格格式正确

---

### 步骤5：生成content.json（article-shorter）

**调用技能**: `article-shorter`（内部实现调用 MiniMax LLM）

**作用**: 将步骤2生成的文章提炼为适合视频生成的 content.json

**重要**: **必须调用 MiniMax LLM 生成 content.json**，使用 `article-shorter` 技能的完整规范作为 system prompt。禁止跳过此步骤或用手动构造替代。

**实现方式**:
- 直接在 `step5_generate_content_json()` 函数内调用 MiniMax API（Anthropic SDK 兼容模式）
- 将 article-shorter 技能的规范作为 system prompt 的一部分
- 使用渐进切片扩展法解析 JSON（见下方 PITFALL）

**MiniMax API 调用方式**: 同步骤2。⚠️ **必须从 `config.json` 动态读取 API Key**，禁止硬编码占位符。详见 `references/minimax-api-call.md`。

**输入**:
- 步骤2的文章 (`02_article.md`)
- images_good 目录中的图片路径（自动填入 JSON 的 images 字段）

**输出**: `05_content.json`

**成功标准**:
- main_title ≤12字
- sub_title ≤15字
- text_sections 三段共约150字
- 语言流畅，按新闻报道口吻缩写
- images 字段自动填入 images_good 中的图片路径（前3张）

---

### 步骤6：生成视频（wechat-video-generator）

**调用技能**: `wechat-video-generator`

**作用**: 根据 content.json 生成短视频

**输入**:
- 步骤5的 content.json (`05_content.json`)
- 步骤3的配图 (`images_good/`)

**重要**: 视频生成使用 `images_good/` 目录（分辨率 ≥800x600），不是 `images-all/`。

**输出**: `06_{标题}.mp4`

**成功标准**:
- 视频文件生成
- 保存到与Word同一目录

**自动部署「重新生成视频.py」**：
Step 6 成功后，pipeline 会自动往项目目录复制一个 `重新生成视频.py`。用户可双击该脚本，或 `python 重新生成视频.py`，直接读取同级的 `05_content.json` 重新生成视频，无需每次喊助手。

**视频输出**：视频现在通过 `output_file` 参数直接写入项目目录（`wechat_video_generator.py` 从 `sys.argv[2]` 读取该路径），无需额外复制步骤。

**已知问题（根因在 wechat_video_generator.py 行118硬编码 WeChatVideo输出/）**：偶尔视频仍会输出到 `/mnt/c/Users/Administrator/Desktop/WeChatVideo输出/` 而非项目目录。Pipeline 层已实现 fallback 机制：在 `return False, None` 前搜索 WeChatVideo输出/ 目录，找到匹配标题的 .mp4 后复制到项目目录。如果 fallback 也未触发，可手动：
```bash
cp "/mnt/c/Users/Administrator/Desktop/WeChatVideo输出/06_{标题}.mp4" "/mnt/e/Desktop/自媒体输出/{项目}/06_{标题}.mp4"
```

---

## 输出文件

**输出目录**: `/mnt/e/Desktop/自媒体输出/`（pipeline 实际写入位置，非 config.json 中的旧路径）

**配置路径更新（重要）**: 如果发现输出到了 `E:\Desktop\自媒体输出\` 而非 `C:\OpenClaw生成文章\`，说明 `config.json` 的 `default_output_dir` 与实际不匹配。直接修改 `config.json` 中的路径为正确位置：
```json
{
  "default_output_dir": "/mnt/e/Desktop/自媒体输出"
}
```

**输出文件结构**:
```
{桌面}/{自媒体输出}/{YYYYMMDD_HHMMSS}_{主题}/
├── 01_research.md      # 新闻资料
├── 02_article.md       # 文章正文
├── 01_news_images.json # Tavily 返回的所有图片 URL
├── images-all/         # 所有下载成功的图片（含低质量/无效，不删除）
├── images_good/        # 分辨率≥800x600的图片（视频用）
├── 04_{标题}.docx      # Word文档（可直接编辑）
├── 05_content.json     # 视频内容配置
├── 06_{标题}.mp4        # 短视频（直接写入项目目录，非 WeChatVideo输出/）
└── 重新生成视频.py          # 微调content.json后双击重新生成视频
```

---

## 配置选项

### 配置文件位置（重要）

`~/.hermes/skills/we-media-pipeline/config.json`

**路径格式要求（必须使用 WSL/Linux 绝对路径）：**
```json
{
  "tavily_api_key": "tvly-xxxxxxxxxxxxxxxx",
  "minimax_api_key": "sk-cp-xxxxxxxxxxxxxxxx",
  "default_output_dir": "/mnt/c/Users/Administrator/Desktop/OpenClaw生成文章"
}
```

**禁止使用 Windows 路径格式**（`C:\\...` 或 `C:/...`），WSL Python 的 `os.path` 不认 Windows 格式，会被拼接成错误路径。

### 完整配置示例

```json
{
  "tavily_api_key": "tvly-xxxxxxxxxxxxxxxx",
  "minimax_api_key": "sk-cp-xxxxxxxxxxxxxxxx",
  "default_output_dir": "/mnt/c/Users/Administrator/Desktop/OpenClaw生成文章",
  "news_search": {
    "default_days": 7,
    "default_results": 10
  },
  "image_search": {
    "default_results": 6
  },
  "article": {
    "min_word_count": 1500,
    "max_word_count": 2500
  }
}
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `tavily_api_key` | string | "" | Tavily API密钥（新闻搜索） |
| `minimax_api_key` | string | "" | MiniMax API密钥（文章生成） |
| `default_output_dir` | string | `桌面/OpenClaw生成文章` | 默认输出目录 |
| `news_search.default_days` | int | 7 | 默认搜索天数 |
| `news_search.default_results` | int | 10 | 默认新闻数量 |
| `image_search.default_results` | int | 6 | 默认图片数量 |
| `article.min_word_count` | int | 1500 | 最小字数 |
| `article.max_word_count` | int | 2500 | 最大字数 |

---

## 使用示例

### 基本用法

```bash
# 生成关于比特币的文章
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币"

# 搜索最近30天的新闻
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --days 30

# 获取更多新闻结果
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --num-results 15

# 生成文章后自动去AI化
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --humanize
```

### 跳过特定步骤

```bash
# 跳过步骤1（已有新闻资料）
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --skip 1

# 跳过步骤2和3（已有文章和配图）
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --skip 2 3
```

### 断点续跑（重要）

**正确方式（已验证）**：
```bash
# ✅ 正确：只用 --skip，让 pipeline 搜索已有目录
python run_pipeline.py "google 2026 io" --skip 1 2 3
# pipeline 输出 📁 Using existing folder: 说明找到了正确目录
```

**错误方式（会导致嵌套子目录）**：
```bash
# ❌ 错误：--skip + --output 会导致 pipeline 在已有目录内再创建时间戳子目录
python run_pipeline.py "google 2026 io" --skip 1 2 3 --output "/path/to/existing"
```

**`--output` 的作用规则**：
- 指定了 `--output`：直接使用该路径（但与 `--skip` 合用会触发嵌套 bug）
- 指定了 `--skip` 且未指定 `--output`：**搜索同名已有文件夹**（推荐）
- 既没指定 `--output` 也没指定 `--skip`：创建新的时间戳子目录

### 检查配置

```bash
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py --check
```

输出示例：
```
API Key Configuration Status:
----------------------------------------
  ✓ Tavily: Configured (config.json)
  ✓ MiniMax: Configured (config.json)

Default output directory: /mnt/c/Users/Administrator/Desktop/OpenClaw生成文章
```

### 自定义输出目录

```bash
# 输出到指定目录（目录不存在会自动创建）
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --output "/mnt/c/Users/Administrator/Desktop/我的文章"

# 生成后自动打开文件夹
python ~/.hermes/skills/we-media-pipeline/scripts/run_pipeline.py "比特币" --open-folder
```

---

## 依赖技能

| 技能 | 类型 | 作用 |
|------|------|------|
| news-searcher | 脚本 | 搜索新闻 |
| article-writer | 指导 | 生成文章（MiniMax LLM） |
| image-searcher | 脚本 | 搜索配图（百度） |
| article-formatter | 脚本 | 导出Word |
| article-shorter | 指导 | 提炼content.json（MiniMax LLM） |
| wechat-video-generator | 脚本 | 生成短视频 |
| humanize-ai-text | 脚本 | 去AI化（可选） |

---

## 脚本参考

### `scripts/regen_video.py`

**用途**: 读取同级 `05_content.json` 生成视频（无需跑完整 pipeline）

**触发场景**: 用户对视频不满意，微调 `content.json` 后双击本脚本重新生成

**跨平台支持**: 自动检测 Windows / WSL / Linux 三种环境：
- **Windows** (`sys.platform == "win32"`): `Path.home() / ".hermes"`
- **WSL** (`sys.platform == "linux"` + `/mnt/c/Users` 存在): `/mnt/c/Users/Administrator/.hermes`
- **Linux** (非 WSL): `Path.home() / ".hermes"`

**WSL stdin 处理**: WSL 下双击运行或 `< /dev/null` 重定向会导致 `input()` 收到 EOF 静默退出。脚本自动将 stdin 绑回 `/dev/tty`，确保 `input("按回车退出...")` 在所有运行方式下都能正常等待。

**用法**:
```bash
# 在项目目录下
python 重新生成视频.py
# 或双击直接运行（视频生成完后按回车退出）
```

**特点**:
- 自动读取同目录 `05_content.json`
- 自动查找 `images_good/`（如不存在回退到 `images-all/`）
- 视频直接输出到脚本所在目录
- 末尾 `input()` 等待回车，方便查看结果后关闭

### `scripts/fix_minimax_api_key.py`

**用途**: 修复 `run_pipeline.py` 中 `step2` 和 `step5` 的 MiniMax API key 硬编码占位符问题（会导致 Step 5 持续报 `No JSON found`）

**触发场景**: Step 5 持续失败时，运行本脚本修复后再重跑 pipeline

**用法**:
```bash
python3 ~/.hermes/skills/we-media-pipeline/scripts/fix_minimax_api_key.py
```

**本脚本自动完成**:
1. 在 `config_loader.py` 中添加 `get_minimax_api_key()` 函数（config优先，fallback到 `MINIMAX_CN_API_KEY` env）
2. 更新 `run_pipeline.py` 的 import 语句
3. 替换两处硬编码 `api_key="sk-cp-...bQTw"` 为 `get_minimax_api_key()`
4. 验证修复后语法正确

### `scripts/run_pipeline.py`

**用途**: 运行完整文章生成流程

**脚本参数**:
- `topic` (必需): 文章主题
- `--type`: 内容类型（`news`默认 | `tutorial` | `product`），决定 Step 1 的搜索方式和查询组合：
  - `news`: 主搜索词 + 5个新闻查询变体 → Tavily
  - `tutorial`: 主搜索词 + GitHub/掘金教程查询 → Tavily
  - `product`: 主搜索词 + 少数派/知乎/B站产品评测查询 → Tavily
- `--days`: 搜索最近N天的新闻（默认：7）
- `--num-results`: 新闻结果数量（默认：10）
- `--skip`: 跳过的步骤编号（如：`--skip 2 3`）
- `--output, -o`: 自定义输出目录（指定后视为最终路径，不再搜索或嵌套）
- `--open-folder`: 生成后自动打开文件夹
- `--check`: 检查API密钥配置
- `--humanize`: 步骤2后调用 humanize-ai-text 去AI化文章
- `--humanize-aggressive`: 激进模式（简化-ing分句，减少em dash）

**示例**:
```bash
# 资讯类（默认）
python run_pipeline.py "DeepSeek降价"

# 教程类
python run_pipeline.py "Next.js教程" --type tutorial

# 产品类
python run_pipeline.py "MacBook评测" --type product
```

### `scripts/step1_sources.py`（已合并到 run_pipeline.py）

**已包含函数**:
- `step1_search_tutorial(topic, output_dir)` — 多查询聚合（GitHub/掘金等）
- `step1_search_product(topic, output_dir)` — 多查询聚合（少数派/知乎/B站等）

这些函数现已直接集成到 `run_pipeline.py` 中，无需额外导入。

### `scripts/config_loader.py`

**用途**: 配置加载工具

**用法**:
```python
import sys
sys.path.insert(0, '/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/scripts')
from config_loader import get_tavily_api_key, get_config_value

tavily_key = get_tavily_api_key()
# MiniMax API key: read directly from config.json via get_config_value("minimax_api_key")
import json
with open('/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json') as f:
    config = json.load(f)
    minimax_key = config.get('minimax_api_key', '')
```

---

## 参考文档

- `references/` — 已清理，文档内容已内置到 SKILL.md

## 关键提示

1. **主题不等于标题**: Pipeline 的 Step 2（article-writer）会从新闻资料中提取最有传播力的角度生成文章，标题往往比用户的原始主题更具体、更有看点。如用户输入"Google Workspace"，AI 可能生成的标题是"Google AI Ultra降价60%"。这是正常现象，说明AI在智能筛选新闻价值。不建议强行把文章拉回用户输入的字面主题。
2. **配置文件优先**: API密钥优先从config.json读取，其次才是环境变量
3. **步骤2必须调用 MiniMax LLM**: 不能手动write或使用其他方式生成文章
3. **断点续跑必须指定 `--output`**: 续跑时指定已有项目目录，避免创建新的时间戳子目录
4. **严格顺序**: 必须按1→2→2.5(可选)→3→4→5→6执行
5. **检查输出**: 每步完成后验证输出
6. **错误处理**: 任一步失败即停止（Step 2.5 除外，失败时继续）
7. **重新生成视频前必须先读 existing content.json**：用户说"重新生成视频"时，**必须先读取项目目录下的 `05_content.json`**，确认其内容后再生成。用户可能已自行修改过，不能假设是上次运行时的内容。

---

## PITFALL: `--skip` + `--output` 嵌套子目录问题

**现象**：`--skip 1 2 3 --output "/path/to/existing_project"` 时，pipeline 在已有目录内部又创建了新的时间戳子目录，导致步骤4找不到文章文件。

**根因**：`--skip` 的"搜索已有文件夹"逻辑与 `--output` 合用时，`output_dir` 被设为 `base_dir`，`find_existing_folder` 搜索到了自己，但随后仍创建了新的时间戳子目录。

**正确续跑方式**：只用 `--skip`，不用 `--output`：
```bash
# ✅ 正确：pipeline 会搜索到正确的已有目录
python run_pipeline.py "topic" --skip 1 2 3

# ❌ 错误：--output 触发嵌套子目录创建
python run_pipeline.py "topic" --skip 1 2 3 --output "/path/to/project"
```

---

## PITFALL: `regen_video.py` 在 WSL 下 stdin EOF 导致静默退出

**现象**: 双击 `重新生成视频.py` 或在 bash 里 `< /dev/null` 运行时，脚本打印几行后直接退出（exit 0），没有任何错误提示，看起来像是"用了老数据"。

**根因**: WSL 环境下 stdin 被重定向（pipe/EOF）时，`input()` 立即收到 EOF 并返回，脚本在视频生成完之前就已经退出了。generator 实际在后台继续运行，但结果用户看不到。

**修复**: `regen_video.py` 开头加 WSL 终端绑定：

```python
if IS_WSL:
    try:
        sys.stdin = open("/dev/tty", "r")
    except Exception:
        pass
```

**判断条件**: `sys.platform == "linux"` 且 `/mnt/c/Users` 存在 → WSL

---

## PITFALL: Step 3 超时但已有足够图片时的手动补救（已验证）

**现象**: Step 3 超时中断，但 `images_good/` 目录已积累 ≥3 张图片。

**关键经验（2026-05-27 验证）**：Step 3 超时时图片已下载到 `images_good/`（本次：7张）。无需等待 Step 3 完成，直接进入 Step 4-6。

**诊断**:
```bash
ls /mnt/e/Desktop/自媒体输出/{项目}/images_good/ | wc -l
```

**手动补救四步曲（Step 4→5→6，依次执行）**:

**Step 4 — 生成 Word**:
```bash
python3 ~/.hermes/skills/article-formatter/scripts/md_to_word.py \
  "/mnt/e/Desktop/自媒体输出/{项目}/02_article.md" \
  -i "/mnt/e/Desktop/自媒体输出/{项目}/images_good" \
  -o "/mnt/e/Desktop/自媒体输出/{项目}/04_标题.docx"
```

**Step 5 — 生成 content.json**（inline Python，已验证可行）:
```bash
cd /mnt/e/Desktop/自媒体输出/{项目} && python3 << 'PYEOF'
import json, anthropic, os

proj = "/mnt/e/Desktop/自媒体输出/{项目}"
with open(proj + "/02_article.md") as f:
    article = f.read()

with open("/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json") as f:
    api_key = json.load(f)["minimax_api_key"]

client = anthropic.Anthropic(base_url="https://api.minimaxi.com/anthropic", api_key=api_key)
msg = client.messages.create(
    model="MiniMax-M2.7", max_tokens=4096,
    system="""你是一个文章精简专家。输入文章后，直接输出JSON，不要任何解释文字。
输出格式：
{
  "main_title": "≤10字",
  "sub_title": "≤12字",
  "text_sections": ["第一段40-50字", "第二段40-50字", "第三段40-50字"],
  "short_article": "约300字的完整短文",
  "tags": ["标签1", "标签2", "标签3"],
  "outro_text": "关注 AI不够酷｜获取更多AI资讯"
}""",
    messages=[{"role":"user","content":f"请精简以下文章：\n\n{article}"}]
)
result = "".join(b.text for b in msg.content if b.type == "text")
content = json.loads(result)

# Auto-fill images from images_good (first 3, RELATIVE filenames!)
imgs = sorted([f for f in os.listdir(proj + "/images_good") if f.endswith((".jpg",".png",".webp"))])
content["images"] = [imgs[i] for i in range(min(3, len(imgs)))]

with open(proj + "/05_content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, ensure_ascii=False, indent=2)
print("Done:", content.get("main_title"))
PYEOF
```

**Step 6 — 生成视频**:
```bash
cd /mnt/e/Desktop/自媒体输出/{项目} && python3 /mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts/run_video_generator.py \
  "/mnt/e/Desktop/自媒体输出/{项目}/05_content.json" \
  "/mnt/e/Desktop/自媒体输出/{项目}/images_good" \
  "/mnt/e/Desktop/自媒体输出/{项目}/06_标题.mp4"
```
**部署重新生成脚本**:
```bash
cp ~/.hermes/skills/we-media-pipeline/scripts/regen_video.py \
   "/mnt/e/Desktop/自媒体输出/{项目}/重新生成视频.py"
```

**预防（永久修复）**: 修改 `image-searcher` 脚本内的 `GOOD_TARGET` 常量，从 30 改为 10：

```bash
# 找到并修改常量
grep -n "GOOD_TARGET" /mnt/c/Users/Administrator/.hermes/skills/image-searcher/scripts/search_baidu.py
# 输出类似：GOOD_TARGET = 30  ← 在第 N 行

# 用 sed 替换（避免手动编辑 CRLF 文件）
sed -i 's/GOOD_TARGET = 30/GOOD_TARGET = 10/' /mnt/c/Users/Administrator/.hermes/skills/image-searcher/scripts/search_baidu.py
```

**原理**: `GOOD_TARGET=10` 意味着每次百度搜索只需找到 10 张合格图片（宽≥800, 高≥600）即停止。百度返回的结果中约 30-40% 合格，2 轮搜索即可完成 Step 3，总耗时从 600s+ 降至约 60-90s。

## PITFALL: Step 3 百度图片下载文件位置异常

**现象**：`image-searcher` 脚本运行时打印了正确的输出目录 `输出目录：/mnt/c/.../images_good`，但 `ls` 检查时文件实际在 `/images_good/`（WSL 根目录），项目目录为空。

**诊断**:
```bash
ls -la /images_good/              # WSL 根目录——有文件说明下到这里了
ls -la /mnt/c/.../images_good/      # 项目目录——这里才是目标
```

**修复（立即执行）**:
```bash
# 将 WSL 根目录的文件迁移到项目目录
cp -r /images_good/. "/mnt/c/Users/Administrator/Desktop/OpenClaw生成文章/{项目目录}/images_good/"
```

**预防**：在项目目录内执行 python，不要用 `bash -c 'cd "$PROJECT" && python3 ...'` 跨目录链式调用。用 Python import 方式调用（见 Step 6 说明）。

---

## PITFALL: run_pipeline.py has HARDCODED placeholder API keys (CRITICAL — check before every run)

**NEVER trust the hardcoded `api_key=` values in `run_pipeline.py`** — during syntax-error repairs, they were accidentally replaced with placeholder strings `"sk-cp-...bQTw"` in BOTH `step2_generate_article()` (line ~402) AND `step5_generate_content_json()` (line ~1498). The real key MUST come from `config.json` via `get_config_value("minimax_api_key")`.

**Must-verify before any pipeline run:**
```bash
python3 -c "
import json
c = json.load(open('/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json'))
tav = c.get('tavily_api_key', '')
minimax = c.get('minimax_api_key', '')
tav_ok = 'YOUR' not in tav and len(tav) > 15
minimax_ok = 'YOUR' not in minimax and len(minimax) > 20
print('Tavily:', 'OK' if tav_ok else 'PLACEHOLDER: ' + tav)
print('MiniMax:', 'OK' if minimax_ok else 'PLACEHOLDER: ' + minimax)
if not minimax_ok:
    print()
    print('WARNING: MiniMax key is placeholder!')
    print('The run_pipeline.py api_key= lines may also have placeholder values.')
    print('REAL KEY IS IN: MINIMAX_CN_API_KEY env var (visible to hermes runtime, NOT to WSL env)')
"
```

**The fix — read MiniMax key from config.json in both step2 and step5:**
```python
import json as _json
_config_path = "/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json"
with open(_config_path) as _f:
    _cfg = _json.load(_f)
_minimax_key = _cfg.get("minimax_api_key", "")

client = anthropic.Anthropic(
    base_url="https://api.minimaxi.com/anthropic",
    api_key=_minimax_key,  # ← NOT hardcoded!
)
```

**Why it worked before**: The placeholder `"sk-cp-...bQTw"` was a masked display of the REAL key `MINIMAX_CN_API_KEY` from the Hermes `.env` file. The WSL Python process cannot see that env var — only the Hermes agent runtime can. When `run_pipeline.py` hardcodes the masked string, the API call fails silently (returns empty response → `No JSON found`).

## PITFALL: config.json contains placeholder API keys (CRITICAL — check before every run)

**Both `tavily_api_key` and `minimax_api_key` in `config.json` may be placeholder strings**, not real keys:

```bash
# Must-run check before ANY pipeline invocation:
python3 -c "
import json
c = json.load(open('/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json'))
tav = c.get('tavily_api_key', '')
minimax = c.get('minimax_api_key', '')
tav_ok = 'YOUR' not in tav and len(tav) > 15
minimax_ok = 'YOUR' not in minimax and len(minimax) > 20
print('Tavily:', 'OK' if tav_ok else 'PLACEHOLDER: ' + tav)
print('MiniMax:', 'OK' if minimax_ok else 'PLACEHOLDER: ' + minimax)
"
```

If either shows `PLACEHOLDER`, edit `config.json` and replace with real keys before running the pipeline.

Real key formats:
- Tavily: `tvly-` + 32 chars (get from tavily.com)
- MiniMax: `sk-cp-` + 32+ chars (get from platform.minimaxi.com)

**Where the real MiniMax key actually lives**: The real `MINIMAX_CN_API_KEY` is stored in `~/.hermes/.env` (Windows path: `C:\Users\Administrator\.hermes\.env`). This is the Hermes-native env var that the Hermes runtime uses. It is NOT visible to WSL Python `os.environ` — WSL sees only `MINIMAX_CN_API_KEY=***` (masked display). The `config.json` `minimax_api_key` field is meant to mirror this, but may contain a placeholder.

If Step 5 (`No JSON found in response:`) or Step 2 fails despite config showing "OK", the `run_pipeline.py` hardcoded key is likely the culprit — patch it to read from config.json per the fix above.

## PITFALL: `--skip` + `--output` always creates a new timestamped subdirectory (DO NOT USE together for resume)

**Verified 2026-05-21**: Even with the `--output` fix, running `--skip 1 2 3 4 --output /existing/project/` always creates a NEW timestamped subdirectory inside the provided path. The pipeline logic cannot reuse an existing directory when `--skip` is used.

**Correct resume approach for Step 5+6**:
1. Manually place `02_article.md` in the new subdirectory (pipeline creates it but it's empty)
2. Generate `content.json` via a standalone Python script (see `references/resume-step5-howto.md`)
3. Call `generate_video()` directly via Python (not via pipeline's `--skip`)

**Do NOT** try to use `--skip 1 2 3 4 --output /path/` to resume — it will create yet another subdirectory.

### Quick resume from Step 5 (copy-paste ready)

```python
# /tmp/resume_step5.py — generates content.json and video in the correct directory
import sys, json, anthropic
sys.path.insert(0, '/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts')
from run_video_generator import generate_video

PROJECT = '/mnt/c/Users/Administrator/Desktop/OpenClaw生成文章/20260521_142410_Android_16_Google_I_O_2026'
ARTICLE = PROJECT + '/02_article.md'

with open(ARTICLE) as f:
    article = f.read()

cfg_path = '/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json'
with open(cfg_path) as f:
    api_key = json.load(f)['minimax_api_key']

client = anthropic.Anthropic(base_url='https://api.minimaxi.com/anthropic', api_key=api_key)
msg = client.messages.create(
    model='MiniMax-M2.7', max_tokens=8192,
    system='你是一个文章精简专家...',  # use article-shorter system prompt
    messages=[{'role': 'user', 'content': f'请精简以下文章：\n\n{article}'}]
)
result = ''.join(b.text for b in msg.content if b.type == 'text')
# extract JSON from ```json code block if present...
content = json.loads(result)

# Auto-fill images from images_good (first 3 landscape images)
import os
imgs = sorted([f for f in os.listdir(PROJECT + '/images_good') if f.endswith(('.jpg','.png'))])
content['images'] = [PROJECT + '/images_good/' + imgs[i] for i in range(min(3, len(imgs)))]

with open(PROJECT + '/content.json', 'w', encoding='utf-8') as f:
    json.dump(content, f, ensure_ascii=False, indent=2)

# Generate video
generate_video(content_json=PROJECT+'/content.json', images_dir=PROJECT+'/images_good', output_file=PROJECT+'/video.mp4')
print('Done:', PROJECT)
```

**症状**：pipeline运行日志没有ERROR，步骤4显示 "skipped" 或直接消失，输出目录有 `01_research.md` + `02_article.md` 但没有 `04_*.docx`，且项目目录下有嵌套的 `YYYYMMDD_HHMMSS_topic/` 子目录（内容为空）。

**快速诊断命令**：
```bash
# 检查是否有嵌套子目录（bug信号）
ls /桌面/OpenClaw生成文章/{项目}/ | grep -E "^[0-9]{8}_[0-9]{6}"
# 检查是否缺少docx（确认已发生）
find /桌面/OpenClaw生成文章/{项目}/ -name "*.docx" -type f
```

**手动补救（无需重跑pipeline）**：
```bash
python3 ~/.hermes/skills/article-formatter/scripts/md_to_word.py \
  "/桌面/OpenClaw生成文章/{项目}/02_article.md" \
  -i "/桌面/OpenClaw生成文章/{项目}/images_good" \
  -o "/桌面/OpenClaw生成文章/{项目}/04_{标题}.docx"
```

## PITFALL: Editing Python source files — bare LF in string literals

**现象**: `SyntaxError: unterminated string literal` 报错，但对应行明明看起来正常（`print(f"...")` 完整闭合）。实际原因：f-string 或普通字符串中的 `\n` 被写成实际 LF 字节（0x0a）而非转义序列二字符 `\n`，Python 把一行拆成多行，导致引号配对错乱。

**受影响位置特征**: 通常是 `print()` 调用，表现为：
```
print(f"\n          ← 这里的 \n 是实际换行，引号在此行就闭合了
--- Downloading...  ← 变成了一条独立语句
")              ← 孤立的右括号
```

**修复方法**: 用 Python 脚本对原始字节做合并，不要用 shell heredoc 写含特殊字符的 Python 代码：
```python
# /tmp/fix_strings.py — 合并被拆分的 print 行
with open('run_pipeline.py', 'rb') as f:
    raw = f.read()
# 找到 \n--- 前面的 " 并将其与下一行合并
...
```

**预防**: 编辑 WSL 挂载的 Windows 文件时，避免用 echo/heredoc 重写含 `\n` 的 Python 代码。用 `write_file` 工具写 Python 修复脚本到 `/tmp/` 再执行。

**CRITICAL: WSL 挂载的 Windows 文件 + CRLF = heredoc 毒药**

WSL 下用 heredoc 写 Python 脚本到 `/mnt/c/...`（Windows 挂载目录）时，如果脚本包含字符串字面量（如 `print("...\n...")` 中的 `\n`），heredoc 会将 `\n` 转换成实际 LF（0x0a）。写入后文件实际为 CRLF（`\r\n` 换行），Python 读取时将 `\r\n` split 成多行，导致字符串被拆散，引号配对完全错乱。

**受影响的操作**:
- `cat > file.py << 'EOF' ... EOF`（heredoc）
- `python3 << 'PYEOF' ... PYEOF`（inline heredoc）
- 任何将含 `\n` 字符串的 Python 代码写入 CRLF 文件的方式

**绝对禁止**: 不要用 heredoc 方式向 WSL 挂载的 Windows 文件写入含转义字符的 Python 代码。

**安全写法**（任选其一）:
1. **写入 `/tmp/` 再 cp**：heredoc 写到 `/tmp/patch.py`，验证语法后 `cp /tmp/patch.py /mnt/c/.../script.py`
2. **用 write_file 工具**：直接写入，避免 heredoc 的编码问题
3. **用 Python import 注入**：在项目目录内用 `python3 -c "exec(open('/tmp/patch.py').read())"` 执行修复脚本，避免文件写入问题
4. **base64 中转**（最可靠）：将 Python 源码 base64 编码后传递，解码时不会有编码问题

**为什么这是「毒药」**：
- `/mnt/c/...` 是 Windows 文件系统，NTFS 默认 CRLF 换行
- heredoc 在 bash 中按 LF split， `\n` 作为二字符进入文件
- Python 读取时把 `\r\n` 当作两行（split by `\n`），字符串被切成碎片
- 看似「语法检查通过」，实际运行时才发现字符串字面量被拆散

**已验证安全的操作**:
- `python3 -m py_compile script.py` — 验证语法（不实际运行）
- `grep` / `wc -l` / `head` — 读文件不修改
- `cp` 已验证的备份文件 — 恢复用

## PITFALL: Modifying skill source files without asking

**现象**: 用户说"我明明没有让你修改视频技能，怎么这些信息会变化"。技能源码（`wechat_video_generator.py`、`run_pipeline.py` 等）在我自主调试过程中被悄悄修改了参数。

**原则**: 发现技能脚本有问题时，**先报告给用户，问是否要改**，再动手。不能因为"我在帮你调试"就默认拥有编辑权。

**例外**: 纯验证性操作（`grep`、`ast.parse`、`wc -l`）不算修改，可以先做。

## PITFALL: Editing scripts on WSL-mounted Windows filesystems

## PITFALL: Step 5 JSON parsing fails — Chinese curly/fancy quotes + truncated JSON

**现象**: Step 5 调用 MiniMax 生成 `content.json`，模型返回内容包含中文弯引号/括号（如 `""` `''`），或 JSON 被截断到 `{"main_title": "上周六，`，导致 `json.loads()` 失败。

**根因**: 两个问题——
1. MiniMax 输出含中文弯引号（`\u201c` `\u201d` 等），不是有效 JSON ASCII 字符
2. 非贪婪正则 `r'\{[\s\S]+?\}'` 遇到嵌套 `}` 时过早截断（如 `"text_sections": ["上周六，` 后遇到文章内的 `}` 就停了）

**已内置修复（run_pipeline.py 行1028-1036）**：Pipeline 的 Step 5 except 块现在包含多策略修复逻辑——
- 中文引号/括号 → ASCII
- 非贪婪截断修复（补全 `]}` 结尾）
- 换行符规范化
- 截断 JSON 补全（若文本在 `"...]` 处截断，尝试追加 `]}"}`）
- 重解析失败才最终放弃

**手动补救**（如果 pipeline 仍失败）:
```python
# /tmp/fix_step5.py
import json, re, os

proj = "/mnt/e/Desktop/自媒体输出/{项目}"
raw = open(f"{proj}/05_content.json").read()

def fix_json(text):
    # 弯引号→ASCII
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u300c', '"').replace('\u300d', '"')
    # 截断修复
    if text.count('[') > text.count(']'):
        text = text.rstrip() + ']}'
    return text

content = json.loads(fix_json(raw))
imgs = sorted([f for f in os.listdir(f"{proj}/images_good") if f.endswith(('.jpg','png'))])[:3]
content['images'] = imgs

with open(f"{proj}/05_content.json", "w", encoding="utf-8") as f:
    json.dump(content, f, ensure_ascii=False, indent=2)
print("OK:", content.get("main_title"))
```

**images 字段格式（重要）**：必须使用**相对文件名**，不是绝对路径：
- ✅ `"baidu_01_800x866.jpg"` — 正确（相对于 `images_dir`）
- ❌ `"/mnt/e/Desktop/.../baidu_01_800x866.jpg"` — 错误（视频生成器会错误拼接成双倍路径）

---

## PITFALL: `timeout` exits 0 with no output = silent Tavily failure (no results)

**现象**: `timeout N python3 run_pipeline.py "主题" --type news` 返回 exit code 0，无任何错误，但输出目录没有新文件或新目录。

**根因**: Tavily 搜索返回 0 结果时，pipeline 的 `step1_dispatch` 没有报错，只是静默返回。`--type news` 的 dispatcher 分派正确（已验证），但搜索 query 在 Tavily 那边没有匹配到任何新闻，导致没有任何产物被创建。Step 6 的视频生成也静默跳过（无 content.json 可用）。

**诊断**:
```bash
# 检查是否创建了输出目录
ls -la /mnt/e/Desktop/自媒体输出/ | grep DeepSeek

# 直接测试 Tavily API
python3 -c "
import requests, json
resp = requests.get('https://api.tavily.com/search', params={
    'api_key': open('/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json').read(),
    'query': 'DeepSeek降价',
    'max_results': 5
})
print(resp.json())
"
```

**修复**: 如果 Tavily 无结果，换用 `--type tutorial` 或 `--type product` 测试搜索路径；或用 `--days 30` 扩大搜索范围。

---

## PITFALL: Editing scripts on WSL-mounted Windows filesystems

Scripts in this pipeline (e.g., `run_pipeline.py`) live on a Windows filesystem mounted in WSL (`/mnt/c/...`). The `patch` tool in Hermes fails post-write verification due to CRLF line endings.

详见 `pipeline-tech-notes.md` 中的 **CRITICAL BUG: Hardcoded API Key Placeholder**。

## PITFALL: `py_compile` fails but `ast.parse` + `exec()` succeed = stale bytecode cache

**现象**: `python3 -m py_compile script.py` 报错 `SyntaxError: unterminated string literal`，但 `ast.parse(src)` 和 `tokenize.tokenize()` 都成功——三者的结果互相矛盾。

**根因**: Python 缓存了 `.pyc` 字节码文件（来自更早的损坏版本），`py_compile` 验证的是缓存而非当前源文件。`ast.parse` 直接解析内存中的 `src` 字符串，`exec()` 同理，所以它们看到的是干净的当前文件。

**诊断**:
```python
import ast, py_compile, tokenize
with open('script.py', 'rb') as f:
    src = f.read()
print('ast.parse:', ast.parse(src) and 'OK')
print('tokenize:', list(tokenize.tokenize(src)) and 'OK')
try:
    py_compile.compile('script.py', doraise=True)
    print('py_compile: OK')
except py_compile.PyCompileError as e:
    print('py_compile: FAILED (stale cache likely)')
```

**修复**: 删除所有 `__pycache__/` 和 `*.pyc` 文件，然后重试：
```bash
find /path/to/skill/scripts/ -name "*.pyc" -delete
find /path/to/skill/scripts/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
python3 -B -m py_compile /path/to/script.py && echo "Syntax OK"
```

**注意**: `python3 -B`（不生成 `.pyc`）和 `find ... -delete`（精确删除）比 `rm -rf __pycache__` 更安全，不会误删其他文件。

---

## PITFALL: Multi-line print() f-strings on CRLF-split files — merging pitfall

**现象**: `print(f"line1\nline2")` 在 CRLF 文件中被拆成物理行 903+904，合并时容易产生双右括号 `'))'` 或错误的 `\n` 转义。

**修复原则**: 用 `b'\n'`（实际换行符）而非 `b'\\n'`（转义序列）来定位，然后用 `raw.replace(seq, merged)` 一次性替换。合并后的 f-string 单行必须有正确的闭合括号和引号。

**验证正确性**: 合并后检查 `b"')" in lines[913]` — 如果只有单引号+右括号才是正确的；如果出现 `'))` 则合并过度了。

**绝对禁止**: 不要用 `re.sub(r'print\(f"\\n', ...)` 之类基于转义字符的替换——CRLF-split 文件里 `\\n` 是两个真实字符（反斜杠+n），不是换行符。只能用字节序查找和替换。

---

## PITFALL: `timeout` 命令超时返回 124，但 pipeline 子进程在后台继续完成

**现象**：`timeout 600 python3 run_pipeline.py ...` 返回 exit code 124（超时），终端无进一步输出，但后续检查发现 Steps 4 & 5 已完成（Word、content.json 均存在），唯独 Step 6 未运行（无 .mp4）。

**根因**：`timeout` 命令超时后强制杀死主进程，但 Python 的 pipeline 在被 SIGTERM 杀死前已通过多线程启动了子步骤，步骤4和5写入文件后，步骤6的视频生成未触发。

**诊断命令**：
```bash
ls /path/to/project/*.mp4 2>/dev/null && echo "Step 6 OK" || echo "Step 6 未运行"
ls /path/to/project/04_*.docx /path/to/project/05_content.json 2>/dev/null
```

**修复**：如果 docx 和 content.json 存在但无 .mp4，直接手动运行 Step 6：
```bash
python3 /mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts/run_video_generator.py \
  "/path/to/project/05_content.json" \
  "/path/to/project/images_good" \
  "/path/to/project/06_标题.mp4"
```

**预防**：遇到 timeout 时先检查中间产物是否已存在，再决定补跑哪些步骤。

---

## PITFALL: `~/.hermes/skills/` 在 WSL 终端里展开为 `/root/.hermes/`

**现象**：执行 `python3 ~/.hermes/skills/.../run_pipeline.py` 报 `No such file or directory`，但 `skill_view` 能正常找到技能。

**根因**：WSL bash 中 `~` 展开为 `/root`，而实际技能在 Windows 用户目录：`/mnt/c/Users/Administrator/.hermes/skills/`。

**修复**：始终用完整路径。`skill_view` 返回的 `skill_dir` 就是正确路径，直接用。

---

## PITFALL: run_pipeline.py MiniMax API key hardcoded bug (CRITICAL)

**Symptom**: Step 5 (content.json) consistently fails with `✗ No JSON found in response:` — empty LLM response. Step 2 (article generation) may appear to succeed.

**Root Cause**: During syntax-error repairs on `run_pipeline.py`, the `api_key=` parameter in BOTH `step2_generate_article()` (~line 402) and `step5_generate_content_json()` (~line 1498) was accidentally replaced with the placeholder string `"sk-cp-...bQTw"`. This is NOT a valid API key — it is a masked display of the real key stored in `MINIMAX_CN_API_KEY` in `~/.hermes/.env`. WSL Python cannot read the real key from `.env` (it sees `***`), so when the hardcoded placeholder is used, the API call fails.

**Fix (two places in run_pipeline.py)**:

Replace BOTH occurrences of:
```python
client = anthropic.Anthropic(
    base_url="https://api.minimaxi.com/anthropic",
    api_key="sk-cp-...bQTw",   # ← REMOVE THIS HARDCODE
)
```

With:
```python
import json as _json
_config_path = "/mnt/c/Users/Administrator/.hermes/skills/we-media-pipeline/config.json"
with open(_config_path) as _f:
    _cfg = _json.load(_f)
_minimax_key = _cfg.get("minimax_api_key", "")
# Safety check
assert "YOUR" not in _minimax_key and len(_minimax_key) > 20, \
    f"FATAL: config.json minimax_api_key is a placeholder: {_minimax_key!r}"

client = anthropic.Anthropic(
    base_url="https://api.minimaxi.com/anthropic",
    api_key=_minimax_key,   # ← Read from config
)
```

**Also update `config_loader.py`** to include `get_minimax_api_key()`:

```python
def get_minimax_api_key():
    """Get MiniMax API key. Priority: config.json > environment variable."""
    config = load_config()
    api_key = config.get('minimax_api_key', '').strip()
    if api_key and 'YOUR' not in api_key:
        return api_key
    return os.environ.get('MINIMAX_CN_API_KEY')
```

**And update the `run_pipeline.py` imports** to include `get_minimax_api_key`:
```python
from config_loader import get_tavily_api_key, get_config_value, check_api_keys, get_minimax_api_key
```

Then replace both hardcoded `api_key=` usages with `get_minimax_api_key()`.

**Why this matters**: Even if config.json has a placeholder, the real key is in `MINIMAX_CN_API_KEY` in `.hermes/.env`. The `get_minimax_api_key()` fallback chain (config → env) ensures the real key is found regardless of config.json state.

---

## 已知限制

- **Step 3 图片下载超时**：229张图片在600s内只下完161张，之后反复重试也会卡在同一张图片（scientificamerican.com 下载极慢）。处理方式：跳过 Step 3 直接继续后续步骤（已有足够高质量图片生成视频）。
- **Step 5 LLM JSON 输出截断或为空**：详见 `references/content-json-fallback.md`（含已验证的补救模板）
- **Step 2.5 humanize 行为**：headers、attribution lines、bold、code blocks 全部保留；仅删除 chatbot 语气句（`I hope this helps`等）和替换 AI 高频词（`serves as a` → `is a`）。
- **`--skip` 不支持小数步**：pipeline 的 `--skip` 参数只接受整数，无法用 `--skip 2.5` 跳过 Step 2.5。如需跳过 humanize，用 `python md_to_word.py` 单独生成 Word；如需跳过 Step 2，保留 Step 2 的输出文件即可自动识别已存在。
- **Step3 创建目录名为 `images_good`（下划线）**，早期版本曾使用 `images-good`（连字符）。如发现目录是 `images-good`，手动改为 `images_good` 后继续。Step5 有 auto-create 逻辑：如果 `images_good` 不存在，会自动从 `images-all` 复制文件。
- **视频整体发暗发虚**：本质是 `yuv444p` 色彩空间在平台二次转码时不兼容导致偏色。当前 wechat-video-generator 已统一改为 `yuv420p` + `medium` 预设，CRF=0（最高质量），兼容性等同于剪映默认输出。

---

## 已知限制

### API密钥未配置

```
✗ Error: Tavily API key not configured
✗ Error: MiniMax API key not configured
```

**解决**: 编辑config.json添加密钥

### 模块导入失败

```
✗ Error: Could not import news-searcher module
```

**解决**: 确保依赖技能已安装且路径正确

### 网络错误

```
✗ Search failed: Connection timeout
```

**解决**: 检查网络连接，或稍后重试

### 步骤4找不到文章文件（No such file or directory）

**现象**: `✗ Failed to create Word document: [Errno 2] No such file or directory: '.../02_article.md'`

**原因**: `--skip` + `--output` 组合导致 pipeline 在错误位置创建了新的时间戳子目录，实际文章文件在 `--output` 指定的目录中。

**解决**: 确认文章文件实际位置，用 `--output` 指向正确目录，或直接用 `--skip` 搜索已有文件夹（不指定 `--output`）。
