import json

with open("next_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Inspecting stats...")
try:
    stats = data['props']['pageProps']['data']['stats']
    print("Type of stats:", type(stats))
    if isinstance(stats, dict):
        print("Keys in stats:", len(stats.keys()))
        # Print first few keys
        print("First 10 keys:", list(stats.keys())[:10])
    elif isinstance(stats, list):
        print("Length of stats list:", len(stats))
        if len(stats) > 0:
            print("First item keys:", stats[0].keys())
except Exception as e:
    print(f"Error: {e}")
