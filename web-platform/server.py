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

PIPELINE_SCRIPT = BASE_DIR / 'we-media-pipeline' / 'scripts' / 'run_pipeline.py'

def find_json_in_output(output):
    lines = output.strip().split('\n')
    for i in range(len(lines) - 1, -1, -1):
        if '{' in lines[i]:
            json_str = '\n'.join(lines[i:])
            try:
                return json.loads(json_str)
            except:
                pass
    return None

LOGS = []
LOG_MAX = 1000
LOG_FILE = BASE_DIR / 'logs.json'

def load_logs():
    global LOGS
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                LOGS = json.load(f)
        except:
            LOGS = []

def save_logs():
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(LOGS[-LOG_MAX:], f, ensure_ascii=False)
    except Exception as e:
        print(f'保存日志失败: {e}')

if LOG_FILE.exists():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                LOGS = data[-LOG_MAX:]
    except Exception:
        pass

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

        elif parsed.path == '/api/log/add':
            try:
                data = json.loads(body) if body else {}
                log_entry = {
                    'time': data.get('time', datetime.datetime.now().strftime('%H:%M:%S')),
                    'level': data.get('level', 'info'),
                    'message': data.get('message', '')
                }
                LOGS.append(log_entry)
                if len(LOGS) > LOG_MAX:
                    LOGS = LOGS[-LOG_MAX:]
                save_logs()
                self.send_json({'success': True})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/log/list':
            try:
                self.send_json({'success': True, 'logs': LOGS})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/log/clear':
            try:
                LOGS.clear()
                save_logs()
                self.send_json({'success': True})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/news/search':
            try:
                data = json.loads(body) if body else {}
                query = data.get('query', '')
                topic = data.get('topic', '')
                days = int(data.get('days', 7))
                num = int(data.get('num', 10))
                article_type = data.get('type', 'news')
                output_dir = data.get('output_dir', '')

                if not query:
                    self.send_json({'success': False, 'error': '缺少查询关键词'}, 400)
                    return

                if not PIPELINE_SCRIPT.exists():
                    self.send_json({'success': False, 'error': 'Pipeline 脚本未找到'}, 404)
                    return

                cmd = [
                    sys.executable, str(PIPELINE_SCRIPT),
                    topic or query,
                    '--skip', '2', '3', '4', '5', '6',
                    '--type', article_type,
                    '--days', str(days),
                    '--num-results', str(num),
                    '--json'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                pipeline_results = find_json_in_output(result.stdout)
                if pipeline_results:
                    step1_data = pipeline_results.get('steps', {}).get('1', {})
                    
                    if step1_data.get('success'):
                        content = step1_data.get('content', '')
                        output_dir = pipeline_results.get('output_dir', '')
                        research_file = step1_data.get('file', '')
                        results_list = []
                        if pipeline_results.get('success') and 'steps' in pipeline_results:
                            step1_results = pipeline_results.get('steps', {}).get('1', {})
                            if 'results' in step1_results:
                                results_list = step1_results['results']
                        self.send_json({
                            'success': True,
                            'output_dir': output_dir,
                            'research_file': research_file,
                            'research_content': content,
                            'results': {'results': results_list}
                        })
                    else:
                        error_msg = step1_data.get('error', '搜索失败')
                        self.send_json({'success': False, 'error': error_msg})
                else:
                    error_output = result.stdout or result.stderr or ''
                    if error_output:
                        lines = error_output.strip().split('\n')
                        errors = [l for l in lines if '✗' in l or 'Error' in l or 'error' in l or 'Failed' in l or 'failed' in l]
                        error_output = '\n'.join(errors[-3:]) if errors else 'Pipeline 输出解析失败'
                    else:
                        error_output = 'Pipeline 输出解析失败'
                    self.send_json({'success': False, 'error': error_output})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '搜索超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)

        elif parsed.path == '/api/article/generate':
            try:
                data = json.loads(body) if body else {}
                research_file = data.get('research_file', '')

                if not research_file or not os.path.exists(research_file):
                    self.send_json({'success': False, 'error': '研究资料文件不存在'}, 400)
                    return

                if not PIPELINE_SCRIPT.exists():
                    self.send_json({'success': False, 'error': 'Pipeline 脚本未找到'}, 404)
                    return

                topic = os.path.basename(os.path.dirname(research_file))
                output_dir = os.path.dirname(research_file)
                cmd = [
                    sys.executable, str(PIPELINE_SCRIPT),
                    topic,
                    '--skip', '1', '3', '4', '5', '6',
                    '--output', output_dir,
                    '--json'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                pipeline_results = find_json_in_output(result.stdout)
                if pipeline_results:
                    step2_data = pipeline_results.get('steps', {}).get('2', {})
                    if step2_data.get('success'):
                        article_text = step2_data.get('content', '')
                        output_dir = pipeline_results.get('output_dir', os.path.dirname(research_file))
                        article_file = step2_data.get('file', '')
                        self.send_json({
                            'success': True,
                            'article': article_text,
                            'file': article_file,
                            'output_dir': output_dir
                        })
                    else:
                        error_msg = step2_data.get('error', '文章生成失败')
                        self.send_json({'success': False, 'error': error_msg})
                else:
                    error_output = result.stdout or result.stderr or ''
                    if error_output:
                        lines = error_output.strip().split('\n')
                        errors = [l for l in lines if '✗' in l or 'Error' in l or 'error' in l or 'Failed' in l or 'failed' in l]
                        error_output = '\n'.join(errors[-3:]) if errors else 'Pipeline 输出解析失败'
                    else:
                        error_output = 'Pipeline 输出解析失败'
                    self.send_json({'success': False, 'error': error_output})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '生成超时'}, 504)

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

                if not output_dir or not os.path.exists(output_dir):
                    self.send_json({'success': False, 'error': '输出目录不存在'}, 400)
                    return

                if not PIPELINE_SCRIPT.exists():
                    self.send_json({'success': False, 'error': 'Pipeline 脚本未找到'}, 404)
                    return

                topic = os.path.basename(output_dir)
                cmd = [
                    sys.executable, str(PIPELINE_SCRIPT),
                    topic,
                    '--skip', '1', '2', '4', '5', '6',
                    '--output', output_dir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                if result.returncode == 0:
                    try:
                        pipeline_results = json.loads(result.stdout)
                        step3_data = pipeline_results.get('steps', {}).get('3', {})
                        images_list = step3_data.get('images', [])
                        output_dir = pipeline_results.get('output_dir', output_dir)
                        images_good_dir = step3_data.get('dir', os.path.join(output_dir, 'images_good'))

                        images = []
                        for img_name in images_list[:num]:
                            img_file = Path(images_good_dir) / img_name
                            if img_file.exists():
                                images.append({
                                    'path': str(img_file.absolute()),
                                    'url': img_file.name,
                                    'title': f'配图 {len(images) + 1}',
                                    'source': 'Baidu Image'
                                })

                        self.send_json({
                            'success': True,
                            'images': images,
                            'output_dir': output_dir,
                            'images_dir': images_good_dir
                        })
                    except json.JSONDecodeError:
                        self.send_json({'success': False, 'error': 'Pipeline 输出解析失败'})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500] or '图片搜索失败'})

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
                    output_dir = os.path.dirname(article_file)

                if not PIPELINE_SCRIPT.exists():
                    self.send_json({'success': False, 'error': 'Pipeline 脚本未找到'}, 404)
                    return

                topic = os.path.basename(output_dir)
                cmd = [
                    sys.executable, str(PIPELINE_SCRIPT),
                    topic,
                    '--skip', '1', '2', '3', '5', '6',
                    '--output', output_dir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    import glob
                    docx_files = glob.glob(os.path.join(output_dir, '04_*.docx'))
                    if docx_files:
                        self.send_json({'success': True, 'path': docx_files[0], 'output_dir': output_dir})
                    else:
                        self.send_json({'success': False, 'error': 'Word 文件未生成'})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500] or '导出失败'})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '转换超时'}, 504)

        elif parsed.path == '/api/content/generate':
            try:
                data = json.loads(body) if body else {}
                article_file = data.get('article_file', '')
                output_dir = data.get('output_dir', '')

                if not article_file or not os.path.exists(article_file):
                    self.send_json({'success': False, 'error': '文章文件不存在'}, 400)
                    return

                if not output_dir:
                    output_dir = os.path.dirname(article_file)

                if not PIPELINE_SCRIPT.exists():
                    self.send_json({'success': False, 'error': 'Pipeline 脚本未找到'}, 404)
                    return

                topic = os.path.basename(output_dir)
                cmd = [
                    sys.executable, str(PIPELINE_SCRIPT),
                    topic,
                    '--skip', '1', '2', '3', '4', '6',
                    '--output', output_dir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                content_json_path = os.path.join(output_dir, '05_content.json')

                if result.returncode == 0 and os.path.exists(content_json_path):
                    self.send_json({'success': True, 'file': content_json_path, 'output_dir': output_dir})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500] or '内容提炼失败'})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '生成超时'}, 504)

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
                    images_dir = os.path.join(os.path.dirname(content_json_file), 'images_good')
                    if not os.path.exists(images_dir):
                        self.send_json({'success': False, 'error': 'images_dir 不存在'}, 400)
                        return

                if not output_dir:
                    output_dir = os.path.dirname(content_json_file)

                if not PIPELINE_SCRIPT.exists():
                    self.send_json({'success': False, 'error': 'Pipeline 脚本未找到'}, 404)
                    return

                topic = os.path.basename(output_dir)
                cmd = [
                    sys.executable, str(PIPELINE_SCRIPT),
                    topic,
                    '--skip', '1', '2', '3', '4', '5',
                    '--output', output_dir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                import glob as glob_module
                video_files = glob_module.glob(os.path.join(output_dir, '06_*.mp4'))

                if result.returncode == 0 and video_files:
                    self.send_json({'success': True, 'path': video_files[0], 'output_dir': output_dir})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500] or '视频生成失败'})

            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '视频生成超时'}, 504)

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
                    [sys.executable, str(pipeline_script), topic, '--output', output_dir, '--days', str(days)],
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