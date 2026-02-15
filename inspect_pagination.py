import json

with open("all_players_next_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Inspecting pagination...")
try:
    # Find where the players list was found (we know it exists)
    # Print siblings of the players list
    
    def find_pagination(obj):
        if isinstance(obj, dict):
            if "players" in obj and isinstance(obj["players"], list):
                print("Found 'players' key container.")
                print("Keys in container:", obj.keys())
                for k, v in obj.items():
                    if k != "players" and not isinstance(v, (dict, list)):
                        print(f"  {k}: {v}")
                return
            for k, v in obj.items():
                find_pagination(v)

    find_pagination(data)

except Exception as e:
    print(f"Error: {e}")
