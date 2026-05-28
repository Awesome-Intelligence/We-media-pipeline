#!/usr/bin/env python3
"""
Shared configuration loader for We-media-pipeline.

This module provides a centralized configuration loading mechanism that:
1. Supports standalone skill usage (skills can work independently)
2. Respects project-level config when running within the pipeline
3. Falls back to environment variables and skill-local configs

Priority order:
  1. Project config (project_root/config.json)
  2. Environment variables
  3. Skill-local config (skill_dir/config.json)
  4. Default values
"""

import os
import sys
import json
from pathlib import Path


def get_platform():
    """Get current platform: 'windows', 'linux', or 'darwin' (macOS)."""
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform == 'darwin':
        return 'darwin'
    return 'unknown'


def get_desktop_dir():
    """
    Get the desktop directory for the current platform.
    
    Windows: C:\\Users\\{username}\\Desktop
    macOS: ~/Desktop
    Linux: ~/Desktop (or ~/桌面 on some distros)
    """
    home = Path.home()
    
    if get_platform() == 'windows':
        desktop = home / 'Desktop'
        if not desktop.exists():
            desktop = home / '桌面'
    elif get_platform() == 'darwin':
        desktop = home / 'Desktop'
    else:
        desktop = home / 'Desktop'
        if not desktop.exists():
            desktop = home / '桌面'
        if not desktop.exists():
            desktop = home
    
    return str(desktop.resolve())


def get_default_output_dir():
    """Get default output directory from project config, or auto-detect desktop."""
    output_dir = get_config_value('default_output_dir')
    if output_dir and str(output_dir).strip():
        return output_dir
    
    return os.path.join(get_desktop_dir(), 'OpenClaw生成文章')


def get_project_root():
    """Get the project root directory (where config.json is located)."""
    return Path(__file__).parent.parent.resolve()


def get_skill_dir(skill_name=None):
    """Get the skill directory. If skill_name is None, returns this file's parent directory."""
    if skill_name is None:
        return Path(__file__).parent.parent.resolve()
    return get_project_root() / skill_name


def load_project_config():
    """Load configuration from project root config.json."""
    config_path = get_project_root() / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_skill_config(skill_name):
    """Load configuration from skill-local config.json."""
    skill_dir = get_skill_dir(skill_name)
    config_path = skill_dir / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_config_value(key, default=None, skill_name=None):
    """
    Get a configuration value by key with fallback chain.
    
    Priority:
      1. Project config
      2. Environment variable (uppercase key with underscores)
      3. Skill-local config
      4. Default value
    
    Args:
        key: Configuration key (supports dot notation for nested values, e.g., 'news_search.default_days')
        default: Default value if key not found
        skill_name: If provided, also checks skill-local config
    
    Returns:
        The configuration value or default
    """
    project_config = load_project_config()
    keys = key.split('.')
    
    value = project_config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            value = None
            break
    
    if value is not None:
        return value
    
    env_key = key.upper().replace('.', '_')
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value
    
    if skill_name:
        skill_config = load_skill_config(skill_name)
        value = skill_config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                value = None
                break
        if value is not None:
            return value
    
    return default


def get_tavily_api_key():
    """Get Tavily API key with priority: project config > env var > skill config."""
    key = get_config_value('tavily_api_key', skill_name='news-searcher')
    if key:
        return key
    return os.environ.get('TAVILY_API_KEY')


def get_minimax_api_key():
    """Get MiniMax API key with priority: project config > env var."""
    return get_config_value('minimax_api_key') or os.environ.get('MINIMAX_API_KEY')


def get_pexels_api_key():
    """Get Pexels API key with priority: project config > env var."""
    return get_config_value('pexels_api_key') or os.environ.get('PEXELS_API_KEY')


def get_news_default_days():
    """Get default days for news search."""
    return get_config_value('news_search.default_days', 7, skill_name='news-searcher')


def get_news_default_results():
    """Get default results count for news search."""
    return get_config_value('news_search.default_results', 10, skill_name='news-searcher')


def get_image_default_results():
    """Get default results count for image search."""
    return get_config_value('image_search.default_results', 6, skill_name='image-searcher')


def get_image_min_width():
    """Get minimum image width for filtering."""
    return get_config_value('image_search.min_width', 800, skill_name='image-searcher')


def get_image_min_height():
    """Get minimum image height for filtering."""
    return get_config_value('image_search.min_height', 600, skill_name='image-searcher')


def get_image_search_engine():
    """Get preferred image search engine ('baidu' or 'pexels')."""
    return get_config_value('image_search.search_engine', 'baidu', skill_name='image-searcher')


def get_style_dir():
    """
    Get the style directory for article-fetcher to save learned styles.
    
    Priority:
      1. Project config (style_dir)
      2. article-fetcher local config
      3. Default: {project_root}/styles
    
    Returns:
        str: Absolute path to style directory
    """
    style_dir = get_config_value('style_dir', skill_name='article-fetcher')
    if style_dir and str(style_dir).strip():
        path = Path(style_dir)
        if not path.is_absolute():
            path = get_project_root() / style_dir
        return str(path.resolve())
    
    return str(get_project_root() / 'styles')


def get_style_path(topic):
    """
    Get the style.md path for a specific topic.
    
    Args:
        topic: Topic name
    
    Returns:
        str: Absolute path to style.md file
    """
    style_dir = get_style_dir()
    topic_dir = os.path.join(style_dir, topic)
    return os.path.join(topic_dir, 'style.md')


def check_required_apis():
    """Check which API keys are configured."""
    return {
        'tavily': bool(get_tavily_api_key()),
        'minimax': bool(get_minimax_api_key()),
        'pexels': bool(get_pexels_api_key()),
    }


def print_config_status():
    """Print current configuration status."""
    status = check_required_apis()
    project_root = get_project_root()
    
    print("=" * 60)
    print("We-media-pipeline Configuration Status")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print(f"Config file: {project_root / 'config.json'}")
    print()
    
    print("API Keys:")
    for api, configured in status.items():
        icon = "✓" if configured else "✗"
        name = api.capitalize()
        print(f"  {icon} {name}: {'Configured' if configured else 'Not configured'}")
    
    print()
    print("Default Settings:")
    print(f"  News days: {get_news_default_days()}")
    print(f"  News results: {get_news_default_results()}")
    print(f"  Image results: {get_image_default_results()}")
    print(f"  Image min size: {get_image_min_width()}x{get_image_min_height()}")
    print(f"  Image search engine: {get_image_search_engine()}")
    print(f"  Output dir: {get_default_output_dir()}")
    print("=" * 60)


if __name__ == '__main__':
    print_config_status()