#!/usr/bin/env python3
"""
AI News Monitor - 获取最新AI资讯（双语HTML版）
- 默认英文，可切换中文
- 支持 Tavily API（需配置）和备用源（Hacker News / Reddit r/ML）
"""
import os, json, requests, argparse
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
CONFIG_PATH = SKILL_DIR / 'config.json'

SOURCES = [
    {"name": "OpenAI",         "query": "OpenAI GPT ChatGPT Sam Altman",     "icon": "🔵"},
    {"name": "Google DeepMind", "query": "Google DeepMind Gemini Google AI",  "icon": "🟢"},
    {"name": "Anthropic",      "query": "Anthropic Claude Dario Amodei",      "icon": "🟤"},
    {"name": "Meta AI",        "query": "Meta AI Llama Mark Zuckerberg AI",  "icon": "🔷"},
    {"name": "xAI",            "query": "xAI Elon Musk Grok AI",             "icon": "⚡"},
    {"name": "Mistral AI",     "query": "Mistral AI large language model",   "icon": "🌊"},
]

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_tavily_key(config):
    return os.environ.get('TAVILY_API_KEY') or config.get('tavily_api_key', '')

def get_minimax_key(config):
    return os.environ.get('MINIMAX_API_KEY') or config.get('minimax_api_key', '')

def search_tavily(query, api_key, days=3, max_results=5):
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "days": days,
        "include_answer": True,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get('results', []), data.get('answer', '')
    except Exception as e:
        return [], str(e)


def search_fallback(query, source_name, days=3, max_results=5):
    """Fallback: scrape news when Tavily is unavailable or unconfigured."""
    results = []
    today = datetime.now().strftime('%Y-%m-%d')

    # Hacker News Algolia API
    try:
        resp = requests.get("https://hn.algolia.com/api/v1/search", params={
            "query": query,
            "tags": "story",
            "numericFilters": f"created_at_i>={int((datetime.now().timestamp() - days*86400))}",
            "hitsPerPage": max_results
        }, timeout=10)
        data = resp.json()
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title", ""),
                "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                "content": hit.get("text", "")[:200],
                "published_date": datetime.fromtimestamp(hit.get("created_at_i", 0)).isoformat() if hit.get("created_at_i") else today,
                "source": "Hacker News",
            })
    except Exception:
        pass

    # Reddit r/MachineLearning
    if not results:
        try:
            resp = requests.get("https://www.reddit.com/r/MachineLearning/search.json", params={
                "q": query, "restrict_sr": 1, "sort": "new", "t": "day", "limit": max_results
            }, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                results.append({
                    "title": post.get("title", ""),
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "content": post.get("selftext", "")[:200],
                    "published_date": datetime.fromtimestamp(post.get("created_utc", 0)).isoformat() if post.get("created_utc") else today,
                    "source": "Reddit r/ML",
                })
        except Exception:
            pass

    return results[:max_results], ""


def translate_to_chinese(text, minimax_key):
    """调用MiniMax将英文翻译为中文"""
    if not text or not minimax_key:
        return text if text else ""
    try:
        import anthropic
        client = anthropic.Anthropic(
            base_url="https://api.minimaxi.com/anthropic",
            api_key=minimax_key,
        )
        response = client.messages.create(
            model="MiniMax-M2.7",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": f"将以下英文内容翻译为简洁的中文新闻语气，保留核心信息，去除冗余描述，控制在50字以内：\n\n{text}"
            }]
        )
        return response.content[0].text.strip()
    except Exception:
        return text[:50] if text else ""

def format_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str[:10] if date_str else ""

def get_desktop_dir():
    if os.path.exists('/mnt/c/Users/Administrator'):
        return Path('/mnt/c/Users/Administrator/Desktop')
    return Path.home() / 'Desktop'

def generate_html(news_by_source, source_stats, today, has_translation):
    lang_js = """
<script>
function setLang(lang) {
  document.getElementById('lang-en').style.fontWeight = lang === 'en' ? 'bold' : 'normal';
  document.getElementById('lang-cn').style.fontWeight = lang === 'cn' ? 'bold' : 'normal';
  document.body.className = 'lang-' + lang;
}
</script>
"""
    total_articles = len(sum(news_by_source.values(), []))
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI News Briefing | {today}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: #fff; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
  .header .meta {{ font-size: 13px; color: #aaa; margin-bottom: 12px; }}
  .lang-bar {{ display: flex; gap: 8px; margin-top: 10px; align-items: center; }}
  .lang-btn {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 5px 16px; border-radius: 20px; cursor: pointer; font-size: 13px; }}
  .lang-btn:hover {{ background: rgba(255,255,255,0.25); }}
  .lang-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  .source-block {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .source-title {{ font-size: 16px; font-weight: bold; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
  .news-item {{ margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px dashed #eee; }}
  .news-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
  .news-title {{ font-size: 15px; font-weight: bold; color: #222; margin-bottom: 4px; }}
  .news-summary {{ font-size: 13px; color: #666; margin-bottom: 6px; background: #f8f8f8; padding: 8px 10px; border-radius: 6px; border-left: 3px solid #ccc; }}
  .news-meta {{ font-size: 12px; color: #999; }}
  .news-meta span {{ margin-right: 14px; }}
  .news-meta a {{ color: #1a73e8; text-decoration: none; }}
  .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px; }}
  .stat-tag {{ background: #e8f0fe; color: #1a73e8; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
  .footer {{ text-align: center; color: #aaa; font-size: 12px; padding: 20px; }}
  .no-trans {{ color: #ffa500; font-size: 11px; margin-left: 8px; }}
  body.lang-cn [data-en] {{ display: none; }}
  body.lang-en [data-cn] {{ display: none; }}
</style>
</head>
<body class="lang-en">
{lang_js}
<div class="container">
  <div class="header">
    <h1>🤖 AI News Briefing</h1>
    <div class="meta">{today} · {total_articles} articles · {len(news_by_source)} sources</div>
    <div class="lang-bar">
      <button class="lang-btn" id="lang-en" onclick="setLang('en')" style="font-weight:bold">🇺🇸 English</button>
      <button class="lang-btn" id="lang-cn" onclick="setLang('cn')" {"disabled" if not has_translation else ""}>🇨🇳 中文</button>
      {"<span class='no-trans'>⚠ Chinese translation unavailable</span>" if not has_translation else ""}
    </div>
    <div class="stats">
"""
    for s in SOURCES:
        count = len(news_by_source.get(s["name"], []))
        if count:
            html += f'      <span class="stat-tag">{s["icon"]} {s["name"]} {count}</span>\n'
    html += """    </div>
  </div>
"""
    for source in SOURCES:
        name = source["name"]
        icon = source["icon"]
        items = news_by_source.get(name, [])
        if not items:
            continue
        html += f"\n  <div class=\"source-block\">\n    <div class=\"source-title\">{icon} {name}</div>\n"
        for item in items:
            en_title = item.get('en_title', item['title'])
            cn_title = item.get('cn_title', '')
            en_summary = item.get('en_summary', item['summary'])
            cn_summary = item.get('cn_summary', '')
            span_date = f'<span data-en="📅 {item["date"]}" data-cn="📅 {item["date"]}">📅 {item["date"]}</span>' if item['date'] else ''
            html += f"""
    <div class="news-item">
      <div class="news-title" data-en="{en_title}" data-cn="{cn_title}">{en_title}</div>
      <div class="news-summary">
        <span data-en="💬 {en_summary}" data-cn="💬 {cn_summary}">💬 {en_summary}</span>
      </div>
      <div class="news-meta">
        <span>📰 {item['source']}</span>
        {span_date}
        <span>🔗 <a href="{item['url']}" target="_blank" data-en="Read more" data-cn="查看原文">Read more</a></span>
      </div>
    </div>
"""
        html += "\n  </div>\n"
    html += f"""
  <div class="footer">
    <p>Generated by AI News Monitor · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
  </div>
</div>
</body>
</html>"""
    return html


def fetch_news(args):
    config = load_config()
    tavily_key = args.tavily_key or get_tavily_key(config) or config.get('tavily_api_key', '')
    minimax_key = args.minimax_key or get_minimax_key(config) or config.get('minimax_api_key', '')

    has_tavily = bool(tavily_key and tavily_key != 'tvly-YOUR_TAVILY_API_KEY')
    has_translation = bool(minimax_key)

    if not has_tavily:
        print("⚠ 警告：未配置有效 Tavily API Key，将使用备用源（Hacker News / Reddit）")
        print(f"   配置文件: {CONFIG_PATH}")
        print()
    elif not has_translation:
        print("⚠ 警告：未配置 MiniMax API Key，新闻将以英文显示（无中文翻译）")
        print(f"   配置文件: {CONFIG_PATH}")
        print()

    days = args.days or config.get('default_days', 3)
    max_results = args.max_results or config.get('default_max_results', 5)

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = Path(args.output or config.get('output_dir', str(get_desktop_dir() / 'AI资讯')))
    output_dir.mkdir(parents=True, exist_ok=True)
    html_file = output_dir / f"{today}_AI资讯简报.html"

    print(f"[AI News Monitor] Fetching AI News | {today}")
    print(f"Range: last {days} days | max {max_results} per source")
    print(f"Output: {html_file}\n")

    news_by_source = {}
    source_stats = {}
    all_news = []

    for source in SOURCES:
        name = source["name"]
        icon = source["icon"]
        query = source["query"]

        print(f"  ▶ {icon} {name}...", end=" ", flush=True)

        if has_tavily:
            results, answer = search_tavily(query, tavily_key, days=days, max_results=max_results)
        else:
            results, answer = search_fallback(query, name, days=days, max_results=max_results)

        if results:
            items = []
            for r in results:
                raw_title = r.get('title', '')
                raw_content = r.get('content', '')[:300]
                raw_summary = answer if answer else raw_content
                en_title = raw_title
                en_summary = raw_summary[:200] if raw_summary else raw_content[:200]
                cn_title = translate_to_chinese(raw_title, minimax_key) if has_translation else ""
                cn_summary = translate_to_chinese(raw_summary, minimax_key) if has_translation else ""
                items.append({
                    "title": en_title,
                    "en_title": en_title,
                    "cn_title": cn_title,
                    "summary": en_summary,
                    "en_summary": en_summary,
                    "cn_summary": cn_summary,
                    "url": r.get('url', ''),
                    "date": format_date(r.get('published_date', '')),
                    "source": r.get('source', name),
                })
            news_by_source[name] = items
            source_stats[name] = len(items)
            all_news.extend(items)
            status = "✓" if has_translation else "✓ (EN only)"
            print(f"{status} {len(items)} articles")
        else:
            news_by_source[name] = []
            source_stats[name] = 0
            print("✗ no results")

    print(f"\n📝 Generating HTML...")
    html_content = generate_html(news_by_source, source_stats, today, has_translation)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    total = len(all_news)
    active = len([k for k, v in source_stats.items() if v > 0])
    print(f"✅ Saved: {html_file}")
    print(f"   {total} articles from {active} sources")
    if not has_tavily:
        print(f"   💡 Tip: add valid tavily_api_key to {CONFIG_PATH} for better results")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI News Monitor - Bilingual HTML news briefing')
    parser.add_argument('--days', type=int, default=3, help='Search last N days (default: 3)')
    parser.add_argument('--max-results', type=int, default=5, help='Max results per source (default: 5)')
    parser.add_argument('--output', type=str, default=None, help='Output directory')
    parser.add_argument('--tavily-key', type=str, default=None, help='Tavily API Key')
    parser.add_argument('--minimax-key', type=str, default=None, help='MiniMax API Key (for Chinese translation)')
    args = parser.parse_args()
    fetch_news(args)
