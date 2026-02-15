import json

with open("next_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Inspecting props.pageProps.data...")
try:
    page_data = data['props']['pageProps']['data']
    print("Keys in page_data:", page_data.keys())
    
    # Check if there is a 'player' key or similar
    if 'player' in page_data:
        print("Found 'player' key!")
        player = page_data['player']
        print("Player Keys:", player.keys())
        # print specific fields
        for k in ['image', 'headshot', 'photo', 'url', 'avatar']:
            if k in player:
                print(f"Player {k}: {player[k]}")
    else:
        # Search for the player ID P009862
        print("Searching for P009862 in page_data...")
        str_dump = json.dumps(page_data)
        if "P009862" in str_dump:
            print("Found P009862 in data!")
            # Find context
            idx = str_dump.find("P009862")
            start = max(0, idx - 100)
            end = min(len(str_dump), idx + 100)
            print(f"Context: ...{str_dump[start:end]}...")
        else:
            print("P009862 NOT found in data.")

except KeyError as e:
    print(f"Key error: {e}")
except Exception as e:
    print(f"Error: {e}")
