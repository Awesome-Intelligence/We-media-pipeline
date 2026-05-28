# WSL / Windows 双环境下 Hermes 的路径问题

## 问题现象

在 WSL bash 里运行 `hermes` 命令报 `command not found`，即使 Windows PATH 里明确有它。

```
$ which hermes
# WSL: nothing

$ where.exe hermes 2>/dev/null
C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Scripts\hermes.exe
C:\Users\Administrator\miniconda3\Scripts\hermes.exe
```

## 根因

Hermes Agent 安装在 Windows 环境（`C:\Users\Administrator\miniconda3\Scripts\hermes.exe`），WSL 是独立的 Linux 子系统，WSL bash 的 `$PATH` 不包含 Windows 路径。

## 正确做法

用 Windows 完整路径调用：

```bash
"/mnt/c/Users/Administrator/miniconda3/Scripts/hermes.exe" config show
"/mnt/c/Users/Administrator/miniconda3/Scripts/hermes.exe" config set <key> <value>
```

## 配置文件位置（Windows）

- Config: `C:\Users\Administrator\.hermes\config.yaml`
- Secrets: `C:\Users\Administrator\.hermes\.env`

## 相关发现（2026-05-19）

- `config.yaml` 中 `platforms: {}` 是空的，没有配置任何 messaging platform
- 可用 platform section：`telegram`, `discord`, `slack`, `whatsapp`, `mattermost`, `matrix`
- 没有看到 wechat 专用 section，用户提到的"channel 配置"可能是在别处或旧版功能
