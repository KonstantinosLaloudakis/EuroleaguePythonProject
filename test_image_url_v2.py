import requests
from euroleague_api import player_stats

# Try to find image URL in player stats
try:
    print("Fetching Player Stats for 2024...")
    # Assuming standard function name
    # methods: get_player_stats, get_game_player_stats?
    # Let's try to list methods first if we don't know
    # But for now, let's assume get_player_stats works
    # Or just use the URL brute force
    pass
except:
    pass

# Known IDs
# Mike James: P002886 ? No, that's a guess.
# Sloukas: P001920? 
# Let's use Nando De Colo: P002100 (Found in traffic_warden.json)

p_id = "P002100" 

patterns = [
    f"https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/2023/{p_id}.jpg",
    f"https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/2024/{p_id}.jpg",
    f"https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/2022/{p_id}.png",
    f"https://www.euroleaguebasketball.net/euroleague/players/nando-de-colo/{p_id}/" # might contain image in og:image
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

for url in patterns:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"{url} -> {r.status_code}")
        if r.status_code == 200:
            if "image" in r.headers.get("Content-Type", ""):
                 print("SUCCESS! Found image.")
            else:
                 print("200 OK but likely HTML")
    except Exception as e:
        print(f"Error: {e}")
