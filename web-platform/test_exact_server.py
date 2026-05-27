import subprocess
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
news_script = BASE_DIR / 'news-search' / 'scripts' / 'search_news.py'

api_key = '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'

print("=" * 60)
print("Testing the EXACT same code as in server.py")
print("=" * 60)

query = 'test'
num = 3
days = 7

result = subprocess.run(
    [sys.executable, str(news_script), query, '-n', str(num), '-d', str(days), '-k', api_key, '-f', 'json'],
    capture_output=True,
    text=True,
    timeout=60,
    cwd=str(news_script.parent)
)

print(f"Return code: {result.returncode}")
print(f"Stdout length: {len(result.stdout)}")

if result.returncode == 0:
    output = result.stdout.strip()
    print(f"After strip length: {len(output)}")
    print(f"First 50 chars: {repr(output[:50])}")
    
    start_idx = output.find('{')
    print(f"start_idx = {start_idx}")
    
    if start_idx >= 0:
        json_str = output[start_idx:]
        print(f"json_str starts with: {repr(json_str[:30])}")
        print(f"json_str length: {len(json_str)}")
        
        bracket_count = 0
        end_idx = len(json_str)
        
        for i, c in enumerate(json_str):
            if c == '{':
                bracket_count += 1
            elif c == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    print(f"Found matching }} at position {i}")
                    break
        
        print(f"end_idx = {end_idx}")
        extracted = json_str[:end_idx]
        print(f"Extracted JSON length: {len(extracted)}")
        print(f"Extracted ends with: {repr(extracted[-20:])}")
        
        try:
            results = json.loads(extracted)
            print(f"SUCCESS! Results count: {len(results.get('results', []))}")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Find where the error is
            err_pos = e.pos
            if err_pos < len(extracted):
                print(f"Char at error position: {repr(extracted[err_pos-5:err_pos+5])}")
            # Try to see what's after the valid JSON
            remaining = extracted[err_pos:err_pos+100]
            print(f"Remaining after error: {repr(remaining)}")