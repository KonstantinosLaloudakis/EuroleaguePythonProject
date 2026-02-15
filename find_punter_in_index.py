import json

with open("all_players_next_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Helper to find key
def find_players_list(obj):
    if isinstance(obj, dict):
        if "players" in obj and isinstance(obj["players"], list):
            return obj["players"]
        for k, v in obj.items():
            res = find_players_list(v)
            if res: return res
    return None

players = find_players_list(data)

if players:
    print(f"Found {len(players)} players.")
    found = False
    for p in players:
        if "Punter" in p.get("lastName", "") or "Punter" in p.get("firstName", ""):
            print("FOUND PUNTER!")
            print(json.dumps(p, indent=2))
            found = True
            break
    
    if not found:
        print("Kevin Punter NOT found in the list.")
        # Print a few others to check IDs
        print("Sample IDs:", [p.get("id") for p in players[:5]])

else:
    print("Could not find players list.")
