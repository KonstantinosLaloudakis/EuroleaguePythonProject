import requests

url = "https://www.euroleaguebasketball.net/euroleague/players/kevin-punter/P009862/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        with open("profile.html", "w", encoding='utf-8') as f:
            f.write(r.text)
        print("Saved profile.html")
    else:
        print("Failed to fetch.")
        
except Exception as e:
    print(f"Error: {e}")
