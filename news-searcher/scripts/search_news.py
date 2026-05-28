#!/usr/bin/env python3
"""
Search latest news using Tavily API.
Requires TAVILY_API_KEY environment variable or config.json.
Get your free API key at: https://tavily.com/
"""

import sys
import argparse
import os
import json
from datetime import datetime, timedelta
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.parent.parent.resolve()


def get_skill_dir():
    return Path(__file__).parent.parent.resolve()


def load_config():
    """
    Load configuration with priority: project config > skill local config.
    
    When used within the project, project config takes precedence.
    When used standalone, skill local config is used.
    """
    project_config = {}
    project_config_path = get_project_root() / "config.json"
    if project_config_path.exists():
        try:
            with open(project_config_path, 'r', encoding='utf-8') as f:
                project_config = json.load(f)
        except Exception:
            pass
    
    skill_config = {}
    local_config_path = get_skill_dir() / "config.json"
    if local_config_path.exists():
        try:
            with open(local_config_path, 'r', encoding='utf-8') as f:
                skill_config = json.load(f)
        except Exception:
            pass
    
    if project_config.get('tavily_api_key', '').strip():
        skill_config.update(project_config)
        return skill_config
    
    return skill_config


def get_api_key(cli_key=None):
    """Get Tavily API key with priority: CLI arg > project config > env var > skill config."""
    if cli_key and cli_key.strip():
        return cli_key.strip()
    
    config = load_config()
    key = config.get('tavily_api_key', '').strip()
    if key:
        return key
    
    key = os.environ.get('TAVILY_API_KEY', '').strip()
    if key:
        return key
    
    return None


def get_default_days():
    config = load_config()
    return config.get('news_search', {}).get('default_days', 7)


def get_default_results():
    config = load_config()
    return config.get('news_search', {}).get('default_results', 10)


def search_news_tavily(query, max_results=10, days=7, api_key=None):
    """
    Search news using Tavily API.
    
    Args:
        query: Search query
        max_results: Maximum number of results (default: 10)
        days: Search news from last N days (default: 7)
        api_key: Tavily API key
    
    Returns:
        dict: Search results
    """
    try:
        import requests
    except ImportError:
        return {
            'success': False,
            'error': 'requests library required. Install with: pip install requests'
        }
    
    if not api_key:
        api_key = get_api_key()
    
    if not api_key:
        raise ValueError(
            "Tavily API key required. "
            "Get your free key at https://tavily.com/ "
            "and configure in:\n"
            "  1. Project config.json (recommended)\n"
            "  2. news-searcher/config.json\n"
            "  3. Environment variable TAVILY_API_KEY"
        )
    
    try:
        url = "https://api.tavily.com/search"
        
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "topic": "news",
            "include_answer": True,
            "include_images": True,
            "include_raw_content": False,
            "time_range": ("day" if days <= 1 else "week" if days <= 7 else "month" if days <= 30 else "year"),
            "max_results": min(max_results, 20)
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text[:500]}", file=sys.stderr)
        
        response.raise_for_status()
        
        data = response.json()
        
        results = {
            'success': True,
            'query': query,
            'time_range': f"Last {days} days",
            'answer': data.get('answer', ''),
            'results': []
        }
        
        if 'results' in data:
            for result in data['results']:
                processed = {
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', ''),
                    'score': result.get('score', 0),
                    'published_date': result.get('published_date', ''),
                    'source': result.get('source', ''),
                    'images': result.get('images', [])
                }
                results['results'].append(processed)
        
        return results
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Tavily API key. Please check your TAVILY_API_KEY.")
        elif e.response.status_code == 429:
            raise ValueError("API rate limit exceeded. Please try again later.")
        elif e.response.status_code == 400:
            raise ValueError(f"Bad request: {e.response.text[:200]}")
        else:
            raise
    except Exception as e:
        raise Exception(f"Search failed: {e}")


def format_output(results, format='text'):
    """
    Format search results for output.
    
    Args:
        results: Search results dict
        format: Output format ('text', 'json', 'markdown')
    
    Returns:
        str: Formatted output
    """
    if not results['success']:
        return f"Error: {results.get('error', 'Unknown error')}"
    
    if format == 'json':
        return json.dumps(results, indent=2, ensure_ascii=False)
    
    elif format == 'markdown':
        lines = []
        lines.append(f"# Search Results: {results['query']}")
        lines.append(f"\n**Time Range:** {results['time_range']}")
        lines.append(f"**Results:** {len(results['results'])}")
        lines.append("\n---\n")
        
        if results['answer']:
            lines.append("## AI Summary\n")
            lines.append(results['answer'])
            lines.append("\n---\n")
        
        lines.append("## News Articles\n")
        
        for i, result in enumerate(results['results'], 1):
            lines.append(f"### {i}. {result['title']}")
            lines.append(f"**Source:** {result['source']}")
            if result['published_date']:
                lines.append(f"**Published:** {result['published_date']}")
            lines.append(f"**URL:** {result['url']}")
            lines.append(f"**Relevance Score:** {result['score']:.2f}")
            if result.get('images'):
                lines.append(f"**Images:** {len(result['images'])} image(s)")
                for img_url in result['images'][:3]:
                    lines.append(f"- {img_url}")
            lines.append(f"\n{result['content'][:300]}...")
            lines.append("\n---\n")
        
        return '\n'.join(lines)
    
    else:
        lines = []
        lines.append(f"Search: {results['query']}")
        lines.append(f"Time Range: {results['time_range']}")
        lines.append(f"Results: {len(results['results'])}")
        lines.append("-" * 60)
        
        if results['answer']:
            lines.append("\n[AI Summary]")
            lines.append(results['answer'])
            lines.append("-" * 60)
        
        lines.append("\n[News Articles]\n")
        
        for i, result in enumerate(results['results'], 1):
            lines.append(f"\n{i}. {result['title']}")
            lines.append(f"   Source: {result['source']}")
            if result['published_date']:
                lines.append(f"   Published: {result['published_date']}")
            lines.append(f"   URL: {result['url']}")
            lines.append(f"   Score: {result['score']:.2f}")
            if result.get('images'):
                lines.append(f"   Images: {len(result['images'])} image(s)")
                for img_url in result['images'][:2]:
                    lines.append(f"   - {img_url}")
            lines.append(f"   {result['content'][:200]}...")
            lines.append("")
        
        return '\n'.join(lines)


def save_results(results, output_file, format='markdown'):
    """
    Save search results to file.
    
    Args:
        results: Search results dict
        output_file: Output file path
        format: Output format
    
    Returns:
        str: Saved file path
    """
    output = format_output(results, format)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Search latest news using Tavily API')
    parser.add_argument('query', help='Search query')
    parser.add_argument('-n', '--num', type=int, default=None, help=f'Number of results (default: {get_default_results()})')
    parser.add_argument('-d', '--days', type=int, default=None, help=f'Search last N days (default: {get_default_days()})')
    parser.add_argument('-k', '--key', help='Tavily API key (overrides config)')
    parser.add_argument('-f', '--format', choices=['text', 'json', 'markdown'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('-o', '--output', help='Save results to file')
    
    args = parser.parse_args()
    
    default_days = get_default_days()
    default_results = get_default_results()
    
    query = args.query
    days = args.days if args.days is not None else default_days
    num = args.num if args.num is not None else default_results
    
    api_key = get_api_key(args.key)
    
    if not api_key:
        print("Error: Tavily API key required.", file=sys.stderr)
        print("Get your free key at https://tavily.com/", file=sys.stderr)
        print()
        print("Configure API key in one of:")
        print("  1. Project config.json (recommended): config.json", file=sys.stderr)
        print("  2. news-searcher/config.json", file=sys.stderr)
        print("  3. Environment variable: TAVILY_API_KEY", file=sys.stderr)
        print("  4. Command line: -k YOUR_KEY", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Searching for: {query}")
        print(f"Time range: Last {days} days")
        print(f"Max results: {num}")
        print("-" * 60)
        
        results = search_news_tavily(
            query=query,
            max_results=num,
            days=days,
            api_key=api_key
        )
        
        output = format_output(results, args.format)
        print(output)
        
        if args.output:
            saved_path = save_results(results, args.output, args.format)
            print(f"\n✓ Results saved to: {saved_path}")
        
        return 0
    
    except ValueError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())