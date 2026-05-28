#!/usr/bin/env python3
"""
Configuration loader for we-media-pipeline.

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

import json
import os
import sys
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


def get_project_root():
    """Get the project root directory (where config.json is located)."""
    script_dir = Path(__file__).parent.absolute()
    return script_dir.parent.parent.resolve()


def get_skill_dir():
    """Get the pipeline skill directory."""
    script_dir = Path(__file__).parent.absolute()
    return script_dir.parent.absolute()


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


def load_skill_config():
    """Load configuration from skill-local config.json."""
    config_path = get_skill_dir() / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_config():
    """
    Load configuration with priority: project config > skill config.
    
    Returns:
        dict: Merged configuration dictionary
    """
    config = load_skill_config()
    project_config = load_project_config()
    
    for key, value in project_config.items():
        if value and str(value).strip():
            config[key] = value
    
    return config


def get_tavily_api_key():
    """
    Get Tavily API key.
    Priority: project config > skill config > environment variable
    
    Returns:
        str: API key or None if not found
    """
    config = load_config()
    api_key = config.get('tavily_api_key', '').strip()
    if api_key:
        return api_key
    
    return os.environ.get('TAVILY_API_KEY')


def get_minimax_api_key():
    """
    Get MiniMax API key.
    Priority: project config > environment variable
    
    Returns:
        str: API key or None if not found
    """
    config = load_config()
    api_key = config.get('minimax_api_key', '').strip()
    if api_key:
        return api_key
    
    return os.environ.get('MINIMAX_API_KEY')


def get_pexels_api_key():
    """
    Get Pexels API key.
    Priority: project config > skill config > environment variable
    
    Returns:
        str: API key or None if not found
    """
    config = load_config()
    api_key = config.get('pexels_api_key', '').strip()
    if api_key:
        return api_key
    
    return os.environ.get('PEXELS_API_KEY')


def get_default_output_dir():
    """
    Get default output directory.
    Priority: project config > skill config > auto-detect desktop.
    """
    config = load_config()
    output_dir = config.get('default_output_dir', '').strip()
    if output_dir:
        return output_dir
    
    return os.path.join(get_desktop_dir(), 'OpenClaw生成文章')


def get_config_value(key, default=None):
    """
    Get a configuration value by key.
    Supports nested keys with dot notation (e.g., 'news_search.default_days')
    
    Args:
        key: Configuration key (supports dot notation for nested values)
        default: Default value if key not found
    
    Returns:
        The configuration value or default
    """
    config = load_config()
    
    keys = key.split('.')
    value = config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value if value is not None else default


def check_api_keys():
    """
    Check if required API keys are configured.
    
    Returns:
        dict: Status of each API key
    """
    tavily_key = get_tavily_api_key()
    minimax_key = get_minimax_api_key()
    
    return {
        'tavily': {
            'configured': bool(tavily_key),
        },
        'minimax': {
            'configured': bool(minimax_key),
        }
    }


def print_api_status():
    """Print API key configuration status."""
    status = check_api_keys()
    project_root = get_project_root()
    
    print("=" * 60)
    print("We-Media-Pipeline Configuration Status")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print(f"Config file: {project_root / 'config.json'}")
    print()
    
    for api, info in status.items():
        status_icon = "✓" if info['configured'] else "✗"
        name = api.capitalize()
        print(f"  {status_icon} {name}: {'Configured' if info['configured'] else 'Not configured'}")
    
    print()
    print("Configure API keys in one of:")
    print("  1. Project config.json (recommended): config.json")
    print("  2. Environment variable")
    print("=" * 60)


if __name__ == '__main__':
    print_api_status()