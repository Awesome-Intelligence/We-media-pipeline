#!/usr/bin/env python3

"""

We-Media-Pipeline - Main runner script.

Coordinates the full article generation workflow.

"""

import sys

import os

import argparse

import json

import re

from datetime import datetime

from pathlib import Path

# Add parent directory to path for importing config_loader

sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from config_loader import get_tavily_api_key, get_minimax_api_key, get_config_value, check_api_keys


def ensure_dir(directory):

    """Create directory if it doesn't exist."""

    Path(directory).mkdir(parents=True, exist_ok=True)

    return directory

def step1_dispatch(topic, output_dir, search_type='news', days=None, num_results=None):

    """Dispatch to the appropriate Step 1 search function based on search_type."""

    if search_type == 'tutorial':

        return step1_search_tutorial(topic, output_dir)

    elif search_type == 'product':

        return step1_search_product(topic, output_dir)

    else:

        return step1_search_news(topic, output_dir, days=days, num_results=num_results)

def step1_search_news(topic, output_dir, days=None, num_results=None):

    """Step 1: Search news using Tavily API."""

    print("\n" + "="*60)

    print("STEP 1: Searching News")

    print("="*60)

    

    api_key = get_tavily_api_key()

    if not api_key:

        print("✗ Error: Tavily API key not configured")

        print("  Please set it in config.json or TAVILY_API_KEY environment variable")

        return False, None

    

    days = days or get_config_value('news_search.default_days', 7)

    num_results = num_results or get_config_value('news_search.default_results', 10)

    

    news_search_path = Path(__file__).parent.parent.parent / "news-searcher" / "scripts"
    if not news_search_path.exists():
        news_search_path = Path("/mnt/c/Users/Administrator/.hermes/skills/news-searcher/scripts")
    if not news_search_path.exists():
        news_search_path = Path.home() / ".hermes/skills/news-searcher/scripts"
    sys.path.insert(0, str(news_search_path))



    try:

        from search_news import search_news_tavily, save_results

        

        print(f"Searching for: {topic}")

        print(f"Time range: Last {days} days")

        print(f"Max results: {num_results}")

        

        results = search_news_tavily(

            query=topic,

            max_results=num_results,

            days=days,

            api_key=api_key

        )

        

        if not results['success']:

            print(f"✗ Search failed: {results.get('error', 'Unknown error')}")

            return False, None

        

        research_file = os.path.join(output_dir, "01_research.md")

        save_results(results, research_file, 'markdown')

        

        print(f"✓ Research saved to: {research_file}")

        print(f"  Found {len(results['results'])} articles")

        

        news_images_file = os.path.join(output_dir, "01_news_images.json")

        news_images = []

        for article in results['results']:

            if article.get('images'):

                news_images.extend(article['images'])

        

        news_images = list(dict.fromkeys(news_images))

        with open(news_images_file, 'w', encoding='utf-8') as f:

            json.dump(news_images, f, indent=2, ensure_ascii=False)

        

        print(f"✓ Found {len(news_images)} news images")

        print(f"  Saved to: {news_images_file}")

        

        return True, research_file

        

    except ImportError as e:

        print(f"✗ Error: Could not import news-searcher module: {e}")

        return False, None

    except Exception as e:

        print(f"✗ Error during news search: {e}")

        return False, None


def step1_search_tutorial(topic, output_dir, api_key=None):
    """Step 1: Search tutorials using Tavily web search."""
    print("\n" + "="*60)
    print("STEP 1: Searching Tutorials")
    print("="*60)

    if api_key is None:
        api_key = get_tavily_api_key()

    if not api_key:
        print("✗ Error: Tavily API key not configured")
        return False, None

    news_search_path = Path(__file__).parent.parent.parent / "news-searcher" / "scripts"
    if not news_search_path.exists():
        news_search_path = Path("/mnt/c/Users/Administrator/.hermes/skills/news-searcher/scripts")
    if not news_search_path.exists():
        news_search_path = Path.home() / ".hermes/skills/news-searcher/scripts"
    sys.path.insert(0, str(news_search_path))

    try:
        from search_news import search_news_tavily
    except ImportError:
        print("✗ Error: Could not import news-searcher module")
        return False, None

    tutorial_queries = [
        topic,
        "%s tutorial" % topic,
        "%s guide from zero to expert" % topic,
        "%s tutorial site:github.com" % topic,
        "%s 使用教程 site:juejin.cn" % topic,
    ]

    all_results = []
    all_images = []
    used_urls = set()

    for query in tutorial_queries:
        print("  Query: %s" % query)
        try:
            results = search_news_tavily(query=query, max_results=5, days=365, api_key=api_key)
            if results and results.get('results'):
                for r in results['results']:
                    if r.get('url') not in used_urls:
                        used_urls.add(r['url'])
                        all_results.append(r)
                        if r.get('images'):
                            all_images.extend(r['images'])
        except Exception as e:
            print("  [!] Search error: %s" % e)

    if not all_results:
        print("  No tutorial results found")
        return False, None

    print("  Found %d sources" % len(all_results))
    all_images = list(dict.fromkeys(all_images))

    research_file = os.path.join(output_dir, "01_research.md")
    with open(research_file, 'w', encoding='utf-8') as f:
        f.write("# Research: %s\n\n" % topic)
        f.write("**Type: tutorial**\n\n")
        f.write("---\n\n")
        for i, r in enumerate(all_results, 1):
            f.write("## %d. %s\n\n" % (i, r.get('title', 'No title')))
            f.write("Source: %s\n\n" % r.get('url', ''))
            f.write("%s\n\n" % r.get('description', ''))

    news_images_file = os.path.join(output_dir, "01_news_images.json")
    with open(news_images_file, 'w', encoding='utf-8') as f:
        json.dump(all_images[:50], f, indent=2, ensure_ascii=False)

    print("\n  [OK] Tutorial research saved: %s" % research_file)
    print("  Found %d source images" % len(all_images))
    return True, research_file


def step1_search_product(topic, output_dir, api_key=None):
    """Step 1: Search product info using Tavily web search."""
    print("\n" + "="*60)
    print("STEP 1: Searching Products")
    print("="*60)

    if api_key is None:
        api_key = get_tavily_api_key()

    if not api_key:
        print("✗ Error: Tavily API key not configured")
        return False, None

    news_search_path = Path(__file__).parent.parent.parent / "news-searcher" / "scripts"
    if not news_search_path.exists():
        news_search_path = Path("/mnt/c/Users/Administrator/.hermes/skills/news-searcher/scripts")
    if not news_search_path.exists():
        news_search_path = Path.home() / ".hermes/skills/news-searcher/scripts"
    sys.path.insert(0, str(news_search_path))

    try:
        from search_news import search_news_tavily
    except ImportError:
        print("✗ Error: Could not import news-searcher module")
        return False, None

    product_queries = [
        topic,
        "%s review" % topic,
        "%s 评测 site:sspai.com" % topic,
        "%s 对比 vs site:zhihu.com" % topic,
        "%s 测评 site:bilibili.com" % topic,
    ]

    all_results = []
    all_images = []
    used_urls = set()

    for query in product_queries:
        print("  Query: %s" % query)
        try:
            results = search_news_tavily(query=query, max_results=5, days=365, api_key=api_key)
            if results and results.get('results'):
                for r in results['results']:
                    if r.get('url') not in used_urls:
                        used_urls.add(r['url'])
                        all_results.append(r)
                        if r.get('images'):
                            all_images.extend(r['images'])
        except Exception as e:
            print("  [!] Search error: %s" % e)

    if not all_results:
        print("  No product results found")
        return False, None

    print("  Found %d sources" % len(all_results))
    all_images = list(dict.fromkeys(all_images))

    research_file = os.path.join(output_dir, "01_research.md")
    with open(research_file, 'w', encoding='utf-8') as f:
        f.write("# Research: %s\n\n" % topic)
        f.write("**Type: product**\n\n")
        f.write("---\n\n")
        for i, r in enumerate(all_results, 1):
            f.write("## %d. %s\n\n" % (i, r.get('title', 'No title')))
            f.write("Source: %s\n\n" % r.get('url', ''))
            f.write("%s\n\n" % r.get('description', ''))

    news_images_file = os.path.join(output_dir, "01_news_images.json")
    with open(news_images_file, 'w', encoding='utf-8') as f:
        json.dump(all_images[:50], f, indent=2, ensure_ascii=False)

    print("\n  [OK] Product research saved: %s" % research_file)
    print("  Found %d source images" % len(all_images))
    return True, research_file


def step2_generate_article(research_file, output_dir):

    """Step 2: Generate article using MiniMax LLM (article-writer skill)."""

    print("\n" + "="*60)

    print("STEP 2: Generate Article")

    print("\n" + "="*60)

    article_file = os.path.join(output_dir, "02_article.md")

    if os.path.exists(article_file):

        print(f"Article file already exists: {article_file}")

        return True, article_file

    print(f"  Input research: {research_file}")

    print(f"  Output article: {article_file}")

    with open(research_file, "r", encoding="utf-8") as f:

        research_content = f.read()

    skill_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    style_guide_path = os.path.join(skill_dir, "article-writer", "references", "style-guide.md")

    with open(style_guide_path, "r", encoding="utf-8") as f:

        style_guide = f.read()

    system_prompt = (

        "You are a WeChat public account article writer following the article-writer skill.\n\n"

        "## Your Task\n"

        "Given research material, generate a WeChat article following ALL rules below.\n\n"

        "## Style Guide\n"

        + style_guide +

        "\n\n## Required Structure\n"

        "1. Title: Use one of the 11 title formulas from style-guide. Must have suspense or conflict.\n"

        "2. Opening Hook: Use one of the 11 hook types from style-guide.\n"

        "3. Attribution block (MUST appear right after title, before body):\n"

        "内容编辑丨虾朋马友\n"

        "内容审核丨休蒙\n\n"

        "4. Body with ## section headers. End each section with [[IMG: description]] placeholder.\n"

        "5. Closing section: ## 写在最后\n"

        "6. Exactly 6 [[IMG: description]] placeholders total, Chinese descriptions.\n\n"

        "## Output Rules\n"

        "Markdown. 1500-2500 Chinese characters. Short paragraphs. Bold key phrases.\n"

        "Conversational but professional. First person perspective.\n\n"

        "## Research Material\n"

        + research_content

    )

    try:

        import anthropic

    except ImportError:

        print("\n  Installing anthropic package...")

        import subprocess

        subprocess.run(["pip", "install", "anthropic", "-q"], check=True)

        import anthropic

    api_key = get_minimax_api_key()
    if not api_key:
        print("\n✗ Error: MiniMax API key not configured")
        print("  Please set it in config.json or MINIMAX_API_KEY environment variable")
        return False, None

    client = anthropic.Anthropic(
        base_url="https://api.minimaxi.com/anthropic",
        api_key=api_key,
    )

    print("\n  Calling MiniMax-M2.7 to generate article...")

    message = client.messages.create(

        model="MiniMax-M2.7",

        max_tokens=8192,

        system=system_prompt,

        messages=[

            {

                "role": "user",

                "content": [

                    {

                        "type": "text",

                        "text": "根据以上研究资料和风格规范，生成一篇微信公众号文章。"

                    }

                ]

            }

        ],

    )

    article_text = ""

    for block in message.content:

        if block.type == "text":

            article_text = block.text

            break

    if not article_text:

        print("  No text in LLM response:")

        for block in message.content:

            print(f"  Block type: {block.type}")

        return False, None

    with open(article_file, "w", encoding="utf-8") as f:

        f.write(article_text)

    print(f"\n  Article generated: {len(article_text)} characters")

    print(f"  Saved to: {article_file}")

    return True, article_file

def extract_image_queries(article_file):

    """Extract image queries from article [[IMG: ...]] tags."""

    if not article_file or not os.path.exists(article_file):

        return []

    

    try:

        with open(article_file, 'r', encoding='utf-8') as f:

            content = f.read()

        

        pattern = r'\[\[IMG:\s*([^\]]+)\]\]'

        matches = re.findall(pattern, content)

        queries = [q.strip() for q in matches if q.strip()]

        return queries

    except Exception as e:

        print(f"⚠ Warning: Could not extract image queries: {e}")

        return []

def download_image_from_url(url, output_path, timeout=30):

    """Download image from URL and save to file."""

    try:

        import requests

        from urllib.parse import urlparse

        

        headers = {

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

        }

        

        response = requests.get(url, headers=headers, timeout=timeout, stream=True)

        response.raise_for_status()

        

        content_type = response.headers.get('content-type', '')

        if 'jpeg' in content_type or 'jpg' in content_type:

            ext = '.jpg'

        elif 'png' in content_type:

            ext = '.png'

        elif 'gif' in content_type:

            ext = '.gif'

        elif 'webp' in content_type:

            ext = '.webp'

        else:

            parsed = urlparse(url)

            path = parsed.path.lower()

            if path.endswith('.jpg') or path.endswith('.jpeg'):

                ext = '.jpg'

            elif path.endswith('.png'):

                ext = '.png'

            elif path.endswith('.gif'):

                ext = '.gif'

            elif path.endswith('.webp'):

                ext = '.webp'

            else:

                ext = '.jpg'

        

        if not output_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):

            output_path = output_path + ext

        

        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)

        

        return True, output_path

    except Exception as e:

        return False, str(e)

def _check_resolution(image_path, min_width=800, min_height=600):

    """Check if image meets minimum resolution. PIL failure = width=0 = skip."""

    try:

        from PIL import Image

        with Image.open(image_path) as img:

            w, h = img.size

            if w > 0 and w >= min_width and h >= min_height:

                return True, w, h

            return False, w, h

    except Exception:

        return False, 0, 0

def _copy_to_good(src_path, good_dir, basename):

    """Copy a PIL-validated image to images_good with a nice name."""

    try:

        from PIL import Image

        import shutil

        dst = os.path.join(good_dir, basename)

        shutil.copy2(src_path, dst)

        return True

    except Exception:

        return False

def step3_search_images(article_file, output_dir):

    """Step 3: Download ALL news images + Baidu supplement, split to images-all and images_good."""

    print("\n" + "="*60)

    print("STEP 3: Downloading Images (ALL + quality split)")

    print("="*60)

    

    # NOTE: images_good dir name must match step5/step6 (underscore, not hyphen)

    images_all_dir  = os.path.join(output_dir, "images-all")

    images_good_dir = os.path.join(output_dir, "images_good")

    ensure_dir(images_all_dir)

    ensure_dir(images_good_dir)

    

    # 1. Read news image list

    news_images_file = os.path.join(output_dir, "01_news_images.json")

    news_images = []

    if os.path.exists(news_images_file):

        try:

            with open(news_images_file, "r", encoding="utf-8") as f:

                news_images = json.load(f)

            print(f"News images: {len(news_images)} (downloading all, no cap)")

        except Exception as e:

            print(f"Could not load news images: {e}")

    

    # 2. Download ALL news images

    all_count = 0

    good_count = 0

    GOOD_TARGET = 10

    

    if news_images:

        print("[INFO] Downloading news images (target: %d good images)" % GOOD_TARGET)

        for i, img_url in enumerate(news_images, 1):

            # Early stop: already have enough good images

            if good_count >= GOOD_TARGET:

                remaining = len(news_images) - i + 1

                print(f'  [Early stop] images_good has {good_count} >= {GOOD_TARGET}, skipping remaining {remaining} news images\n')
                break

            if not img_url:

                continue

            print(f"[{i}/{len(news_images)}] {img_url[:80]}...", end=" ")

            output_path = os.path.join(images_all_dir, f"news_{i:03d}")

            success, result = download_image_from_url(img_url, output_path)

            

            if success:

                is_valid, w, h = _check_resolution(result)

                if is_valid:

                    basename = f"news_{i:03d}_{w}x{h}{os.path.splitext(result)[1]}"

                    _copy_to_good(result, images_good_dir, basename)

                    good_count += 1

                    print(f"OK -> images-all + images_good ({w}x{h}) [{good_count}/{GOOD_TARGET}]")

                else:

                    print(f"OK -> images-all (low res {w}x{h}, not in images_good)")

                all_count += 1

            else:

                print(f"FAIL: {result[:60]}")

    

    print(f"\n  news images: {all_count} downloaded, {good_count} in images_good")

    

    # 3. Baidu supplement (only if news images < 7)

    if good_count >= GOOD_TARGET:

        print("Skipping Baidu (good images >= GOOD_TARGET, already have enough)")

        baidu_all = 0

        baidu_good = 0

    else:

        image_queries = extract_image_queries(article_file)

        if not image_queries:

            print("\nNo [[IMG:...]] tags found, using default queries")

            image_queries = ["concept", "business", "digital", "office", "future", "professional"]

        else:

            print(f"\nFound {len(image_queries)} Baidu query terms")

        

        baidu_search_path = Path(__file__).parent.parent.parent / "image-searcher" / "scripts"
        if not baidu_search_path.exists():
            baidu_search_path = Path("/mnt/c/Users/Administrator/.hermes/skills/image-searcher/scripts")
        if not baidu_search_path.exists():
            baidu_search_path = Path.home() / ".hermes/skills/image-searcher/scripts"
        sys.path.insert(0, str(baidu_search_path))

        

        baidu_all = 0

        baidu_good = 0

        

        try:

            from search_baidu import search_and_download

            

            baidu_max = get_config_value("image_search.default_results", 6)

            

            for qi, query in enumerate(image_queries, 1):

                print(f"\n[{qi}/{len(image_queries)}] Baidu: {query}")

                res = search_and_download(

                    query=query,

                    output_dir=images_all_dir,

                    max_results=baidu_max,

                    prefix=f"baidu_{qi:02d}"

                )

                

                if res["success"]:

                    for item in res["downloaded"]:

                        p = item["path"]

                        is_valid, w, h = _check_resolution(p)

                        fname = os.path.basename(p)

                        if is_valid:

                            good_name = f"baidu_{qi:02d}_{w}x{h}{os.path.splitext(p)[1]}"

                            _copy_to_good(p, images_good_dir, good_name)

                            baidu_good += 1

                            print(f"  OK {fname} -> images_good ({w}x{h})")

                        else:

                            print(f"  OK {fname} -> images-all (low res {w}x{h})")

                        baidu_all += 1

                    print(f"  This query: {len(res['downloaded'])} downloaded")

                else:

                    print(f"  FAIL: {res.get('error', 'Unknown')}")

        except ImportError as e:

            print(f"Cannot import Baidu module: {e}")

            baidu_all = 0

            baidu_good = 0

    

    total_all  = all_count  + baidu_all

    total_good = good_count + baidu_good

    

    print("\n" + "="*60)

    print(f"Image download complete")

    print(f"  images-all : {total_all} images")

    print(f"  images_good: {total_good} images (>= 800x600)")

    print("="*60)

    

    return total_good > 0, images_good_dir

def extract_title_from_article(article_path):

    """Extract title from article markdown file (first # heading)."""

    try:

        with open(article_path, 'r', encoding='utf-8') as f:

            for line in f:

                line = line.strip()

                if line.startswith('# ') and not line.startswith('## '):

                    title = line[2:].strip()

                    import re

                    clean_title = re.sub(r'[^\w\s\u4e00-\u9fff]', '', title)

                    clean_title = re.sub(r'\s+', '', clean_title)

                    return clean_title[:50]

    except Exception:

        pass

    return None

def step4_export_word(article_file, images_dir, output_dir, topic):

    """Step 4: Export to Word document."""

    print("\n" + "="*60)

    print("STEP 4: Article Formatter")

    print("="*60)

    

    md_to_word_path = Path(__file__).parent.parent.parent / "article-formatter" / "scripts"
    if not md_to_word_path.exists():
        md_to_word_path = Path("/mnt/c/Users/Administrator/.hermes/skills/article-formatter/scripts")
    if not md_to_word_path.exists():
        md_to_word_path = Path.home() / ".hermes/skills/article-formatter/scripts"
    sys.path.insert(0, str(md_to_word_path))

    

    try:

        from md_to_word import convert_markdown_to_word

        

        article_title = extract_title_from_article(article_file)

        if article_title:

            word_filename = f"04_{article_title}.docx"

        else:

            safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in topic).strip()

            safe_topic = safe_topic.replace(' ', '_')

            word_filename = f"04_{safe_topic}.docx"

        

        docx_file = os.path.join(output_dir, word_filename)

        

        print(f"Converting: {article_file}")

        print(f"Output: {docx_file}")

        

        result = convert_markdown_to_word(article_file, docx_file, images_dir)

        

        if result.get('success') and os.path.exists(docx_file):

            print(f"✓ Word document created: {docx_file}")

            return True, docx_file

        else:

            error_msg = result.get('error', 'Unknown error')

            print(f"✗ Failed to create Word document: {error_msg}")

            return False, None

            

        

    except ImportError as e:

        print(f"✗ Error: Could not import article-formatter module: {e}")

        return False, None

    except Exception as e:

        print(f"✗ Error during Word export: {e}")

        return False, None

def step5_generate_content_json(article_file, output_dir):

    """Step 5: Generate content.json using MiniMax LLM + article-shorter skill."""

    import anthropic

    print("\n" + "="*60)

    print("STEP 5: Generate content.json (article-shorter)")

    print("="*60)

    content_json_file = os.path.join(output_dir, "05_content.json")

    images_dir = os.path.join(output_dir, "images_good")

    # Auto-create images_good from news images if directory doesn't exist

    if not os.path.exists(images_dir):

        images_all_dir = os.path.join(output_dir, "images-all")

        if os.path.exists(images_all_dir):

            ensure_dir(images_dir)

            import shutil

            for f in os.listdir(images_all_dir):

                src = os.path.join(images_all_dir, f)

                if os.path.isfile(src):

                    shutil.copy2(src, images_dir)

            print(f"✓ Auto-created images_good from images-all ({len(os.listdir(images_dir))} files)")

    # Read article

    try:

        with open(article_file, 'r', encoding='utf-8') as f:

            article_content = f.read()

        print(f"✓ Article loaded: {article_file}")

    except Exception as e:

        print(f"✗ Failed to read article: {e}")

        return False, None

    # Extract title

    article_lines = article_content.split('\n')

    title_line = next((l for l in article_lines if l.strip().startswith('# ')), '')

    article_title = title_line[2:].strip() if title_line else 'article'

    # Extract images (first 3)

    image_files = []

    if os.path.exists(images_dir):

        for f in os.listdir(images_dir):

            if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):

                image_files.append(os.path.join(images_dir, f))

        image_files = sorted(image_files)[:3]

    print(f"✓ Found {len(image_files)} images in {images_dir}")

    print(f"  Calling MiniMax-M2.7 to generate content.json...")

    # article-shorter prompt

    system_prompt = """You are an article summarizer. Input: a long article. Output: a JSON file matching this exact structure:

{

  "main_title": "大标题（≤10字，含数字优先）",

  "sub_title": "副标题（≤12字，含悬念或背景）",

  "text_sections": ["第一段（40-50字）", "第二段（40-50字）", "第三段（40-50字）"],

  "outro_text": "关注 AI不够酷｜获取更多AI资讯"

}

Rules:

1. main_title: ≤10 Chinese characters, use numbers if possible, create tension/conflict

2. sub_title: ≤12 characters, add suspense or background context

3. text_sections: THREE paragraphs totaling ~150 characters, written in news reporter style

4. news style: concise, professional, cover time/person/event/numbers/results

5. split the 150-char news summary into three ~50-char sections by natural meaning

6. output pure JSON only, no explanation"""

    user_prompt = f"Article title: {article_title}\n\nArticle content:\n{article_content[:3000]}"

    api_key = get_minimax_api_key()
    if not api_key:
        print("\n✗ Error: MiniMax API key not configured")
        print("  Please set it in config.json or MINIMAX_API_KEY environment variable")
        return False, None

    client = anthropic.Anthropic(
        base_url="https://api.minimaxi.com/anthropic",
        api_key=api_key,
    )

    try:

        message = client.messages.create(

            model="MiniMax-M2.7",

            max_tokens=4096,

            system=system_prompt,

            messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],

        )

    except Exception as e:

        print(f"✗ API call failed: {e}")

        return False, None

    # Extract text blocks

    response_text = ""

    for block in message.content:

        if hasattr(block, 'text') and block.text:

            response_text += block.text

    # Parse JSON

    import json, re

    json_match = re.search(r'\{[\s\S]+?\}', response_text)

    if not json_match:

        print(f"✗ No JSON found in response: {response_text[:200]}")

        return False, None

    try:

        data = json.loads(json_match.group())

    except Exception as e:

        print(f"✗ JSON parse failed: {e}")

        # 尝试修复常见问题：中文引号、截断等
        fixed = False
        raw = json_match.group()

        # 1. 替换中文引号为英文引号
        for old, new in [('“', '"'), ('”', '"'), ('「', '"'), ('」', '"'),
                         ('＂', '"'), ('‘', "'"), ('’', "'")]:
            if old in raw:
                raw = raw.replace(old, new)
                fixed = True

        # 2. 如果 images 字段引用了绝对路径，简化为文件名
        if fixed:
            try:
                data = json.loads(raw)
                print(f"  ✓ JSON fixed after quote replacement")
            except Exception:
                data = None
                fixed = False

        if not fixed:
            return False, None

    # Ensure images field is auto-filled

    if image_files:

        data["images"] = image_files

    else:

        data["images"] = []

    # Write content.json

    try:

        with open(content_json_file, 'w', encoding='utf-8') as f:

            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ content.json generated: {content_json_file}")

        print(f"  main_title: {data.get('main_title', 'N/A')}")

        print(f"  sub_title: {data.get('sub_title', 'N/A')}")

        return True, content_json_file

    except Exception as e:

        print(f"✗ Failed to write content.json: {e}")

        return False, None

def step6_generate_video(content_json_file, images_dir, output_dir):

    """Step 6: Generate video using wechat-video-generator."""

    print("\n" + "="*60)

    print("STEP 6: Video Generator (we-video-generator)")

    print("="*60)

    

    video_generator_path = Path(__file__).parent.parent.parent / "we-video-generator" / "scripts"
    if not video_generator_path.exists():
        video_generator_path = Path("/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator/scripts")
    if not video_generator_path.exists():
        video_generator_path = Path.home() / ".hermes/skills/wechat-video-generator/scripts"
    sys.path.insert(0, str(video_generator_path))

    

    try:

        from run_video_generator import generate_video

        

        # Load content.json to get the title for filename

        with open(content_json_file, 'r', encoding='utf-8') as f:

            content_data = json.load(f)

        

        

        main_title = content_data.get('main_title', 'output')

        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in main_title).strip()

        safe_title = safe_title.replace(' ', '_')[:30]

        video_file = os.path.join(output_dir, f"06_{safe_title}.mp4")

        

        print(f"Input: {content_json_file}")

        print(f"Images: {images_dir}")

        print(f"Output: {video_file}")

        

        result = generate_video(

            content_json=content_json_file,

            images_dir=images_dir,

            output_file=video_file

        )

        

        if result.get('success') and os.path.exists(video_file):

            print(f"✓ Video created: {video_file}")

            _deploy_regen_script(output_dir)

            return True, video_file

        else:

            error_msg = result.get('error', 'Unknown error')

            print(f"✗ Failed to create video: {error_msg}")

            return False, None

            # 视频可能输出到了 WeChatVideo输出/，尝试复制回来
            wcv_dir = Path("/mnt/c/Users/Administrator/Desktop/WeChatVideo输出")
            if wcv_dir.exists():
                for mp4 in wcv_dir.glob("*.mp4"):
                    if content_data.get("main_title", "")[:10] in mp4.name:
                        print(f"  Found video in WeChatVideo: {mp4}")
                        shutil.copy2(str(mp4), video_file)
                        print(f"  Copied to project: {video_file}")
                        _deploy_regen_script(output_dir)
                        return True, video_file

            return False, None

    except ImportError as e:

        print(f"✗ Error: Could not import wechat-video-generator module: {e}")

        print(f"  Make sure wechat-video-generator skill is installed")

        return False, None

    except Exception as e:

        print(f"✗ Error during video generation: {e}")

        return False, None

def _deploy_regen_script(output_dir):

    """Deploy regen_video.py to project directory after Step 6 succeeds."""

    src = Path(__file__).parent / "regen_video.py"

    dst = Path(output_dir) / "重新生成视频.py"

    import shutil

    try:

        shutil.copy2(src, dst)

        print(f"  ✓ 重新生成视频.py 已放置: {dst}")

    except Exception as e:

        print(f"  ⚠ 无法复制 regen_video.py: {e}")

def get_default_output_dir():
    """Get default output directory from shared config loader."""
    from config_loader import get_default_output_dir as shared_get_output_dir
    return shared_get_output_dir()

def find_existing_folder(topic, base_dir):

    """Find existing folder for the same topic."""

    safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in topic).strip()

    safe_topic = safe_topic.replace(' ', '_')

    

    import glob

    pattern = os.path.join(base_dir, f"*_{safe_topic}")

    existing = glob.glob(pattern)

    

    if existing:

        return max(existing, key=os.path.getmtime)

    return None

def run_pipeline(topic, skip_steps=None, output_dir=None, humanize=False, humanize_aggressive=False, type_=None, days=None, num_results=None):

    """

    Run the complete article generation pipeline.

    

    Steps:

        1. Search News (news-searcher)

        2. Generate Article (article-writer) - requires LLM

        3. Download Images (image-searcher)

        4. Export to Word (article-formatter)

        5. Generate content.json (article-shorter) - requires LLM

        6. Generate Video (wechat-video-generator)

    """

    skip_steps = skip_steps or []

    

    if output_dir:

        base_dir = output_dir

    else:

        base_dir = get_default_output_dir()

    

    if skip_steps:

        existing_folder = find_existing_folder(topic, base_dir)

        if existing_folder:

            output_dir = existing_folder

            print(f"\n📁 Using existing folder: {output_dir}")

        else:

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in topic).strip()

            safe_topic = safe_topic.replace(' ', '_')

            output_dir = os.path.join(base_dir, f"{timestamp}_{safe_topic}")

            ensure_dir(output_dir)

    else:

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in topic).strip()

        safe_topic = safe_topic.replace(' ', '_')

        output_dir = os.path.join(base_dir, f"{timestamp}_{safe_topic}")

        ensure_dir(output_dir)

    

    print(f"\n{'='*60}")

    print(f"We-Media-Pipeline")

    print(f"Topic: {topic}")

    print(f"Output: {output_dir}")

    print(f"{'='*60}")

    

    results = {

        'success': False,

        'output_dir': output_dir,

        'steps': {}

    }

    

    # Step 1: Search News

    if 1 not in skip_steps:

        success, research_file = step1_dispatch(topic, output_dir, type_, days=days, num_results=num_results)

        results['steps'][1] = {'success': success, 'file': research_file}

        if not success:

            print("\n✗ Pipeline stopped at Step 1")

            return results

    else:

        research_file = os.path.join(output_dir, "01_research.md")

        results['steps'][1] = {'success': True, 'file': research_file, 'skipped': True}

    

    # Step 2: Generate Article (requires LLM)

    if 2 not in skip_steps:

        success, article_file = step2_generate_article(research_file, output_dir)

        results['steps'][2] = {'success': success, 'file': article_file}

        if not success:

            print("\n⚠ Pipeline paused at Step 2 (requires LLM generation)")

            print(f"   Please generate article manually and save to: {output_dir}/02_article.md")

            return results

    else:

        article_file = os.path.join(output_dir, "02_article.md")

        results['steps'][2] = {'success': True, 'file': article_file, 'skipped': True}

    

    # Step 2.5: Humanize article (if enabled)

    if humanize:

        success, humanized_file = step2_5_humanize(article_file, output_dir, aggressive=humanize_aggressive)

        results['steps']['2.5'] = {'success': success, 'file': humanized_file}

        if not success:

            print("[!] Humanize failed - continuing with original article")

    else:

        results['steps']['2.5'] = {'success': True, 'skipped': True}

    if 3 not in skip_steps:

        success, images_dir = step3_search_images(article_file, output_dir)

        results['steps'][3] = {'success': success, 'dir': images_dir}

        if not success:

            print("\n✗ Pipeline stopped at Step 3")

            return results

    else:

        images_dir = os.path.join(output_dir, "images_good")

        results['steps'][3] = {'success': True, 'dir': images_dir, 'skipped': True}

    

    # Step 4: Export to Word

    if 4 not in skip_steps:

        success, docx_file = step4_export_word(article_file, images_dir, output_dir, topic)

        results['steps'][4] = {'success': success, 'file': docx_file}

        if not success:

            print("\n✗ Pipeline stopped at Step 4")

            return results

    else:

        results['steps'][4] = {'success': True, 'skipped': True}

    

    # Step 5: Generate content.json (requires LLM)

    if 5 not in skip_steps:

        success, content_json_file = step5_generate_content_json(article_file, output_dir)

        results['steps'][5] = {'success': success, 'file': content_json_file}

        if not success:

            print("\n⚠ Pipeline paused at Step 5 (requires LLM generation)")

            print(f"   Please generate content.json using article-shorter skill")

            return results

    else:

        content_json_file = os.path.join(output_dir, "05_content.json")

        results['steps'][5] = {'success': True, 'file': content_json_file, 'skipped': True}

    

    # Step 6: Generate Video

    if 6 not in skip_steps:

        success, video_file = step6_generate_video(content_json_file, images_dir, output_dir)

        results['steps'][6] = {'success': success, 'file': video_file}

        if not success:

            print("\n✗ Pipeline stopped at Step 6")

            return results

    else:

        results['steps'][6] = {'success': True, 'skipped': True}

    

    results['success'] = True

    

    # Print summary

    print("\n" + "="*60)

    print("PIPELINE COMPLETE")

    print("="*60)

    print(f"Output directory: {output_dir}")

    print(f"Files generated:")

    for step, info in results['steps'].items():

        status = "✓" if info.get('success') else "✗"

        skipped = " (skipped)" if info.get('skipped') else ""

        file_info = info.get('file') or info.get('dir', '')

        if file_info:

            print(f"  {status} Step {step}: {os.path.basename(file_info)}{skipped}")

    

    results['output_dir'] = output_dir

    

    return results

def step2_5_humanize(article_file, output_dir, aggressive=False):

    """Step 2.5: Humanize article using humanize-ai-text transform.py."""

    import subprocess

    print("\n" + "="*60)

    print("STEP 2.5: Humanize Article (humanize-ai-text)")

    print("="*60)

    if not os.path.exists(article_file):

        print(f"✗ Article file not found: {article_file}")

        return False, None

    humanize_script = Path(__file__).parent.parent.parent / "humanize-ai-text" / "scripts" / "transform.py"
    if not humanize_script.exists():
        humanize_script = Path("/mnt/c/Users/Administrator/.hermes/skills/humanize-ai-text/scripts/transform.py")

    if not humanize_script.exists():

        print(f"✗ humanize-ai-text transform.py not found: {humanize_script}")

        return False, None

    output_file = article_file  # overwrite in-place

    cmd = [sys.executable, str(humanize_script), article_file, "-o", output_file, "-q"]

    if aggressive:

        cmd.append("-a")

    print(f"Running: {' '.join(cmd)}")

    try:

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:

            print(f"✗ transform.py failed: {result.stderr}")

            return False, None

        # transform.py saves to output_file, confirm it exists

        if os.path.exists(output_file):

            # Count characters as rough measure

            with open(output_file, 'r', encoding='utf-8') as f:

                char_count = len(f.read())

            print(f"✓ Article humanized: {output_file} ({char_count} chars)")

            return True, output_file

        else:

            print(f"✗ Output file not created: {output_file}")

            return False, None

    except subprocess.TimeoutExpired:

        print("✗ Humanize timed out (5 min)")

        return False, None

    except Exception as e:

        print(f"✗ Error during humanize: {e}")

        return False, None

def main():

    parser = argparse.ArgumentParser(description='We-Media-Pipeline - Generate articles from topic')

    parser.add_argument('topic', nargs='?', help='Article topic (e.g., "比特币最新动态")')

    parser.add_argument('--skip', type=int, nargs='+', help='Steps to skip (e.g., --skip 2 3)')

    parser.add_argument('--type', default='news', choices=['news', 'tutorial', 'product'], help='Content type')

    parser.add_argument('--days', type=int, help='Search news from last N days')

    parser.add_argument('--num-results', type=int, help='Number of news results')

    parser.add_argument('--output', '-o', help='Custom output directory')

    parser.add_argument('--check', action='store_true', help='Check API key configuration')

    parser.add_argument('--open-folder', action='store_true', help='Open output folder after completion')

    parser.add_argument('--humanize', action='store_true', help='Run humanize-ai-text on article after Step 2')

    parser.add_argument('--humanize-aggressive', action='store_true', help='Use aggressive mode for humanization')

    args = parser.parse_args()

    

    if args.check:

        from config_loader import print_api_status

        print_api_status()

        print(f"\nDefault output directory: {get_default_output_dir()}")

        return 0

    

    

    if not args.topic:

        parser.print_help()

        print("\n✗ Error: Topic is required (unless using --check)")

        return 1

    

    

    api_status = check_api_keys()

    if not all(s['configured'] for s in api_status.values()):

        print("✗ Error: Required API keys not configured")

        print("\nRun with --check to see configuration status")

        print("Or edit: ~/.hermes/skills/wechat-article-pipeline/config.json")

        return 1

    

    

    results = run_pipeline(args.topic, skip_steps=args.skip, output_dir=args.output, humanize=args.humanize, humanize_aggressive=args.humanize_aggressive, type_=args.type, days=args.days, num_results=args.num_results)

    

    if args.open_folder and results['success']:

        import subprocess

        output_path = results.get('output_dir', '')

        if output_path and os.path.exists(output_path):

            print(f"\nOpening folder: {output_path}")

            if sys.platform == 'win32':

                subprocess.run(['explorer', output_path])

            elif sys.platform == 'darwin':

                subprocess.run(['open', output_path])

            else:

                subprocess.run(['xdg-open', output_path])

    elif results['success']:

        output_path = results.get('output_dir', '')

        print(f"\nTo open the folder, run:")

        if sys.platform == 'win32':

            print(f'  explorer "{output_path}"')

        elif sys.platform == 'darwin':

            print(f'  open "{output_path}"')

        else:

            print(f'  xdg-open "{output_path}"')

    

    

    return 0 if results['success'] else 1

if __name__ == '__main__':

    sys.exit(main())

