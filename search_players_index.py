import json

with open("all_players_next_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Searching all_players_next_data.json...")

# Function to search recursively
def find_punter(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if isinstance(v, str) and ("Punter" in v or "P009862" in v):
                print(f"MATCH: {new_path} -> {v}")
                # Print siblings if possible
                print(f"CONTEXT: {obj}")
            
            if k == "players": # Likely a list of players
                print(f"Found 'players' key with {len(v)} items")
            
            find_punter(v, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_punter(item, f"{path}[{i}]")

find_punter(data)
