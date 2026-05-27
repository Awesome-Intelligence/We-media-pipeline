import subprocess
import sys

sys.path.insert(0, '..')
sys.path.insert(0, '../news-search/scripts')

import search_news

query = "test"
days = 7
num = 5
api_key = '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'

result = subprocess.run(
    [sys.executable, '../news-search/scripts/search_news.py', query, '-n', str(num), '-d', str(days), '-k', api_key, '-f', 'json'],
    capture_output=True,
    text=True,
    cwd='.'
)

print(f"Return code: {result.returncode}")
print(f"Stdout length: {len(result.stdout)}")
print(f"Stderr: {result.stderr[:200] if result.stderr else '(none)'}")

if result.returncode == 0:
    output = result.stdout.strip()
    print(f"Output after strip length: {len(output)}")
    print(f"Output starts: {output[:50]}")

    import json
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
        print(f"JSON string length: {len(json_str)}")

        try:
            results = json.loads(json_str)
            print("SUCCESS! Parsed JSON")
            print(f"Results count: {len(results.get('results', []))}")
        except Exception as e:
            print(f"FAILED: {e}")
            # Show what's after the JSON
            remaining = output[end_idx:]
            print(f"Remaining chars after JSON: {len(remaining)}")
            print(f"Remaining content: {repr(remaining[:200])}")