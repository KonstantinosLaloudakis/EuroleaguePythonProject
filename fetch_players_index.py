import json
import requests

# 1. Get buildId from next_data.json (which we saved earlier)
# If it's old, we might need to re-fetch, but let's try the one we have first/
try:
    with open("next_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        build_id = data.get("buildId")
        print(f"Using buildId: {build_id}")
except Exception as e:
    print(f"Error reading next_data.json: {e}")
    # Fallback to the one user provided if file fails, though file should exist
    build_id = "3FbTKPX1FVq8Hzvg5Xr7P" 

if not build_id:
    build_id = "3FbTKPX1FVq8Hzvg5Xr7P"

# 2. Construct URL
# https://www.euroleaguebasketball.net/_next/data/{build_id}/en/euroleague/players.json
url = f"https://www.euroleaguebasketball.net/_next/data/{build_id}/en/euroleague/players.json"
print(f"Fetching URL: {url}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 3. Fetch
try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        players_json = response.json()
        with open("all_players_next_data.json", "w", encoding="utf-8") as f:
            json.dump(players_json, f, indent=4)
        print("Saved all_players_next_data.json")
        
        # Quick check for Punter or Image URLs
        str_dump = json.dumps(players_json)
        print(f"Size of JSON: {len(str_dump)} bytes")
        if "P009862" in str_dump:
            print("Found P009862 (Punter) in index!")
        if "media-cdn" in str_dump:
            print("Found media-cdn links in index!")
            
    else:
        print(f"Failed to fetch: {response.status_code}")
except Exception as e:
    print(f"Error fetching: {e}")
