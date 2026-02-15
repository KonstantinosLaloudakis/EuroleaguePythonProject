import json

with open("all_players_next_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Inspecting players list...")
try:
    # Based on previous output, we need to find where 'players' key is
    # It's likely in props.pageProps.players or similar
    
    # Helper to find key
    def find_key(obj, target):
        if isinstance(obj, dict):
            if target in obj:
                return obj[target]
            for k, v in obj.items():
                res = find_key(v, target)
                if res: return res
        return None

    players_list = find_key(data, "players")
    
    if players_list and isinstance(players_list, list):
        print(f"Found players list with {len(players_list)} items.")
        with open("players_list_inspection.txt", "w", encoding="utf-8") as f_out:
            if len(players_list) > 0:
                first_player = players_list[0]
                f_out.write(f"First Player Keys: {first_player.keys()}\n")
                f_out.write(f"First Player Data: {json.dumps(first_player, indent=2)}\n")
                
                # Check for images in the first few
                for i, p in enumerate(players_list[:20]):
                     f_out.write(f"Player {i}: {p.get('name', 'Unknown')} - {p.get('images', 'No Images')}\n")
                     # Also print all keys to see if there is a 'headshot' or something
                     f_out.write(f"Keys: {p.keys()}\n")
    else:
        print("Could not find players list or it's not a list.")

except Exception as e:
    print(f"Error: {e}")
