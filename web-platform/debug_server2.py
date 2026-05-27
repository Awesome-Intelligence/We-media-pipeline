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
}

def load_config():
    config_path = BASE_DIR / 'wechat-media-publish-pipeline' / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}", flush=True)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/':
            index_path = Path(__file__).parent / 'index.html'
            if index_path.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'index.html not found')
        
        elif parsed.path == '/api/config':
            config = load_config()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({'success': True, 'config': config})
            self.wfile.write(response.encode())
        
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        print(f"[POST] Path: {self.path}", flush=True)
        
        content_length = int(self.headers.get('Content-Length', 0))
        print(f"[POST] Content-Length: {content_length}", flush=True)
        
        body = self.rfile.read(content_length).decode('utf-8')
        print(f"[POST] Body length: {len(body)}", flush=True)
        print(f"[POST] Body: {body[:100]}", flush=True)
        
        parsed = urlparse(self.path)
        print(f"[POST] Parsed path: {parsed.path}", flush=True)
        
        if parsed.path == '/api/news/search':
            try:
                data = json.loads(body)
                print(f"[POST] Parsed data: {data}", flush=True)
                
                query = data.get('query', '')
                days = int(data.get('days', 7))
                num = int(data.get('num', 10))
                
                print(f"[POST] query={query}, days={days}, num={num}", flush=True)
                
                config = load_config()
                api_key = config.get('tavily_api_key', '')
                print(f"[POST] API key length: {len(api_key)}", flush=True)
                
                news_script = SKILL_DIRS['news-search'] / 'search_news.py'
                print(f"[POST] Script: {news_script}", flush=True)
                
                result = subprocess.run(
                    [sys.executable, str(news_script), query, '-n', str(num), '-d', str(days), '-k', api_key, '-f', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(news_script.parent)
                )
                
                print(f"[POST] Subprocess RC: {result.returncode}", flush=True)
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    print(f"[POST] Output length: {len(output)}", flush=True)
                    
                    start_idx = output.find('{')
                    print(f"[POST] JSON start index: {start_idx}", flush=True)
                    
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
                        print(f"[POST] Extracted JSON length: {len(json_str)}", flush=True)
                        print(f"[POST] JSON ends with: {repr(json_str[-20:])}", flush=True)
                        
                        results = json.loads(json_str)
                        print(f"[POST] Parsed JSON OK, results count: {len(results.get('results', []))}", flush=True)
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        response = json.dumps({'success': True, 'results': results})
                        self.wfile.write(response.encode())
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        response = json.dumps({'success': False, 'error': 'No JSON found'})
                        self.wfile.write(response.encode())
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = json.dumps({'success': False, 'error': result.stderr[:500]})
                    self.wfile.write(response.encode())
            
            except Exception as e:
                print(f"[POST] Error: {e}", flush=True)
                import traceback
                traceback.print_exc()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'success': False, 'error': str(e)})
                self.wfile.write(response.encode())

        else:
            self.send_response(404)
            self.end_headers()

port = 8082
server = http.server.HTTPServer(('localhost', port), Handler)
print(f"Debug server running on port {port}")
server.serve_forever()