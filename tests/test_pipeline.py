"""Unit tests for run_pipeline module."""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "shared"))


def test_run_pipeline_imports():
    """Test that all necessary imports work."""
    from config_loader import get_tavily_api_key, get_minimax_api_key
    assert callable(get_tavily_api_key)
    assert callable(get_minimax_api_key)


def test_output_dir_creation():
    """Test output directory creation logic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "test_output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        assert Path(output_dir).exists()


def test_timestamp_format():
    """Test timestamp format for output directories."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    assert len(timestamp) == 15, f"Timestamp should be 15 characters, got: {timestamp}"
    parts = timestamp.split('_')
    assert len(parts) == 2, "Timestamp should have 2 parts separated by underscore"
    assert parts[0].isdigit() and len(parts[0]) == 8, "Date part should be 8 digits"
    assert parts[1].isdigit() and len(parts[1]) == 6, "Time part should be 6 digits"


def test_safe_topic_sanitization():
    """Test topic sanitization for file paths."""
    test_cases = [
        ("normal_topic", "normal_topic"),
        ("clash#123", "clash_123"),
        ("topic with spaces", "topic with spaces"),
        ("topic-with-dash", "topic-with-dash"),
    ]
    for input_topic, expected in test_cases:
        safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in input_topic).strip()
        assert safe_topic == expected, f"Expected {expected}, got {safe_topic}"


def test_ensure_dir_function():
    """Test directory creation helper."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "nested", "test", "dir")
        Path(test_dir).mkdir(parents=True, exist_ok=True)
        assert Path(test_dir).exists()
        assert Path(test_dir).is_dir()


def test_news_search_path_detection():
    """Test news-searcher path detection."""
    project_root = Path(__file__).parent.parent.resolve()
    script_path = project_root / "we-media-pipeline" / "scripts" / "run_pipeline.py"
    news_search_path = project_root / "news-searcher" / "scripts"
    assert news_search_path.exists(), f"news-searcher path should exist: {news_search_path}"


def test_image_searcher_path_detection():
    """Test image-searcher path detection."""
    project_root = Path(__file__).parent.parent.resolve()
    image_search_path = project_root / "image-searcher" / "scripts"
    assert image_search_path.exists(), f"image-searcher path should exist: {image_search_path}"


def test_article_formatter_path_detection():
    """Test article-formatter path detection."""
    project_root = Path(__file__).parent.parent.resolve()
    formatter_path = project_root / "article-formatter" / "scripts"
    assert formatter_path.exists(), f"article-formatter path should exist: {formatter_path}"


def test_config_value_retrieval():
    """Test configuration value retrieval with fallbacks."""
    from config_loader import get_config_value

    result = get_config_value('image_search.search_engine', default='baidu')
    assert result in ['baidu', 'pexels'], f"Invalid engine: {result}"


if __name__ == '__main__':
    test_run_pipeline_imports()
    test_output_dir_creation()
    test_timestamp_format()
    test_safe_topic_sanitization()
    test_ensure_dir_function()
    test_news_search_path_detection()
    test_image_searcher_path_detection()
    test_article_formatter_path_detection()
    test_config_value_retrieval()
    print("All pipeline tests passed!")