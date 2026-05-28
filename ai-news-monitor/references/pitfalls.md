# AI News Monitor - 已知问题

## WSL 下 `Path.home()` 返回 `/root` 而非 Windows 桌面路径

**问题**：`fetch_ai_news.py` 使用 `Path.home() / 'Desktop' / 'AI资讯'` 作为默认输出目录。在 WSL 环境下，`Path.home()` 返回 `/root`，导致文件写到 `/root/Desktop/AI资讯/`（不存在），而非预期的 `/mnt/c/Users/Administrator/Desktop/AI资讯/`。

**现象**：脚本打印 "✅ 简报已保存"，但文件实际未写入目标目录。

**修复**：在 `fetch_ai_news.py` 开头新增 `get_desktop_dir()` 函数，优先检测 WSL 环境并硬编码 Administrator Desktop 路径：

```python
def get_desktop_dir():
    if os.path.exists('/mnt/c/Users/Administrator'):
        return Path('/mnt/c/Users/Administrator/Desktop')
    return Path.home() / 'Desktop'
```

## `~` 路径未展开

**问题**：`config.json` 中的 `output_dir` 字段值为 `~/Desktop/AI资讯`，Python 的 `pathlib.Path` 不会自动展开 `~`。

**现象**：配置文件设置了 output_dir，但脚本仍然写到错误位置。

**修复**：直接写入完整路径到 config.json，不再依赖 `~` 展开。

## 调用 pipeline 密钥的正确方式

直接用 `subprocess.run(..., env={'TAVILY_API_KEY': key})` 传入密钥，但 shell 变量引用（如 `"$KEY"`）在 WSL bash 中会报 EOF 错误。

**修复**：用 Python 读取密钥，通过 `subprocess.run` 的 `env` 参数传入环境变量：

```python
import json, subprocess, os
with open('config.json') as f:
    key = json.load(f)['tavily_api_key']
subprocess.run(
    ['python3', 'fetch_ai_news.py'],
    env={**os.environ, 'TAVILY_API_KEY': key}
)
```
