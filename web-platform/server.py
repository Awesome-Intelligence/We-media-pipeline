#!/usr/bin/env python3
import http.server
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import subprocess

BASE_DIR = Path(__file__).parent.parent.resolve()
SKILL_DIRS = {
    'news-search': BASE_DIR / 'news-search' / 'scripts',
    'image-search-baidu': BASE_DIR / 'image-search-baidu' / 'scripts',
    'markdown-to-word': BASE_DIR / 'markdown-to-word' / 'scripts',
    'wechat-video-generator': BASE_DIR / 'wechat-video-generator' / 'scripts',
}

def load_config():
    config_path = BASE_DIR / 'wechat-media-publish-pipeline' / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

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
        
        if parsed.path == '/api/status':
            config = load_config()
            self.send_json({
                'success': True,
                'tavily_configured': bool(config.get('tavily_api_key', '').strip()),
                'minimax_configured': bool(config.get('minimax_api_key', '').strip()),
                'pexels_configured': bool(config.get('pexels_api_key', '').strip()),
                'output_dir': config.get('default_output_dir', ''),
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
                config_path = BASE_DIR / 'wechat-media-publish-pipeline' / 'config.json'
                config = {}
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                
                for key in ['tavily_api_key', 'minimax_api_key', 'pexels_api_key', 'default_output_dir', 'article_editor', 'article_reviewer']:
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
                days = int(data.get('days', 7))
                num = int(data.get('num', 10))
                
                if not query:
                    self.send_json({'success': False, 'error': '缺少查询关键词'}, 400)
                    return
                
                config = load_config()
                api_key = config.get('tavily_api_key', '')
                
                if not api_key:
                    self.send_json({'success': False, 'error': 'Tavily API Key 未配置'}, 400)
                    return
                
                news_script = SKILL_DIRS['news-search'] / 'search_news.py'
                if not news_script.exists():
                    self.send_json({'success': False, 'error': 'news-search 脚本未找到'}, 404)
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
                        self.send_json({'success': True, 'results': results})
                    else:
                        self.send_json({'success': False, 'error': 'No JSON found in output'})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500]})
            
            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '搜索超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        
        elif parsed.path == '/api/images/search':
            try:
                data = json.loads(body) if body else {}
                query = data.get('query', '')
                num = int(data.get('num', 6))
                
                if not query:
                    self.send_json({'success': False, 'error': '缺少查询关键词'}, 400)
                    return
                
                config = load_config()
                
                baidu_script = SKILL_DIRS['image-search-baidu'] / 'search_baidu.py'
                if not baidu_script.exists():
                    self.send_json({'success': False, 'error': '百度图片搜索脚本未找到'}, 404)
                    return
                
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    result = subprocess.run(
                        [sys.executable, str(baidu_script), query, '-n', str(num), '-o', tmpdir, '-p', 'img'],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=str(baidu_script.parent)
                    )
                    
                    if result.returncode == 0:
                        from pathlib import Path
                        tmp_path = Path(tmpdir)
                        images = []
                        
                        for img_file in sorted(tmp_path.glob('*.jpg'))[:num]:
                            img_path = str(img_file.absolute())
                            images.append({
                                'path': img_path,
                                'url': img_file.name,
                                'title': f'配图 {len(images) + 1}',
                                'source': 'Baidu Image'
                            })
                        
                        if not images:
                            images = [
                                {'url': f'https://picsum.photos/400/300?random={i}', 'title': f'配图 {i+1}', 'source': 'Pexels'}
                                for i in range(num)
                            ]
                        
                        self.send_json({'success': True, 'images': images})
                    else:
                        self.send_json({'success': False, 'error': result.stderr[:500] or result.stdout[:500]})
            
            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '搜索超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        
        elif parsed.path == '/api/word/export':
            try:
                data = json.loads(body) if body else {}
                markdown_content = data.get('markdown', '')
                title = data.get('title', 'article')
                
                if not markdown_content:
                    self.send_json({'success': False, 'error': '缺少 Markdown 内容'}, 400)
                    return
                
                config = load_config()
                output_dir = config.get('default_output_dir', str(BASE_DIR / 'output'))
                os.makedirs(output_dir, exist_ok=True)
                
                md_path = os.path.join(output_dir, 'temp_article.md')
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                md_to_word_script = SKILL_DIRS['markdown-to-word'] / 'md_to_word.py'
                if not md_to_word_script.exists():
                    self.send_json({'success': False, 'error': 'markdown-to-word 脚本未找到'}, 404)
                    return
                
                safe_title = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in title).strip().replace(' ', '_')
                docx_path = os.path.join(output_dir, f'{safe_title}.docx')
                
                result = subprocess.run(
                    [sys.executable, str(md_to_word_script), md_path, '-o', docx_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(md_to_word_script.parent)
                )
                
                if result.returncode == 0:
                    self.send_json({'success': True, 'path': docx_path})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500]})
            
            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '转换超时'}, 504)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        
        elif parsed.path == '/api/video/generate':
            try:
                data = json.loads(body) if body else {}
                content_json = data.get('content_json', {})
                images = data.get('images', [])
                
                if not content_json:
                    self.send_json({'success': False, 'error': '缺少内容配置'}, 400)
                    return
                
                config = load_config()
                output_dir = config.get('default_output_dir', str(BASE_DIR / 'output'))
                os.makedirs(output_dir, exist_ok=True)
                
                content_json_path = os.path.join(output_dir, 'content.json')
                with open(content_json_path, 'w', encoding='utf-8') as f:
                    json.dump(content_json, f, ensure_ascii=False, indent=2)
                
                images_dir = os.path.join(output_dir, 'images_good')
                os.makedirs(images_dir, exist_ok=True)
                
                video_script = SKILL_DIRS['wechat-video-generator'] / 'run_video_generator.py'
                if not video_script.exists():
                    self.send_json({'success': False, 'error': '视频生成脚本未找到'}, 404)
                    return
                
                safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in content_json.get('main_title', 'video')).strip().replace(' ', '_')[:30]
                video_path = os.path.join(output_dir, f'{safe_title}.mp4')
                
                result = subprocess.run(
                    [sys.executable, str(video_script), content_json_path, '-o', video_path, '-i', images_dir],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(video_script.parent)
                )
                
                if result.returncode == 0:
                    self.send_json({'success': True, 'path': video_path})
                else:
                    self.send_json({'success': False, 'error': result.stderr[:500]})
            
            except subprocess.TimeoutExpired:
                self.send_json({'success': False, 'error': '视频生成超时'}, 504)
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
                
                pipeline_script = BASE_DIR / 'wechat-media-publish-pipeline' / 'scripts' / 'run_pipeline.py'
                if not pipeline_script.exists():
                    self.send_json({'success': False, 'error': 'pipeline 脚本未找到'}, 404)
                    return
                
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in topic).strip().replace(' ', '_')
                output_dir = os.path.join(config.get('default_output_dir', str(BASE_DIR / 'output')), f"{timestamp}_{safe_topic}")
                os.makedirs(output_dir, exist_ok=True)
                
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
        
        else:
            self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)


def run_server(port=8080):
    server = http.server.HTTPServer(('localhost', port), Handler)
    print(f"\n🎯 创作方舟服务已启动")
    print(f"   访问地址: http://localhost:{port}")
    print(f"   按 Ctrl+C 停止服务\n")
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='创作方舟 - 自媒体创作平台后端服务')
    parser.add_argument('-p', '--port', type=int, default=8080, help='服务端口 (默认: 8080)')
    args = parser.parse_args()
    run_server(args.port)