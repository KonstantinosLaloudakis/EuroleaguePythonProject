import json
import requests

build_id = "3FbTKPX1FVq8Hzvg5Xr7P"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Strategy 1: Fetch player JSON without P
url1 = f"https://www.euroleaguebasketball.net/_next/data/{build_id}/en/euroleague/players/kevin-punter/009862.json"
print(f"Strategy 1: {url1}")
try:
    res1 = requests.get(url1, headers=headers)
    print(f"Status: {res1.status_code}")
    if res1.status_code == 200:
        print("Success! Saving to strategy1.json")
        with open("strategy1.json", "w", encoding="utf-8") as f:
            json.dump(res1.json(), f, indent=4)
except Exception as e:
    print(f"Error: {e}")

# Strategy 2: HTML Search
url2 = "https://www.euroleaguebasketball.net/euroleague/players/?search=Kevin%20Punter"
print(f"\nStrategy 2: {url2}")
try:
    res2 = requests.get(url2, headers=headers)
    print(f"Status: {res2.status_code}")
    if "Punter" in res2.text:
       print("Found 'Punter' in HTML")
       with open("strategy2.html", "w", encoding="utf-8") as f:
           f.write(res2.text)
    else:
       print("'Punter' NOT found in HTML")
except Exception as e:
    print(f"Error: {e}")

# Strategy 3: Try to find a 'search' API endpoint in the next JS build manifest?
# Maybe search is client side algolia?
# Let's check for 'algolia' in strategy2.html or next_data.json
