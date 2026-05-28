#!/usr/bin/env python3
"""
重新生成视频 - 读取同目录下的 05_content.json 生成视频
支持 Windows (Python 直接运行) 和 WSL (bash 窗口双击)
"""
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. 检测系统：Windows (nt) vs WSL/Linux (linux)
# ---------------------------------------------------------------------------
IS_WSL = sys.platform == "linux" and os.path.exists("/mnt/c/Users")
IS_WINDOWS = sys.platform == "win32" or (sys.platform == "linux" and not IS_WSL)

# WSL 下 stdin 可能是 pipe，导致 input() 直接返回。
# 尝试重定向到终端（如果失败则静默继续，不卡死）。
if IS_WSL:
    try:
        sys.stdin = open("/dev/tty", "r")
    except Exception:
        pass  # 无法打开终端就用原来的 stdin

def get_hermes_base():
    """在两个系统下都找到 .hermes 目录"""
    if IS_WSL:
        return Path("/mnt/c/Users/Administrator/.hermes")
    elif IS_WINDOWS:
        return Path.home() / ".hermes"
    else:
        for p in [Path.home() / ".hermes", Path("/mnt/c/Users/Administrator/.hermes")]:
            if p.exists():
                return p
        raise FileNotFoundError("找不到 .hermes 目录")

HERMES_BASE = get_hermes_base()
VIDEO_GENERATOR_SCRIPTS = HERMES_BASE / "skills" / "wechat-video-generator" / "scripts"

# ---------------------------------------------------------------------------
# 2. 当前项目目录（脚本所在目录）
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
CONTENT_JSON = SCRIPT_DIR / "05_content.json"
IMAGES_DIR = SCRIPT_DIR / "images_good"
OUTPUT_DIR = SCRIPT_DIR

# ---------------------------------------------------------------------------
# 3. 主逻辑
# ---------------------------------------------------------------------------
def main():
    print(f"[系统] {'WSL (Linux)' if IS_WSL else 'Windows'}")
    print(f"[Hermes] {HERMES_BASE}")
    print()

    if not CONTENT_JSON.exists():
        print(f"[ERROR] 找不到 content.json: {CONTENT_JSON}")
        input("按回车退出...")
        return 1

    images_dir = IMAGES_DIR
    if not images_dir.exists():
        images_dir = SCRIPT_DIR / "images-all"
        print(f"[WARN] images_good 不存在，使用 images-all: {images_dir}")

    if not VIDEO_GENERATOR_SCRIPTS.exists():
        print(f"[ERROR] 找不到 wechat-video-generator: {VIDEO_GENERATOR_SCRIPTS}")
        input("按回车退出...")
        return 1

    sys.path.insert(0, str(VIDEO_GENERATOR_SCRIPTS))
    from run_video_generator import generate_video

    import json
    with open(CONTENT_JSON, "r", encoding="utf-8") as f:
        content_data = json.load(f)

    main_title = content_data.get("main_title", "output")
    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in main_title).strip()
    safe_title = safe_title.replace(" ", "_")[:30]
    video_file = OUTPUT_DIR / f"06_{safe_title}.mp4"

    print(f"[重新生成视频]")
    print(f"  content.json: {CONTENT_JSON}")
    print(f"  images dir  : {images_dir}")
    print(f"  output video: {video_file}")
    print()

    result = generate_video(
        content_json=str(CONTENT_JSON),
        images_dir=str(images_dir),
        output_file=str(video_file)
    )

    if result.get("success") and os.path.exists(video_file):
        print(f"\n✅ 视频已生成: {video_file}")
    else:
        error_msg = result.get("error", "Unknown error")
        print(f"\n❌ 视频生成失败: {error_msg}")

    input("按回车退出...")
    return 0 if result.get("success") else 1

if __name__ == "__main__":
    sys.exit(main())
