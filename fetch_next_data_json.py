import json
import requests

# 1. Get buildId
try:
    with open("next_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        build_id = data.get("buildId")
        print(f"Found buildId: {build_id}")
except Exception as e:
    print(f"Error reading next_data.json: {e}")
    exit(1)

if not build_id:
    print("No buildId found!")
    exit(1)

# 2. Construct URL
# https://www.euroleaguebasketball.net/_next/data/{buildId}/euroleague/players/kevin-punter/P009862.json
url = f"https://www.euroleaguebasketball.net/_next/data/{build_id}/euroleague/players/kevin-punter/P009862.json"
print(f"Fetching URL: {url}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 3. Fetch
try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        player_json = response.json()
        with open("player_data.json", "w", encoding="utf-8") as f:
            json.dump(player_json, f, indent=4)
        print("Saved player_data.json")
    else:
        print(f"Failed to fetch: {response.status_code}")
except Exception as e:
    print(f"Error fetching: {e}")
