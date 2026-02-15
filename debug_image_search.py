import requests

players = {
    "Kevin Punter": "P009862",
    "Kendrick Nunn": "P012774",
    "Nando De Colo": "P002100",
    "Mike James": "P002886"
}

base_patterns = [
    "https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/{season}/{pid}.jpg",
    "https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/{season}/{pid}.png",
    "https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/{pid}.jpg"
]

seasons = [2024, 2023, 2022, 2021, 2020]

print("Testing Image URLs...")

for name, pid in players.items():
    print(f"\n--- {name} ({pid}) ---")
    found = False
    for season in seasons:
        for pattern in base_patterns:
            if "{season}" in pattern:
                url = pattern.format(season=season, pid=pid)
            else:
                 url = pattern.format(pid=pid)
            
            try:
                r = requests.head(url, timeout=1)
                if r.status_code == 200:
                    print(f"[SUCCESS] {url}")
                    found = True
                    break
                else:
                    pass
                    # print(f"[FAIL] {url} ({r.status_code})")
            except Exception as e:
                print(f"Error: {e}")
        if found: break
    
    if not found:
        print("No image found.")
