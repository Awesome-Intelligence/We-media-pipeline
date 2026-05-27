#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path
import http.server
import threading

BASE_DIR = Path(__file__).parent.parent.resolve()
SKILL_DIRS = {
    'news-search': BASE_DIR / 'news-search' / 'scripts',
}

def load_config():
    config_path = BASE_DIR / 'wechat-media-publish-pipeline' / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/news/search':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            query = data.get('query', '')
            days = int(data.get('days', 7))
            num = int(data.get('num', 10))
            
            config = load_config()
            api_key = config.get('tavily_api_key', '')
            
            news_script = SKILL_DIRS['news-search'] / 'search_news.py'
            
            result = subprocess.run(
                ['python', str(news_script), query, '-n', str(num), '-d', str(days), '-k', api_key, '-f', 'json'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(news_script.parent)
            )
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
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
                    print(f"DEBUG: JSON extracted length = {len(json_str)}", flush=True)
                    print(f"DEBUG: JSON ends with = {repr(json_str[-10:])}", flush=True)
                    
                    try:
                        results = json.loads(json_str)
                        response = json.dumps({'success': True, 'results': results})
                        self.wfile.write(response.encode())
                    except Exception as e:
                        print(f"DEBUG: JSON parse error = {e}", flush=True)
                        response = json.dumps({'success': False, 'error': str(e)})
                        self.wfile.write(response.encode())
                else:
                    response = json.dumps({'success': False, 'error': 'No JSON found'})
                    self.wfile.write(response.encode())
            else:
                response = json.dumps({'success': False, 'error': result.stderr[:500]})
                self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

print("Testing server logic directly...")
print("=" * 50)

config = load_config()
api_key = config.get('tavily_api_key', '')
print(f"API Key: {api_key[:20]}...")

news_script = SKILL_DIRS['news-search'] / 'search_news.py'
print(f"Script: {news_script}")

query = 'test'
num = 3
days = 7

result = subprocess.run(
    ['python', str(news_script), query, '-n', str(num), '-d', str(days), '-k', api_key, '-f', 'json'],
    capture_output=True,
    text=True,
    timeout=60,
    cwd=str(news_script.parent)
)

print(f"RC: {result.returncode}")

if result.returncode == 0:
    output = result.stdout.strip()
    start_idx = output.find('{')
    print(f"Start index: {start_idx}")
    
    if start_idx >= 0:
        json_str = output[start_idx:]
        bracket_count = 0
        end_idx = len(json_str)
        
        print(f"Total output length: {len(output)}")
        print(f"JSON string initial length: {len(json_str)}")
        
        for i, c in enumerate(json_str):
            if c == '{':
                bracket_count += 1
            elif c == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    print(f"Found end at position {i}, char = {repr(c)}")
                    break
        
        print(f"Final end_idx: {end_idx}")
        json_str = json_str[:end_idx]
        print(f"Final JSON length: {len(json_str)}")
        print(f"Final JSON ends with: {repr(json_str[-10:])}")
        
        try:
            results = json.loads(json_str)
            print(f"SUCCESS! Results: {len(results.get('results', []))}")
        except Exception as e:
            print(f"FAILED: {e}")
else:
    print(f"FAILED: {result.stderr[:200]}")