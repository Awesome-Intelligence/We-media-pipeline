"""Unit tests for config_loader module."""
import os
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))


def test_get_platform():
    """Test platform detection."""
    from config_loader import get_platform
    platform = get_platform()
    assert platform in ['windows', 'linux', 'darwin', 'unknown'], f"Invalid platform: {platform}"


def test_get_desktop_dir():
    """Test desktop directory detection."""
    from config_loader import get_desktop_dir
    desktop = get_desktop_dir()
    assert desktop, "Desktop directory should not be empty"
    assert isinstance(desktop, str), "Desktop directory should be a string"


def test_get_default_output_dir():
    """Test default output directory."""
    from config_loader import get_default_output_dir
    output_dir = get_default_output_dir()
    assert output_dir, "Default output directory should not be empty"


def test_project_config_loading():
    """Test loading project config."""
    from config_loader import load_project_config
    config = load_project_config()
    assert isinstance(config, dict), "Config should be a dictionary"


def test_get_config_value_with_nested_keys():
    """Test nested config value retrieval."""
    from config_loader import get_config_value

    result = get_config_value('image_search.default_results', default=6)
    assert result is not None


def test_get_tavily_api_key():
    """Test Tavily API key retrieval."""
    from config_loader import get_tavily_api_key
    key = get_tavily_api_key()
    assert key is None or isinstance(key, str), "API key should be None or string"


def test_get_image_search_engine():
    """Test image search engine config."""
    from config_loader import get_image_search_engine
    engine = get_image_search_engine()
    assert engine in ['baidu', 'pexels'], f"Invalid search engine: {engine}"


def test_load_skill_config():
    """Test loading skill-specific config."""
    from config_loader import load_skill_config
    config = load_skill_config('image-searcher')
    assert isinstance(config, dict), "Skill config should be a dictionary"


if __name__ == '__main__':
    test_get_platform()
    test_get_desktop_dir()
    test_get_default_output_dir()
    test_project_config_loading()
    test_get_config_value_with_nested_keys()
    test_get_tavily_api_key()
    test_get_image_search_engine()
    test_load_skill_config()
    print("All config_loader tests passed!")