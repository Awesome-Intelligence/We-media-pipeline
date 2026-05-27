import requests

# Test images search
print("Testing images search...")
r = requests.post("http://localhost:8083/api/images/search", json={"query": "微软", "num": 6})
data = r.json()
print("Success:", data.get("success"))
if not data.get("success"):
    print("Error:", data.get("error"))
else:
    images = data.get("images", [])
    print(f"Images count: {len(images)}")