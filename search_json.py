import json

with open("player_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Searching player_data.json...")
with open("player_json_search_results.txt", "w") as f_out:
    def search(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if "image" in k.lower() or "headshot" in k.lower() or "photo" in k.lower():
                    f_out.write(f"Key match: {new_path} -> {v}\n")
                if isinstance(v, str) and ("http" in v or "media-cdn" in v):
                    # Print only if it looks like an image
                    if any(ext in v.lower() for ext in ['.jpg', '.png', '.svg', 'webp']):
                         f_out.write(f"Value match: {new_path} -> {v}\n")
                
                search(v, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search(item, f"{path}[{i}]")
    search(data)
