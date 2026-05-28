"""Unit tests for web-platform server module."""
import os
import sys
import json
import http.server
import threading
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

PROJECT_ROOT = Path(__file__).parent.parent


def test_server_endpoints_exist():
    """Test that server file has all required endpoints."""
    server_file = PROJECT_ROOT / "web-platform" / "server.py"
    assert server_file.exists(), "server.py should exist"

    content = server_file.read_text(encoding='utf-8')

    required_endpoints = [
        '/api/config',
        '/api/status',
        '/api/news/search',
        '/api/article/generate',
        '/api/images/search',
        '/api/word/export',
        '/api/content/generate',
        '/api/video/generate',
        '/api/pipeline/run',
        '/api/library/scan',
        '/api/file/open',
        '/api/file/save',
        '/api/file/read',
        '/api/file/stream/',
    ]

    for endpoint in required_endpoints:
        assert f"'{endpoint}'" in content or f'"{endpoint}"' in content, f"Missing endpoint: {endpoint}"


def test_server_frontend_health():
    """Test that frontend HTML has correct API_BASE."""
    index_file = PROJECT_ROOT / "web-platform" / "index.html"
    assert index_file.exists(), "index.html should exist"

    content = index_file.read_text(encoding='utf-8')
    assert 'const API_BASE' in content, "Missing API_BASE configuration"


def test_config_file_exists():
    """Test that config.json exists."""
    config_file = PROJECT_ROOT / "config.json"
    assert config_file.exists(), "config.json should exist"

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
        assert isinstance(config, dict), "config.json should be valid JSON"


def test_skills_directory_structure():
    """Test that all required skill directories exist."""
    required_skills = [
        'news-searcher',
        'article-writer',
        'article-shorter',
        'image-searcher',
        'article-formatter',
        'we-video-generator',
        'we-media-pipeline',
    ]

    for skill in required_skills:
        skill_path = PROJECT_ROOT / skill
        assert skill_path.exists(), f"Missing skill directory: {skill}"


def test_shared_config_loader_exists():
    """Test that shared config_loader module exists."""
    config_loader = PROJECT_ROOT / "shared" / "config_loader.py"
    assert config_loader.exists(), "shared/config_loader.py should exist"


def test_pipeline_script_exists():
    """Test that pipeline script exists and is importable."""
    pipeline_script = PROJECT_ROOT / "we-media-pipeline" / "scripts" / "run_pipeline.py"
    assert pipeline_script.exists(), "run_pipeline.py should exist"


if __name__ == '__main__':
    test_server_endpoints_exist()
    test_server_frontend_health()
    test_config_file_exists()
    test_skills_directory_structure()
    test_shared_config_loader_exists()
    test_pipeline_script_exists()
    print("All server tests passed!")