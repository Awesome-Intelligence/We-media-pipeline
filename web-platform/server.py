#!/usr/bin/env python3
import http.server
import json
import os
import sys
import datetime
import re
from pathlib import Path
from urllib.parse import urlparse
import subprocess

BASE_DIR = Path(__file__).parent.parent.resolve()

SKILL_DIRS = {
    'news-search': BASE_DIR / 'news-searcher' / 'scripts',
    'image-search-baidu': BASE_DIR / 'image-searcher' / 'scripts',
    'markdown-to-word': BASE_DIR / 'article-formatter' / 'scripts',
    'wechat-video-generator': BASE_DIR / 'we-video-generator' / 'scripts',
}

sys.path.insert(0, str(BASE_DIR / 'web-platform'))
from llm_client import LLMClient, get_available_models

def get_default_output_dir():
    config = load_config()
    output_dir = config.get('default_output_dir', '').strip()
    if output_dir:
        return output_dir
    home = Path.home()
    desktop = home / 'Desktop'
    if not desktop.exists():
        desktop = home / '桌面'
    return str(desktop / 'OpenClaw生成文章')

def load_config():
    config_path = BASE_DIR / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def create_topic_folder(topic, base_dir=None):
    if base_dir is None:
        base_dir = get_default_output_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in topic).strip().replace(' ', '_')
    folder_name = f"{timestamp}_{safe_topic}"
    output_dir = os.path.join(base_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def ensure_topic_folder(topic):
    base_dir = get_default_output_dir()
    return create_topic_folder(topic, base_dir)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def read_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            return self.rfile.read(content_length).decode('utf-8')
        return None

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path.startswith('/api/file/stream/'):
            try:
                file_path = parsed.path[len('/api/file/stream/'):]
                import urllib.parse
                file_path = urllib.parse.unquote(file_path)

                if not os.path.exists(file_path):
                    self.send_json({'success': False, 'error': '文件不存在'}, 404)
                    return

                ext = os.path.splitext(file_path)[1].lower()
                mime_types = {
                    '.mp4': 'video/mp4',
                    '.avi': 'video/x-msvideo',
                    '.mov': 'video/quicktime',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                }
                content_type = mime_types.get(ext, 'application/octet-stream')

                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', os.path.getsize(file_path))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()

                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())

            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
            return

        if parsed.path == '/api/status':
            config = load_config()
            available_models = get_available_models(config)
            self.send_json({
                'success': True,
                'tavily_configured': bool(config.get('tavily_api_key', '').strip()),
                'minimax_configured': bool(config.get('minimax_api_key', '').strip()),
                'deepseek_configured': bool(config.get('deepseek_api_key', '').strip()),
                'openai_configured': bool(config.get('openai_api_key', '').strip()),
                'pexels_configured': bool(config.get('pexels_api_key', '').strip()),
                'output_dir': config.get('default_output_dir', ''),
                'available_models': available_models,
            })

        elif parsed.path == '/api/config':
            config = load_config()
            self.send_json({'success': True, 'config': config})

        elif parsed.path == '/':
            index_path = Path(__file__).parent / 'index.html'
            if index_path.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_json({'success': False, 'error': 'index.html not found'}, 404)

        else:
            self.send_json({'success': False, 'error': 'Not found'}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self.read_body()

        if parsed.path == '/api/config':
            try:
                data = json.loads(body) if body else {}
                config_path = BASE_DIR / 'config.json'
                config = {}
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                for key in ['tavily_api_key', 'minimax_api_key', 'minimax_model', 'deepseek_api_key', 'deepseek_base_url', 'deepseek_model', 'openai_api_key', 'openai_base_url', 'openai_model', 'custom_api_key', 'custom_base_url', 'custom_model', 'default_model_provider', 'pexels_api_key', 'default_output_dir', 'article_editor', 'article_reviewer', 'style_dir', 'article_fetch_dir']:
                    if key in data:
                        config[key] = data[key]

                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                self.send_json({'success': True, 'message': '配置已保存'})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/news/search':
            try:
                data = json.loads(body) if body else {}
                query = data.get('query', '')
                topic = data.get('topic', '')
                days = int(data.get('days', 7))
                num = int(data.get('num', 10))
                output_dir = data.get('output_dir', '')

                if not query:
                    self.send_json({'success': False, 'error': '缺少查询关键词'}, 400)
                    return

                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                else:
                    output_dir = ensure_topic_folder(topic)

                config = load_config()
                api_key = config.get('tavily_api_key', '')

                if not api_key:
                    self.send_json({'success': False, 'error': 'Tavily API Key 未配置'}, 400)
                    return

                news_script = SKILL_DIRS['news-search'] / 'search_news.py'
                if not news_script.exists():
                    self.send_json({'success': False, 'error': 'news-searcher 脚本未找到'}, 404)
                    return

                result = subprocess.run(
                    [sys.executable, str(news_script), query, '-n', str(num), '-d', str(days), '-k', api_key, '-f', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(news_script.parent)
                )

                if result.returncode == 0:
                    output = result.stdout.strip()
                    start_idx = output.find('{')

                    if start_idx >= 0:
                        json_str = output[start_idx:]
                        bracket_count = 0
                        end_idx = len(json_str)

                        for i, c in enumerate(json_str):
                            if c == '{':
                                bracket_count += 1
                            elif c == '}':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    end_idx = i + 1
                                    break

                        json_str = json_str[:end_idx]
                        results = json.loads(json_str)

                        research_file = os.path.join(output_dir, '01_research.md')
                        with open(research_file, 'w', encoding='utf-8') as f:
                            f.write(f"# 研究资料: {topic}\n\n")
                            for r in results.get('results', []):
                                f.write(f"## {r.get('title', '')}\n")
                                f.write(f"来源: {r.get('url', '')}\n")
                                f.write(f"{r.get('description', '')}\n\n")

                        self.send_json({'success': True, 'results': results, 'output_dir': output_dir, 'research_file': research_file})
                    else:
                        self.send_json({'success': False, 'error': 'No JSON found in output'})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500]})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '搜索超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/article/generate':
            try:
                data = json.loads(body) if body else {}
                research_file = data.get('research_file', '')
                output_dir = data.get('output_dir', '')
                model_provider = data.get('model_provider', 'minimax')
                model_name = data.get('model_name', None)
                base_url = data.get('base_url', None)

                if not research_file or not os.path.exists(research_file):
                    self.send_json({'success': False, 'error': '研究资料文件不存在'}, 400)
                    return

                config = load_config()
                
                api_key = config.get(f'{model_provider}_api_key', '').strip()
                if not api_key:
                    provider_info = LLMClient.SUPPORTED_MODELS.get(model_provider)
                    provider_name = provider_info['name'] if provider_info else model_provider
                    self.send_json({'success': False, 'error': f'{provider_name} API Key 未配置'}, 400)
                    return

                # Get model name from request or config
                if not model_name:
                    model_name = config.get(f'{model_provider}_model', '').strip()
                
                # Get base_url from request or config
                if not base_url:
                    base_url = config.get(f'{model_provider}_base_url', '').strip()
                    if not base_url and model_provider != 'openai':
                        provider_info = LLMClient.SUPPORTED_MODELS.get(model_provider)
                        if provider_info:
                            base_url = provider_info.get('default_base_url', '')

                with open(research_file, 'r', encoding='utf-8') as f:
                    research_content = f.read()

                style_dir = config.get('style_dir', '').strip()
                if style_dir and os.path.exists(style_dir):
                    style_guide_path = Path(style_dir) / 'style-guide.md'
                else:
                    style_guide_path = BASE_DIR / 'reference' / 'style-guide.md'

                if not style_guide_path.exists():
                    self.send_json({'success': False, 'error': f'style-guide.md 未找到: {style_guide_path}'}, 404)
                    return

                with open(style_guide_path, 'r', encoding='utf-8') as f:
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
                    client = LLMClient(model_provider, api_key, model_name, base_url)
                    article_text = client.generate(system_prompt, "根据以上研究资料和风格规范，生成一篇微信公众号文章。", max_tokens=8192)
                except Exception as e:
                    self.send_json({'success': False, 'error': f'LLM 调用失败: {str(e)}'}, 500)
                    return

                if not article_text:
                    self.send_json({'success': False, 'error': 'LLM 返回内容为空'}, 500)
                    return

                if not output_dir:
                    self.send_json({'success': False, 'error': '缺少 output_dir'}, 400)
                    return

                article_file = os.path.join(output_dir, '02_article.md')
                with open(article_file, 'w', encoding='utf-8') as f:
                    f.write(article_text)

                self.send_json({'success': True, 'article': article_text, 'file': article_file, 'output_dir': output_dir})

            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/model/test':
            try:
                data = json.loads(body) if body else {}
                provider = data.get('provider', '').lower()
                api_key = data.get('api_key', '').strip()
                model = data.get('model', '').strip()
                base_url = data.get('base_url', '').strip()
                
                if not provider:
                    self.send_json({'success': False, 'error': '请指定模型提供商'}, 400)
                    return
                
                if not api_key:
                    self.send_json({'success': False, 'error': '请提供 API Key'}, 400)
                    return
                
                try:
                    client = LLMClient(provider, api_key, model, base_url)
                    response = client.generate("你是一个测试助手。", "请回复 '测试成功'。", max_tokens=10)
                    
                    if response and '测试成功' in response:
                        self.send_json({'success': True, 'message': '连接成功'})
                    else:
                        self.send_json({'success': True, 'message': '连接成功', 'response': response.strip()[:50]})
                
                except Exception as e:
                    error_msg = str(e)
                    if 'rate_limit' in error_msg.lower() or '429' in error_msg:
                        self.send_json({'success': True, 'message': '连接成功（但 API 额度已用完）', 'warning': 'API 调用额度已用完，请稍后重试'})
                    else:
                        self.send_json({'success': False, 'error': f'连接失败: {error_msg}'})
            
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/images/search':
            try:
                data = json.loads(body) if body else {}
                query = data.get('query', '')
                num = int(data.get('num', 6))
                output_dir = data.get('output_dir', '')

                if not query:
                    self.send_json({'success': False, 'error': '缺少查询关键词'}, 400)
                    return

                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                else:
                    output_dir = ensure_topic_folder('')

                images_all_dir = os.path.join(output_dir, 'images-all')
                images_good_dir = os.path.join(output_dir, 'images_good')
                os.makedirs(images_all_dir, exist_ok=True)
                os.makedirs(images_good_dir, exist_ok=True)

                baidu_script = SKILL_DIRS['image-search-baidu'] / 'search_baidu.py'
                if not baidu_script.exists():
                    self.send_json({'success': False, 'error': '百度图片搜索脚本未找到'}, 404)
                    return

                result = subprocess.run(
                    [sys.executable, str(baidu_script), query, '-n', str(num), '-o', images_all_dir, '-p', 'img'],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(baidu_script.parent)
                )

                if result.returncode == 0:
                    tmp_path = Path(images_all_dir)
                    images = []
                    good_count = 0

                    for img_file in sorted(tmp_path.glob('*.jpg'))[:num]:
                        img_path = str(img_file.absolute())
                        is_valid, w, h = check_resolution(img_file)
                        images.append({
                            'path': img_path,
                            'url': img_file.name,
                            'title': f'配图 {len(images) + 1}',
                            'source': 'Baidu Image'
                        })
                        if is_valid and good_count < 10:
                            good_name = f"baidu_{len(images):02d}_{w}x{h}{img_file.suffix}"
                            import shutil
                            shutil.copy2(img_file, os.path.join(images_good_dir, good_name))
                            good_count += 1

                    if not images:
                        images = [{'url': f'https://picsum.photos/400/300?random={i}', 'title': f'配图 {i+1}', 'source': 'Pexels'} for i in range(num)]

                    self.send_json({'success': True, 'images': images, 'output_dir': output_dir, 'images_dir': images_good_dir})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500] or result.stdout[:500]})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '搜索超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/word/export':
            try:
                data = json.loads(body) if body else {}
                article_file = data.get('article_file', '')
                output_dir = data.get('output_dir', '')

                if not article_file or not os.path.exists(article_file):
                    self.send_json({'success': False, 'error': '文章文件不存在'}, 400)
                    return

                if not output_dir:
                    self.send_json({'success': False, 'error': '缺少 output_dir'}, 400)
                    return

                images_dir = data.get('images_dir', os.path.join(output_dir, 'images_good'))

                md_to_word_script = SKILL_DIRS['markdown-to-word'] / 'md_to_word.py'
                if not md_to_word_script.exists():
                    self.send_json({'success': False, 'error': 'article-formatter 脚本未找到'}, 404)
                    return

                with open(article_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                print(f"[DEBUG] Before re.search, content length: {len(content)}", file=sys.stderr)
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                print(f"[DEBUG] After re.search, title_match: {title_match}", file=sys.stderr)
                article_title = title_match.group(1) if title_match else 'article'
                print(f"[DEBUG] article_title: {article_title}", file=sys.stderr)
                safe_title = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in article_title).strip().replace(' ', '_')
                docx_path = os.path.join(output_dir, f'04_{safe_title}.docx')

                result = subprocess.run(
                    [sys.executable, str(md_to_word_script), article_file, '-o', docx_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(md_to_word_script.parent)
                )

                if result.returncode == 0:
                    self.send_json({'success': True, 'path': docx_path, 'output_dir': output_dir})
                else:
                    stderr_str = str(result.stderr) if result.stderr else 'None'
                    print(f"[DEBUG] md_to_word failed: returncode={result.returncode}, stderr_type={type(result.stderr)}, stderr={stderr_str[:500]}", file=sys.stderr)
                    error_msg = stderr_str[:500] if len(stderr_str) <= 500 else stderr_str[:500] + '...'
                    self.send_json({'success': False, 'error': error_msg})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '转换超时'}, 504)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/content/generate':
            try:
                data = json.loads(body) if body else {}
                article_file = data.get('article_file', '')
                output_dir = data.get('output_dir', '')

                if not article_file or not os.path.exists(article_file):
                    self.send_json({'success': False, 'error': '文章文件不存在'}, 400)
                    return

                if not output_dir:
                    self.send_json({'success': False, 'error': '缺少 output_dir'}, 400)
                    return

                config = load_config()
                minimax_key = config.get('minimax_api_key', '').strip()
                if not minimax_key:
                    self.send_json({'success': False, 'error': 'MiniMax API Key 未配置'}, 400)
                    return

                with open(article_file, 'r', encoding='utf-8') as f:
                    article_content = f.read()

                title_match = re.search(r'^#\s+(.+)$', article_content, re.MULTILINE)
                article_title = title_match.group(1) if title_match else 'article'

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

                try:
                    import anthropic
                except ImportError:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', 'anthropic', '-q'], check=True)
                    import anthropic

                client = anthropic.Anthropic(
                    base_url="https://api.minimaxi.com/anthropic",
                    api_key=minimax_key,
                )

                message = client.messages.create(
                    model="MiniMax-M2.7",
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": [{"type": "text", "text": f"Article title: {article_title}\n\nArticle content:\n{article_content[:3000]}"}]}],
                )

                response_text = ""
                for block in message.content:
                    if hasattr(block, 'text') and block.text:
                        response_text += block.text

                json_match = re.search(r'\{[\s\S]+?\}', response_text)
                if not json_match:
                    self.send_json({'success': False, 'error': f'No JSON found in response: {response_text[:200]}'}, 500)
                    return

                try:
                    content_data = json.loads(json_match.group())
                except Exception:
                    raw = json_match.group()
                    for old, new in [('\u201c', '\u0022'), ('\u201d', '\u0022'), ('\u300c', '\u0022'), ('\u300d', '\u0022'), ('\u2018', '\u0027'), ('\u2019', '\u0027')]:
                        if old in raw:
                            raw = raw.replace(old, new)
                    try:
                        content_data = json.loads(raw)
                    except Exception:
                        raw = re.sub(r',(\s*[}\]])', r'\1', raw)
                        raw = re.sub(r'[^\x00-\x7F]+', '', raw)
                        content_data = json.loads(raw)

                images_dir = os.path.join(output_dir, 'images_good')
                image_files = []
                if os.path.exists(images_dir):
                    for f in os.listdir(images_dir):
                        if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                            image_files.append(os.path.join(images_dir, f))
                    image_files = sorted(image_files)[:3]

                content_data['images'] = image_files

                content_json_path = os.path.join(output_dir, '05_content.json')
                with open(content_json_path, 'w', encoding='utf-8') as f:
                    json.dump(content_data, f, ensure_ascii=False, indent=2)

                self.send_json({'success': True, 'file': content_json_path, 'output_dir': output_dir})

            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/video/generate':
            try:
                data = json.loads(body) if body else {}
                content_json_file = data.get('content_json_file', '')
                images_dir = data.get('images_dir', '')
                output_dir = data.get('output_dir', '')

                if not content_json_file or not os.path.exists(content_json_file):
                    self.send_json({'success': False, 'error': 'content.json 文件不存在'}, 400)
                    return

                if not images_dir or not os.path.exists(images_dir):
                    self.send_json({'success': False, 'error': 'images_dir 不存在'}, 400)
                    return

                if not output_dir:
                    self.send_json({'success': False, 'error': '缺少 output_dir'}, 400)
                    return

                with open(content_json_file, 'r', encoding='utf-8') as f:
                    content_data = json.load(f)

                main_title = content_data.get('main_title', 'output')
                safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in main_title).strip().replace(' ', '_')[:30]
                video_path = os.path.join(output_dir, f'06_{safe_title}.mp4')

                video_script = SKILL_DIRS['wechat-video-generator'] / 'run_video_generator.py'
                if not video_script.exists():
                    self.send_json({'success': False, 'error': '视频生成脚本未找到'}, 404)
                    return

                result = subprocess.run(
                    [sys.executable, str(video_script), content_json_file, images_dir, video_path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(video_script.parent)
                )

                if result.returncode == 0 and os.path.exists(video_path):
                    self.send_json({'success': True, 'path': video_path, 'output_dir': output_dir})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500] or result.stdout[:500]})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '视频生成超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/library/scan':
            try:
                data = json.loads(body) if body else {}
                output_dir = data.get('output_dir', '') or get_default_output_dir()

                if not os.path.exists(output_dir):
                    self.send_json({'success': True, 'projects': []})
                    return

                projects = []
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    if not os.path.isdir(item_path):
                        continue

                    project = {
                        'name': item,
                        'path': item_path,
                        'files': []
                    }

                    for f in os.listdir(item_path):
                        if os.path.isfile(os.path.join(item_path, f)):
                            ext = os.path.splitext(f)[1].lower()
                            file_type = 'other'
                            if ext in ['.md']:
                                file_type = 'article'
                            elif ext in ['.docx', '.doc']:
                                file_type = 'word'
                            elif f == '05_content.json':
                                file_type = 'content'
                            elif ext in ['.mp4', '.avi', '.mov']:
                                file_type = 'video'
                            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                                file_type = 'image'
                            project['files'].append({
                                'name': f,
                                'path': os.path.join(item_path, f),
                                'type': file_type
                            })

                    if project['files']:
                        projects.append(project)

                projects.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)

                self.send_json({'success': True, 'projects': projects, 'output_dir': output_dir})

            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/file/read':
            try:
                data = json.loads(body) if body else {}
                file_path = data.get('path', '')

                if not file_path:
                    self.send_json({'success': False, 'error': '缺少文件路径'}, 400)
                    return

                if not os.path.exists(file_path):
                    self.send_json({'success': False, 'error': '文件不存在'}, 404)
                    return

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                try:
                    data = json.loads(content)
                    self.send_json({'success': True, 'data': data})
                except:
                    self.send_json({'success': True, 'content': content})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/file/save':
            try:
                data = json.loads(body) if body else {}
                file_path = data.get('path', '')
                content = data.get('content', '')

                if not file_path:
                    self.send_json({'success': False, 'error': '缺少文件路径'}, 400)
                    return

                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.send_json({'success': True, 'message': '文件已保存'})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/file/open':
            try:
                data = json.loads(body) if body else {}
                file_path = data.get('path', '')

                if not file_path:
                    self.send_json({'success': False, 'error': '缺少文件路径'}, 400)
                    return

                if not os.path.exists(file_path):
                    self.send_json({'success': False, 'error': '文件或目录不存在'}, 404)
                    return

                if sys.platform == 'win32':
                    os.startfile(file_path)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', file_path])
                else:
                    subprocess.run(['xdg-open', file_path])

                self.send_json({'success': True, 'message': '已打开'})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/pipeline/run':
            try:
                data = json.loads(body) if body else {}
                topic = data.get('topic', '')
                days = int(data.get('days', 7))

                if not topic:
                    self.send_json({'success': False, 'error': '缺少创作主题'}, 400)
                    return

                config = load_config()
                api_status = {
                    'tavily': bool(config.get('tavily_api_key', '').strip()),
                    'minimax': bool(config.get('minimax_api_key', '').strip()),
                }

                if not all(api_status.values()):
                    self.send_json({
                        'success': False,
                        'error': f'API Key 未配置完整: Tavily={api_status["tavily"]}, MiniMax={api_status["minimax"]}'
                    }, 400)
                    return

                pipeline_script = BASE_DIR / 'we-media-pipeline' / 'scripts' / 'run_pipeline.py'
                if not pipeline_script.exists():
                    self.send_json({'success': False, 'error': 'pipeline 脚本未找到'}, 404)
                    return

                output_dir = ensure_topic_folder(topic)

                self.send_json({'success': True, 'message': '流水线已启动', 'output_dir': output_dir})

                subprocess.Popen(
                    [sys.executable, str(pipeline_script), topic, '-o', output_dir, '--days', str(days)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(pipeline_script.parent)
                )

            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/article/fetch':
            try:
                data = json.loads(body) if body else {}
                url = data.get('url', '')
                output_dir = data.get('output_dir', '')

                if not url:
                    self.send_json({'success': False, 'error': '缺少文章链接'}, 400)
                    return

                if not url.startswith('http'):
                    url = 'https://' + url

                if not output_dir:
                    output_dir = get_default_output_dir()

                os.makedirs(output_dir, exist_ok=True)

                fetch_script = BASE_DIR / 'article-fetcher' / 'scripts' / 'fetch_wechat_article.py'
                if not fetch_script.exists():
                    self.send_json({'success': False, 'error': '文章抓取脚本未找到'}, 404)
                    return

                result = subprocess.run(
                    [sys.executable, str(fetch_script), url, '-o', output_dir],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(fetch_script.parent)
                )

                if result.returncode == 0:
                    title_match = re.search(r'保存到[:：]\s*(.+)', result.stdout)
                    path_match = re.search(r'文件已保存[:：]\s*(.+)', result.stdout)

                    self.send_json({
                        'success': True,
                        'message': '文章抓取成功',
                        'path': path_match.group(1) if path_match else output_dir,
                        'title': title_match.group(1) if title_match else ''
                    })
                else:
                    error_output = result.stderr or result.stdout
                    self.send_json({'success': False, 'error': error_output[:500]})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '抓取超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/dialog/select-directory':
            try:
                import tkinter as tk
                from tkinter import filedialog
                
                # Create hidden tkinter window
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                # Open directory dialog
                directory = filedialog.askdirectory(title='选择文件夹')
                
                root.destroy()
                
                if directory:
                    self.send_json({'success': True, 'path': directory})
                else:
                    self.send_json({'success': False, 'error': '用户取消选择'})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        else:
            self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)


def check_resolution(image_path, min_width=800, min_height=600):
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            w, h = img.size
            if w > 0 and w >= min_width and h >= min_height:
                return True, w, h
            return False, w, h
    except Exception:
        return False, 0, 0


def run_server(port=8080):
    server = http.server.HTTPServer(('localhost', port), Handler)
    print(f"\n🎯 We 自媒体创作服务已启动")
    print(f"   访问地址: http://localhost:{port}")
    print(f"   按 Ctrl+C 停止服务\n")
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='We 自媒体创作 - 自媒体创作平台后端服务')
    parser.add_argument('-p', '--port', type=int, default=8080, help='服务端口 (默认: 8080)')
    args = parser.parse_args()
    run_server(args.port)