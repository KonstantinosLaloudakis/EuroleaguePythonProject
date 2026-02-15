import requests

player_id = "P002100" # Nando De Colo
# Potential URL patterns
urls = [
    f"https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/{player_id}.jpg",
    f"https://media-cdn.euroleague.net/raw/upload/f_auto,q_auto/v1/media/players/euroleague/{player_id}.jpg",
    f"https://www.euroleaguebasketball.net/euroleague/players/-/P{player_id}"
]

for url in urls:
    try:
        response = requests.get(url, timeout=5)
        print(f"URL: {url} -> Status: {response.status_code}")
        if response.status_code == 200:
            print("Found valid image URL!")
            # Check content type
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            break
    except Exception as e:
        print(f"Error fetching {url}: {e}")
