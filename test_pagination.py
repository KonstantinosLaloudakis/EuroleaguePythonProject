import json
import requests
import time

build_id = "3FbTKPX1FVq8Hzvg5Xr7P"
base_url = f"https://www.euroleaguebasketball.net/_next/data/{build_id}/en/euroleague/players.json"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def test_param(params):
    print(f"Testing params: {params}")
    try:
        response = requests.get(base_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            # Extract players
            def get_players(obj):
                if isinstance(obj, dict):
                    if "players" in obj and isinstance(obj["players"], list):
                        return obj["players"]
                    for k, v in obj.items():
                        res = get_players(v)
                        if res: return res
                return None
            
            players = get_players(data)
            if players:
                print(f"  Returned {len(players)} players.")
                first = players[0]
                print(f"  First: {first.get('name')} {first.get('lastName')} (ID: {first.get('id')})")
            else:
                print("  No players returned.")
        else:
            print(f"  Failed: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(1)

# Test various params
test_param({"page": 2})
test_param({"letter": "P"})
test_param({"search": "Punter"})
test_param({"q": "Punter"})
